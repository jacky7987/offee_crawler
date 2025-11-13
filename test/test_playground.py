from pathlib import Path

from bs4 import BeautifulSoup


if __name__ == '__main__':
    here = Path(__file__).resolve().parent.parent
    html_path = here / "data" / "raw_html" / "colombia-sweet-realm-coffee-bean.html"

    html_text =  html_path.read_text(encoding='utf-8')
    soup = BeautifulSoup(html_text, "html.parser")

    print(soup)