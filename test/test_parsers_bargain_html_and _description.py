from pathlib import Path
from parsers.bargain import parse_product_bargain, parse_product_description, extract_desc_from_full_html

def test_bargain_parser_can_parse_html():
    # 1. 準備測試資料（你的 raw_html 範例）
    project_root = Path(__file__).resolve().parents[1]
    html_file = project_root / "data" / "raw_html" / "colombia-sweet-realm-coffee-bean.html"
    lex_file = project_root / "data" / "normalize" / "coffee_lexicon.yaml"

    assert html_file.exists(), "測試用的 HTML 檔案不存在，先確認一下路徑"
    assert lex_file.exists()

    # 2. 執行我們的 parser
    product_data = parse_product_bargain(html_file, lex_file)


    # 3. 最基本的欄位要有
    assert "title" in product_data
    assert product_data["title"]  # 不要是空字串

    # 價格有時是 550 有時是 600，看你抓哪個欄位，
    # 我們只驗證「有抓到數字」就好
    assert "price" in product_data
    assert isinstance(product_data["price"], (int, float))


def test_bargain_parser_can_extract_desc_fields():
    project_root = Path(__file__).resolve().parents[1]
    html_path = project_root / "data" / "raw_html" / "colombia-sweet-realm-coffee-bean.html"

    html_text = html_path.read_text(encoding='utf-8')

    desc_html = extract_desc_from_full_html(html_text)
    desc_data = parse_product_description(desc_html)


    # 這些欄位你剛寫的 parser 會回傳 None 或字串
    # 這裡只要確認「有這個 key」就好，之後你再加更嚴格的
    assert "process_raw" in desc_data
    assert "roast_raw" in desc_data
    assert "origin_raw" in desc_data

    # 如果你知道這支商品真的有寫「咖啡烘焙度：淺中」
    # 就可以再加一條比較嚴的：
    # assert desc_data["roast_raw"] in ("淺中", "淺中焙")


def test_bargain_parser_detects_blend_by_region():
    project_root = Path(__file__).resolve().parents[1]
    html_file = project_root / "data" / "raw_html" / "bargain-cafe--best--coffee-bean-roaster-coffee-sister-costa-rica-brasil-454g.html"
    lex_file = project_root / "data" / "normalize" / "coffee_lexicon.yaml"

    product = parse_product_bargain(html_file, lex_file)

    assert product["bean_type"] == "配方（Blend）"
