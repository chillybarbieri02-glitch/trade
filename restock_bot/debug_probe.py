"""One-off diagnostic: fetch each retailer's search page/API with realistic
headers and print status/headers/a body snippet, so we can see what a live
GitHub Actions runner actually gets back (bot-block page, redirect, real
HTML, etc.) without guessing blind.
"""

import requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TARGETS = {
    "pokemon_center": "https://www.pokemoncenter.com/search/index?q=pokemon%20booster%20box",
    "target_redsky_v1": (
        "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v1"
        "?key=9f36aeafbe60771e321a7cc95a78140772ab3e96&channel=WEB&count=24"
        "&default_purchasability_filter=true&keyword=pokemon+booster+box"
        "&platform=desktop&visitor_id=0000000000000000000000000000000000"
    ),
    "target_page": "https://www.target.com/s?searchTerm=pokemon+booster+box",
    "walmart": "https://www.walmart.com/search?q=pokemon%20booster%20box",
    "best_buy_page": "https://www.bestbuy.com/site/searchpage.jsp?st=pokemon+booster+box",
}


def probe() -> None:
    for name, url in TARGETS.items():
        print(f"=== {name} ===")
        print("url:", url)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            print("status:", resp.status_code)
            print("final_url:", resp.url)
            print("content-type:", resp.headers.get("content-type"))
            print("content-length:", len(resp.content))
            snippet = resp.text[:600].replace("\n", " ")
            print("body_snippet:", snippet)
        except Exception as exc:
            print("ERROR:", repr(exc))
        print()


if __name__ == "__main__":
    probe()
