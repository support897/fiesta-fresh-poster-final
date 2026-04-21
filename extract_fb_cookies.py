import sys
import time
import json

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    pass

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        page.goto("https://www.facebook.com/")

        print("Chrome is open! Please log into Facebook.")
        print("This script is continuously backing up your cookies in the background.")
        
        # Loop infinitely and constantly save cookies every 3 seconds.
        # This completely removes the need for terminal inputs or buggy macOS popup alerts.
        while True:
            time.sleep(3)
            try:
                if page.is_closed():
                    break
                
                # Constantly overwrite the trusted session safely
                context.storage_state(path="fb_trusted_session.json")
            except Exception:
                break

        print("Browser was closed! Your final cookies are safely locked in fb_trusted_session.json")

if __name__ == "__main__":
    main()
