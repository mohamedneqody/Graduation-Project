"""
e2e test v3: wait for modal properly with longer timeout
"""
import asyncio
import requests
import json
from playwright.async_api import async_playwright

BASE = "http://127.0.0.1:8000"

async def run():
    print("=== Opening browser and uploading file directly ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        page.on("console", lambda msg: print(f"[{msg.type}] {msg.text[:100]}") if msg.type in ("error", "warning") else None)

        await page.goto("http://localhost:3000", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        print("Setting file input...")
        await page.set_input_files('input[type="file"]', "D:/مشروع تخرج/files/real_02.jpg")
        print("File set. Waiting for modal (90s)...")

        # Wait for any overlay or modal that Next.js renders
        try:
            # Look for text that appears in the modal header
            await page.wait_for_function(
                "document.body.innerText.includes('نتيجة') || document.body.innerText.includes('ادوية') || document.body.innerText.includes('matched') || document.querySelectorAll('[class*=\"modal\"], [class*=\"Modal\"], [role=\"dialog\"]').length > 0",
                timeout=90000
            )
            print("Modal content detected!")
        except Exception as e:
            print(f"Timeout waiting: {e}")

        await page.wait_for_timeout(2000)
        await page.screenshot(
            path="C:/Users/zbook/.gemini/antigravity/brain/34246367-9d6f-4433-b7c5-08f4302af46c/playwright_result.png",
            full_page=False
        )
        print("Screenshot saved!")
        
        # Also get page text to debug
        text = await page.evaluate("() => document.body.innerText")
        print("Page text snippet:", text[:500])

        await browser.close()

asyncio.run(run())
