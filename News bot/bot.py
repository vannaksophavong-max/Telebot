"""
Telegram Macro Analysis Bot
============================
Pulls (mock) macro news/data inputs, analyzes them with Google Gemini
(gemini-2.5-flash via the official google-genai SDK), and pushes a formatted
Markdown alert to a Telegram chat. Deduplicates alerts using a local
sent_alerts.json file.

SETUP
-----
1. pip install requests google-genai
2. Paste your keys in the CONFIG section below (or set them as environment
   variables GEMINI_API_KEY / TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).
3. Run: python bot.py
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime, timezone

import requests
from google import genai
from google.genai import types

# ============================================================
# CONFIG — paste your keys here, or rely on environment variables
# ============================================================
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

GEMINI_MODEL = "gemini-2.5-flash"
SENT_ALERTS_FILE = "sent_alerts.json"
POLL_INTERVAL_SECONDS = 60

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("macro_bot")

# ============================================================
# SYSTEM INSTRUCTION FOR GEMINI
# ============================================================
SYSTEM_INSTRUCTION = """You are an elite global macro hedge fund strategist. Your task is to analyze the provided financial news headline from a specific source.
Provide your response strictly in the following Markdown format for Telegram:
**🚨 FLASH MACRO ALERT: [Short Event Name]**
**📰 The News:** 
[Summarize the event in 1 clear, scannable sentence. Bold all key data figures or percentage points.]
**📈 Market Direction Impact:**
* **[Primary Impacted Asset/Currency, e.g., US Dollar (DXY) or S&P 500]:** [🟢 UP / 🔴 DOWN / 🟡 NEUTRAL]
**🧠 Why This Happens:**
[Provide a punchy, 2-to-3 sentence economic analysis explaining the exact mechanical causal relationship driving this market movement. Keep the language highly accessible for mobile viewing.]"""


# ============================================================
# STEP 1: DATA INGESTION STUBS
# ============================================================
def fetch_forex_factory():
    """
    STUB: Simulates pulling a high-impact economic data release from
    ForexFactory's calendar. In production, replace this with a real
    scraper/API call (ForexFactory has no official public API, so this
    typically requires scraping their calendar JSON endpoint or an
    economic-calendar provider like TradingEconomics).
    """
    return {
        "source": "ForexFactory",
        "headline": "US Unemployment Rate falls to 3.8% vs 4.0% expected",
    }


def fetch_polymarket():
    """
    STUB: Simulates a sudden shift in prediction market odds pulled from
    Polymarket. In production, replace with a call to Polymarket's public
    CLOB/Gamma API to detect large probability swings on a tracked market.
    """
    return {
        "source": "Polymarket",
        "headline": "Odds of a Fed 50bps rate cut in September crash from 60% to 15%",
    }


def fetch_bloomberg_alternative():
    """
    STUB: Simulates a breaking macro headline from a Bloomberg-alternative
    news wire. In production, replace with a real news API (e.g. NewsAPI,
    Benzinga, Finnhub) filtered for high-impact macro keywords.
    """
    return {
        "source": "Bloomberg Alternative Wire",
        "headline": "ECB officials signal aggressive interest rate cuts ahead due to slowing growth",
    }


def get_all_news_items():
    """Aggregate results from every ingestion stub into one list."""
    fetchers = [fetch_forex_factory, fetch_polymarket, fetch_bloomberg_alternative]
    items = []
    for fetch in fetchers:
        try:
            items.append(fetch())
        except Exception as e:
            log.error(f"Error fetching from {fetch.__name__}: {e}")
    return items


# ============================================================
# DEDUPLICATION (sent_alerts.json)
# ============================================================
def load_sent_alerts():
    if not os.path.exists(SENT_ALERTS_FILE):
        return {}
    try:
        with open(SENT_ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"Could not read {SENT_ALERTS_FILE} ({e}); starting fresh.")
        return {}


def save_sent_alerts(sent_alerts):
    try:
        with open(SENT_ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(sent_alerts, f, indent=2)
    except OSError as e:
        log.error(f"Failed to write {SENT_ALERTS_FILE}: {e}")


def hash_headline(source, headline):
    """Create a stable hash key for a (source, headline) pair."""
    raw = f"{source}::{headline}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


# ============================================================
# STEP 2: GEMINI AI ANALYSIS ENGINE
# ============================================================
def analyze_news(source, headline):
    """
    Sends the headline to Gemini (gemini-2.5-flash) with a strict system
    instruction that forces a Summary + Direction + Why-analysis structure,
    formatted for Telegram Markdown.

    Returns the formatted Markdown string, or None on failure.
    """
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        user_prompt = f"Source: {source}\nHeadline: {headline}"

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.4,
            ),
        )

        text = response.text
        if not text:
            log.error("Gemini returned an empty response.")
            return None
        return text.strip()

    except Exception as e:
        # Catches rate limits, auth errors, network errors, etc.
        log.error(f"Gemini API error while analyzing '{headline[:60]}...': {e}")
        return None


# ============================================================
# STEP 3: TELEGRAM DELIVERY ROUTER
# ============================================================
def send_to_telegram(formatted_text):
    """
    Sends the finalized Markdown text to the configured Telegram chat
    using the Bot API sendMessage endpoint.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": formatted_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)

        if resp.status_code == 429:
            # Telegram rate limit — respects the 'retry_after' hint if present
            retry_after = resp.json().get("parameters", {}).get("retry_after", 5)
            log.warning(f"Telegram rate-limited. Retry after {retry_after}s.")
            time.sleep(retry_after)
            resp = requests.post(url, json=payload, timeout=15)

        if not resp.ok:
            log.error(f"Telegram API error {resp.status_code}: {resp.text}")

        if not resp.ok:
            log.error(f"Telegram API error {resp.status_code}: {resp.text}")

        resp.raise_for_status()
        log.info("Alert successfully sent to Telegram.")
        return True

    except requests.exceptions.RequestException as e:
        log.error(f"Failed to send message to Telegram: {e}")
        return False


