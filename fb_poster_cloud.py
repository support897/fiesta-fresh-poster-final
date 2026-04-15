"""
Fiesta Fresh Cleaning — Weekly Facebook Group Poster (GitHub Actions Edition)
=============================================================================
Designed to run on GitHub Actions — wakes up, posts today's groups, exits.
Scheduling is handled by GitHub (.github/workflows/poster.yml), not this script.

HOW IT WORKS:
- GitHub wakes this script up every day at 9:30am Brisbane time
- Script checks which groups are assigned to today
- Posts to each group with a delay between each one
- Exits cleanly when done

ROTATING SCHEDULE (50 groups example):
  Monday:    Groups 1-7    (template variation 1)
  Tuesday:   Groups 8-14   (template variation 2)
  Wednesday: Groups 15-21  (template variation 3)
  Thursday:  Groups 22-28  (template variation 4)
  Friday:    Groups 29-35  (template variation 5)
  Saturday:  Groups 36-42  (template variation 6)
  Sunday:    Groups 43-50  (template variation 7)
"""

import json
import logging
import os
import random
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path

try:
    import pytz
except ImportError:
    print("ERROR: pytz not installed. Run: pip install pytz")
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("ERROR: Playwright not installed.")
    sys.exit(1)

# ── Load config ───────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# GitHub Actions injects secrets as environment variables
# Falls back to config.json values for local testing
FB_EMAIL    = os.environ.get("FB_EMAIL")    or CONFIG["facebook"]["email"]
FB_PASSWORD = os.environ.get("FB_PASSWORD") or CONFIG["facebook"]["password"]

# Filter out placeholder lines from groups and templates
GROUPS = [
    g for g in CONFIG["groups"]
    if g.startswith("https://www.facebook.com/groups/")
    and "GROUP_URL_" not in g
    and "PASTE" not in g
    and "══" not in g
]

TEMPLATES = [
    t for t in CONFIG["post_templates"]
    if "PASTE YOUR POST TEMPLATE" not in t
    and "══" not in t
    and len(t.strip()) > 30
]

SCHEDULE     = CONFIG["schedule"]
TIMEZONE     = SCHEDULE["timezone"]
PER_DAY      = SCHEDULE["groups_per_day"]

S            = CONFIG["settings"]
DRY_RUN      = S["dry_run"]
MIN_DELAY    = S["min_delay_between_posts_seconds"]
MAX_DELAY    = S["max_delay_between_posts_seconds"]
MIN_PAGE     = S["min_delay_page_load_seconds"]
MAX_PAGE     = S["max_delay_page_load_seconds"]
HISTORY_FILE = S["post_history_file"]

TZ = pytz.timezone(TIMEZONE)

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ── Validation ────────────────────────────────────────────────────────────────
def validate_config():
    errors = []
    if not FB_EMAIL or "YOUR_FACEBOOK_EMAIL" in FB_EMAIL:
        errors.append("Facebook email not set — add FB_EMAIL as a GitHub secret.")
    if not FB_PASSWORD or "YOUR_FACEBOOK_PASSWORD" in FB_PASSWORD:
        errors.append("Facebook password not set — add FB_PASSWORD as a GitHub secret.")
    if not GROUPS:
        errors.append("No group URLs found — replace GROUP_URL_X placeholders in config.json.")
    if not TEMPLATES:
        errors.append("No post templates found — replace placeholder text in config.json.")
    if errors:
        for e in errors:
            log.error(f"CONFIG ERROR: {e}")
        sys.exit(1)
    log.info(f"Config OK — {len(GROUPS)} groups | {len(TEMPLATES)} templates")

# ── Schedule helpers ──────────────────────────────────────────────────────────
def get_todays_groups() -> list:
    """
    Returns the slice of groups assigned to today based on a 7-day rotation.
    Same groups always post on the same weekday every week.
    """
    total     = len(GROUPS)
    day_index = datetime.now(TZ).weekday()  # 0=Monday, 6=Sunday
    start     = day_index * PER_DAY
    end       = start + PER_DAY

    if start >= total:
        return []

    return GROUPS[start:min(end, total)]


def pick_template(day_index: int) -> str:
    """Rotate through template variations by day of week."""
    if not TEMPLATES:
        return ""
    return TEMPLATES[day_index % len(TEMPLATES)]

# ── Post history ──────────────────────────────────────────────────────────────
def load_history() -> dict:
    if Path(HISTORY_FILE).exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"posts": {}}


def save_history(data: dict):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def was_posted_this_week(history: dict, group_url: str) -> bool:
    if group_url not in history["posts"]:
        return False
    last_date = datetime.fromisoformat(history["posts"][group_url]).date()
    return (date.today() - last_date).days < 6


def record_post(history: dict, group_url: str):
    history["posts"][group_url] = datetime.now(TZ).isoformat()

# ── Human-like helpers ────────────────────────────────────────────────────────
def human_delay(min_s: float, max_s: float):
    time.sleep(random.uniform(min_s, max_s))


def human_type(element, text: str):
    for char in text:
        element.type(char, delay=random.randint(45, 135))
        if random.random() < 0.04:
            time.sleep(random.uniform(0.1, 0.4))


def scroll_down(page):
    page.evaluate(f"window.scrollBy(0, {random.randint(200, 500)})")
    time.sleep(random.uniform(0.5, 1.5))

