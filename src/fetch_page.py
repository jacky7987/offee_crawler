from pathlib import Path
import requests


def fetch_page(url: str, save_html:bool=False) -> Path:
    """Fetch a page from the given URL and save it to the given directory.

    Args:
        url (str): The URL of the page to fetch.
        save_dir (str, optional): The directory to save the page to. Defaults to "../data/raw_html".

    Returns:
        Path: The path to the saved page.
    """

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    }

    # send a GET request to the URL
    resp = requests.get(url, headers=headers)

    # check if the request was successful
    resp.raise_for_status()

    if not save_html:
        return resp.text

    # create the output directory if it doesn't exist
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    output_dir = project_root / "data" / "raw_html"
    output_dir.mkdir(parents=True, exist_ok=True)

    # get the slug from the URL
    slug = url.strip("/").split("/")[-1]

    # create the file path
    file_path = output_dir / f"{slug}.html"

    # save the page to the file
    file_path.write_text(resp.text, encoding="utf-8")

    return file_path
