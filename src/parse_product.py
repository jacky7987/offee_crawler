from pathlib import Path
from parsers import bargain


def parse_product(source: str,html_path: Path, lex_yaml_path:Path) -> dict:
    """
    Parse a product from a given HTML file and source.

    Args:
        html_path (Path): The path to the HTML file.
        source (str): The source of the product.

    Returns:
        dict: The parsed product.
    """

    if source == "bargain":
        return bargain.parse_product_bargain(html_path, lex_yaml_path)
    else:
        raise ValueError(f"Unknown source: {source}")