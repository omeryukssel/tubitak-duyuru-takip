# TÜBİTAK Duyuru Takip Botu

`https://tubitak.gov.tr/tr/duyuru` sayfasındaki duyuruları takip eder, yeni bir duyuru
yayınlandığında Telegram üzerinden bildirim gönderir. Periyodik çalıştırmak için
cron (Linux/macOS), Görev Zamanlayıcı (Windows) veya bilgisayarınız kapalıyken bile
çalışması için GitHub Actions ile kullanılması amaçlanmıştır (bkz. "Periyodik
çalıştırma" bölümü).

## Nasıl çalışır?

1. Duyuru sayfasını çeker, `/tr/duyuru/{slug}` formatındaki tüm bağlantıları ayrıştırır.
2. Aynı duyuruya ait birden fazla bağlantı varsa ("Devamını oku" dahil), en anlamlı
   (en uzun) başlık metnini saklar; tüm bağlantılar URL bazında tekilleştirilir.
3. Daha önce görülen duyuruları `gorulen_duyurular.json` dosyasında tutar.
4. Bu dosyada olmayan her URL "yeni duyuru" sayılır → Telegram'a bildirim gönderilir,
   ardından dosyaya eklenir.
5. **İlk çalıştırmada** (dosya yoksa) mevcut tüm duyurular "görülmüş" olarak kaydedilir
   ama hiçbir bildirim gönderilmez. Yoksa ilk çalıştırmada onlarca bildirim birden gelir.

## Kurulum

### 1. Bağımlılıkları kurun

```bash
pip install requests beautifulsoup4
```

### 2. Telegram botu oluşturun (BotFather)

1. Telegram'da [@BotFather](https://t.me/BotFather) ile sohbet açın.
2. `/newbot` komutunu gönderin, botunuza bir isim ve kullanıcı adı verin.
3. BotFather size bir **token** verecek, örneğin:
   `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   Bu değeri `TELEGRAM_BOT_TOKEN` olarak kullanacaksınız.

### 3. Chat ID'nizi bulun

1. Oluşturduğunuz bota Telegram'dan herhangi bir mesaj gönderin (örn. `/start`).
2. Aşağıdaki komutu çalıştırın:

   ```bash
   TELEGRAM_BOT_TOKEN="123456789:AA..." python3 tubitak_duyuru_bot.py --chatid
   ```

3. Ekrana yazdırılan `chat_id` değerini not edin. Bu değeri `TELEGRAM_CHAT_ID`
   olarak kullanacaksınız.

### 4. Ortam değişkenlerini ayarlayın

Windows (PowerShell):

```powershell
$env:TELEGRAM_BOT_TOKEN = "123456789:AA..."
$env:TELEGRAM_CHAT_ID = "987654321"
```

Linux/macOS (bash):

```bash
export TELEGRAM_BOT_TOKEN="123456789:AA..."
export TELEGRAM_CHAT_ID="987654321"
```

Kalıcı olması için bu değerleri `~/.bashrc`, `~/.profile` veya cron/Task Scheduler
görev tanımına ekleyin (aşağıya bakın).

### 5. Test mesajı gönderin

```bash
python3 tubitak_duyuru_bot.py --test
```

### 6. İlk çalıştırma

```bash
python3 tubitak_duyuru_bot.py
```

Bu ilk çalıştırma `gorulen_duyurular.json` dosyasını oluşturur ve **hiçbir bildirim
göndermez** — mevcut tüm duyurular sadece "görülmüş" olarak işaretlenir. Bir sonraki
çalıştırmadan itibaren yalnızca yeni düşen duyurular bildirilir.

## Kullanım (CLI)

```bash
python3 tubitak_duyuru_bot.py            # Normal çalışma: yeni duyuruları bildirir
python3 tubitak_duyuru_bot.py --chatid   # getUpdates ile chat_id'yi bulup yazdırır
python3 tubitak_duyuru_bot.py --test     # Telegram'a test mesajı gönderir
```

## Periyodik çalıştırma

Üç seçenek var: bilgisayarınız açıkken cron/Task Scheduler (basit ama bilgisayar
kapalıyken/uyurken çalışmaz), ya da bilgisayarınız kapalı olsa bile 7/24 çalışması
için **GitHub Actions** (ücretsiz, bulutta).

### GitHub Actions (bilgisayar kapalıyken bile çalışır, önerilen)

Repoda `.github/workflows/duyuru-takip.yml` dosyası hazır durumda; GitHub Actions'ın
zamanlanmış (`schedule`) tetikleyicisiyle her 20 dakikada bir bulutta çalışır ve
`gorulen_duyurular.json` state dosyasını her çalıştırmadan sonra otomatik olarak
depoya geri commit'ler.

1. GitHub'da bir repo oluşturun (public önerilir — Actions dakikası sınırsız
   ücretsizdir; kodda/state dosyasında hassas bilgi yoktur) ve bu klasörü push'layın:

   ```bash
   git init
   git add .
   git commit -m "TÜBİTAK duyuru botu"
   gh repo create <kullanici>/<repo-adi> --public --source=. --push
   ```

2. Repo ayarlarında **Settings → Secrets and variables → Actions → New repository
   secret** ile iki secret ekleyin (veya `gh` ile):

   ```bash
   gh secret set TELEGRAM_BOT_TOKEN --body "123456789:AA..."
   gh secret set TELEGRAM_CHAT_ID --body "987654321"
   ```

3. **Actions** sekmesinden workflow'u görüp elle bir kez tetikleyerek
   (`workflow_dispatch` / "Run workflow") test edebilirsiniz. Sonrasında otomatik
   olarak 20 dakikada bir çalışır.
4. Repo private ise aylık 2000 dakika ücretsiz Actions kotası vardır; 20 dakikalık
   aralık bu kotaya yakın/üzerinde kalabilir — gerekirse workflow dosyasındaki
   `cron: "*/20 * * * *"` satırını `*/30` veya `0 * * * *` (saatte bir) yaparak
   kullanımı azaltabilirsiniz. Public repolarda bu sınır yoktur.
5. GitHub Actions'ın `schedule` tetikleyicisi "en erken şu saatte" çalışır garantisi
   verir, yoğun saatlerde birkaç dakika gecikme olabilir — bu bir bildirim botu için
   sorun teşkil etmez.

### cron (Linux/macOS) — her 20 dakikada bir

```bash
crontab -e
```

Aşağıdaki satırı ekleyin (token/chat_id'yi kendi değerlerinizle değiştirin,
script'in tam yolunu kullanın):

```cron
*/20 * * * * TELEGRAM_BOT_TOKEN="123456789:AA..." TELEGRAM_CHAT_ID="987654321" /usr/bin/python3 /tam/yol/tubitak_duyuru_bot.py >> /tam/yol/duyuru_bot.log 2>&1
```

### Windows Görev Zamanlayıcı (Task Scheduler)

1. **Görev Zamanlayıcı**'yı açın → **Temel Görev Oluştur**.
2. Tetikleyici: **Günlük**, ardından tekrarlama aralığını 20 dakika olacak şekilde
   ayarlayın (Görevin özelliklerinden **Tetikleyiciler** sekmesinde "Görevi şu sıklıkla
   tekrarla: 20 dakika, süre: sınırsız" seçeneğini işaretleyin).
3. Eylem: **Program başlat**.
   - Program/script: `python` (veya `python.exe`'nin tam yolu)
   - Bağımsız değişken ekle: `tubitak_duyuru_bot.py`
   - Başlangıç konumu: script'in bulunduğu klasör
4. Ortam değişkenlerini kalıcı olarak ayarlamak için (sistem genelinde):

   ```powershell
   [System.Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", "123456789:AA...", "User")
   [System.Environment]::SetEnvironmentVariable("TELEGRAM_CHAT_ID", "987654321", "User")
   ```

   Bu komuttan sonra oturumu kapatıp açmanız veya bilgisayarı yeniden başlatmanız
   gerekebilir.

## Dosyalar

- `tubitak_duyuru_bot.py` — ana script.
- `gorulen_duyurular.json` — daha önce görülen duyuruların state dosyası (script ile
  aynı klasörde otomatik oluşturulur, elle düzenlemeyin).

## Notlar

- Sayfa yapısı değişir ve hiç duyuru bulunamazsa script bir uyarı verip hata koduyla
  (exit code 1) sonlanır; bildirim göndermeye çalışmaz.
- Bir duyuru için Telegram gönderimi başarısız olursa, o duyuru state dosyasına
  eklenmez ve bir sonraki çalıştırmada tekrar denenir; diğer duyuruların gönderimi
  bundan etkilenmez.
