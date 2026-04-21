"""
Facebook Cookie Extractor Tool
================================
Run this script locally on your Mac to generate a trusted session for GitHub Actions.
"""
import sys
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright is missing. Install it by running:")
    print("pip install playwright && playwright install chromium")
    sys.exit(1)

def main():
    print("=" * 60)
    print("🚀 FIESTA FRESH - TRUSTED COOKIE GENERATOR 🚀")
    print("=" * 60)
    print("\nInstructions:")
    print("1. A Chromium browser window will open automatically.")
    print("2. Log in to Facebook normally and solve ANY captchas if they appear.")
    print("3. Wait until you see your normal Facebook News Feed.")
    print("4. ONCE YOU SEE THE NEWS FEED, come back to this terminal and press Enter.")
    print("\nStarting browser now...\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False) # Headless=False so the user can see to log in!
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://www.facebook.com/")

        # Halt the script until the user physically presses Enter in their terminal
        input("\n[WAITING] 👉 Press ENTER here ONLY AFTER you are fully logged in and seeing your feed...")

        print("\n📸 Extracting trusted digital fingerprint (Cookies/Tokens)...")
        context.storage_state(path="fb_trusted_session.json")
        browser.close()

    print("\n✅ SUCCESS! Your session has been securely extracted to: fb_trusted_session.json")
    print("You can now copy the contents of that file and paste it into GitHub Secrets!")
    print("=" * 60)

if __name__ == "__main__":
    main()
