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

## Notlar

- Windows kullanıyorsanız ve emoji hataları (`UnicodeEncodeError`) alıyorsanız komutu şöyle çalıştırın:
  ```powershell
  $env:PYTHONIOENCODING="utf-8"
  python oracle_auto_create.py
  ```
- Script çalıştığında her adımı ekrana ve aynı zamanda `stok_log.txt` dosyasına kaydeder.
