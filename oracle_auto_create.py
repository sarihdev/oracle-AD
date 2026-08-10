import oci
import time
import builtins
import os
from dotenv import load_dotenv

load_dotenv()

# Log dosyasını her başlangıçta temizle
with open("stok_log.txt", "w", encoding="utf-8") as f:
    f.write("")

def custom_print(*args, **kwargs):
    kwargs['flush'] = True
    builtins.print(*args, **kwargs)
    with open("stok_log.txt", "a", encoding="utf-8") as f:
        builtins.print(*args, **kwargs, file=f)

print = custom_print

# --- Oracle API Konfigürasyonu ---
config = {
    "user": os.getenv("OCI_USER_OCID"),
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "key_file": os.getenv("OCI_KEY_FILE"),
    "tenancy": os.getenv("OCI_TENANCY_OCID"),
    "region": os.getenv("OCI_REGION", "eu-frankfurt-1")
}

compartment_id = os.getenv("OCI_COMPARTMENT_OCID")

# Daha önce indirdiğiniz SSH Public Key (Açık Anahtar) metni
ssh_public_key = os.getenv("SSH_PUBLIC_KEY")

# Takip edilecek Availability Domain'ler
availability_domains = [
    "dEjo:EU-FRANKFURT-1-AD-1",
    "dEjo:EU-FRANKFURT-1-AD-2",
    "dEjo:EU-FRANKFURT-1-AD-3"
]

compute_client = oci.core.ComputeClient(config)

print("🚀 Stok takip scripti başlatıldı! 3 AD bölgesinde de kontrol yapılıyor...")

attempt = 1
success = False

while not success:
    for ad in availability_domains:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Deneme #{attempt} -> {ad} kontrol ediliyor...")
        
        instance_details = oci.core.models.LaunchInstanceDetails(
            compartment_id=compartment_id,
            display_name=f"Ampere-Ubuntu-24-{ad[-4:]}",
            availability_domain=ad,
            shape="VM.Standard.A1.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=4,
                memory_in_gbs=24
            ),
            # Canonical Ubuntu 24.04 Frankfurt Image OCID
            image_id=os.getenv("OCI_IMAGE_ID"),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                assign_public_ip=True,
                subnet_id=os.getenv("OCI_SUBNET_ID")
            ),
            metadata={
                "ssh_authorized_keys": ssh_public_key
            }
        )

        try:
            response = compute_client.launch_instance(instance_details)
            print("\n" + "="*50)
            print("🎉 TEBRİKLER! Sunucu başarıyla oluşturuldu!")
            print(f"Instance ID: {response.data.id}")
            print(f"Bölge: {ad}")
            print("="*50)
            success = True
            break
        except oci.exceptions.ServiceError as e:
            if e.status == 500 or "Out of host capacity" in e.message or "Out of capacity" in e.message:
                print(f"  └─ Kapasite yok ({ad}).")
            else:
                print(f"  └─ Hata: {e.message}")
        
        attempt += 1
        time.sleep(5) # AD'ler arası 5 saniye bekleme

    if not success:
        print("⏳ Tüm AD'ler dolu. 60 saniye sonra tekrar denecek...\n")
        time.sleep(60)