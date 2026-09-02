import asyncio
import os
from playwright.async_api import async_playwright
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv
import random

async def run_test():
    load_dotenv(r"D:\Graduation Project\backend\backend\.env")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        context_a = await browser.new_context(viewport={"width": 1280, "height": 720})
        page_a = await context_a.new_page()
        
        context_b = await browser.new_context(viewport={"width": 1280, "height": 720})
        page_b = await context_b.new_page()
        
        print("Logging in User A...")
        await page_a.goto("http://localhost:3000/login")
        await page_a.fill("input[type='email']", "tenant_a@test.com")
        await page_a.fill("input[type='password']", "Password123!")
        await page_a.click("button[type='submit']")
        
        print("Logging in User B...")
        await page_b.goto("http://localhost:3000/login")
        await page_b.fill("input[type='email']", "tenant_b@test.com")
        await page_b.fill("input[type='password']", "Password123!")
        await page_b.click("button[type='submit']")
        
        # Wait for navigation and sync
        await asyncio.sleep(8)
        
        print("Navigating to /admin/customers")
        await page_a.goto("http://localhost:3000/admin/customers")
        await page_b.goto("http://localhost:3000/admin/customers")
        
        # Wait for data to load
        await asyncio.sleep(8)
        
        print("Taking screenshots before update...")
        await page_a.screenshot(path=r"C:\Users\zbook\.gemini\antigravity\brain\f060737c-82d1-4ac6-967a-2c159f8a03b1\tenant_a_before.png")
        await page_b.screenshot(path=r"C:\Users\zbook\.gemini\antigravity\brain\f060737c-82d1-4ac6-967a-2c159f8a03b1\tenant_b_before.png")
        
        print("Updating database from backend...")
        engine = create_async_engine(os.environ.get('DATABASE_URL'))
        new_phone = f"+2010{random.randint(1000000, 9999999)}"
        async with engine.begin() as conn:
            await conn.execute(text(f"UPDATE customers SET phone = '{new_phone}' WHERE email = 'target_a@test.com' OR email LIKE 'target_a_%@test.com'"))
            
        print("Waiting for Realtime to push updates...")
        await asyncio.sleep(6)
        
        print("Taking screenshots after update...")
        await page_a.screenshot(path=r"C:\Users\zbook\.gemini\antigravity\brain\f060737c-82d1-4ac6-967a-2c159f8a03b1\tenant_a_after.png")
        await page_b.screenshot(path=r"C:\Users\zbook\.gemini\antigravity\brain\f060737c-82d1-4ac6-967a-2c159f8a03b1\tenant_b_after.png")
        
        await browser.close()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(run_test())
