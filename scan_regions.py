"""Tenancy'nin abone olduğu tüm bölgelerde A1 kapasitesini raporlar.

Instance oluşturmaz; yalnızca `CreateComputeCapacityReport` çağırır. Amaç,
home region dışında kapasite boşluğu olup olmadığını görmek (Always Free
yalnızca home region'da geçerlidir, diğer bölgeler ücretli olur).
"""

import logging
import sys

import oci

from oracle_auto_create import (
    SHAPE,
    available_shape_configs,
    build_config,
    getenv_str,
    resolve_shape_ladder,
)

log = logging.getLogger("bolge-tarama")


def subscribed_regions(config):
    identity = oci.identity.IdentityClient(config)
    subscriptions = identity.list_region_subscriptions(config["tenancy"]).data
    return [(s.region_name, s.is_home_region) for s in subscriptions]


def main():
    config = build_config()
    compartment_id = getenv_str("OCI_COMPARTMENT_OCID")
    if compartment_id is None:
        log.error("OCI_COMPARTMENT_OCID gerekli.")
        return 1
    ladder = resolve_shape_ladder()

    log.info(
        "Shape: %s, sorgulanan konfigürasyonlar: %s",
        SHAPE,
        ", ".join(f"{int(o)}c/{int(m)}g" for o, m in ladder),
    )

    found = False
    for region, is_home in subscribed_regions(config):
        region_config = dict(config, region=region)
        label = f"{region}{' (home)' if is_home else ''}"
        try:
            identity = oci.identity.IdentityClient(region_config)
            domains = identity.list_availability_domains(
                compartment_id=config["tenancy"]
            ).data
            compute = oci.core.ComputeClient(region_config)
        except oci.exceptions.ServiceError as exc:
            log.warning("%s: bölgeye erişilemedi (%s)", label, exc.code)
            continue

        for domain in domains:
            try:
                available = available_shape_configs(
                    compute, compartment_id, domain.name, ladder
                )
            except oci.exceptions.ServiceError as exc:
                log.warning(
                    "%s / %s: rapor alınamadı (%s / %s)",
                    label,
                    domain.name,
                    exc.status,
                    exc.code,
                )
                continue

            if available:
                found = True
                log.info(
                    "UYGUN → %s / %s: %s",
                    label,
                    domain.name,
                    ", ".join(f"{int(o)}c/{int(m)}g" for o, m in available),
                )
            else:
                log.info("dolu    %s / %s", label, domain.name)

    if not found:
        log.info("Abone olunan hiçbir bölgede kapasite raporlanmadı.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
