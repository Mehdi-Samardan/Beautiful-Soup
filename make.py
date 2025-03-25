import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import uuid
import copy
import re
import json
import shutil

def fetch_page(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ Failed to fetch page {url}. Error: {e}")
        return None

def get_image_folder(base_url):
    parsed_url = urlparse(base_url)
    path = parsed_url.path.strip("/")
    if path:
        folder_name = f"{path.replace('/', '_')}_images"
    else:
        folder_name = f"{parsed_url.netloc}_images"
    return folder_name

def process_images(soup, base_url, headers, images_folder):
    if not os.path.exists(images_folder):
        os.makedirs(images_folder)
    
    for img in soup.find_all('img'):
        src = img.get('src')
        if not src:
            continue
        absolute_src = urljoin(base_url, src)
        try:
            img_response = requests.get(absolute_src, headers=headers, timeout=30)
            img_response.raise_for_status()
            filename = os.path.basename(urlparse(absolute_src).path)
            if not filename or '.' not in filename:
                filename = f"{uuid.uuid4()}.jpg"
            local_path = os.path.join(images_folder, filename)
            with open(local_path, 'wb') as f:
                f.write(img_response.content)
            print(f"✅ Image downloaded: {absolute_src} -> {local_path}")
            # Update the img tag's src attribute to the local file path
            img['src'] = local_path
        except Exception as e:
            print(f"❌ Error downloading image: {absolute_src}. Error: {e}")
    return soup

def extract_meta(soup, fallback_title):
    meta_og = soup.find("meta", property="og:title")
    meta_name = soup.find("meta", attrs={"name": "title"})
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    
    meta_title = (meta_og.get("content") or meta_name.get("content")).strip() if (meta_og or meta_name) else fallback_title
    meta_description = meta_desc_tag.get("content").strip() if meta_desc_tag else "Meta description not found"
    return meta_title, meta_description

def clean_content(soup):
    # Remove script and style tags
    for unwanted in soup(['script', 'style']):
        unwanted.decompose()
    
    # Only allow basic HTML tags: p, a, ul, ol, li (images are excluded from content)
    allowed_tags = ["p", "a", "ul", "ol", "li"]
    content_soup = copy.deepcopy(soup.body or soup)
    
    for tag in content_soup.find_all(True):
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            tag.attrs = {}
    
    content_str = re.sub(r'\s+', ' ', str(content_soup)).strip()
    return content_str

def zip_images(images_folder):
    shutil.make_archive(images_folder, 'zip', images_folder)
    zip_path = f"{images_folder}.zip"
    return zip_path

def process_url(url, headers):
    html = fetch_page(url, headers)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    
    # Page Title: Use first <h1> if available; otherwise, use <title>
    h1_tag = soup.find("h1")
    if h1_tag and h1_tag.get_text(strip=True):
        page_title = h1_tag.get_text(strip=True)
    else:
        page_title = soup.title.get_text(strip=True) if soup.title else "Title not found"
    
    meta_title, meta_description = extract_meta(soup, page_title)
    permalink = url
    
    # Process images: download images and update <img> tag src attribute
    images_folder = get_image_folder(url)
    soup = process_images(soup, url, headers, images_folder)
    
    # Clean content: keep only basic HTML tags (p, a, ul, ol, li)
    content = clean_content(soup)
    
    # Create ZIP archive for the images folder
    zip_file_path = zip_images(images_folder)
    
    return {
        "page_title": page_title,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "permalink": permalink,
        "content": content,
        "zip_file_path": zip_file_path  # For attachment purposes.
    }

def send_bundle(bundle, webhook_url):
    # Extract the ZIP file path and remove it from the JSON payload
    zip_file_path = bundle.pop("zip_file_path")
    # Prepare a multipart payload where each property is a separate field
    multipart_data = {
        "page_title": (None, bundle.get("page_title"), "text/plain"),
        "meta_title": (None, bundle.get("meta_title"), "text/plain"),
        "meta_description": (None, bundle.get("meta_description"), "text/plain"),
        "permalink": (None, bundle.get("permalink"), "text/plain"),
        "content": (None, bundle.get("content"), "text/plain")
    }
    # Open the ZIP file for attachment
    with open(zip_file_path, "rb") as f_zip:
        multipart_data["zip_file"] = (os.path.basename(zip_file_path), f_zip, "application/zip")
        try:
            response = requests.post(webhook_url, files=multipart_data, timeout=30)
            print("🔔 Webhook Response status code:", response.status_code)
            print("🔔 Webhook Response text:", response.text)
            if response.status_code in [200, 201, 202]:
                print("✅ Bundle successfully sent to the webhook.")
            else:
                print(f"❌ Error sending bundle: {response.status_code}")
        except Exception as e:
            print("❌ Error during webhook request:", e)

def main():
    # Process only the "over-mij" website
    url = "https://www.ellindecoratie.nl/over-mij"
    webhook_url = "https://hook.eu2.make.com/is1dhkyhge8iuqg4jsxykh6dkyaejawy"
    
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/87.0.4280.66 Safari/537.36")
    }
    
    print(f"🔗 Processing URL: {url}")
    bundle_data = process_url(url, headers)
    if not bundle_data:
        print("❌ No data processed.")
        return
    
    # (Optional) Save JSON payload without ZIP file path for backup
    output_file = "output.json"
    try:
        backup_data = {k: v for k, v in bundle_data.items() if k != "zip_file_path"}
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Data successfully written to {output_file}.")
    except Exception as e:
        print("❌ Error writing to file:", e)
    
    # Send all properties along with the ZIP file in one bundle
    send_bundle(bundle_data, webhook_url)
    
    # Debug output
    print("------------------------------------------------")
    for key, value in bundle_data.items():
        if key != "zip_file_path":
            preview = value[:300] if isinstance(value, str) else value
            print(f"{key}: {preview}")
    print("ZIP File path:", bundle_data.get("zip_file_path"))
    print("------------------------------------------------")

if __name__ == "__main__":
    main()
