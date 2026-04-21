"""
Fiesta Fresh Cleaning — Weekly Facebook Group Poster (AI Cloud Edition)
=============================================================================
Designed to run on GitHub Actions at specific hours based on the schedule.
Uses Google Gemini to rewrite the master post uniquely every time.
"""

import json
import logging
import os
import random
import sys
import time
from datetime import datetime, date
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

try:
    import google.generativeai as genai
except ImportError:
    print("ERROR: google-generativeai not installed. Run: pip install google-generativeai")
    sys.exit(1)

# ── Load config ───────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "config.json"
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

FB_EMAIL    = os.environ.get("FB_EMAIL")    or CONFIG["facebook"]["email"]
FB_PASSWORD = os.environ.get("FB_PASSWORD") or CONFIG["facebook"]["password"]
GEMINI_KEY  = os.environ.get("GEMINI_API_KEY")

SCHEDULE     = CONFIG["schedule"]
TIMEZONE     = SCHEDULE["timezone"]
AI_SETTINGS  = CONFIG["ai_settings"]

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

# ── AI Generation ─────────────────────────────────────────────────────────────
def generate_ai_post() -> str:
    if not GEMINI_KEY:
        log.error("GEMINI_API_KEY is not set. Falling back to master post.")
        return AI_SETTINGS["master_post"]
    
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        system_instruction=AI_SETTINGS["system_prompt"]
    )
    
    prompt = f"Rewrite this master post following your brand instructions EXACTLY:\n\n{AI_SETTINGS['master_post']}"
    
    log.info("Generating fresh AI variation of the post...")
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        log.info("AI generation successful.")
        return text
    except Exception as e:
        log.error(f"AI generation failed: {e}")
        return AI_SETTINGS["master_post"]

# ── Photo Selection ───────────────────────────────────────────────────────────
def pick_random_photo() -> str:
    photos_dir = Path(__file__).parent / "photos"
    if not photos_dir.exists():
        return ""
    
    valid_exts = {".jpg", ".jpeg", ".png", ".webp"}
    photos = [p for p in photos_dir.iterdir() if p.is_file() and p.suffix.lower() in valid_exts]
    
    if not photos:
        return ""
        
    chosen = random.choice(photos)
    return str(chosen.resolve())

# ── Validation ────────────────────────────────────────────────────────────────
def validate_config():
    errors = []
    if not FB_EMAIL or "YOUR_FACEBOOK_EMAIL" in FB_EMAIL:
        errors.append("Facebook email not set — add FB_EMAIL as a GitHub secret.")
    if not FB_PASSWORD or "YOUR_FACEBOOK_PASSWORD" in FB_PASSWORD:
        errors.append("Facebook password not set — add FB_PASSWORD as a GitHub secret.")
    if errors:
        for e in errors:
            log.error(f"CONFIG ERROR: {e}")
        sys.exit(1)
    log.info("Config OK.")

# ── Schedule helpers ──────────────────────────────────────────────────────────
def get_current_scheduled_groups() -> list:
    """
    Looks up the schedule for the current Day and current Hour.
    """
    now = datetime.now(TZ)
    day_name = now.strftime("%A")     # e.g., "Monday"
    hour_str = now.strftime("%H")     # e.g., "09"

    log.info(f"Checking schedule for {day_name} at hour {hour_str}:00...")
    
    if day_name in SCHEDULE and hour_str in SCHEDULE[day_name]:
        return SCHEDULE[day_name][hour_str]
    
    return []

# ── Post history ──────────────────────────────────────────────────────────────
def load_history() -> dict:
    if Path(HISTORY_FILE).exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"posts": {}}

def save_history(data: dict):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def was_posted_today(history: dict, group_url: str) -> bool:
    if group_url not in history["posts"]:
        return False
    last_date = datetime.fromisoformat(history["posts"][group_url]).date()
    return last_date == datetime.now(TZ).date()

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


def post_to_group(page, group_url: str, post_text: str, photo_path: str) -> bool:
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

    # Upload photo if any
    if photo_path:
        log.info(f"  Attaching photo: {Path(photo_path).name}")
        try:
            file_input = page.locator("input[type='file'][accept*='image']").last
            if file_input.count() > 0:
                file_input.set_input_files(photo_path)
                human_delay(5, 8) # Waiting longer for photo upload preview to process
            else:
                log.warning("  Could not find the file input selector.")
        except Exception as e:
            log.warning(f"  Failed to attach photo: {e}")

    text_box.click()
    human_delay(0.5, 1.5)
    page.keyboard.insert_text(post_text)
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
                group_id = Path(group_url).name
                page.screenshot(path=f"screenshot_01_filled_{group_id}.png", full_page=True)

                if btn.get_attribute("aria-disabled") == "true" or btn.get_attribute("disabled") is not None:
                    log.error(f"  CRITICAL: Facebook Post button is visibly GRAYED OUT/DISABLED.")
                    log.error("  Taking failure screenshot and aborting this post...")
                    page.screenshot(path=f"screenshot_02_failed_disabled_{group_id}.png", full_page=True)
                    page.keyboard.press("Escape")
                    return False

                btn.click()
                log.info("  Waiting 20 seconds for Facebook's background photo upload to finish...")
                time.sleep(20)
                log.info(f"  ✅ Posted.")
                page.screenshot(path=f"screenshot_03_success_{group_id}.png", full_page=True)
                return True
        except Exception:
            continue

    log.warning(f"  Could not find Post button.")
    page.screenshot(path="screenshot_02_failed_missing_btn.png", full_page=True)
    page.keyboard.press("Escape")
    return False

# ── Main — runs check, posts, exits cleanly ──────────────────────────────────
def main():
    validate_config()

    today      = datetime.now(TZ)
    day_name   = today.strftime("%A %d %b %Y")

    log.info(f"{'='*60}")
    log.info(f"Fiesta Fresh AI Poster — {day_name}")
    log.info(f"Mode: {'⚪ DRY RUN' if DRY_RUN else '🔴 LIVE'}")
    log.info(f"{'='*60}")

    groups_to_post = get_current_scheduled_groups()

    if not groups_to_post:
        log.info("No groups scheduled for this hour. Going back to sleep. 💤")
        sys.exit(0)

    history = load_history()
    pending = [g for g in groups_to_post if not was_posted_today(history, g)]
    
    if not pending:
        log.info("Already posted to scheduled groups for this hour today. Exiting.")
        sys.exit(0)
        
    log.info(f"Groups to post this hour: {len(pending)}")

    # Generate the unique AI post for this run
    ai_post_text = generate_ai_post()
    
    # Pick a random photo globally for this run
    photo_path = pick_random_photo()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
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
            success = post_to_group(page, group_url, ai_post_text, photo_path)

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
    log.info(f"Done — ✅ {success_count} AI variations posted | ❌ {fail_count} failed")
    log.info(f"{'='*60}")
    sys.exit(0)

if __name__ == "__main__":
    main()
