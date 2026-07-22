import logging
import sys

from .config import SEARCHES
from .notifier import DiscordNotifier
from .retailers import BestBuyChecker, PokemonCenterChecker, TargetChecker, WalmartChecker
from .retailers.base import RetailerChecker
from .state import StateStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("restock_bot")

CHECKERS: dict[str, RetailerChecker] = {
    "pokemon_center": PokemonCenterChecker(),
    "target": TargetChecker(),
    "walmart": WalmartChecker(),
    "best_buy": BestBuyChecker(),
}


def run() -> int:
    state = StateStore()
    previously_seen = state.load()
    notifier = DiscordNotifier()

    currently_in_stock: set[str] = set()
    restocks = []

    for retailer_id, checker in CHECKERS.items():
        for query in SEARCHES.get(retailer_id, []):
            try:
                products = checker.search(query)
            except Exception as exc:
                log.warning("%s search for %r failed: %s", checker.name, query, exc)
                continue

            for product in products:
                if not product.in_stock:
                    continue
                currently_in_stock.add(product.key)
                if product.key not in previously_seen:
                    restocks.append(product)

    for product in restocks:
        log.info("RESTOCK: %s - %s (%s)", product.retailer, product.name, product.url)
        try:
            notifier.send_restock(product)
        except Exception as exc:
            log.error("Failed to send Discord alert for %s: %s", product.name, exc)

    state.save(currently_in_stock)
    log.info(
        "Checked %d retailer(s), found %d new restock(s), %d item(s) currently in stock",
        len(CHECKERS),
        len(restocks),
        len(currently_in_stock),
    )
    return 0


if __name__ == "__main__":
    sys.exit(run())
