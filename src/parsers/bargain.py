from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urlparse
from pathlib import Path
from normalizer.coffee_lexicon import CoffeeLexicon

def extract_title(soup: BeautifulSoup) -> str:
    """提取 HTML 文件的標題。

    Args:
        soup (BeautifulSoup): BeautifulSoup 物件。

    Returns:
        str: 標題。
    """

    # try to extract the title from the h1 tag
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)

    # try to extract the title from the og:title meta tag
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        return og_title.get("content")

    return None


BLEND_KEYWORDS = [
    "配方",
    "混合",
    "混搭",
    "調配",
    "調和",
    "blend",
    "綜合",
]


def infer_bean_type(title: str | None, origin_text: str | None, region_text: str | None = None) -> str:
    """
    判斷是否為配方豆。
    """
    title_text = (title or "").lower()
    for kw in BLEND_KEYWORDS:
        if kw.lower() in title_text:
            return "配方（Blend）"

    def _text_has_multiple_places(text: str | None) -> bool:
        if not text:
            return False
        raw = re.sub(r"[()（）]", " ", text)
        if re.search(r"[、，,/&＋+和與及]", raw):
            parts = [p.strip() for p in re.split(r"[、，,/&＋+和與及]", raw) if p.strip()]
            if len(parts) >= 2:
                return True
        return False

    if _text_has_multiple_places(origin_text):
        return "配方（Blend）"

    if _text_has_multiple_places(region_text):
        return "配方（Blend）"

    return "單品（Single Origin）"


def extract_product_json(html_text) -> dict:
    """
    從整個商品頁 HTML 檔案中，把 app.value('product', JSON.parse('...')) 這段抓出來
    然後回傳成 Python dict
    """
    # 用正則把 JSON 內文抓出來
    pattern = r"app\.value\(\s*'product'\s*,\s*JSON\.parse\('(.+?)'\)\s*\);"
    m = re.search(pattern, html_text, flags=re.DOTALL)
    if not m:
        raise ValueError("找不到 product JSON 塊，結構可能改了")

    raw_escaped_json = m.group(1)

    # 網站把雙引號做了反斜線跳脫，所以要先還原
    raw_json_str = raw_escaped_json.encode('utf-8').decode('unicode_escape')

    # 轉成 dict
    product_data = json.loads(raw_json_str)

    return product_data


def extract_weight_from_fields(fields)->int|None:
    """
    嘗試從 fields 裡面抓出重量（公克數），
    例如 [{"name": "200克"}, {"name": "熟豆（無研磨）"}] → 200
    """
    for f in fields:
        name = f.get("name", "")
        # 抓「數字 + 克」→ 即使是 "200å…‹" 也會有 "200"
        m = re.search(r"(\d+)\s*", name)
        if m:
            return int(m.group(1))
        # 補一點磅的常見寫法
        if "半磅" in name:
            return 227
        if "1/4" in name:
            return 113
        if "磅" in name:
            return 454
    return None


def extract_product_info(product_data: dict) -> dict:
    """
    從 product_data（已是 dict）中抽出來的 Json
    - 最低銷售價 price_raw
    - 對應的原價 price_original
    - 對應的 variation 規格文字 (ex: "200克 / 熟豆（無研磨）")
    - 是否有貨 in_stock
    """
    variations = product_data.get("variations", [])
    if not variations:
        return {
            "price_raw": None,
            "price_original": None,
            "variation_desc": None,
            "in_stock": None,
            "weight_g": None,
        }

    offer_list = []
    for v in variations:    
        # 1. 決定實際賣價（含特價）
        price_sale = v.get("price_sale")
        if price_sale and price_sale.get("dollars"):
            price_final = price_sale["dollars"]  # e.g. 550.0
        else:
            price_final = v["price"]["dollars"]       # e.g. 600.0

        # 2. 原價
        price_original = v["price"]["dollars"] if v.get("price") else None

        # 3. 找出產品規格
        fields = v.get("fields", [])
        # 3.1 嘗試從 fields 裡面抓出重量（公克數），例如 [{"name": "200克"}, {"name": "熟豆（無研磨）"}] → 200
        weight_g = extract_weight_from_fields(fields)
        
        
        #3.2 若從 fields 沒抓到，嘗試從 fields_translations（字串陣列）補抓重量（公克數），例如 [{"name": "200克"}, {"name": "熟豆（無研磨）"}] → 200
        if weight_g is None:
            ftr = (v.get("fields_translations") or {}).get("zh-hant") or []
            for txt in ftr:
                # 同步套用上面的規則
                m = re.search(r"(\d+)\s*克", txt or "")
                if m:
                    weight_g = int(m.group(1))
                    break
                m = re.search(r"(\d+)\s*g", txt or "", flags=re.IGNORECASE)
                if m:
                    weight_g = int(m.group(1))
                    break
                m = re.search(r"(\d{2,4})\b", txt or "")
                if m:
                    val = int(m.group(1))
                    if 50 <= val <= 5000:
                        weight_g = val
                        break

        # 4. 有沒有庫存
        qty = v.get("quantity")
        in_stock = (qty is not None and qty > 0)

        offer_list.append({
            "price_final": price_final,
            "price_original": price_original,
            "weight_g": weight_g,
            "in_stock": in_stock,
        })

    # 取最低價的那組
    best = min(offer_list, key=lambda x: x["price_final"])

    return {
        "price_raw": best["price_final"],
        "price_original": best["price_original"],
        "weight_g": best["weight_g"],
        "in_stock": best["in_stock"],
    }


