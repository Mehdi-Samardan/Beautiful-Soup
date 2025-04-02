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
        return None

def get_image_folder(base_url):
    parsed_url = urlparse(base_url)
    path = parsed_url.path.strip("/")
    if path:
        return f"{path.replace('/', '_')}_images"
    else:
        return f"{parsed_url.netloc}_images"

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
            img['src'] = local_path
        except Exception as e:
            continue
    return soup

def extract_meta(soup, fallback_title):
    meta_og = soup.find("meta", property="og:title")
    meta_name = soup.find("meta", attrs={"name": "title"})
    meta_desc_tag = soup.find("meta", attrs={"name": "description"})
    meta_title = (meta_og.get("content") or meta_name.get("content")).strip() if (meta_og or meta_name) else fallback_title
    meta_description = meta_desc_tag.get("content").strip() if meta_desc_tag else "Meta description not found"
    return meta_title, meta_description

def extract_all_meta(soup):
    meta_tags = {}
    for meta in soup.find_all("meta"):
        key = meta.get("name") or meta.get("property")
        content = meta.get("content")
        if key and content:
            meta_tags[key] = content.strip()
    return meta_tags

def clean_content(soup):
    for unwanted in soup(['script', 'style']):
        unwanted.decompose()
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
    return f"{images_folder}.zip"

def process_url(url, headers):
    html = fetch_page(url, headers)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    h1_tag = soup.find("h1")
    page_title = h1_tag.get_text(strip=True) if h1_tag and h1_tag.get_text(strip=True) else (soup.title.get_text(strip=True) if soup.title else "Title not found")
    meta_title, meta_description = extract_meta(soup, page_title)
    meta_tags = extract_all_meta(soup)
    permalink = url
    images_folder = get_image_folder(url)
    soup = process_images(soup, url, headers, images_folder)
    content = clean_content(soup)
    zip_file_path = zip_images(images_folder)
    return {
        "page_title": page_title,
        "meta_title": meta_title,
        "meta_description": meta_description,
        "meta_tags": meta_tags,
        "permalink": permalink,
        "content": content,
        "zip_file_path": zip_file_path
    }

def send_property_with_zip(prop_name, prop_value, zip_file_path, webhook_url):
    payload = {"property": prop_name, "value": prop_value}
    try:
        with open(zip_file_path, "rb") as f_zip:
            files = {
                "data": (None, json.dumps(payload, ensure_ascii=False), "application/json"),
                "zip_file": (os.path.basename(zip_file_path), f_zip, "application/zip")
            }
            requests.post(webhook_url, files=files, timeout=30)
    except Exception as e:
        pass

def send_all_properties(bundle, webhook_url):
    zip_file_path = bundle.pop("zip_file_path")
    for key, value in bundle.items():
        send_property_with_zip(key, value, zip_file_path, webhook_url)

def main():
    url = "https://www.ellindecoratie.nl/over-mij"
    webhook_url = "https://hook.eu2.make.com/is1dhkyhge8iuqg4jsxykh6dkyaejawy"
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/87.0.4280.66 Safari/537.36")
    }
    bundle_data = process_url(url, headers)
    if not bundle_data:
        return
    # (Optional) Save backup without zip_file_path
    output_file = "output.json"
    try:
        backup_data = {k: v for k, v in bundle_data.items() if k != "zip_file_path"}
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        pass
    # Send each property (with the same ZIP file) separately
    send_all_properties(bundle_data, webhook_url)
    print("Process complete.")

if __name__ == "__main__":
    main()
