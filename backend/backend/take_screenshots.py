from playwright.sync_api import sync_playwright
import time
import os

artifact_dir = "C:\\Users\\zbook\\.gemini\\antigravity\\brain\\f060737c-82d1-4ac6-967a-2c159f8a03b1"

def take_screenshots():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Tenant A
        context_a = browser.new_context(viewport={'width': 1280, 'height': 800})
        page_a = context_a.new_page()
        page_a.goto("http://localhost:3000/login")
        
        # Fill login A
        page_a.fill('input[type="email"]', 'admin_a@example.com')
        page_a.fill('input[type="password"]', 'Test1234!')
        page_a.click('button:has-text("Continue"), button:has-text("Sign In")')
        
        # Wait for nav to /admin
        try:
            page_a.wait_for_url("**/admin**", timeout=15000)
            time.sleep(3) # Wait for KPIs and customers to load
            
            # Try to navigate specifically to customers tab/page if needed
            if "customers" not in page_a.url.lower():
                # click customers tab
                page_a.goto("http://localhost:3000/admin")
                time.sleep(3)
        except Exception as e:
            print("Tenant A navigation error:", e)
        
        screenshot_path_a = os.path.join(artifact_dir, "tenant_a.png")
        page_a.screenshot(path=screenshot_path_a, full_page=True)
        print(f"Saved Tenant A screenshot to {screenshot_path_a}")
        
        context_a.close()

        # Tenant B
        context_b = browser.new_context(viewport={'width': 1280, 'height': 800})
        page_b = context_b.new_page()
        page_b.goto("http://localhost:3000/login")
        
        # Fill login B
        page_b.fill('input[type="email"]', 'admin_b@example.com')
        page_b.fill('input[type="password"]', 'Test1234!')
        page_b.click('button:has-text("Continue"), button:has-text("Sign In")')
        
        # Wait for nav
        try:
            page_b.wait_for_url("**/admin**", timeout=15000)
            time.sleep(3) # Wait for KPIs and customers to load
            
            if "customers" not in page_b.url.lower():
                # click customers tab
                page_b.goto("http://localhost:3000/admin")
                time.sleep(3)
        except Exception as e:
            print("Tenant B navigation error:", e)
        
        screenshot_path_b = os.path.join(artifact_dir, "tenant_b.png")
        page_b.screenshot(path=screenshot_path_b, full_page=True)
        print(f"Saved Tenant B screenshot to {screenshot_path_b}")

        context_b.close()
        browser.close()

if __name__ == "__main__":
    take_screenshots()
