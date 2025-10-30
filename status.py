import requests

sites = ["https://gmail.com", "https://google.com"]  # Add your sites
for site in sites:
    try:
        response = requests.get(site, timeout=5)
        if response.status_code == 200:
            print(f"{site}: UP")
        else:
            print(f"{site}: DOWN (Status: {response.status_code})")
            # Optional: Add email alert here from script #2
    except requests.RequestException:
        print(f"{site}: DOWN (Connection error)")
