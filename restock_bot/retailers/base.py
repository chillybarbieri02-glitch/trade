from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:
    retailer: str
    name: str
    url: str
    price: Optional[str] = None
    in_stock: bool = False

    @property
    def key(self) -> str:
        return f"{self.retailer}:{self.url}"


class RetailerChecker:
    """Base class for a retailer-specific stock checker."""

    name: str = "base"

    def search(self, query: str) -> list[Product]:
        raise NotImplementedError
