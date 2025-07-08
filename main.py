import requests
from bs4 import BeautifulSoup
import os
import zipfile
from io import BytesIO
import json

BASE_URL = "https://ambientcg.com"
TEXTURE_PAGE = f"{BASE_URL}/list?type=All"
OUTPUT_DIR = "ambientcg_textures"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_texture_links():
    r = requests.get(TEXTURE_PAGE)
    soup = BeautifulSoup(r.text, "html.parser")
    cards = soup.select(".card-title a")
    links = [BASE_URL + card["href"] for card in cards]
    return links

def download_and_extract_zip(url, name):
    zip_url = f"{BASE_URL}/get?file={name}_1K-JPG.zip"
    print(f"Downloading: {zip_url}")
    r = requests.get(zip_url)
    z = zipfile.ZipFile(BytesIO(r.content))
    out_path = os.path.join(OUTPUT_DIR, name)
    os.makedirs(out_path, exist_ok=True)
    z.extractall(out_path)

    metadata = {
        "name": name,
        "source": "ambientcg",
        "path": out_path,
        "files": os.listdir(out_path)
    }

    with open(os.path.join(out_path, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

def main():
    links = get_texture_links()
    for link in links:
        name = link.split("=")[-1]
        try:
            download_and_extract_zip(link, name)
        except Exception as e:
            print(f"Failed to download {name}: {e}")

if __name__ == "__main__":
    main()
