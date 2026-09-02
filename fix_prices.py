import os
import re

folder = r'D:\Graduation Project\stitch_ai_cos_pharmacy\واجهات_Premium_V2'

# 1. AI-COS Pharmacy - Storefront Homepage.html
file1 = os.path.join(folder, 'AI-COS Pharmacy - Storefront Homepage.html')
if os.path.exists(file1):
    with open(file1, 'r', encoding='utf-8') as f: c = f.read()
    c = c.replace('>$15.99<', '>EGP 175.00<')
    c = c.replace('>$12.50<', '>EGP 160.00<')
    c = c.replace('>$8.20<', '>EGP 40.00<')
    c = c.replace('>$5.90<', '>EGP 85.00<')
    c = c.replace('>$22.00<', '>EGP 50.00<')
    c = c.replace('>$18.50<', '>EGP 45.00<')
    
    target = '<div class="bg-surface-container-low rounded-xl border border-outline-variant p-lg">'
    replacement = '''<div class="relative">
  <div class="absolute inset-0 bg-gray-200 bg-opacity-70 z-10 flex flex-col items-center justify-center rounded-xl">
    <span class="bg-gray-800 text-white px-4 py-2 rounded-full font-bold shadow-lg">Coming Soon</span>
    <span class="mt-2 text-gray-800 font-medium">Non-drug catalog expansion</span>
  </div>
  <div class="bg-surface-container-low rounded-xl border border-outline-variant p-lg pointer-events-none opacity-50">'''
    
    if target in c and '<div class="relative">' not in c:
        c = c.replace(target, replacement, 1)
        c = c.replace('</section>', '  </div>\n</section>', 1)

    with open(file1, 'w', encoding='utf-8') as f: f.write(c)


# 2. Checkout - Pharmacy Platform.html
file2 = os.path.join(folder, 'Checkout - Pharmacy Platform.html')
if os.path.exists(file2):
    with open(file2, 'r', encoding='utf-8') as f: c = f.read()
    c = c.replace('$12.50', 'EGP 85.00')
    c = c.replace('$5.99', 'EGP 22.00')
    c = c.replace('$18.49', 'EGP 107.00')
    c = c.replace('$20.14', 'EGP 107.00')
    with open(file2, 'w', encoding='utf-8') as f: f.write(c)


# 3. Product Catalog - PharmaCOS AI Admin.html
file3 = os.path.join(folder, 'Product Catalog - PharmaCOS AI Admin.html')
if os.path.exists(file3):
    with open(file3, 'r', encoding='utf-8') as f: c = f.read()
    c = c.replace('$12.50', 'EGP 160.00')
    c = c.replace('$8.75', 'EGP 85.00')
    c = c.replace('$5.20', 'EGP 40.00')
    c = c.replace('$14.00', 'EGP 95.00')
    c = c.replace('$9.30', 'EGP 90.00')
    with open(file3, 'w', encoding='utf-8') as f: f.write(c)


# 4. Product Catalog - Edit Product Modal.html
file4 = os.path.join(folder, 'Product Catalog - Edit Product Modal.html')
if os.path.exists(file4):
    with open(file4, 'r', encoding='utf-8') as f: c = f.read()
    c = c.replace('UNIT PRICE ($)', 'UNIT PRICE (EGP)')
    c = c.replace('"8.90"', '"85.00"')
    with open(file4, 'w', encoding='utf-8') as f: f.write(c)


# Global replace for $ signs
for root, dirs, files in os.walk(folder):
    for fname in files:
        if fname.endswith('.html'):
            filepath = os.path.join(root, fname)
            with open(filepath, 'r', encoding='utf-8') as f: c = f.read()
            new_c = re.sub(r'\$(\d[\d,]*\.\d{2})', r'EGP \1', c)
            if c != new_c:
                with open(filepath, 'w', encoding='utf-8') as f: f.write(new_c)

print('Done fixing prices and overlay.')
