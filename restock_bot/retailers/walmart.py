import json

import requests
from bs4 import BeautifulSoup

from .base import Product, RetailerChecker

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class WalmartChecker(RetailerChecker):
    """Parses the __NEXT_DATA__ JSON blob Walmart's search page embeds for
    its own React app to hydrate from. This is more stable than scraping
    rendered HTML, but the JSON path still shifts when Walmart redesigns
    the search page — if this raises "structure changed", re-inspect a
    fresh page's __NEXT_DATA__ script tag and update the path below.
    """

    name = "Walmart"
    search_url = "https://www.walmart.com/search?q={query}"

    def search(self, query: str) -> list[Product]:
        url = self.search_url.format(query=requests.utils.quote(query))
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        script = soup.find("script", id="__NEXT_DATA__")
        if not script or not script.string:
            raise RuntimeError("Walmart page structure changed; __NEXT_DATA__ not found")

        data = json.loads(script.string)
        try:
            item_stacks = data["props"]["pageProps"]["initialData"]["searchResult"]["itemStacks"]
            items = item_stacks[0]["items"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("Walmart search JSON structure changed; update the path in walmart.py")

        products: list[Product] = []
        for item in items:
            name = item.get("name", query)
            canonical = item.get("canonicalUrl", "")
            product_url = f"https://www.walmart.com{canonical}" if canonical else "https://www.walmart.com"
            price_info = item.get("priceInfo", {}) or {}
            current_price = price_info.get("currentPrice", {}) or {}
            price = current_price.get("priceString")
            availability = item.get("availabilityStatus", "")
            in_stock = availability == "IN_STOCK"

            products.append(
                Product(
                    retailer=self.name,
                    name=name,
                    url=product_url,
                    price=price,
                    in_stock=in_stock,
                )
            )
        return products
