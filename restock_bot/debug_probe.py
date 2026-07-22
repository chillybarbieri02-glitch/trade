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

BASE_PARAMS = {
    "key": "9f36aeafbe60771e321a7cc95a78140772ab3e96",
    "channel": "WEB",
    "count": 24,
    "keyword": "pokemon booster box",
    "platform": "desktop",
    "visitor_id": "0000000000000000000000000000000000",
}

REDSKY_ENDPOINTS = {
    "plp_search_v1": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v1",
    "plp_search_v2": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2",
    "plp_search_v3": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v3",
    "plp_search_v4": "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v4",
    "pdp_client_v1_probe": "https://redsky.target.com/redsky_aggregations/v1/web/pdp_client_v1",
}


def probe() -> None:
    for name, url in REDSKY_ENDPOINTS.items():
        print(f"=== {name} ===")
        print("url:", url)
        try:
            resp = requests.get(url, params=BASE_PARAMS, headers=HEADERS, timeout=20)
            print("status:", resp.status_code)
            print("content-length:", len(resp.content))
            print("body_snippet:", resp.text[:300].replace("\n", " "))
        except Exception as exc:
            print("ERROR:", repr(exc))
        print()


if __name__ == "__main__":
    probe()
