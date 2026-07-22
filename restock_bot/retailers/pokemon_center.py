import requests
from bs4 import BeautifulSoup

from .base import Product, RetailerChecker

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class PokemonCenterChecker(RetailerChecker):
    """Scrapes Pokémon Center's search results page.

    Pokémon Center runs on Salesforce Commerce Cloud. Product tiles and
    out-of-stock markers occasionally change class names during site
    redesigns — if this consistently returns zero products, inspect a
    fresh search page and update the selectors below.
    """

    name = "Pokémon Center"
    search_url = "https://www.pokemoncenter.com/search/index?q={query}"

    def search(self, query: str) -> list[Product]:
        url = self.search_url.format(query=requests.utils.quote(query))
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        products: list[Product] = []
        tiles = soup.select("[data-testid='product-tile'], li.product-tile, div.product-tile")
        for tile in tiles:
            link = tile.select_one("a[href]")
            if not link:
                continue
            href = link["href"]
            product_url = href if href.startswith("http") else f"https://www.pokemoncenter.com{href}"

            name_el = tile.select_one(
                "[data-testid='product-name'], .product-name, .pdp-link, img[alt]"
            )
            if name_el is not None and name_el.name == "img":
                name = name_el.get("alt", query)
            else:
                name = name_el.get_text(strip=True) if name_el else link.get_text(strip=True)
            name = name or query

            tile_text = tile.get_text(" ", strip=True).lower()
            out_of_stock = "out of stock" in tile_text or "sold out" in tile_text
            notify_me = "notify me" in tile_text

            price_el = tile.select_one(".price, [data-testid='price'], .product-price")
            price = price_el.get_text(strip=True) if price_el else None

            products.append(
                Product(
                    retailer=self.name,
                    name=name,
                    url=product_url,
                    price=price,
                    in_stock=not (out_of_stock or notify_me),
                )
            )
        return products
