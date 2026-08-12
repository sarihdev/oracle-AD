import logging
import os
import sys
import time

import oci
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = os.getenv("LOG_FILE", "stok_log.txt")

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
    ],
)
log = logging.getLogger("oracle-bot")

REQUIRED_VARS = [
    "OCI_USER_OCID",
    "OCI_FINGERPRINT",
    "OCI_KEY_FILE",
    "OCI_TENANCY_OCID",
    "OCI_COMPARTMENT_OCID",
    "OCI_IMAGE_ID",
    "OCI_SUBNET_ID",
    "SSH_PUBLIC_KEY",
]

# Kapasite yokluğunu belirten OCI hata kodları
CAPACITY_CODES = {"OutOfHostCapacity", "OutOfCapacity", "InternalError"}
# Tekrar denemenin anlamsız olduğu, konfigürasyon/yetki kaynaklı hata kodları
FATAL_CODES = {
    "NotAuthenticated",
    "NotAuthorized",
    "NotAuthorizedOrNotFound",
    "InvalidParameter",
    "LimitExceeded",
    "QuotaExceeded",
    "CannotParseRequest",
}

SHAPE = os.getenv("OCI_SHAPE", "VM.Standard.A1.Flex")
TARGET_STATES = {"PROVISIONING", "STARTING", "RUNNING", "STOPPING", "STOPPED"}


def getenv_str(name, default=None):
    """Boş string'i de eksik kabul ederek env değişkenini okur."""
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def build_config():
    missing = [name for name in REQUIRED_VARS if getenv_str(name) is None]
    if missing:
        log.error("Eksik ortam değişkenleri: %s", ", ".join(missing))
        log.error("`.env.example` dosyasını referans alarak tüm değerleri doldurun.")
        sys.exit(1)

    key_file = getenv_str("OCI_KEY_FILE")
    if not os.path.isfile(os.path.expanduser(key_file)):
        log.error("API key dosyası bulunamadı: %s", key_file)
        sys.exit(1)

    config = {
        "user": getenv_str("OCI_USER_OCID"),
        "fingerprint": getenv_str("OCI_FINGERPRINT"),
        "key_file": os.path.expanduser(key_file),
        "tenancy": getenv_str("OCI_TENANCY_OCID"),
        "region": getenv_str("OCI_REGION", "eu-frankfurt-1"),
    }
    try:
        oci.config.validate_config(config)
    except oci.exceptions.InvalidConfig as exc:
        log.error("Geçersiz OCI konfigürasyonu: %s", exc)
        sys.exit(1)
    return config


def resolve_availability_domains(config):
    """AD isimleri tenancy'ye özgü olduğu için runtime'da API'den çekilir."""
    override = getenv_str("OCI_AVAILABILITY_DOMAINS")
    if override:
        return [ad.strip() for ad in override.split(",") if ad.strip()]

    identity_client = oci.identity.IdentityClient(config)
    domains = identity_client.list_availability_domains(
        compartment_id=config["tenancy"]
    ).data
    return [domain.name for domain in domains]


def find_existing_instance(compute_client, compartment_id):
    """Aynı shape ile daha önce oluşturulmuş bir instance varsa döner (idempotency)."""
    instances = oci.pagination.list_call_get_all_results(
        compute_client.list_instances, compartment_id=compartment_id
    ).data
    for instance in instances:
        if instance.shape == SHAPE and instance.lifecycle_state in TARGET_STATES:
            return instance
    return None


