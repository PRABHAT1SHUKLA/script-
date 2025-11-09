import requests
import sys

def brute_force_dirs(url, wordlist):
    with open(wordlist, 'r') as f:
        words = [line.strip() for line in f]

    for word in words:
        test_url = f"{url.rstrip('/')}/{word}"
        try:
            resp = requests.get(test_url, timeout=5)
            if resp.status_code == 200:
                print(f"Found: {test_url}")
        except:
            pass

base_url = sys.argv[1] if len(sys.argv) > 1 else 'http://example.com'
wordlist = sys.argv[2] if len(sys.argv) > 2 else 'dirs.txt'

brute_force_dirs(base_url, wordlist)
