import csv
import os

def generate_final_csv():
    # Base 30 items
    drugs_data = [
        ["Concor 5mg", "مزمن - ضغط", True, 85, 30],
        ["Amlopres 5mg", "مزمن - ضغط", True, 45, 30],
        ["Diovan 80mg", "مزمن - ضغط", True, 150, 30],
        ["Norvasc 5mg", "مزمن - ضغط", True, 60, 30],
        ["Capoten 25mg", "مزمن - ضغط", True, 35, 30],
        ["Glucophage 500mg", "مزمن - سكر", True, 40, 30],
        ["Glucomin 500mg", "مزمن - سكر", True, 35, 30],
        ["Galvus Met 50/1000mg", "مزمن - سكر", True, 220, 30],
        ["Amaryl 2mg", "مزمن - سكر", True, 90, 30],
        ["Diamicron MR 60mg", "مزمن - سكر", True, 110, 30],
        ["Lipitor 20mg", "مزمن - كوليسترول", True, 130, 30],
        ["Crestor 10mg", "مزمن - كوليسترول", True, 160, 30],
        ["Eltroxin 100mcg", "مزمن - غدة درقية", True, 25, 30],
        ["Panadol Extra", "مسكنات", False, 20, 10],
        ["Bi Alcofan", "مسكنات", False, 30, 10],
        ["Cataflam 50mg", "مسكنات", False, 25, 10],
        ["Brufen 400mg", "مسكنات", False, 22, 10],
        ["Amoclan 1g", "مضاد حيوي", False, 65, 7],
        ["Augmentin 1g", "مضاد حيوي", False, 90, 7],
        ["Zinnat 500mg", "مضاد حيوي", False, 110, 7],
        ["Rani 150mg", "جهاز هضمي", False, 15, 15],
        ["Motilium 10mg", "جهاز هضمي", False, 30, 15],
        ["Nexium 40mg", "جهاز هضمي", False, 95, 20],
        ["Cal-D-Vita", "فيتامينات", False, 65, 30],
        ["Bio Vit-C 1000mg", "فيتامينات", False, 55, 30],
        ["Feroglobin", "فيتامينات", False, 120, 30],
        ["Omega Life 3", "فيتامينات", False, 140, 30],
        ["Coldrex", "نزلات برد", False, 25, 10],
        ["Comtrex", "نزلات برد", False, 28, 10],
        ["Zyrtec 10mg", "حساسية", False, 45, 20]
    ]

    # Additional drugs to make it 150 (We will duplicate some with variation to reach 150 for demo purposes, 
    # but since this is for seeding, having varied realistic names is better)
    categories = [
        ("مزمن - ضغط", True, 30),
        ("مزمن - سكر", True, 30),
        ("مزمن - كوليسترول", True, 30),
        ("مزمن - غدة درقية", True, 30),
        ("مسكنات", False, 10),
        ("مضاد حيوي", False, 7),
        ("جهاز هضمي", False, 15),
        ("فيتامينات", False, 30),
        ("نزلات برد", False, 10),
        ("حساسية", False, 20)
    ]
    
    # Let's generate 120 more pseudo-realistic drugs
    import random
    random.seed(42)
    prefixes = ["Meto", "Cipro", "Amoxi", "Azi", "Para", "Ibu", "Dexam", "Lorat", "Omepra", "Panto", "Diclo", "Bisop", "Atorva", "Levo"]
    suffixes = ["pril", "fenac", "lol", "statin", "mox", "zole", "cetamol", "profen", "thromycin", "tidine"]
    dosages = ["5mg", "10mg", "20mg", "50mg", "100mg", "200mg", "500mg", "1g", "2g"]
    
    generated_names = set(d[0] for d in drugs_data)
    
    while len(drugs_data) < 150:
        cat_name, is_chronic, cycle = random.choice(categories)
        name = f"{random.choice(prefixes)}{random.choice(suffixes)} {random.choice(dosages)}"
        if name not in generated_names:
            generated_names.add(name)
            price = random.randint(15, 300)
            drugs_data.append([name, cat_name, is_chronic, price, cycle])

    save_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "seed_data", "final_drugs_sheet.csv"))
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    with open(save_path, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "category", "is_chronic", "base_price", "default_cycle_days", "image_url"])
        for d in drugs_data:
            writer.writerow(d + [""]) # Empty image_url
            
    print(f"Generated {len(drugs_data)} drugs at {save_path}")

if __name__ == "__main__":
    generate_final_csv()
