import hashlib
import itertools
import string
import sys

def md5_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

def crack_hash(target_hash, charset, max_len=4):
    for length in range(1, max_len + 1):
        for attempt in itertools.product(charset, repeat=length):
            candidate = ''.join(attempt)
            if md5_hash(candidate) == target_hash:
                return candidate
    return None

target = sys.argv[1] if len(sys.argv) > 1 else '5d41402abc4b2a76b9719d911017c592'
charset = string.ascii_lowercase + string.digits

cracked = crack_hash(target, charset)
print(cracked if cracked else "Not found")
