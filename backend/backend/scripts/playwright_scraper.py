import asyncio
import urllib.parse
import os
from playwright.async_api import async_playwright

async def scrape_images_playwright():
    drugs = [
        "Panadol Advance", 
        "Concor 5mg", 
        "Augmentin 1g", 
        "Glucophage", 
        "Cataflam 50mg"
    ] # Simplified queries to increase search hit rates
    
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "drug_images"))
    os.makedirs(base_dir, exist_ok=True)
    
    print("Starting Playwright scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Use realistic user agent
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        for d in drugs:
            print(f"\nSearching for {d} on SeifPharmacy...")
            query = urllib.parse.quote(d)
            url = f"https://seifpharmacy.com/?s={query}&post_type=product"
            
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Wait for Cloudflare if present, then wait for products
                await page.wait_for_selector("img.attachment-woocommerce_thumbnail", timeout=15000)
                
                img_url = await page.evaluate("() => { const img = document.querySelector('img.attachment-woocommerce_thumbnail'); return img ? img.src : null; }")
                
                if img_url:
                    print(f"Found image URL: {img_url}")
                    # Download image directly via playwright to inherit cookies/session
                    response = await page.request.get(img_url)
                    if response.ok:
                        body = await response.body()
                        safe_name = d.replace(" ", "_").lower()
                        filename = os.path.join(base_dir, f"{safe_name}.jpg")
                        with open(filename, "wb") as f:
                            f.write(body)
                        print(f"SUCCESS: Saved {filename}")
                    else:
                        print(f"Failed to download image. HTTP {response.status}")
                else:
                    print(f"No image found for {d} in search results.")
            except Exception as e:
                print(f"Error scraping {d}: {type(e).__name__} - {e}")
                
            await asyncio.sleep(2) # Small delay between searches to be respectful
            
        await browser.close()
        
    print("\nScraping complete.")

if __name__ == "__main__":
    asyncio.run(scrape_images_playwright())
