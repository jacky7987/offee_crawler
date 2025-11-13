from pathlib import Path
import requests
from bs4 import BeautifulSoup

def fetch_sitemap(sitemap_url: str) -> Path:
    """Fetch a sitemap from the given URL and save it to the given directory.

    Args:
        url (str): The URL of the sitemap to fetch.
    """
    resp = requests.get(sitemap_url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "xml")
    all_urls = [loc.text for loc in soup.find_all("loc")]
    product_urls = [url for url in all_urls if "/products/" in url]

    return product_urls