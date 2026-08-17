# Oracle Auto Create Script

Bu script, Oracle Cloud üzerinde belirli Availability Domain (AD) bölgelerinde kapasite açılmasını sürekli kontrol ederek istenilen sanal makineyi otomatik olarak oluşturur.

## Gereksinimler

- Python 3.8+
- Oracle Cloud hesabı ve API Anahtarları (PEM dosyası)

## Kurulum

1. Bilgisayarınıza Python kurun.
2. Proje dosyalarını indirin ve terminal/komut satırında proje klasörüne gidin.
3. Gerekli kütüphaneleri yüklemek için aşağıdaki komutu çalıştırın:
   ```bash
   pip install -r requirements.txt
   ```

## Ayarların Yapılması (.env)

Projenin içindeki özel OCID ve anahtar (PEM) dosyalarının konfigürasyonunu ayarlamak için:
1. `.env.example` dosyasının bir kopyasını alarak adını `.env` yapın.
2. İçerisindeki değişkenleri kendi Oracle Cloud bilgilerinize göre doldurun:
   - `OCI_USER_OCID`: Oracle Cloud profilinizdeki Kullanıcı OCID'si.
   - `OCI_FINGERPRINT`: API Key oluşturduğunuzda verilen Fingerprint.
   - `OCI_KEY_FILE`: API Key PEM dosyanızın TAM yolu (Örn: `C:\yol\dosya.pem` veya Linux'ta `/home/yol/dosya.pem`).
   - `OCI_TENANCY_OCID`: Tenancy OCID numaranız.
   - `OCI_REGION`: Hangi bölgede açmak istiyorsanız (Örn: `eu-frankfurt-1`).
   - `OCI_COMPARTMENT_OCID`: Oluşturacağınız sunucunun ait olacağı Compartment OCID numarası.
   - `SSH_PUBLIC_KEY`: Sunucuya SSH ile bağlanırken kullanacağınız Açık Anahtarınız.
   - `OCI_IMAGE_ID`: Kurmak istediğiniz işletim sistemi imajının OCID'si.
   - `OCI_SUBNET_ID`: Sunucunun kurulacağı ağın Subnet OCID'si.

## Kullanım

Tüm ayarları yaptıktan sonra scripti başlatmak için:
```bash
python oracle_auto_create.py
```

### Opsiyonel ayarlar

`.env.example` içindeki opsiyonel değişkenler:

- `OCI_AVAILABILITY_DOMAINS`: Virgülle ayrılmış AD listesi. Boş bırakılırsa AD'ler OCI API'sinden otomatik çekilir (tenancy'ye özgü `xxxx:EU-FRANKFURT-1-AD-1` önekini elle yazmak gerekmez).
- `OCI_SHAPE`, `OCI_OCPUS`, `OCI_MEMORY_IN_GBS`, `OCI_BOOT_VOLUME_SIZE_IN_GBS`: Donanım konfigürasyonu. Kapasite bulunamıyorsa daha küçük değerler (örn. 1 OCPU / 6 GB) şansı artırır.
- `OCI_SHAPE_LADDER`: Sırayla denenecek `ocpu/bellek` listesi, örn. `4/24,2/12,1/6`. Tam 4 OCPU / 24 GB'lık blok nadiren boşalır; küçük parçalar çok daha sık bulunur. Bir konfigürasyon hesabın kotasını aşarsa (`LimitExceeded`) o kademe listeden düşürülür ve daha küçükleri denenmeye devam edilir. Boş bırakılırsa yalnızca `OCI_OCPUS`/`OCI_MEMORY_IN_GBS` denenir.

  Kota: ücretsiz tenancy'lerde A1 için aylık 1.500 OCPU-saat + 9.000 GB-saat, yani kesintisiz **2 OCPU / 12 GB**; Pay As You Go tenancy'lerde 3.000 OCPU-saat + 18.000 GB-saat, yani kesintisiz **4 OCPU / 24 GB** ücretsizdir.
- `USE_CAPACITY_REPORT` (varsayılan `true`): Her AD için önce `CreateComputeCapacityReport` çağrılır ve yalnızca `AVAILABLE` raporlanan konfigürasyon için `LaunchInstance` denenir. Rapor alınamazsa (yetki yoksa) otomatik olarak körlemesine denemeye düşer.
- `BLIND_ATTEMPT_EVERY` (varsayılan `5`, `0` = kapalı): Kapasite raporu "kapasite yok" derken bile launch'ın başarılı olabildiği durumları kaçırmamak için her N. turda rapor atlanır ve konfigürasyonlar küçükten büyüğe doğrudan denenir.
- `AD_SLEEP_SECONDS`, `CYCLE_SLEEP_SECONDS`: AD'ler arası ve turlar arası bekleme.
- `MAX_CYCLES`: Tur sınırı; `0` sınırsız demektir.

## GitHub Actions ile çalıştırma

`.github/workflows/oracle-bot.yml` her 6 saatte bir (ve manuel olarak) botu çalıştırır.

Gerekli repository **secret**'ları: `OCI_USER_OCID`, `OCI_FINGERPRINT`, `OCI_TENANCY_OCID`, `OCI_COMPARTMENT_OCID`, `OCI_IMAGE_ID`, `OCI_SUBNET_ID`, `SSH_PUBLIC_KEY`, `OCI_KEY_FILE_BASE64` (PEM dosyasının base64 hâli: `base64 -w 0 key.pem`).

Gizli olmayan ayarlar repository **variables** olarak verilir: `OCI_REGION`, `OCI_AVAILABILITY_DOMAINS`, `OCI_OCPUS`, `OCI_MEMORY_IN_GBS`, `OCI_SHAPE_LADDER`, `USE_CAPACITY_REPORT`, `BLIND_ATTEMPT_EVERY`, `CYCLE_SLEEP_SECONDS`.

Manuel tetiklemede `max_cycles` girdisi verilebilir (`1` = tek tur; test için pratiktir).

Notlar:

- Actions dakikası: bot sürekli çalıştığı için private repoda aylık ücretsiz dakika kotası hızla tükenir (public repolarda Actions ücretsizdir). Kotayı uzatmak için `CYCLE_SLEEP_SECONDS`'ı artırmak yerine daha sık ama kısa koşular (örn. `MAX_CYCLES=3` ile 15 dakikada bir cron) tercih edilebilir.
- Workflow'da `concurrency` grubu vardır; zamanlanmış ve manuel koşular aynı anda çalışıp iki sunucu açmaz. Script de başlangıçta aynı shape'te mevcut bir instance olup olmadığını kontrol eder, varsa hiç deneme yapmadan çıkar.
- `stok_log.txt` her koşunun sonunda artifact olarak yüklenir (14 gün).
- GitHub, 60 gün boyunca commit atılmayan repolarda zamanlanmış workflow'ları devre dışı bırakır; botun çalışmaya devam etmesi için repoyu ara ara güncellemeniz gerekir.

### SSH anahtarı üretme workflow'u

`generate-ssh-keys.yml` anahtar çifti üretir. Private key **artifact olarak yüklenmez**; yalnızca `secrets: write` yetkili bir fine-grained PAT'i `GH_PAT` secret'i olarak eklediyseniz `ORACLE_SSH_PRIVATE_KEY_BASE64` secret'ine yazılır. Varsayılan `GITHUB_TOKEN` secret yazamaz. Genelde en güvenlisi anahtarı lokalde `ssh-keygen` ile üretmektir.

## Notlar

- Script'in çıkış kodları: `0` başarılı (veya zaten instance var), `1` konfigürasyon/yetki hatası, `2` `MAX_CYCLES` doldu.
- Script çalıştığında her adımı ekrana ve aynı zamanda `stok_log.txt` dosyasına (ekleyerek) kaydeder.
- Kapasite dışındaki hatalar (yetkisiz erişim, geçersiz image/subnet, limit aşımı) sonsuz döngüye girmek yerine script'i hatayla sonlandırır. `429 TooManyRequests` durumunda bekleme süresi kademeli olarak artırılır.
