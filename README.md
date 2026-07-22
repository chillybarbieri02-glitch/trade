# Pokémon Restock Bot

Checks Pokémon Center, Target, Walmart, and Best Buy for in-stock Pokémon TCG
products and posts alerts to a Discord webhook. Runs on a schedule via GitHub
Actions, so there's nothing to host yourself.

## How it works

Every 15 minutes, a GitHub Actions workflow (`.github/workflows/restock-check.yml`)
runs `python -m restock_bot.main`, which:

1. Searches each retailer for the terms configured in `restock_bot/config.py`
   (defaults: "pokemon booster box", "pokemon elite trainer box").
2. Compares in-stock results against `state/seen_in_stock.json` (committed
   back to the repo each run) so you're only alerted once per restock, not
   every 15 minutes while an item stays in stock.
3. Posts a Discord embed for anything newly in stock.

Each retailer lives in its own module under `restock_bot/retailers/`, so
adding a new retailer or search term doesn't require touching the others.

## Setup

1. **Add the Discord webhook as a repo secret** (required):
   Repo → Settings → Secrets and variables → Actions → New repository secret
   → name `DISCORD_WEBHOOK_URL`, value your webhook URL.

2. **Optional: Best Buy** — Best Buy blocks scraping, so this uses their
   official Products API instead. Get a free key at
   https://developer.bestbuy.com/ and add it as a repo secret named
   `BESTBUY_API_KEY`. Without it, Best Buy checks are skipped (logged as a
   warning, not an error).

3. **Optional: Target** — uses the same public search API target.com's own
   frontend calls, with a default client key baked in. If Target requests
   start failing, that key may have rotated; add a repo secret named
   `TARGET_API_KEY` with a fresh value.

4. **Enable the workflow to actually run on schedule** — GitHub only fires
   `schedule` triggers for workflow files on the repo's *default* branch.
   This bot was built on a feature branch, so merge it into the default
   branch (or make this branch the default) before the cron schedule starts
   firing. Until then, you can still trigger it manually from the Actions
   tab ("Run workflow").

## Customizing what it searches for

Edit `restock_bot/config.py` — it's a plain dict of retailer → list of search
terms. Add, remove, or narrow terms there; each one is a separate request per
run, so keep the list focused.

## Running locally

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in DISCORD_WEBHOOK_URL at minimum
export $(cat .env | xargs)
python -m restock_bot.main
```

## A note on fragility

Pokémon Center, Target, and Walmart are checked by parsing their public
search pages/APIs rather than official product APIs (they don't offer one).
Retailers change their site markup periodically, which can silently break a
selector — if a retailer stops producing alerts, check the Actions run logs
for warnings like "search failed" or "structure changed", and update the
corresponding file in `restock_bot/retailers/`. Best Buy uses an official API
instead specifically to avoid this problem.

Requests run once per search term per retailer every 15 minutes — intended
for personal restock monitoring, not high-frequency polling.