def build_launch_details(compartment_id, availability_domain):
    shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
        ocpus=float(os.getenv("OCI_OCPUS", "4")),
        memory_in_gbs=float(os.getenv("OCI_MEMORY_IN_GBS", "24")),
    )
    boot_volume_size = getenv_str("OCI_BOOT_VOLUME_SIZE_IN_GBS")
    source_details = oci.core.models.InstanceSourceViaImageDetails(
        image_id=getenv_str("OCI_IMAGE_ID"),
        boot_volume_size_in_gbs=int(boot_volume_size) if boot_volume_size else None,
    )
    return oci.core.models.LaunchInstanceDetails(
        compartment_id=compartment_id,
        display_name=f"Ampere-Ubuntu-{availability_domain[-4:]}",
        availability_domain=availability_domain,
        shape=SHAPE,
        shape_config=shape_config,
        source_details=source_details,
        create_vnic_details=oci.core.models.CreateVnicDetails(
            assign_public_ip=True,
            subnet_id=getenv_str("OCI_SUBNET_ID"),
        ),
        metadata={"ssh_authorized_keys": getenv_str("SSH_PUBLIC_KEY")},
    )


def main():
    config = build_config()
    compartment_id = getenv_str("OCI_COMPARTMENT_OCID")
    cycle_sleep = int(os.getenv("CYCLE_SLEEP_SECONDS", "60"))
    ad_sleep = int(os.getenv("AD_SLEEP_SECONDS", "5"))
    max_cycles = int(os.getenv("MAX_CYCLES", "0"))  # 0 = sınırsız

    compute_client = oci.core.ComputeClient(config)

    try:
        availability_domains = resolve_availability_domains(config)
    except oci.exceptions.ServiceError as exc:
        log.error("Availability domain listesi alınamadı: %s", exc.message)
        return 1
    if not availability_domains:
        log.error("Hiç availability domain bulunamadı.")
        return 1

    try:
        existing = find_existing_instance(compute_client, compartment_id)
    except oci.exceptions.ServiceError as exc:
        log.error("Mevcut instance kontrolü başarısız: %s", exc.message)
        return 1
    if existing is not None:
        log.info(
            "Zaten bir %s instance mevcut (%s / %s). Yeni sunucu oluşturulmayacak.",
            SHAPE,
            existing.display_name,
            existing.lifecycle_state,
        )
        return 0

    log.info(
        "Stok takibi başladı. Shape: %s, AD sayısı: %d",
        SHAPE,
        len(availability_domains),
    )

    cycle = 0
    backoff = cycle_sleep
    while max_cycles == 0 or cycle < max_cycles:
        cycle += 1
        rate_limited = False

        for index, availability_domain in enumerate(availability_domains, start=1):
            log.info(
                "Tur #%d - AD %d/%d (%s) kontrol ediliyor...",
                cycle,
                index,
                len(availability_domains),
                availability_domain,
            )
            try:
                response = compute_client.launch_instance(
                    build_launch_details(compartment_id, availability_domain)
                )
            except oci.exceptions.ServiceError as exc:
                if exc.status == 429 or exc.code == "TooManyRequests":
                    log.warning("Rate limit (429). Backoff uygulanacak.")
                    rate_limited = True
                    break
                if exc.code in FATAL_CODES:
                    log.error(
                        "Düzeltilmesi gereken hata (%s / %s): %s",
                        exc.status,
                        exc.code,
                        exc.message,
                    )
                    return 1
                if exc.code in CAPACITY_CODES or "capacity" in exc.message.lower():
                    log.info("  └─ Kapasite yok (%s).", availability_domain)
                else:
                    log.warning(
                        "  └─ Beklenmeyen hata (%s / %s): %s",
                        exc.status,
                        exc.code,
                        exc.message,
                    )
            else:
                log.info("Sunucu oluşturuldu! Instance ID: %s", response.data.id)
                log.info("Bölge: %s", availability_domain)
                return 0

            time.sleep(ad_sleep)

        if rate_limited:
            backoff = min(backoff * 2, 900)
            log.info("Rate limit nedeniyle %d saniye bekleniyor...", backoff)
            time.sleep(backoff)
        else:
            backoff = cycle_sleep
            log.info("Tüm AD'ler dolu. %d saniye sonra tekrar denenecek.", cycle_sleep)
            time.sleep(cycle_sleep)

    log.info("MAX_CYCLES (%d) sınırına ulaşıldı, kapasite bulunamadı.", max_cycles)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.info("Kullanıcı tarafından durduruldu.")
        sys.exit(130)
