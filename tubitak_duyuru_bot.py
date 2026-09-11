#!/usr/bin/env python3
"""TÜBİTAK duyuru takip botu.

https://tubitak.gov.tr/tr/duyuru sayfasındaki duyuruları takip eder,
yeni bir duyuru yayınlandığında Telegram üzerinden bildirim gönderir.
"""

import argparse
import html
import json
import os
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

# Windows konsolu/görev zamanlayıcı log dosyaları varsayılan olarak UTF-8 kullanmadığından
# Türkçe karakterler bozuk görünebilir; çıktıyı açıkça UTF-8'e zorla.
for _akis in (sys.stdout, sys.stderr):
    if hasattr(_akis, "reconfigure"):
        _akis.reconfigure(encoding="utf-8")

DUYURU_URL = "https://tubitak.gov.tr/tr/duyuru"
BASE_URL = "https://tubitak.gov.tr"
STATE_DOSYASI = Path(__file__).resolve().parent / "gorulen_duyurular.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

DEVAMINI_OKU = "devamını oku"


def normalize_url(url: str) -> str:
    """Relative URL'yi absolute yapar, fragment'ı atar, sondaki / karakterini temizler."""
    mutlak = urljoin(BASE_URL, url)
    parcalar = urlparse(mutlak)
    parcalar = parcalar._replace(fragment="")
    temiz = urlunparse(parcalar)
    if temiz.endswith("/"):
        temiz = temiz.rstrip("/")
    return temiz


def duyurulari_cek() -> dict:
    """/tr/duyuru sayfasını çeker ve {url: başlık} sözlüğü döndürür."""
    headers = {"User-Agent": USER_AGENT}
    yanit = requests.get(DUYURU_URL, headers=headers, timeout=30)
    yanit.raise_for_status()

    soup = BeautifulSoup(yanit.text, "html.parser")
    duyurular: dict[str, str] = {}

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "/duyuru/" not in href:
            continue

        url = normalize_url(href)
        parcalar = urlparse(url)
        if not parcalar.path.startswith("/tr/duyuru/"):
            continue

        metin = link.get_text(strip=True)
        if not metin or metin.lower() == DEVAMINI_OKU:
            continue

        mevcut = duyurular.get(url, "")
        if len(metin) > len(mevcut):
            duyurular[url] = metin

    return duyurular