# ============================================================
# STEP 4: MAIN ORCHESTRATION LOOP
# ============================================================
def process_cycle(sent_alerts):
    """Runs a single pass: fetch -> dedupe -> analyze -> send -> log."""
    news_items = get_all_news_items()

    for item in news_items:
        source = item["source"]
        headline = item["headline"]
        key = hash_headline(source, headline)

        if key in sent_alerts:
            log.info(f"Skipping duplicate: [{source}] {headline[:60]}...")
            continue

        log.info(f"New item detected: [{source}] {headline}")

        analysis = analyze_news(source, headline)
        if analysis is None:
            log.warning("Skipping send due to failed analysis (will retry next cycle).")
            continue

        sent_ok = send_to_telegram(analysis)
        if sent_ok:
            sent_alerts[key] = {
                "source": source,
                "headline": headline,
                "sent_at": datetime.now(timezone.utc).isoformat(),
            }
            save_sent_alerts(sent_alerts)
        else:
            log.warning("Send failed; will retry this headline next cycle.")


def main():
    log.info("Starting Macro Analysis Bot...")

    if "PASTE_YOUR" in GEMINI_API_KEY or "PASTE_YOUR" in TELEGRAM_BOT_TOKEN or "PASTE_YOUR" in TELEGRAM_CHAT_ID:
        log.warning(
            "One or more credentials still contain placeholder values. "
            "Set GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, and TELEGRAM_CHAT_ID "
            "in the CONFIG section (or as environment variables) before running for real."
        )

    sent_alerts = load_sent_alerts()

    while True:
        try:
            process_cycle(sent_alerts)
        except Exception as e:
            # Top-level safety net so the loop never dies from one bad cycle
            log.error(f"Unhandled error during cycle: {e}")

        log.info(f"Sleeping {POLL_INTERVAL_SECONDS}s until next check...")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()