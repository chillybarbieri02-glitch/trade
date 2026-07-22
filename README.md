# Pokémon Restock Bot

Checks retailers for in-stock Pokémon TCG products and posts alerts to a
Discord webhook. Runs on a schedule via GitHub Actions, so there's nothing to
host yourself.

> This repo also contains [`ar_assistant/`](ar_assistant/README.md), an
> unrelated project: an AI accounts-receivable assistant for small
> businesses. See its own README for setup.

## Current retailer status (verified against live sites)

| Retailer | Status | Why |
|---|---|---|
| Best Buy | **Works**, once you add an API key | Uses Best Buy's official Products API |
| Pokémon Center | Blocked | Incapsula/Imperva bot-challenge page on every request |
| Walmart | Blocked | PerimeterX bot-challenge ("Robot or human?") on every request |
| Target | Blocked | The search page loads, but the client-side data API (RedSky) returns 403/410 to scripted requests |

Only Best Buy is reliably automatable right now. Pokémon Center, Walmart, and
Target all front their sites/APIs with dedicated anti-bot vendors that reject
plain HTTP requests regardless of headers used. Getting past that would mean
building headless-browser stealth automation specifically to evade that
protection — that's not something this bot does. Their checkers are still in
the code (`restock_bot/retailers/`) and run every cycle, but expect them to
mostly log "search failed" warnings rather than find anything. If you want
reliable coverage for those three, your best options are:

- Sign up for the retailer's own "notify me when back in stock" feature
  directly on the product page — this is the one channel bot protection
  doesn't apply to, since it's a first-party feature.
- Use an official API where one exists for a retailer you care about (e.g.
  Amazon's Product Advertising API, if you have an Associates account) —
  swap in a new checker module the same way `best_buy.py` is built.

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

2. **Best Buy** (the retailer that actually works): get a free key at
   https://developer.bestbuy.com/ and add it as a repo secret named
   `BESTBUY_API_KEY`. Without it, Best Buy checks are skipped (logged as a
   warning, not an error).

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

## Re-diagnosing a retailer

`restock_bot/debug_probe.py` (run via the "Debug Retailer Probe" workflow,
Actions tab → Run workflow) fetches each retailer directly and prints status
codes, redirect targets, and body snippets — use it if you suspect a
retailer's blocking behavior changed, before guessing at fixes blind.

Requests run once per search term per retailer every 15 minutes — intended
for personal restock monitoring, not high-frequency polling.
