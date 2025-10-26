import requests
import json

url = "https://careers.aramark.com/wp-json/aramark/jobs?limit=10&req_id=614164"

response = requests.get(url)

print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"\nTotal results: {len(data) if isinstance(data, list) else 'Not a list'}")
    
    if isinstance(data, list) and len(data) > 0:
        job = data[0]
        print(f"\nJob ID: {job.get('req_id')}")
        print(f"Title: {job.get('title')}")
        print(f"\nDescription:")
        print(job.get('description', 'No description field'))
        print(f"\nAll available fields:")
        print(json.dumps(job, indent=2))
else:
    print(f"\nError: {response.text}")
