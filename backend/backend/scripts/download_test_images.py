import asyncio
import httpx
import os

async def download_images():
    drugs = [
        {"name": "Panadol_Advance", "url": "https://upload.wikimedia.org/wikipedia/commons/4/4b/Panadol_box.jpg"},
        {"name": "Concor", "url": "https://upload.wikimedia.org/wikipedia/commons/6/63/Bisoprolol_5_mg_tablet.jpg"},
        {"name": "Augmentin", "url": "https://upload.wikimedia.org/wikipedia/commons/8/86/Amoxicillin_Clavulanate_Potassium_Tablets.jpg"},
        {"name": "Glucophage", "url": "https://upload.wikimedia.org/wikipedia/commons/3/30/Metformin_tablets.jpg"},
        {"name": "Cataflam", "url": "https://upload.wikimedia.org/wikipedia/commons/a/ae/Diclofenac_sodium_tablets.jpg"}
    ]
    
    save_dir = r"d:\Graduation Project\backend\backend\drug_images"
    os.makedirs(save_dir, exist_ok=True)
    
    headers = {"User-Agent": "Mozilla/5.0"}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        for d in drugs:
            print(f"Downloading {d['name']}...")
            try:
                r = await client.get(d['url'], timeout=10.0)
                if r.status_code == 200:
                    path = os.path.join(save_dir, f"{d['name']}.jpg")
                    with open(path, "wb") as f:
                        f.write(r.content)
                    print(f"Saved: {path}")
                else:
                    print(f"Failed to download {d['name']}: HTTP {r.status_code}")
            except Exception as e:
                print(f"Error downloading {d['name']}: {e}")

if __name__ == "__main__":
    asyncio.run(download_images())