def extract_external_id_from_soup(soup: BeautifulSoup) -> str:
    """
    從 soup 中提取 external_id。
    """
    meta = soup.find("meta", property="og:url")
    if meta and meta.get("content"):
        url = meta["content"]
        path = urlparse(url).path
        return path.rstrip("/").split("/")[-1]
    return None



#<-- 下面是解析商品描述的函數 -->

def extract_desc_from_full_html(html_text) -> str | None:
    '''
    解析商品描述的 HTML 檔案，回傳 string，包含商品描述的文字。
    '''
    soup = BeautifulSoup(html_text, "html.parser")

    # 1) 優先抓商品描述區塊，否則退回整個 body
    main = (
        soup.select_one(".ProductDetail-description-content")
        or soup.select_one(".ProductDetail-description")
        or soup.find(id="product-show")
        or soup
    )
    text = main.get_text(separator="\n", strip=True)

    return text


_DESC_KEYWORDS = [
    # 產地 / 產區
    "咖啡烘焙度",
    "處理方式",
    "處理法",
    "品種",
    "國別",
    "國家",
    "產地",
    "產區",
    "地區",
    "區域",
    "海拔",
    "處理廠",
    "處理場",
    "處理站",
    "莊園",
    "庄園",
    "農場",
    "農園",
    "生產者",
    "Producer",
    "producer",
    "Process",
    "process",
    "Variety",
    "variety",
    "Country",
    "country",
    "Origin",
    "origin",
    "Region",
    "region",
    "Farm",
    "farm",
    "Roast",
    "roast",
    "焙度",
    "烘焙度",
    "烘焙",
]

_DESC_KEY_PATTERN = re.compile(
    "|".join(sorted({re.escape(k) for k in _DESC_KEYWORDS}, key=len, reverse=True))
)


def _normalize_desc_text(text: str) -> str:
    text = text.replace("\r", "\n")
    # unify common unicode spaces
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    text = re.sub(r"(莊|庄)\s+(園)", r"\1\2", text)
    # add newlines before repeated keys sitting on the same line
    text = re.sub(
        rf"(?<!^)(?<!\n)(?<![\w\u4e00-\u9fff])({_DESC_KEY_PATTERN.pattern})(?=[\s：:｜|│／/=－\-])",
        r"\n\1",
        text,
    )
    text = text.replace(":", "：")
    # 處理「國家\n：衣索比亞」形式
    text = re.sub(
        rf"({_DESC_KEY_PATTERN.pattern})\s*\n\s*：",
        r"\1：",
        text,
    )
    text = re.sub(r"[｜|│／/=－\-]", "：", text)
    # turn "國家 衣索比亞" into "國家：衣索比亞"
    text = re.sub(rf"({_DESC_KEY_PATTERN.pattern})[ \t]+(?=[^\s：])", r"\1：", text)
    text = re.sub(r"[ \t]*：[ \t]*", "：", text)
    text = re.sub(r"\n+", "\n", text.strip())
    return text


def parse_kv_from_desc(text: str) -> dict:
    '''
    解析商品描述的 string，把標點符號切割，最後以 key: value 的形式轉換成 dict。
    '''
    cleaned = _normalize_desc_text(text)
    result = {}
    pending_key = None
    for raw_line in cleaned.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "：" not in line:
            if pending_key:
                if any(token in line for token in ("{{", "}}", "=>", "translate")):
                    continue
                addition = line.strip()
                if addition:
                    result[pending_key] = f"{result[pending_key]} {addition}".strip()
                    opened = result[pending_key].count("（") + result[pending_key].count("(")
                    closed = result[pending_key].count("）") + result[pending_key].count(")")
                    if closed >= opened:
                        pending_key = None
            continue
        key, val = line.split("：", 1)
        key = key.strip()
        val = val.strip()
        if not key or not val:
            continue
        # 排除模板標記或是動態語系 placeholder
        if "{{" in key or "{{" in val or "}}" in key or "}}" in val:
            continue
        if "=>" in key or "translate" in key or "=>" in val:
            continue
        # 特殊：生產者往往是「XX處理廠 + 小農」的形式，保留完整字串，並額外拆出處理廠
        if key in {"生產者", "Producer", "producer"}:
            parts = re.split(r"\s+", val)
            producers = []
            buffer = []
            for part in parts:
                buffer.append(part)
                if part.endswith(("廠", "場", "站")):
                    producers.append(" ".join(buffer).strip())
                    buffer = []
            if buffer:
                producers.append(" ".join(buffer).strip())
            if len(producers) >= 2:
                result[key] = " ".join(producers)
                result.setdefault("處理廠", producers[0])
                continue
        result[key] = val
        if val.endswith(("（", "(")):
            pending_key = key
        else:
            pending_key = None
    return result

