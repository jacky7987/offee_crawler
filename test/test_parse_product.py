from pathlib import Path
from parse_product import parse_product

def test_parse_bargain_product():
    # 準備：拿你剛剛存好的 html
    project_root = Path(__file__).resolve().parents[1]
    html_file = project_root / "data" / "raw_html" / "colombia-sweet-realm-coffee-bean.html"
    lex_file = project_root / "data" / "normalize" / "coffee_lexicon.yaml"

    result = parse_product(source="bargain", html_path=html_file, lex_yaml_path=lex_file)

    print(result)

    assert isinstance(result, dict)
    assert result.get("external_id") is not None
    assert result.get("title") is not None
    assert result.get("bean_type") is not None
    assert result.get("price") is not None
    assert result.get("price_original") is not None
    assert result.get("weight_g") is not None
    assert result.get("in_stock") is not None