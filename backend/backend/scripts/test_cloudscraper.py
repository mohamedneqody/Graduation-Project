import cloudscraper
from bs4 import BeautifulSoup

def test():
    scraper = cloudscraper.create_scraper()
    r = scraper.get("https://seifpharmacy.com/en/shop")
    print("Seif length:", len(r.text))
    if len(r.text) > 1000:
        soup = BeautifulSoup(r.text, 'html.parser')
        products = soup.find_all("div", class_="product")
        print(f"Found {len(products)} products on Seif")

    r2 = scraper.get("https://chefaa.com/search?q=%D8%B6%D8%BA%D8%B7")
    print("Chefaa length:", len(r2.text))

if __name__ == "__main__":
    test()
