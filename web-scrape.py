#!/usr/bin/env python3


import requests
from bs4 import BeautifulSoup
import threading
import queue
import time
import json
import csv
import logging
import re
import hashlib
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from urllib.parse import urljoin, urlparse
from collections import defaultdict, Counter
import concurrent.futures
import argparse
import sqlite3
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(threadName)-12s] %(levelname)-8s %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ScrapedPage:
    """Data class for scraped page information"""
    url: str
    title: str
    content: str
    links: List[str]
    images: List[str]
    metadata: Dict
    timestamp: str
    status_code: int
    load_time: float
    word_count: int
    sentiment_score: Optional[float] = None
    keywords: Optional[List[str]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class RateLimiter:
    """Thread-safe rate limiter"""
    
    def __init__(self, requests_per_second: float = 2.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request = defaultdict(lambda: 0)
        self.lock = threading.Lock()
    
    def wait(self, domain: str):
        """Wait if necessary to respect rate limit for domain"""
        with self.lock:
            elapsed = time.time() - self.last_request[domain]
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_request[domain] = time.time()


class ScraperDatabase:
    """SQLite database for storing scraped data"""
    
    def __init__(self, db_path: str = "scraper_data.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize database and create tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                url_hash TEXT NOT NULL,
                title TEXT,
                content TEXT,
                word_count INTEGER,
                status_code INTEGER,
                load_time REAL,
                timestamp TEXT,
                metadata_json TEXT,
                sentiment_score REAL,
                keywords_json TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_url TEXT NOT NULL,
                target_url TEXT NOT NULL,
                link_text TEXT,
                timestamp TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_url TEXT NOT NULL,
                image_url TEXT NOT NULL,
                alt_text TEXT,
                timestamp TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_url_hash ON pages(url_hash)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON pages(timestamp)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")
    
    def insert_page(self, page: ScrapedPage) -> bool:
        """Insert scraped page into database"""
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                url_hash = hashlib.md5(page.url.encode()).hexdigest()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO pages 
                    (url, url_hash, title, content, word_count, status_code, 
                     load_time, timestamp, metadata_json, sentiment_score, keywords_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    page.url,
                    url_hash,
                    page.title,
                    page.content,
                    page.word_count,
                    page.status_code,
                    page.load_time,
                    page.timestamp,
                    json.dumps(page.metadata),
                    page.sentiment_score,
                    json.dumps(page.keywords) if page.keywords else None
                ))
                
                for link in page.links:
                    cursor.execute('''
                        INSERT INTO links (source_url, target_url, timestamp)
                        VALUES (?, ?, ?)
                    ''', (page.url, link, page.timestamp))
                
                for img in page.images:
                    cursor.execute('''
                        INSERT INTO images (page_url, image_url, timestamp)
                        VALUES (?, ?, ?)
                    ''', (page.url, img, page.timestamp))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                logger.error(f"Error inserting page {page.url}: {e}")
                return False
    
    def url_exists(self, url: str) -> bool:
        """Check if URL has been scraped"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            url_hash = hashlib.md5(url.encode()).hexdigest()
            cursor.execute('SELECT 1 FROM pages WHERE url_hash = ?', (url_hash,))
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
    
    def get_stats(self) -> Dict:
        """Get scraping statistics"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM pages')
            total_pages = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM links')
            total_links = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM images')
            total_images = cursor.fetchone()[0]
            
            cursor.execute('SELECT AVG(load_time) FROM pages')
            avg_load_time = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT AVG(word_count) FROM pages')
            avg_word_count = cursor.fetchone()[0] or 0
            
            conn.close()
            
            return {
                'total_pages': total_pages,
                'total_links': total_links,
                'total_images': total_images,
                'avg_load_time': round(avg_load_time, 2),
                'avg_word_count': round(avg_word_count, 0)
            }


class TextAnalyzer:
    """Advanced text analysis without external NLP libraries"""
    
    def __init__(self):
        self.stop_words = set([
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but',
            'in', 'with', 'to', 'for', 'of', 'as', 'by', 'that', 'this',
            'it', 'from', 'be', 'are', 'was', 'were', 'been', 'have', 'has'
        ])
        
        self.positive_words = set([
            'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
            'best', 'love', 'perfect', 'awesome', 'happy', 'beautiful',
            'outstanding', 'brilliant', 'superb', 'magnificent'
        ])
        
        self.negative_words = set([
            'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate', 'poor',
            'disappointing', 'useless', 'wrong', 'fail', 'failed', 'problem',
            'issue', 'difficult', 'hard', 'complex', 'confusing'
        ])
    
    def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """Extract top keywords from text"""
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        filtered_words = [w for w in words if w not in self.stop_words]
        
        word_freq = Counter(filtered_words)
        
        return [word for word, _ in word_freq.most_common(top_n)]
    
    def calculate_sentiment(self, text: str) -> float:
        """Calculate simple sentiment score (-1 to 1)"""
        words = re.findall(r'\b[a-z]+\b', text.lower())
        
        positive_count = sum(1 for w in words if w in self.positive_words)
        negative_count = sum(1 for w in words if w in self.negative_words)
        
        total_sentiment_words = positive_count + negative_count
        
        if total_sentiment_words == 0:
            return 0.0
        
        sentiment_score = (positive_count - negative_count) / total_sentiment_words
        
        return round(sentiment_score, 3)
    
    def extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        return list(set(re.findall(email_pattern, text)))
    
    def extract_phones(self, text: str) -> List[str]:
        """Extract phone numbers from text"""
        phone_pattern = r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'
        return list(set(re.findall(phone_pattern, text)))


class AdvancedWebScraper:
    """Main web scraper class with multi-threading support"""
    
    def __init__(
        self,
        max_workers: int = 5,
        rate_limit: float = 2.0,
        timeout: int = 10,
        max_depth: int = 2,
        db_path: str = "scraper_data.db"
    ):
        self.max_workers = max_workers
        self.timeout = timeout
        self.max_depth = max_depth
        
        self.rate_limiter = RateLimiter(requests_per_second=rate_limit)
        self.db = ScraperDatabase(db_path)
        self.analyzer = TextAnalyzer()
        
        self.url_queue = queue.Queue()
        self.visited_urls: Set[str] = set()
        self.lock = threading.Lock()
        
        self.stats = {
            'total_requested': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for consistent comparison"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip('/')
    
    def _is_valid_url(self, url: str, base_domain: str) -> bool:
        """Check if URL is valid and within allowed domain"""
        parsed = urlparse(url)
        
        if not parsed.scheme or not parsed.netloc:
            return False
        
        if parsed.scheme not in ['http', 'https']:
            return False
        
        if base_domain and base_domain not in parsed.netloc:
            return False
        
        excluded_extensions = ['.pdf', '.jpg', '.png', '.gif', '.css', '.js', '.zip']
        if any(url.lower().endswith(ext) for ext in excluded_extensions):
            return False
        
        return True
    
    def scrape_page(self, url: str) -> Optional[ScrapedPage]:
        """Scrape a single page"""
        domain = urlparse(url).netloc
        self.rate_limiter.wait(domain)
        
        start_time = time.time()
        
        try:
            with self.lock:
                self.stats['total_requested'] += 1
            
            response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
            load_time = time.time() - start_time
            
            if response.status_code != 200:
                logger.warning(f"Non-200 status for {url}: {response.status_code}")
                with self.lock:
                    self.stats['failed'] += 1
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for script in soup(['script', 'style', 'nav', 'footer', 'header']):
                script.decompose()
            
            title = soup.title.string if soup.title else ''
            
            content = soup.get_text(separator=' ', strip=True)
            content = re.sub(r'\s+', ' ', content)
            
            links = []
            for link in soup.find_all('a', href=True):
                absolute_url = urljoin(url, link['href'])
                normalized_url = self._normalize_url(absolute_url)
                links.append(normalized_url)
            
            images = []
            for img in soup.find_all('img', src=True):
                img_url = urljoin(url, img['src'])
                images.append(img_url)
            
            meta_tags = {}
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                content_value = meta.get('content')
                if name and content_value:
                    meta_tags[name] = content_value
            
            word_count = len(content.split())
            
            keywords = self.analyzer.extract_keywords(content)
            sentiment = self.analyzer.calculate_sentiment(content)
            
            page = ScrapedPage(
                url=url,
                title=title.strip(),
                content=content[:5000],
                links=links,
                images=images,
                metadata=meta_tags,
                timestamp=datetime.now().isoformat(),
                status_code=response.status_code,
                load_time=round(load_time, 2),
                word_count=word_count,
                sentiment_score=sentiment,
                keywords=keywords
            )
            
            with self.lock:
                self.stats['successful'] += 1
            
            logger.info(f"✓ Scraped: {url} ({word_count} words, {len(links)} links)")
            
            return page
            
        except requests.Timeout:
            logger.error(f"Timeout scraping {url}")
            with self.lock:
                self.stats['failed'] += 1
        except requests.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            with self.lock:
                self.stats['failed'] += 1
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            with self.lock:
                self.stats['failed'] += 1
        
        return None
    
    def crawl(self, start_urls: List[str], follow_links: bool = True):
        """Crawl websites starting from given URLs"""
        base_domains = [urlparse(url).netloc for url in start_urls]
        
        for url in start_urls:
            self.url_queue.put((url, 0))
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            while not self.url_queue.empty() or futures:
                while not self.url_queue.empty() and len(futures) < self.max_workers:
                    try:
                        url, depth = self.url_queue.get_nowait()
                        
                        normalized_url = self._normalize_url(url)
                        
                        with self.lock:
                            if normalized_url in self.visited_urls:
                                self.stats['skipped'] += 1
                                continue
                            self.visited_urls.add(normalized_url)
                        
                        if self.db.url_exists(normalized_url):
                            logger.info(f"↷ Skipping (already in DB): {normalized_url}")
                            with self.lock:
                                self.stats['skipped'] += 1
                            continue
                        
                        future = executor.submit(self.scrape_page, normalized_url)
                        futures.append((future, normalized_url, depth))
                        
                    except queue.Empty:
                        break
                
                done_futures = []
                for future, url, depth in futures:
                    if future.done():
                        done_futures.append((future, url, depth))
                
                for future, url, depth in done_futures:
                    futures.remove((future, url, depth))
                    
                    try:
                        page = future.result()
                        
                        if page:
                            self.db.insert_page(page)
                            
                            if follow_links and depth < self.max_depth:
                                for link in page.links:
                                    if any(domain in link for domain in base_domains):
                                        if self._is_valid_url(link, None):
                                            self.url_queue.put((link, depth + 1))
                    except Exception as e:
                        logger.error(f"Error processing result for {url}: {e}")
                
                time.sleep(0.1)
        
        logger.info("Crawling completed!")
        self.print_stats()
    
    def print_stats(self):
        """Print scraping statistics"""
        print("\n" + "="*60)
        print("SCRAPING STATISTICS")
        print("="*60)
        print(f"Total URLs Requested:  {self.stats['total_requested']}")
        print(f"Successfully Scraped:  {self.stats['successful']}")
        print(f"Failed:                {self.stats['failed']}")
        print(f"Skipped (duplicates):  {self.stats['skipped']}")
        print("="*60)
        
        db_stats = self.db.get_stats()
        print("\nDATABASE STATISTICS")
        print("="*60)
        for key, value in db_stats.items():
            print(f"{key.replace('_', ' ').title():.<40} {value}")
        print("="*60 + "\n")
    
    def export_to_csv(self, filename: str):
        """Export scraped data to CSV"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT url, title, word_count, status_code, 
                   load_time, sentiment_score, timestamp 
            FROM pages
        ''')
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Title', 'Word Count', 'Status', 
                           'Load Time', 'Sentiment', 'Timestamp'])
            writer.writerows(cursor.fetchall())
        
        conn.close()
        logger.info(f"Data exported to {filename}")
        print(f"\n✅ Data exported to {filename}")
    
    def export_to_json(self, filename: str):
        """Export scraped data to JSON"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM pages')
        columns = [description[0] for description in cursor.description]
        
        data = []
        for row in cursor.fetchall():
            data.append(dict(zip(columns, row)))
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        conn.close()
        logger.info(f"Data exported to {filename}")
        print(f"\n✅ Data exported to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Advanced Multi-threaded Web Scraper with AI Analysis'
    )
    parser.add_argument('urls', nargs='+', help='URLs to scrape')
    parser.add_argument('-w', '--workers', type=int, default=5,
                        help='Number of concurrent workers (default: 5)')
    parser.add_argument('-r', '--rate', type=float, default=2.0,
                        help='Requests per second (default: 2.0)')
    parser.add_argument('-d', '--depth', type=int, default=2,
                        help='Maximum crawl depth (default: 2)')
    parser.add_argument('--no-follow', action='store_true',
                        help='Do not follow links (single page scrape)')
    parser.add_argument('--export-csv', type=str,
                        help='Export results to CSV file')
    parser.add_argument('--export-json', type=str,
                        help='Export results to JSON file')
    parser.add_argument('--timeout', type=int, default=10,
                        help='Request timeout in seconds (default: 10)')
    
    args = parser.parse_args()
    
    print("\n" + "="*60)
    print("ADVANCED WEB SCRAPER WITH AI ANALYSIS")
    print("="*60)
    print(f"Target URLs: {', '.join(args.urls)}")
    print(f"Workers: {args.workers}")
    print(f"Rate Limit: {args.rate} req/s")
    print(f"Max Depth: {args.depth}")
    print(f"Follow Links: {not args.no_follow}")
    print("="*60 + "\n")
    
    scraper = AdvancedWebScraper(
        max_workers=args.workers,
        rate_limit=args.rate,
        timeout=args.timeout,
        max_depth=args.depth
    )
    
    try:
        scraper.crawl(args.urls, follow_links=not args.no_follow)
        
        if args.export_csv:
            scraper.export_to_csv(args.export_csv)
        
        if args.export_json:
            scraper.export_to_json(args.export_json)
        
    except KeyboardInterrupt:
        print("\n\nScraping interrupted by user.")
        scraper.print_stats()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        scraper.print_stats()


if __name__ == "__main__":
    main()
