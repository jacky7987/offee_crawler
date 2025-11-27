from fetch_page import fetch_page
from fetch_sitemap import fetch_sitemap_text, parse_sitemap_xml, filter_product_urls

def fetch_all_pages(sitemap_url: str, brand_name: str = None, save_html:bool=False):
    """
    根據 sitemap URL 抓取該網站所有商品頁 HTML。
    Args:
        sitemap_url (str): 該網站的 sitemap.xml 位置
        brand_name (str, optional): 品牌名稱（可選，用於檔名或日誌）
    """
    sitemap__text = fetch_sitemap_text(sitemap_url)
    urls = parse_sitemap_xml(sitemap__text)
    product_urls = filter_product_urls(urls)

    print(f"🔍 Found {len(product_urls)} product pages from {brand_name or sitemap_url}")

    if not save_html:
        return product_urls

    path_list = []

    for url in product_urls:
        try:
            path = fetch_page(url, save_html)
            path_list.append(path)
            print(f"✅ Saved: {path}")
        except Exception as e:
            print(f"❌ Failed: {url} ({e})")
    
    return path_list