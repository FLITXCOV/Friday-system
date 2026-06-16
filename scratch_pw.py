import asyncio
import urllib.parse
from playwright.async_api import async_playwright

async def get_spotify_track(query):
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            safe_query = urllib.parse.quote(query)
            await page.goto(f'https://open.spotify.com/search/{safe_query}/tracks')
            
            # Wait for the tracks to load
            element = await page.wait_for_selector('a[href^="/track/"]', timeout=10000)
            href = await element.get_attribute('href')
            print('FOUND:', href)
            await browser.close()
        except Exception as e:
            print("Error:", e)

asyncio.run(get_spotify_track('heat waves glass animals'))
