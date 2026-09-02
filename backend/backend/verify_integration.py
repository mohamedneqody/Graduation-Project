import requests
import json
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

print('=== 1. VERIFYING CATEGORIES API ===')
r_cat = requests.get('http://localhost:8000/api/v1/drugs/categories')
print('Status:', r_cat.status_code)
cats = r_cat.json()
print('Total Categories in DB:', len(cats))
for c in cats:
    print(f"  - {c['name']}: {c['count']} drugs")

print('\n=== 2. VERIFYING DRUGS PAGINATION API ===')
r_p1 = requests.get('http://localhost:8000/api/v1/drugs/?page=1&limit=12')
data_p1 = r_p1.json()
print('Status:', r_p1.status_code, '| Total in DB:', data_p1['total'], '| Page 1 items:', len(data_p1['items']))

r_p2 = requests.get('http://localhost:8000/api/v1/drugs/?page=2&limit=12')
data_p2 = r_p2.json()
print('Status:', r_p2.status_code, '| Page 2 items:', len(data_p2['items']))

print('\n=== 3. VERIFYING SEARCH API ===')
r_search = requests.get('http://localhost:8000/api/v1/drugs/?search=sinopril')
data_search = r_search.json()
print('Search "sinopril" matches in DB:', data_search['total'])
for item in data_search['items']:
    print(f"  - {item['name']} (EGP {item['base_price']})")

print('\n=== 4. VERIFYING RECOMMENDATIONS API ===')
r_recs = requests.get('http://localhost:8000/api/v1/drugs/recommendations?limit=6')
recs = r_recs.json()
print('Recommendations returned:', len(recs))
for rec in recs[:3]:
    print(f"  - {rec['name']} (Category: {rec['category']}, Price: EGP {rec['base_price']})")

print('\n=== 5. VERIFYING ADMIN ORDERS API ===')
r_orders = requests.get('http://localhost:8000/api/v1/orders/all?limit=5')
orders_data = r_orders.json()
print('Total Orders in DB:', orders_data['total'], '| Returned:', len(orders_data['items']))
