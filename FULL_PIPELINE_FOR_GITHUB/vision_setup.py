"""
vision_setup.py - ONE-TIME SETUP for VisionIAS Monthly Magazine access.

Navigates directly to the monthly magazine archive.
Whatever login page appears — fill in your credentials there.
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

SESSION_FILE = Path(__file__).parent / "vision_session.json"
BROWSER_DATA = Path(__file__).parent / "vision_browser_data"
BROWSER_DATA.mkdir(exist_ok=True)

# The EXACT page we need access to
TARGET_URL = "https://visionias.in/current-affairs/monthly-magazine/archive"

def run_setup():
    print("=" * 60)
    print("VisionIAS - Monthly Magazine Login Setup")
    print("=" * 60)
    print()
    print(f"Will open: {TARGET_URL}")
    print()
    print("INSTRUCTIONS:")
    print("  1. Browser opens — it goes directly to the magazine page")
    print("  2. If it redirects to a login page — log in there")
    print("  3. After login, you should see the magazine archive")
    print("  4. Come back here and press ENTER to save your session")
    print()
    input("Press ENTER to open the browser...")
    print()
    print("Opening browser...")

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA),
            headless=False,
            slow_mo=50,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            ignore_default_args=["--enable-automation"],
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport=None,
            locale="en-US",
        )

        page = context.new_page()

        # Remove webdriver fingerprint
        page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
        )

        # Go DIRECTLY to the magazine archive
        print(f"Navigating to: {TARGET_URL}")
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)

        print()
        print(f"Current URL: {page.url}")
        print()
        print("-" * 60)
        print("The browser is now open.")
        print()
        print("→ If you see a LOGIN FORM: fill in your credentials")
        print("    Email:    [YOUR_EMAIL]")
        print("    Password: [YOUR_PASSWORD]")
        print()
        print("→ After login you should see the magazine archive")
        print("   with monthly PDFs listed.")
        print("-" * 60)
        print()

        input("Press ENTER here once you can see the magazine PDFs: ")
        print()

        final_url = page.url
        print(f"Final URL: {final_url}")

        # Save session
        context.storage_state(path=str(SESSION_FILE))
        context.close()

    print()
    if SESSION_FILE.exists():
        state     = json.loads(SESSION_FILE.read_text())
        n_cookies = len(state.get("cookies", []))
        size_kb   = SESSION_FILE.stat().st_size // 1024
        print(f"✅ Session saved!")
        print(f"   File:    {SESSION_FILE}")
        print(f"   Cookies: {n_cookies}  |  Size: {size_kb} KB")
        print()
        print("Now run the scraper:")
        print("   python vision_scraper.py")
    else:
        print("❌ Session file not found — please try again.")


if __name__ == "__main__":
    run_setup()
