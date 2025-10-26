import requests
import json

url = "https://careers.aramark.com/wp-json/aramark/jobs?&path=&zips=&industries=correctional%20facilities&categories=&jobfunction=&sub_categories=&types=&keyword=&limit=100"

response = requests.get(url)

print(f"Status Code: {response.status_code}")
print(f"\nResponse Headers:")
print(json.dumps(dict(response.headers), indent=2))

if response.status_code == 200:
    data = response.json()
    print(f"\nTotal jobs returned: {len(data) if isinstance(data, list) else 'Not a list'}")
    print(f"\nFirst job sample:")
    print(json.dumps(data[0] if isinstance(data, list) and len(data) > 0 else data, indent=2))
else:
    print(f"\nError: {response.text}")