# ── Facebook automation ───────────────────────────────────────────────────────
def login(page):
    log.info("Logging in to Facebook...")
    page.goto("https://www.facebook.com/login", wait_until="domcontentloaded")
    human_delay(2, 4)

    for cookie_text in ["Allow all cookies", "Accept all"]:
        try:
            btn = page.locator(f'button:has-text("{cookie_text}")').first
            if btn.count() > 0:
                btn.click()
                human_delay(1, 2)
                break
        except Exception:
            pass

    email_field = page.locator("#email")
    email_field.wait_for(timeout=8000)
    email_field.click()
    human_delay(0.3, 0.8)
    human_type(email_field, FB_EMAIL)
    human_delay(0.5, 1.2)

    pass_field = page.locator("#pass")
    pass_field.click()
    human_delay(0.3, 0.8)
    human_type(pass_field, FB_PASSWORD)
    human_delay(0.8, 1.5)

    page.keyboard.press("Enter")
    page.wait_for_load_state("networkidle", timeout=20000)
    human_delay(3, 5)

    if "login" in page.url.lower():
        raise RuntimeError(
            "Login failed — check FB_EMAIL and FB_PASSWORD in your GitHub secrets."
        )
    log.info("Logged in ✓")


def post_to_group(page, group_url: str, post_text: str) -> bool:
    """Navigate to a group and post. Returns True on success."""
    log.info(f"  → {group_url}")

    try:
        page.goto(group_url, wait_until="domcontentloaded", timeout=20000)
    except PlaywrightTimeout:
        log.warning(f"  Timeout — skipping.")
        return False

    human_delay(MIN_PAGE, MAX_PAGE)
    scroll_down(page)
    human_delay(1, 2)

    # Click the post composer
    clicked = False
    for sel in [
        '[aria-label="Write something..."]',
        '[aria-label*="Write something"]',
        'span:has-text("Write something...")',
        '[role="button"]:has-text("Write something")',
    ]:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                el.click()
                clicked = True
                human_delay(1.5, 3)
                break
        except Exception:
            continue

    if not clicked:
        log.warning(f"  Could not find post composer — group may have restrictions.")
        return False

    # Find text input
    text_box = None
    for sel in [
        '[contenteditable="true"][aria-label*="What"]',
        '[contenteditable="true"][role="textbox"]',
        '[contenteditable="true"]',
    ]:
        try:
            candidate = page.locator(sel).last
            if candidate.count() > 0:
                text_box = candidate
                break
        except Exception:
            continue

    if not text_box:
        log.warning(f"  Could not find text input.")
        return False

    text_box.click()
    human_delay(0.5, 1.5)
    human_type(text_box, post_text)
    human_delay(2, 4)

    if DRY_RUN:
        log.info(f"  [DRY RUN] Would post: {post_text[:100]}...")
        page.keyboard.press("Escape")
        human_delay(1, 2)
        return True

    # Click Post button
    for sel in [
        'div[aria-label="Post"][role="button"]',
        'button[type="submit"]:has-text("Post")',
        '[data-testid="react-composer-post-button"]',
    ]:
        try:
            btn = page.locator(sel).last
            if btn.count() > 0:
                btn.click()
                human_delay(3, 5)
                log.info(f"  ✅ Posted.")
                return True
        except Exception:
            continue

    log.warning(f"  Could not find Post button.")
    page.keyboard.press("Escape")
    return False

# ── Main — runs once and exits cleanly ───────────────────────────────────────
def main():
    validate_config()

    today      = datetime.now(TZ)
    day_index  = today.weekday()
    day_name   = today.strftime("%A %d %b %Y")

    log.info(f"{'='*60}")
    log.info(f"Fiesta Fresh Poster — {day_name}")
    log.info(f"Mode: {'⚪ DRY RUN' if DRY_RUN else '🔴 LIVE'}")
    log.info(f"{'='*60}")

    todays_groups = get_todays_groups()

    if not todays_groups:
        log.info("No groups assigned for today. Exiting.")
        sys.exit(0)

    history  = load_history()
    template = pick_template(day_index)

    if not template:
        log.error("No post template found. Fill in config.json → post_templates.")
        sys.exit(1)

    pending = [g for g in todays_groups if not was_posted_this_week(history, g)]

    log.info(f"Today's groups: {len(todays_groups)} | Pending: {len(pending)}")

    if not pending:
        log.info("All today's groups already posted this week. Exiting.")
        sys.exit(0)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,   # invisible — no screen needed on GitHub's servers
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )

        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 768},
            locale="en-AU",
            timezone_id="Australia/Brisbane",
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-AU', 'en'] });
        """)

        page = context.new_page()

        try:
            login(page)
        except RuntimeError as e:
            log.error(str(e))
            browser.close()
            sys.exit(1)

        success_count = 0
        fail_count    = 0

        for i, group_url in enumerate(pending, 1):
            log.info(f"[{i}/{len(pending)}]")
            success = post_to_group(page, group_url, template)

            if success:
                if not DRY_RUN:
                    record_post(history, group_url)
                    save_history(history)
                success_count += 1
            else:
                fail_count += 1

            if i < len(pending):
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                log.info(f"  Waiting {delay/60:.1f} min before next post...")
                time.sleep(delay)

        browser.close()

    log.info(f"{'='*60}")
    log.info(f"Done — ✅ {success_count} posted | ❌ {fail_count} failed")
    log.info(f"{'='*60}")
    sys.exit(0)  # ← Tells GitHub Actions: job complete, all good


if __name__ == "__main__":
    main()
