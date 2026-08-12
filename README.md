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
- `AD_SLEEP_SECONDS`, `CYCLE_SLEEP_SECONDS`: AD'ler arası ve turlar arası bekleme.
- `MAX_CYCLES`: Tur sınırı; `0` sınırsız demektir.

## GitHub Actions ile çalıştırma

`.github/workflows/oracle-bot.yml` her 6 saatte bir (ve manuel olarak) botu çalıştırır.

Gerekli repository **secret**'ları: `OCI_USER_OCID`, `OCI_FINGERPRINT`, `OCI_TENANCY_OCID`, `OCI_COMPARTMENT_OCID`, `OCI_IMAGE_ID`, `OCI_SUBNET_ID`, `SSH_PUBLIC_KEY`, `OCI_KEY_FILE_BASE64` (PEM dosyasının base64 hâli: `base64 -w 0 key.pem`).

Gizli olmayan ayarlar repository **variables** olarak verilir: `OCI_REGION`, `OCI_AVAILABILITY_DOMAINS`, `OCI_OCPUS`, `OCI_MEMORY_IN_GBS`.

Notlar:

- Workflow'da `concurrency` grubu vardır; zamanlanmış ve manuel koşular aynı anda çalışıp iki sunucu açmaz. Script de başlangıçta aynı shape'te mevcut bir instance olup olmadığını kontrol eder, varsa hiç deneme yapmadan çıkar.
- `stok_log.txt` her koşunun sonunda artifact olarak yüklenir (14 gün).
- GitHub, 60 gün boyunca commit atılmayan repolarda zamanlanmış workflow'ları devre dışı bırakır; botun çalışmaya devam etmesi için repoyu ara ara güncellemeniz gerekir.

### SSH anahtarı üretme workflow'u

`generate-ssh-keys.yml` anahtar çifti üretir. Private key **artifact olarak yüklenmez**; yalnızca `secrets: write` yetkili bir fine-grained PAT'i `GH_PAT` secret'i olarak eklediyseniz `ORACLE_SSH_PRIVATE_KEY_BASE64` secret'ine yazılır. Varsayılan `GITHUB_TOKEN` secret yazamaz. Genelde en güvenlisi anahtarı lokalde `ssh-keygen` ile üretmektir.

## Notlar

- Script'in çıkış kodları: `0` başarılı (veya zaten instance var), `1` konfigürasyon/yetki hatası, `2` `MAX_CYCLES` doldu.
- Script çalıştığında her adımı ekrana ve aynı zamanda `stok_log.txt` dosyasına (ekleyerek) kaydeder.
- Kapasite dışındaki hatalar (yetkisiz erişim, geçersiz image/subnet, limit aşımı) sonsuz döngüye girmek yerine script'i hatayla sonlandırır. `429 TooManyRequests` durumunda bekleme süresi kademeli olarak artırılır.
