from fetch_sitemap import fetch_sitemap

def test_fetch_sitemap():
    sitemap_url = "https://www.bargain-cafe.com/sitemap.xml"
    product_urls = fetch_sitemap(sitemap_url)
    print(product_urls)
    assert len(product_urls) > 0