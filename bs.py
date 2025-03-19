import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import uuid
import copy

def fetch_page(url, headers):
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Sayfa çekilemedi. Durum kodu: {response.status_code}")
        return None

def process_images(soup, base_url, images_folder, headers):
    gallery_images = []  # Galeri için indirilen görsellerin yolunu saklayacağız.
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
                parsed_url = urlparse(absolute_src)
                filename = os.path.basename(parsed_url.path)
                if not filename or '.' not in filename:
                    filename = f"{uuid.uuid4()}.jpg"
                local_path = os.path.join(images_folder, filename)
                with open(local_path, 'wb') as f:
                    f.write(img_response.content)
                print(f"İndirildi: {absolute_src} -> {local_path}")
                # Görsel URL'sini galerimiz için kaydediyoruz
                gallery_images.append(local_path)
                # img tag'inin src özniteliğini güncelle (görselin yeni yolu)
                img['src'] = local_path
            else:
                print(f"Resim indirilemedi: {absolute_src} (Status: {img_response.status_code})")
        except Exception as e:
            print(f"Resim indirirken hata oluştu: {absolute_src}\nHata: {str(e)}")
    return gallery_images

def extract_meta_details(soup):
    meta_details = {}
    for meta in soup.find_all('meta'):
        content = meta.get('content')
        if content:
            key = meta.get('name') or meta.get('property')
            if key:
                meta_details[key] = content.strip()
    return meta_details

def clean_content(soup):
    """
    Body içerisinden yalnızca p, a, ul, ol, li etiketlerini korur.
    Diğer tüm etiketler unwrap edilerek iç metin korunur.
    Ayrıca, p, a, ul, ol, li etiketlerinin tüm attribute'ları temizlenir.
    """
    allowed_tags = ['p', 'a', 'ul', 'ol', 'li']
    # Derinlemesine kopyasını alarak orijinal üzerinde oynamayalım.
    content_soup = copy.deepcopy(soup.body)
    
    for tag in content_soup.find_all(True):
        # Eğer izin verilen etiketler dışındaysa, etiketin kendisini kaldırıp, içeriğini koruruz.
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            # İzin verilen etiketlerdeki tüm attribute'ları temizleyelim.
            tag.attrs = {}
    return str(content_soup)

def save_final_html(page_title, meta_details, content_html, gallery_images, permalink, output_filename="final_page.html"):
    # Galeri için listeyi HTML haline getirelim:
    gallery_html = "<div class='gallery'><h2>Gallery</h2><ul>"
    for img_path in gallery_images:
        gallery_html += f"<li><img src='{img_path}' alt='Görsel'></li>\n"
    gallery_html += "</ul></div>"
    
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
        .gallery ul {{
            list-style-type: none;
            padding: 0;
        }}
        .gallery li {{
            display: inline-block;
            margin-right: 10px;
        }}
        .gallery img {{
            max-width: 150px;
            height: auto;
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
    html_output += content_html
    html_output += """
    </div>
    <!-- Galeri -->
"""
    html_output += gallery_html
    html_output += """
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
    
    # Title: Sayfadaki ilk H1 etiketini kullan (varsa), yoksa <title> etiketine fallback
    h1_tag = soup.find('h1')
    if h1_tag:
        page_title = h1_tag.get_text().strip()
    else:
        page_title = soup.title.string.strip() if soup.title else "Başlık bulunamadı"
    
    # Meta bilgileri: Örnek olarak og:title veya meta name="title" tercih edilebilir, fakat artık içerik isteğinize göre H1'den gelen başlık kullanılacak.
    meta_title = page_title  # İstenirse meta_title olarak H1 kullanılabilir.
    
    # Meta description
    meta_description = None
    if soup.find('meta', attrs={'name': 'description'}):
        meta_description = soup.find('meta', attrs={'name': 'description'}).get('content', '').strip()
    else:
        meta_description = "Meta açıklama bulunamadı"
    
    permalink = url  # Orijinal URL
    
    # Görselleri indir ve güncelle
    images_folder = "images"
    gallery_images = process_images(soup, url, images_folder, headers)
    
    # Tüm meta detaylarını çekelim
    meta_details = extract_meta_details(soup)
    meta_details['meta-title'] = meta_title
    meta_details['meta-description'] = meta_description
    
    # İçerik: Body içerisinden yalnızca p, a, ul, ol, li etiketlerini koruyarak temiz içerik elde ediyoruz.
    cleaned_content = clean_content(soup)
    
    # Final HTML dosyasını kaydet
    save_final_html(page_title, meta_details, cleaned_content, gallery_images, permalink)

if __name__ == "__main__":
    main()
