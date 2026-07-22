"""Re-diagnosis tool: fetch each retailer's search page with realistic
headers and print status/redirects/a body snippet, so you can see what's
actually happening (bot-block page, redirect, real HTML, etc.) before
guessing at fixes blind. Run via the "Debug Retailer Probe" workflow
(Actions tab -> Run workflow), or locally with `python -m restock_bot.debug_probe`.
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
