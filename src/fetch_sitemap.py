from __future__ import annotations

import requests
from bs4 import BeautifulSoup
import re



def fetch_sitemap_text(sitemap_url: str) -> str:
    """下載 sitemap.xml，回傳原始 sitemap 文字

    Args:
        sitemap_url (str): sitemap 網址

    Returns:
        str: sitemap 原文
    """
    resp = requests.get(sitemap_url)
    resp.raise_for_status()

    return resp.text

def parse_sitemap_xml(xml_text:str)->list[str]:
    """解析 sitemap XML，回傳所有 URL（含非商品頁）。

    Args:
        xml_text (str): xml 文字

    Returns:
        list[str]: 所有 URL 的清單，並且去重複
    """

    soup = BeautifulSoup(xml_text, 'xml')
    urls = [loc_tag.text.strip() for loc_tag in soup.find_all("loc")]

    return sorted(set[str](urls))

def filter_product_urls(urls:list[str])->list[str]:
    """從網址清單中保留商品的網址

    Args:
        urls (list[str]): 完整網址清單

    Returns:
        list[str]: 含有 products 的網址清單
    """
    PRODUCT_re = re.compile(r"/products/")
    product_urls = [url for url in urls if PRODUCT_re.search(url)]

    return product_urls