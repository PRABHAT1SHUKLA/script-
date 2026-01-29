#!/usr/bin/env python3
"""
Advanced Web Scraper with Async, Rate Limiting, and Error Recovery
Key concepts: asyncio, aiohttp, semaphores, exponential backoff, caching
"""

import asyncio
import aiohttp
import time
import hashlib
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class ScrapedData:
    url: str
    title: str
    content: str
    timestamp: str
    status_code: int
    headers: Dict

class AdvancedScraper:
    def __init__(self, max_concurrent=5, rate_limit=2, cache_dir="cache"):
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.request_times = []
        
    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _get_cache_path(self, url: str) -> Path:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.cache_dir / f"{url_hash}.json"
    
    def _load_from_cache(self, url: str, max_age_hours=24) -> Optional[ScrapedData]:
        cache_path = self._get_cache_path(url)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > timedelta(hours=max_age_hours):
                return None
            
            return ScrapedData(**data)
        except Exception as e:
            logging.warning(f"Cache read error for {url}: {e}")
            return None
    
    def _save_to_cache(self, data: ScrapedData):
        cache_path = self._get_cache_path(data.url)
        try:
            with open(cache_path, 'w') as f:
                json.dump(asdict(data), f, indent=2)
        except Exception as e:
            logging.warning(f"Cache write error: {e}")
    
    async def _rate_limit_wait(self):
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 1.0]
        
        if len(self.request_times) >= self.rate_limit:
            sleep_time = 1.0 - (now - self.request_times[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        
        self.request_times.append(time.time())
    
    async def _fetch_with_retry(self, url: str, max_retries=3) -> Optional[tuple]:
        for attempt in range(max_retries):
            try:
                await self._rate_limit_wait()
                
                async with self.session.get(url) as response:
                    text = await response.text()
                    return text, response.status, dict(response.headers)
            
            except asyncio.TimeoutError:
                wait_time = 2 ** attempt
                logging.warning(f"Timeout for {url}, retry {attempt + 1}/{max_retries} after {wait_time}s")
                await asyncio.sleep(wait_time)
            
            except aiohttp.ClientError as e:
                logging.error(f"Client error for {url}: {e}")
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(2 ** attempt)
        
        return None
    
    def _parse_html(self, html: str) -> Dict[str, str]:
        soup = BeautifulSoup(html, 'html.parser')
        
        for script in soup(['script', 'style']):
            script.decompose()
        
        title = soup.find('title')
        title_text = title.get_text(strip=True) if title else "No title"
        
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text(strip=True) for p in paragraphs[:5]])
        
        return {
            'title': title_text,
            'content': content[:500]
        }
    
    async def scrape_url(self, url: str, use_cache=True) -> Optional[ScrapedData]:
        if use_cache:
            cached = self._load_from_cache(url)
            if cached:
                logging.info(f"Cache hit: {url}")
                return cached
        
        async with self.semaphore:
            logging.info(f"Fetching: {url}")
            
            result = await self._fetch_with_retry(url)
            if not result:
                return None
            
            html, status, headers = result
            parsed = self._parse_html(html)
            
            data = ScrapedData(
                url=url,
                title=parsed['title'],
                content=parsed['content'],
                timestamp=datetime.now().isoformat(),
                status_code=status,
                headers=headers
            )
            
            self._save_to_cache(data)
            return data
    
    async def scrape_multiple(self, urls: List[str]) -> List[ScrapedData]:
        tasks = [self.scrape_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logging.error(f"Error scraping {urls[i]}: {result}")
            elif result:
                valid_results.append(result)
        
        return valid_results
    
    async def scrape_with_pagination(self, base_url: str, max_pages=5) -> List[ScrapedData]:
        all_results = []
        
        for page in range(1, max_pages + 1):
            url = f"{base_url}?page={page}"
            result = await self.scrape_url(url)
            
            if result:
                all_results.append(result)
            else:
                logging.info(f"Stopping at page {page}")
                break
        
        return all_results

async def main():
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://httpbin.org/delay/1",
        "https://www.python.org",
    ]
    
    async with AdvancedScraper(max_concurrent=3, rate_limit=2) as scraper:
        print("Starting concurrent scraping...")
        results = await scraper.scrape_multiple(urls)
        
        print(f"\nSuccessfully scraped {len(results)} URLs:")
        for data in results:
            print(f"\n{data.url}")
            print(f"  Title: {data.title}")
            print(f"  Status: {data.status_code}")
            print(f"  Content preview: {data.content[:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
