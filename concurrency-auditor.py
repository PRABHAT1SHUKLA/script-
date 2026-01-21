import asyncio
import aiohttp
import time
import logging
from datetime import datetime

# 1. ADVANCED LOGGING
# High-end systems use JSON-ready formatting for ELK Stack or Splunk
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

# 2. ASYNC TASK DEFINITION
async def check_endpoint(session, name, url):
    """
    Asynchronously pings a service and measures latency (speed).
    """
    start_time = time.perf_counter()
    try:
        async with session.get(url, timeout=10) as response:
            latency = time.perf_counter() - start_time
            status = response.status
            
            if status == 200:
                logging.info(f"SUCCESS: {name} | Latency: {latency:.4f}s")
            else:
                logging.warning(f"ALERT: {name} returned {status}")
            
            return {"name": name, "status": status, "latency": latency}
            
    except Exception as e:
        logging.error(f"CRITICAL: {name} is unreachable | Error: {type(e).__name__}")
        return {"name": name, "status": "DOWN", "latency": 0}

# 3. CONCURRENCY ENGINE
async def main():
    # A list of internal company services to monitor
    services = [
        ("Auth-Service", "https://httpbin.org/get"),
        ("Payment-Gateway", "https://httpbin.org/status/200"),
        ("Inventory-DB", "https://httpbin.org/delay/1"),
        ("Frontend-CDN", "https://google.com"),
    ]

    # Use a single session for all requests (Performance Best Practice)
    async with aiohttp.ClientSession() as session:
        tasks = []
        for name, url in services:
            # We don't "run" the function here, we create a "Task"
            tasks.append(check_endpoint(session, name, url))
        
        # This is where the magic happens: All tasks start simultaneously
        results = await asyncio.gather(*tasks)
        
        # Process results
        avg_latency = sum(r['latency'] for r in results) / len(results)
        print(f"\n--- Global Health Report ---")
        print(f"Average System Latency: {avg_latency:.4f}s")

if __name__ == "__main__":
    # Start the asynchronous event loop
    asyncio.run(main())
