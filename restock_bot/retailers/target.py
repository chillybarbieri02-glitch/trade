import os

import requests

from .base import Product, RetailerChecker

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class TargetChecker(RetailerChecker):
    """Uses Target's RedSky search API — the same endpoint target.com's own
    search page calls. The `key` query param is a public client key embedded
    in Target's frontend bundle (not a secret), but it does rotate
    occasionally. Set TARGET_API_KEY to override the built-in default if
    requests start failing.
    """

    name = "Target"
    search_url = "https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v1"
    default_api_key = "9f36aeafbe60771e321a7cc95a78140772ab3e96"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("TARGET_API_KEY") or self.default_api_key

    def search(self, query: str) -> list[Product]:
        params = {
            "key": self.api_key,
            "channel": "WEB",
            "count": 24,
            "default_purchasability_filter": "true",
            "keyword": query,
            "platform": "desktop",
            "visitor_id": "0000000000000000000000000000000000",
        }
        resp = requests.get(
            self.search_url, params=params, headers={"User-Agent": USER_AGENT}, timeout=20
        )
        resp.raise_for_status()
        data = resp.json()

        try:
            items = data["data"]["search"]["products"]
        except KeyError:
            raise RuntimeError(
                "Target RedSky response shape changed or the API key is stale; "
                "set TARGET_API_KEY to a fresh value."
            )

        products: list[Product] = []
        for item in items:
            item_data = item.get("item", {})
            tcin = item_data.get("tcin")
            title = item_data.get("product_description", {}).get("title", query)
            price = item.get("price", {}).get("current_retail")
            fulfillment = item.get("fulfillment", {})
            shipping = fulfillment.get("shipping_options", {})
            availability = shipping.get("availability_status")
            in_stock = availability == "IN_STOCK"

            products.append(
                Product(
                    retailer=self.name,
                    name=title,
                    url=f"https://www.target.com/p/-/A-{tcin}" if tcin else "https://www.target.com",
                    price=f"${price}" if price is not None else None,
                    in_stock=in_stock,
                )
            )
        return products
