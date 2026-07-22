import logging
import os

import requests

from .retailers.base import Product

log = logging.getLogger("restock_bot.notifier")


class DiscordNotifier:
    def __init__(self, webhook_url: str | None = None) -> None:
        self.webhook_url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")

    def send_restock(self, product: Product) -> None:
        if not self.webhook_url:
            log.warning("No DISCORD_WEBHOOK_URL configured; skipping alert for %s", product.name)
            return

        embed = {
            "title": product.name,
            "url": product.url,
            "description": f"Back in stock at {product.retailer}!",
            "color": 0x2ECC71,
        }
        if product.price:
            embed["fields"] = [{"name": "Price", "value": product.price, "inline": True}]

        payload = {
            "username": "Pokémon Restock Bot",
            "embeds": [embed],
        }
        resp = requests.post(self.webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
