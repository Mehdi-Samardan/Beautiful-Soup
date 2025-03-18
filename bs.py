import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import uuid  # Benzersiz dosya isimleri üretmek için

def fetch_page(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Sayfa çekilemedi. Durum kodu: {response.status_code}")
        return None

def process_images(soup, base_url, images_folder, headers):
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)
        
    # Tüm <img> etiketlerini işle: görseli indir, src'yi yerel dosya yoluna güncelle
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src:
            continue
        absolute_src = urljoin(base_url, src)
        try:
            img_response = requests.get(absolute_src, headers=headers)
            if img_response.status_code == 200:
                # URL'den dosya adını al, yoksa benzersiz bir ad üret
                parsed_url = urlparse(absolute_src)
                filename = os.path.basename(parsed_url.path)
                if not filename or '.' not in filename:
                    filename = f"{uuid.uuid4()}.jpg"
                local_path = os.path.join(images_folder, filename)
                with open(local_path, 'wb') as f:
                    f.write(img_response.content)
                print(f"İndirildi: {absolute_src} -> {local_path}")
                # img tag'inin src özniteliğini güncelle (görselin yeni yolu)
                img['src'] = os.path.join(images_folder, filename)
            else:
                print(f"Resim indirilemedi: {absolute_src} (Status: {img_response.status_code})")
        except Exception as e:
            print(f"Resim indirirken hata oluştu: {absolute_src}\nHata: {str(e)}")
            
def extract_meta_details(soup):
    # Tüm meta etiketlerini (hem name hem property) bir sözlükte toplayalım
    meta_details = {}
    for meta in soup.find_all('meta'):
        content = meta.get('content')
        if content:
            key = meta.get('name') or meta.get('property')
            if key:
                meta_details[key] = content.strip()
    return meta_details

def save_final_html(page_title, meta_details, updated_html, permalink, output_filename="final_page.html"):
    # Şık bir HTML şablonunda meta bilgiler ve güncellenmiş içeriği yerleştiriyoruz
    html_output = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <title>{page_title}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 20px;
        }}
        .meta-info {{
            background-color: #f4f4f4;
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
        }}
        .meta-info h2 {{
            margin-top: 0;
        }}
    </style>
</head>
<body>
    <div class="meta-info">
        <h2>Meta Bilgileri</h2>
        <p><strong>Permalink:</strong> <a href="{permalink}">{permalink}</a></p>
        <ul>
"""
    for key, value in meta_details.items():
        html_output += f"            <li><strong>{key}:</strong> {value}</li>\n"
    html_output += """        </ul>
    </div>
    <div class="page-content">
"""
    # Güncellenmiş HTML içeriği (örneğin, <body> içeriği) ekleniyor
    html_output += updated_html
    html_output += """
    </div>
</body>
</html>
"""
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_output)
    print(f"Final HTML dosyası '{output_filename}' olarak kaydedildi.")

def main():
    url = "https://www.ellindecoratie.nl/"
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/87.0.4280.66 Safari/537.36")
    }
    
    html = fetch_page(url, headers)
    if not html:
        return
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Sayfa başlığını al
    page_title = soup.title.string.strip() if soup.title else "Başlık bulunamadı"
    
    # Meta title: önce og:title, sonra meta name="title", yoksa sayfa başlığı
    meta_title = None
    if soup.find('meta', attrs={'property': 'og:title'}):
        meta_title = soup.find('meta', attrs={'property': 'og:title'}).get('content', '').strip()
    elif soup.find('meta', attrs={'name': 'title'}):
        meta_title = soup.find('meta', attrs={'name': 'title'}).get('content', '').strip()
    if not meta_title:
        meta_title = page_title
        
    # Meta description
    meta_description = None
    if soup.find('meta', attrs={'name': 'description'}):
        meta_description = soup.find('meta', attrs={'name': 'description'}).get('content', '').strip()
    else:
        meta_description = "Meta açıklama bulunamadı"
    
    # Permalink (orijinal URL)
    permalink = url
    
    # Görselleri indir ve <img> etiketlerindeki src özniteliklerini yerelleştir
    images_folder = "images"
    process_images(soup, url, images_folder, headers)
    
    # Tüm meta detaylarını çekelim
    meta_details = extract_meta_details(soup)
    # Özel olarak meta title ve meta description'ı ekleyelim
    meta_details['meta-title'] = meta_title
    meta_details['meta-description'] = meta_description
    
    # Güncellenmiş HTML içeriği: Genellikle body etiketini kullanıyoruz
    updated_html = str(soup.body) if soup.body else str(soup)
    
    # Tüm verileri şık bir HTML dosyası olarak kaydedelim
    save_final_html(page_title, meta_details, updated_html, permalink)

if __name__ == "__main__":
    main()
