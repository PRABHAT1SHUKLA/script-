import requests
import sys

def enumerate_subdomains(domain, subdomains_file):
    with open(subdomains_file, 'r') as f:
        subs = [line.strip() for line in f]

    results = []
    for sub in subs:
        test_domain = f"{sub}.{domain}"
        try:
            resp = requests.get(f"http://{test_domain}", timeout=5)
            if resp.status_code in [200, 403, 301, 302]:
                results.append(test_domain)
        except:
            pass

    for res in results:
        print(res)

domain = sys.argv[1] if len(sys.argv) > 1 else 'example.com'
subs_file = sys.argv[2] if len(sys.argv) > 2 else 'subdomains.txt'

enumerate_subdomains(domain, subs_file)
