"""
Capture les cookies d'un tracker en ouvrant un vrai navigateur.
Utile pour les trackers avec captcha anti-bot (ex: Gemini).

Usage:
    python capture_cookies.py <tracker_name> <login_url>

Exemple:
    python capture_cookies.py gemini https://gemini-tracker.org/login

Le navigateur s'ouvre, vous vous connectez manuellement,
puis les cookies sont sauvegardes pour le scraper.
"""
import asyncio
import json
import re
import sys
from pathlib import Path
from playwright.async_api import async_playwright


async def capture(tracker_name: str, login_url: str):
    cookies_dir = Path("cookies")
    cookies_dir.mkdir(exist_ok=True)
    safe_name = re.sub(r'[^a-zA-Z0-9]', '_', tracker_name).lower()
    cookies_path = cookies_dir / f"{safe_name}.json"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(login_url)

        print(f"\n{'='*50}")
        print(f"Connectez-vous manuellement a {tracker_name}")
        print(f"Cochez 'Se souvenir de moi' / 'Remember me'")
        print(f"Une fois connecte, fermez le navigateur.")
        print(f"{'='*50}\n")

        # Attendre que le navigateur soit ferme
        try:
            await page.wait_for_event("close", timeout=300000)
        except:
            pass

        # Sauvegarder les cookies
        state = await context.storage_state()
        cookies_path.write_text(json.dumps(state))
        print(f"\nCookies sauvegardes: {cookies_path}")
        print(f"Nombre de cookies: {len(state.get('cookies', []))}")

        await browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python capture_cookies.py <tracker_name> <login_url>")
        print("Ex:    python capture_cookies.py 'G3MINI TR4CK3R' https://gemini-tracker.org/login")
        sys.exit(1)

    asyncio.run(capture(sys.argv[1], sys.argv[2]))
