import requests
import hashlib
import time
from datetime import datetime

class WebsiteMonitor:
    def __init__(self, url, check_interval=300):
        """Monitor website for changes."""
        self.url = url
        self.check_interval = check_interval  # seconds
        self.last_hash = None
        
    def get_content_hash(self):
        """Get hash of website content."""
        try:
            response = requests.get(self.url, timeout=10)
            content = response.text
            return hashlib.md5(content.encode()).hexdigest()
        except Exception as e:
            print(f"Error fetching {self.url}: {e}")
            return None
    
    def check_change(self):
        """Check if website has changed."""
        current_hash = self.get_content_hash()
        
        if current_hash is None:
            return False
        
        if self.last_hash is None:
            self.last_hash = current_hash
            print(f"[{datetime.now()}] Started monitoring: {self.url}")
            return False
        
        if current_hash != self.last_hash:
            print(f"\n🔔 CHANGE DETECTED at {datetime.now()}")
            print(f"URL: {self.url}")
            self.last_hash = current_hash
            return True
        
        return False
    
    def monitor(self):
        """Start monitoring."""
        print(f"Monitoring: {self.url}")
        print(f"Check interval: {self.check_interval}s\n")
        
        while True:
            self.check_change()
            time.sleep(self.check_interval)

if __name__ == "__main__":
    url = input("Enter URL to monitor: ")
    interval = int(input("Check interval (seconds, default 300): ") or 300)
    
    monitor = WebsiteMonitor(url, interval)
    monitor.monitor()
