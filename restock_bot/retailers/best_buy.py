import os

import requests

from .base import Product, RetailerChecker


class BestBuyChecker(RetailerChecker):
    """Uses Best Buy's official Products API instead of scraping — Best Buy
    fronts its site with aggressive bot protection, but offers a free
    developer API that's actually more reliable for this use case.

    Get a free key at https://developer.bestbuy.com/ and set it as
    BESTBUY_API_KEY.
    """

    name = "Best Buy"
    api_url = "https://api.bestbuy.com/v1/products((search={query}))"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("BESTBUY_API_KEY")

    def search(self, query: str) -> list[Product]:
        if not self.api_key:
            raise RuntimeError(
                "BESTBUY_API_KEY is not set; get a free key at https://developer.bestbuy.com/"
            )

        url = self.api_url.format(query=requests.utils.quote(query))
        params = {
            "apiKey": self.api_key,
            "format": "json",
            "show": "sku,name,url,salePrice,onlineAvailability,inStoreAvailability",
            "pageSize": 20,
        }
        resp = requests.get(url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        products: list[Product] = []
        for item in data.get("products", []):
            in_stock = bool(item.get("onlineAvailability") or item.get("inStoreAvailability"))
            sale_price = item.get("salePrice")
            products.append(
                Product(
                    retailer=self.name,
                    name=item.get("name", query),
                    url=item.get("url", "https://www.bestbuy.com"),
                    price=f"${sale_price}" if sale_price is not None else None,
                    in_stock=in_stock,
                )
            )
        return products
