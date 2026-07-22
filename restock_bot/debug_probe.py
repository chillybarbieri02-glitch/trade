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
    "target_page": "https://www.target.com/s?searchTerm=pokemon+booster+box",
}


def probe() -> None:
    for name, url in TARGETS.items():
        print(f"=== {name} ===")
        print("url:", url)
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            print("status:", resp.status_code)
            print("content-length:", len(resp.content))

            has_next_data = "__NEXT_DATA__" in resp.text
            print("has __NEXT_DATA__ script:", has_next_data)

            if has_next_data:
                start = resp.text.index("__NEXT_DATA__")
                # Print a window around the script tag so we can see its
                # opening structure without dumping the whole (huge) blob.
                print("snippet_around_next_data:", resp.text[start : start + 400])

            tcin_count = resp.text.count('"tcin"')
            print("occurrences of \"tcin\":", tcin_count)
            if tcin_count:
                idx = resp.text.index('"tcin"')
                print("snippet_around_first_tcin:", resp.text[max(0, idx - 200) : idx + 400])

            api_key_count = resp.text.count("redsky.target.com")
            print("occurrences of redsky.target.com:", api_key_count)
            if api_key_count:
                idx = resp.text.index("redsky.target.com")
                print("snippet_around_redsky_ref:", resp.text[max(0, idx - 300) : idx + 100])
        except Exception as exc:
            print("ERROR:", repr(exc))
        print()


if __name__ == "__main__":
    probe()
