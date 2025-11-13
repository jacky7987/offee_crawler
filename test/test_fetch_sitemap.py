import re
from fetch_sitemap import parse_sitemap_xml, filter_product_urls


# 🧩 1. 提供一個 sample sitemap fixture
SAMPLE_SITEMAP_XML = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.bargain-cafe.com/</loc></url>
  <url><loc>https://www.bargain-cafe.com/products/sample-coffee</loc></url>
  <url><loc>https://www.bargain-cafe.com/pages/about</loc></url>
</urlset>
"""

def test_parse_and_filter_sitemap():
    # 🧩 2. 驗證 fetch_sitemap_text 能正確解析出所有 URL
    urls = parse_sitemap_xml(SAMPLE_SITEMAP_XML)
    assert isinstance(urls, list)
    assert len(urls) == 3
    assert "https://www.bargain-cafe.com/products/sample-coffee" in urls

    # 🧩 3. 驗證 filter_product_urls 正確篩出產品頁
    product_urls = filter_product_urls(urls)
    assert len(product_urls) == 1
    assert product_urls[0].startswith("https://www.bargain-cafe.com/products/")
    assert re.match(r"https://www\.bargain-cafe\.com/products/.+", product_urls[0])


