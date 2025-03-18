import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin, urlparse

def download_page_and_images(url, text_filename="page_content.txt", images_folder="images"):
    # Görseller için klasör oluşturuluyor (eğer yoksa)
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)
    
    # Sayfanın HTML içeriğini çekiyoruz
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Sayfa Başlığı
        title_tag = soup.find('title')
        page_title = title_tag.text.strip() if title_tag else "Başlık bulunamadı"
        
        # 2. Meta Title
        meta_title_tag = soup.find('meta', attrs={'property': 'og:title'})
        if meta_title_tag and meta_title_tag.get('content'):
            meta_title = meta_title_tag['content'].strip()
        else:
            meta_title_tag = soup.find('meta', attrs={'name': 'title'})
            meta_title = meta_title_tag['content'].strip() if meta_title_tag and meta_title_tag.get('content') else page_title
        
        # 3. Meta Description
        meta_desc_tag = soup.find('meta', attrs={'name': 'description'})
        meta_description = meta_desc_tag['content'].strip() if meta_desc_tag and meta_desc_tag.get('content') else "Meta açıklama bulunamadı"
        
        # 4. Permalink (orijinal URL)
        permalink = url
        
        # 5. Görseller: Tüm <img> etiketlerinden src özniteliğini alıyoruz
        images = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                absolute_src = urljoin(url, src)
                images.append(absolute_src)
                
        # 6. Sayfa içeriği: Tüm metni alıyoruz
        content_text = soup.get_text(separator='\n').strip()
        
        # Metin verilerini dosyaya kaydetme
        with open(text_filename, "w", encoding="utf-8") as file:
            file.write("Page Title: " + page_title + "\n")
            file.write("Meta Title: " + meta_title + "\n")
            file.write("Meta Description: " + meta_description + "\n")
            file.write("Permalink: " + permalink + "\n")
            file.write("\n--- İçerik ---\n")
            file.write(content_text)
            
        print(f"Metin içeriği '{text_filename}' dosyasına kaydedildi.")
        
        # Görselleri indirme
        for img_url in images:
            try:
                img_response = requests.get(img_url)
                if img_response.status_code == 200:
                    parsed_url = urlparse(img_url)
                    img_name = os.path.basename(parsed_url.path)
                    if not img_name:
                        img_name = "image.jpg"
                    img_path = os.path.join(images_folder, img_name)
                    with open(img_path, "wb") as img_file:
                        img_file.write(img_response.content)
                    print(f"İndirildi: {img_url} -> {img_path}")
                else:
                    print(f"İndirme başarısız: {img_url}")
            except Exception as e:
                print(f"İndirme hatası: {img_url}\nHata: {str(e)}")
    else:
        print("Sayfa çekilemedi. Durum kodu:", response.status_code)

if __name__ == "__main__":
    target_url = "https://www.ellindecoratie.nl/"
    download_page_and_images(target_url)
