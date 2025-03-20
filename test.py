import requests
from bs4 import BeautifulSoup

# 🌟 Kullanıcı bilgilerini tarayıcı gibi göstermek için sahte User-Agent
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
}

# 🌟 Tarayıcıdan alınan çerezler (Gerekiyorsa güncelle)
COOKIES = {
    # "cookie_name": "cookie_value"  # Çerez kullanmıyorsan bunu boş bırak
}

# 🌟 Proxy kullanmıyorsan burayı tamamen kaldır
# PROXIES = {
#     "http": "http://your_proxy:port",
#     "https": "https://your_proxy:port"
# }

# 🌟 Web sayfasını kazıyan fonksiyon
def scrape_and_save(url, filename):
    session = requests.Session()
    session.headers.update(HEADERS)  # Headers güncelle
    session.cookies.update(COOKIES)  # Çerezleri ekle (varsa)

    try:
        # Eğer proxy kullanmıyorsan bu satırda 'proxies=PROXIES' KALDIRILDI!
        response = session.get(url)  

        if response.status_code == 403:
            print("🚫 403 Hatası: Erişim engellendi. Tarayıcı bilgilerini güncelleyerek tekrar dene!")
            return
        elif response.status_code != 200:
            print(f"⚠️ Hata: Sayfa {response.status_code} ile yanıt verdi.")
            return

        soup = BeautifulSoup(response.text, 'html.parser')

        # 🏆 Sayfa başlığı (H1)
        title = soup.find('h1').text.strip() if soup.find('h1') else "Başlık bulunamadı"

        # 📜 Temel içerik (p, a, ul, ol, li)
        content_tags = soup.find_all(['p', 'a', 'ul', 'ol', 'li'])
        content = "\n".join(tag.get_text(strip=True) for tag in content_tags)

        # 🖼️ Medya içerikleri (img kaynakları)
        media = [img['src'] for img in soup.find_all('img') if 'src' in img.attrs]

        # 💾 Verileri dosyaya kaydetme
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(f"Başlık: {title}\n\n")
            file.write("İçerik:\n")
            file.write(content + "\n\n")
            file.write("Medya:\n")
            for src in media:
                file.write(src + "\n")

        print(f"✅ Veriler '{filename}' dosyasına başarıyla kaydedildi!")

    except requests.exceptions.RequestException as e:
        print(f"⛔ İstek hatası: {e}")

# 🌍 Kullanılacak URL ve dosya adı
URL = "https://www.ellindecoratie.nl/boomstam-bijzettafeltje"
FILENAME = "ellindecoratie_verileri.txt"

# 🚀 Web sitesini kazı ve verileri dosyaya kaydet
scrape_and_save(URL, FILENAME)
