from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from fetch_manifest import fetch_all_pages
from parse_product import parse_product


DEFAULT_SITEMAP = "https://www.bargain-cafe.com/sitemap.xml"
DEFAULT_BRAND = "bargain"
SKIP_KEYWORDS_DEFAULT = ("組合", "濾掛", "濾紙", "濾杯", "+", "|")

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
OG_TITLE_RE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
    re.IGNORECASE | re.DOTALL,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="抓一次 bargain sitemap，下載商品頁並解析成結構化資料"
    )
    parser.add_argument(
        "--sitemap-url",
        default=DEFAULT_SITEMAP,
        help="Shopline sitemap 位置（預設為 bargain）",
    )
    parser.add_argument(
        "--brand-name",
        default=DEFAULT_BRAND,
        help="品牌名稱，僅做日誌用途（預設 bargain）",
    )
    parser.add_argument(
        "--lexicon",
        type=Path,
        default=None,
        help="lexicon YAML 路徑（預設 data/normalize/coffee_lexicon.yaml）",
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        default=None,
        help="若使用 --use-existing，從此目錄讀 HTML（預設 data/raw_html）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="只處理前 N 個商品，方便開發時快速驗證",
    )
    parser.add_argument(
        "--use-existing",
        action="store_true",
        help="不打 API，直接讀 data/raw_html 裡面既有的檔案",
    )
    parser.add_argument(
        "--skip-keywords",
        default=",".join(SKIP_KEYWORDS_DEFAULT),
        help="若商品標題含此清單中的任一關鍵字就略過，使用逗號分隔（預設：組合,濾掛）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="輸出 CSV 檔案路徑（預設寫在專案根目錄 products.csv）",
    )
    return parser


def iter_existing_html(html_dir: Path) -> Iterable[Path]:
    html_files = sorted(html_dir.glob("*.html"))
    if not html_files:
        raise SystemExit(f"⚠️ 在 {html_dir} 找不到任何 HTML，請先移除 --use-existing 再跑一次")
    return html_files


def extract_title_from_html(html_path: Path) -> str | None:
    text = html_path.read_text(encoding="utf-8", errors="ignore")
    m = TITLE_RE.search(text)
    if m:
        return m.group(1).strip()
    m = OG_TITLE_RE.search(text)
    if m:
        return m.group(1).strip()
    return None


def should_skip_html(html_path: Path, skip_keywords: tuple[str, ...]) -> bool:
    if not skip_keywords:
        return False
    title = extract_title_from_html(html_path) or ""
    return any(keyword and keyword in title for keyword in skip_keywords)


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    skip_keywords = tuple(
        kw.strip() for kw in (args.skip_keywords or "").split(",") if kw.strip()
    )

    project_root = Path(__file__).resolve().parents[1]
    lex_yaml = args.lexicon or (project_root / "data" / "normalize" / "coffee_lexicon.yaml")
    html_dir = args.html_dir or (project_root / "data" / "raw_html")

    if args.use_existing:
        html_paths = iter_existing_html(html_dir)
    else:
        html_paths = fetch_all_pages(
            sitemap_url=args.sitemap_url,
            brand_name=args.brand_name,
            save_html=True,
        )

    if args.limit:
        html_paths = list(html_paths)[: args.limit]

    if not html_paths:
        raise SystemExit("⚠️ 沒有可用的 HTML 檔案，請確認 sitemap 或目錄。")

    rows: List[dict] = []
    for html_path in html_paths:
        path = Path(html_path)
        if should_skip_html(path, skip_keywords):
            print(f"⏭️  Skip {path.name}（標題含排除關鍵字）")
            continue

        product = parse_product(source="bargain", html_path=path, lex_yaml_path=lex_yaml)
        print(f"📦 Parsed {html_path}")
        print(json.dumps(product, ensure_ascii=False, indent=2))
        rows.append(product)

    if not rows:
        raise SystemExit("⚠️ 沒有任何商品被解析，請調整條件後再試。")

    output_path = args.output or (project_root / "products.csv")
    df = pd.DataFrame(rows)
    if "norm_variety" in df.columns:
        df["norm_variety"] = df["norm_variety"].apply(
            lambda v: ", ".join(v) if isinstance(v, list) else (v or "")
        )
    df.to_csv(output_path, index=False)
    print(f"💾 Saved CSV to {output_path}")


if __name__ == "__main__":
    main()