def state_yukle() -> dict:
    if not STATE_DOSYASI.exists():
        return {}
    try:
        with open(STATE_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[UYARI] State dosyası okunamadı, sıfırdan başlanıyor: {e}", file=sys.stderr)
        return {}


def state_kaydet(state: dict) -> None:
    with open(STATE_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)


def telegram_config_oku() -> tuple[str, str]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token:
        print("[HATA] TELEGRAM_BOT_TOKEN ortam değişkeni tanımlı değil.", file=sys.stderr)
        sys.exit(1)
    return token, chat_id


def telegram_mesaj_gonder(token: str, chat_id: str, metin: str) -> bool:
    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    veri = {
        "chat_id": chat_id,
        "text": metin,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        yanit = requests.post(api_url, data=veri, timeout=30)
        if yanit.status_code != 200:
            print(f"[HATA] Telegram mesajı gönderilemedi (HTTP {yanit.status_code}): {yanit.text}", file=sys.stderr)
            return False
        return True
    except requests.RequestException as e:
        print(f"[HATA] Telegram mesajı gönderilirken ağ hatası: {e}", file=sys.stderr)
        return False


def komut_normal() -> None:
    token, chat_id = telegram_config_oku()
    if not chat_id:
        print("[HATA] TELEGRAM_CHAT_ID ortam değişkeni tanımlı değil.", file=sys.stderr)
        sys.exit(1)

    try:
        guncel_duyurular = duyurulari_cek()
    except requests.RequestException as e:
        print(f"[HATA] Duyuru sayfası çekilirken ağ hatası: {e}", file=sys.stderr)
        sys.exit(1)

    if not guncel_duyurular:
        print("[UYARI] Sayfada hiç duyuru bulunamadı. Site yapısı değişmiş olabilir.", file=sys.stderr)
        sys.exit(1)

    state = state_yukle()
    ilk_calisma = len(state) == 0

    yeni_duyurular = {
        url: baslik for url, baslik in guncel_duyurular.items() if url not in state
    }

    if ilk_calisma:
        print(f"[BILGI] İlk çalışma: {len(guncel_duyurular)} duyuru görüldü olarak kaydedildi, bildirim gönderilmedi.")
        state.update(guncel_duyurular)
        state_kaydet(state)
        return

    if not yeni_duyurular:
        print("[BILGI] Yeni duyuru yok.")
        state.update(guncel_duyurular)
        state_kaydet(state)
        return

    print(f"[BILGI] {len(yeni_duyurular)} yeni duyuru bulundu.")
    for url, baslik in yeni_duyurular.items():
        mesaj = f"<b>{html.escape(baslik)}</b>\n{html.escape(url)}"
        basarili = telegram_mesaj_gonder(token, chat_id, mesaj)
        if basarili:
            print(f"[BILGI] Bildirim gönderildi: {baslik}")
            state[url] = baslik
        else:
            print(f"[HATA] Bildirim gönderilemedi, sonraki çalışmada tekrar denenecek: {baslik}", file=sys.stderr)

    for url, baslik in guncel_duyurular.items():
        if url in state:
            state[url] = baslik

    state_kaydet(state)


def komut_test() -> None:
    token, chat_id = telegram_config_oku()
    if not chat_id:
        print("[HATA] TELEGRAM_CHAT_ID ortam değişkeni tanımlı değil.", file=sys.stderr)
        sys.exit(1)

    basarili = telegram_mesaj_gonder(token, chat_id, "✅ TÜBİTAK duyuru botu test mesajı.")
    if basarili:
        print("[BILGI] Test mesajı başarıyla gönderildi.")
    else:
        print("[HATA] Test mesajı gönderilemedi.", file=sys.stderr)
        sys.exit(1)


def komut_chatid() -> None:
    token, _ = telegram_config_oku()
    api_url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        yanit = requests.get(api_url, timeout=30)
        yanit.raise_for_status()
    except requests.RequestException as e:
        print(f"[HATA] getUpdates çağrısı başarısız: {e}", file=sys.stderr)
        sys.exit(1)

    veri = yanit.json()
    sonuclar = veri.get("result", [])
    if not sonuclar:
        print(
            "[UYARI] Hiç güncelleme bulunamadı. Önce Telegram'da botunuza bir mesaj "
            "(örn. /start) gönderin, sonra bu komutu tekrar çalıştırın."
        )
        return

    gorulen_chatler = {}
    for guncelleme in sonuclar:
        mesaj = guncelleme.get("message") or guncelleme.get("channel_post")
        if not mesaj:
            continue
        chat = mesaj.get("chat", {})
        chat_id = chat.get("id")
        if chat_id is None:
            continue
        ad = chat.get("username") or chat.get("first_name") or chat.get("title") or ""
        gorulen_chatler[chat_id] = ad

    if not gorulen_chatler:
        print("[UYARI] Hiç chat_id bulunamadı.")
        return

    print("Bulunan chat_id değerleri:")
    for chat_id, ad in gorulen_chatler.items():
        print(f"  {chat_id}  ({ad})")


def main() -> None:
    parser = argparse.ArgumentParser(description="TÜBİTAK duyuru takip botu")
    grup = parser.add_mutually_exclusive_group()
    grup.add_argument("--chatid", action="store_true", help="getUpdates ile chat_id'yi bulup yazdırır")
    grup.add_argument("--test", action="store_true", help="Telegram'a test mesajı gönderir")
    args = parser.parse_args()

    if args.chatid:
        komut_chatid()
    elif args.test:
        komut_test()
    else:
        komut_normal()


if __name__ == "__main__":
    main()
