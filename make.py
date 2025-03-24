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
    
    allowed_tags = ["p", "a", "ul", "ol", "li"]
    # We'll remove <img> tags entirely from content (per your requirement).
    content_soup = copy.deepcopy(soup.body or soup)
    
    for tag in content_soup.find_all(True):
        if tag.name not in allowed_tags:
            tag.unwrap()
        else:
            tag.attrs = {}
    
    content_str = re.sub(r'\s+', ' ', str(content_soup)).strip()
    return content_str

def zip_images(images_folder):
    # Create a zip archive from the images folder
    zip_name = images_folder  # Use the folder name as base
    shutil.make_archive(zip_name, 'zip', images_folder)
    zip_path = f"{zip_name}.zip"
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
    
    # Process images: download and update image src in HTML
    images_folder = get_image_folder(url)
    soup = process_images(soup, url, headers, images_folder)
    
    # Clean content: only allow basic HTML tags: p, a, ul, ol, li
    content = clean_content(soup)
    
    # Do not include the zip data in the JSON payload; send it separately.
    return {
        "page_title": page_title,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "permalink": permalink,
        "content": content,
        "images_folder": images_folder  # We'll use this to attach the zip file separately.
    }

def main():
    # Process only one URL
    url = "https://www.ellindecoratie.nl/boomstam-bijzettafeltje"
    webhook_url = "https://hook.eu2.make.com/is1dhkyhge8iuqg4jsxykh6dkyaejawy"
    
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/87.0.4280.66 Safari/537.36")
    }
    
    print(f"🔗 Processing URL: {url}")
    data = process_url(url, headers)
    if not data:
        print("❌ No data processed.")
        return
    
    # Remove images_folder from JSON payload
    images_folder = data.pop("images_folder")
    
    # Write JSON payload (without the zip data) to output.json (optional backup)
    output_file = "output.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"✅ Data successfully written to {output_file}.")
    except Exception as e:
        print("❌ Error writing to file:", str(e))
    
    # Create the zip archive for the images folder
    zip_file_path = zip_images(images_folder)
    
    # Send a multipart/form-data POST request with two parts:
    # 1. "data": the JSON payload (output.json content)
    # 2. "zip_file": the zip file of images
    try:
        with open(output_file, "r", encoding="utf-8") as f_json, open(zip_file_path, "rb") as f_zip:
            multipart_data = {
                "data": (output_file, f_json, "application/json"),
                "zip_file": (os.path.basename(zip_file_path), f_zip, "application/zip")
            }
            response = requests.post(webhook_url, files=multipart_data, timeout=30)
        print("🔔 Webhook Response status code:", response.status_code)
        print("🔔 Webhook Response text:", response.text)
        if response.status_code in [200, 201, 202]:
            print("✅ Payload and zip file successfully sent to the webhook.")
        else:
            print(f"❌ Error sending payload: {response.status_code}")
    except Exception as e:
        print("❌ Error during webhook request:", str(e))
    
    # Debug output
    print("------------------------------------------------")
    print("Page Title:", data["page_title"])
    print("Meta-title:", data["meta_title"])
    print("Meta-description:", data["meta_description"])
    print("Permalink:", data["permalink"])
    print("Content (first 300 characters):", data["content"][:300])
    print("Zip file path:", zip_file_path)
    print("------------------------------------------------")

if __name__ == "__main__":
    main()
