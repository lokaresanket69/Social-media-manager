import requests

# Paste your Instagram Graph API access token here
ACCESS_TOKEN = "EAARkzaSwwz4BPMzGDZBJZBXoANEwfkdNOfEWujigpf7rlVguKTYR69JrV85EKp6ZB3exkXoJeJj0gMivZC3TVqsZAVZCM7qXQHD059cga76hUZBajVMAfN2MGqE3CaQrNL3eIhJFRV45103EPquKuxPcaZCPK0aPsioBkYC4zbXlpuOqxNtZAOHzFmoZBwTpaVi2hMy7rFnnyAwux6a4TeEzAWI1CXYu6rw0rjo6ThtsBWZAAZDZD"

# Step 1: Get Facebook Pages
pages_url = f"https://graph.facebook.com/v19.0/me/accounts?access_token={ACCESS_TOKEN}"
pages_resp = requests.get(pages_url)
pages_data = pages_resp.json()

if "data" not in pages_data or not pages_data["data"]:
    print("No Facebook Pages found for this token. Make sure your IG business account is linked to a Facebook Page.")
    exit(1)

page = pages_data["data"][0]
page_id = page["id"]
print(f"Found Facebook Page: {page.get('name', 'N/A')} (ID: {page_id})")

# Step 2: Get Instagram Business Account ID
ig_url = f"https://graph.facebook.com/v19.0/{page_id}?fields=instagram_business_account&access_token={ACCESS_TOKEN}"
ig_resp = requests.get(ig_url)
ig_data = ig_resp.json()

ig_account = ig_data.get("instagram_business_account")
if ig_account and "id" in ig_account:
    print(f"Instagram Business Account ID: {ig_account['id']}")
else:
    print("No Instagram Business Account linked to this Facebook Page. Make sure your IG account is a business account and is linked to this page.") 