def normalize_product_desciprtion(desc_raw:dict, lex:CoffeeLexicon) -> dict:
    def _collect_countries(text: str | None) -> list[str]:
        """把可能含多個產國的文字逐一正規化並去重"""
        if not text:
            return []
        parts = re.split(r"[、，,/&＋+和與及\\s]+", re.sub(r"[()（）]", " ", text))
        countries: list[str] = []
        seen = set()
        for part in parts:
            part = part.strip()
            if not part:
                continue
            norm = lex.normalize_country(part)
            if not norm:
                t = lex._canon(part)
                for code, spec in lex.country.items():
                    if any(alias in t for alias in spec["aliases"]):
                        norm = code
                        break
            if norm and norm not in seen:
                seen.add(norm)
                countries.append(norm)
        return countries

    countries = _collect_countries(desc_raw.get("origin_raw"))
    if not countries:
        countries = _collect_countries(desc_raw.get("region_raw"))

    norm_country = ",".join(countries) if countries else None

    return {
        "process" : lex.normalize_process(desc_raw.get("process_raw")),
        "roast" : lex.normalize_roast(desc_raw.get("roast_raw")),
        "variety" : lex.normalize_variety(desc_raw.get("variety_raw")),
        "country": norm_country,
    }


def _clean_origin_value(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = re.sub(r"\(.*?\)", " ", text)
    cleaned = re.sub(r"[、，,/|&]+", " ", cleaned)
    cleaned = cleaned.strip()
    if not cleaned:
        return None
    # 取第一個片段
    first = cleaned.split()[0]
    return first.strip()


def parse_product_description(html_text) -> dict:
    """解析商品描述，回傳 dict。

    Args:
        html_text : 商品描述 HTML。

    Returns:
        dict: 商品描述。
        - process_raw: 處理方式。
        - roast_raw: 烘焙度。
        - variety_raw: 品種。
        - origin_raw: 產地。
        - region_raw: 產區。
        - farm_raw: 農場。
    """
    description = extract_desc_from_full_html(html_text)

    kv = parse_kv_from_desc(description)

    def pick(*keys: str) -> str | None:
        for key in keys:
            val = kv.get(key)
            if val:
                return val
        return None

    origin_full_raw = pick("國家", "國別", "產地", "Country", "country", "Origin", "origin")
    origin_raw = _clean_origin_value(origin_full_raw)

    result = {
        "process_raw": pick("處理方式", "處理法", "Process", "process"),
        "roast_raw": pick("咖啡烘焙度", "烘焙度", "焙度", "烘焙", "Roast", "roast"),
        "variety_raw": pick("品種", "Variety", "variety"),
        "origin_raw": origin_raw,
        "_origin_raw_full": origin_full_raw,
        "region_raw": pick("產區", "地區", "區域", "Region", "region"),
        "farm_raw": pick(
            "莊園",
            "庄園",
            "農場",
            "農園",
            "Farm",
            "farm",
            "處理廠",
            "處理場",
            "處理站",
            "產埋廠",
            "生產者",
            "Producer",
            "producer",
        ),
    }

    return result



#<---- 商品描述區塊結束 -->




def parse_product_bargain(html_path: Path, lex_yaml_path: Path) -> dict:
    """
    對單一商品 HTML 檔進行完整解析，回傳 dict。
    包含：
    - title
    - price
    - description
    """
    # 1. 讀取 HTML
    html_text = html_path.read_text(encoding="utf-8")
    # 2. 解析 HTML
    soup = BeautifulSoup(html_text, "html.parser")

    # 3. 解析 title
    title = extract_title(soup)

    # 4. 解析 product_data
    product_data = extract_product_json(html_text)

    # 5. 解析 product info
    product_info = extract_product_info(product_data)
    external_id = extract_external_id_from_soup(soup)

    #6. 抽出 product_description_raw
    desc_raw = parse_product_description(html_text)
    origin_raw_full = desc_raw.pop("_origin_raw_full", None)
    # 3.1 解析 bean type
    bean_type = infer_bean_type(title, origin_raw_full, desc_raw.get("region_raw"))

    #6.1 做正規化

    lex = CoffeeLexicon(lex_yaml_path)
    desc_norm = normalize_product_desciprtion(desc_raw, lex)

    return {
        "external_id": external_id,
        "title": title,
        "bean_type": bean_type,
        "price": product_info['price_raw'],
        "price_original": product_info['price_original'],
        "weight_g": product_info['weight_g'],
        "in_stock": product_info['in_stock'],
        **desc_raw,
        **{f"norm_{k}":v for k, v in desc_norm.items()}
    }
