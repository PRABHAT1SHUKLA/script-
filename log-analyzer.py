#!/usr/bin/env python3
"""
Advanced Log Analyzer with Pattern Detection and Anomaly Detection
Key concepts: regex, generators, decorators, context managers, multiprocessing, statistics
"""

import re
import gzip
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Iterator, Dict, List, Tuple
from dataclasses import dataclass, field
from functools import wraps
import time
import json
from concurrent.futures import ProcessPoolExecutor
import statistics

@dataclass
class LogEntry:
    timestamp: datetime
    level: str
    message: str
    source: str
    metadata: Dict = field(default_factory=dict)

@dataclass
class AnalysisReport:
    total_entries: int
    error_count: int
    warning_count: int
    time_range: Tuple[datetime, datetime]
    top_errors: List[Tuple[str, int]]
    error_rate_by_hour: Dict[int, int]
    anomalies: List[Dict]
    patterns: Dict[str, int]

def timing_decorator(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        print(f"{func.__name__} took {elapsed:.2f}s")
        return result
    return wrapper

class LogAnalyzer:
    
    LOG_PATTERNS = {
        'apache': re.compile(
            r'(?P<ip>\d+\.\d+\.\d+\.\d+).*?\[(?P<timestamp>.*?)\].*?"(?P<method>\w+) (?P<path>.*?) HTTP.*?" (?P<status>\d+)'
        ),
        'nginx': re.compile(
            r'(?P<ip>\d+\.\d+\.\d+\.\d+).*?\[(?P<timestamp>.*?)\].*?"(?P<method>\w+) (?P<path>.*?) HTTP.*?" (?P<status>\d+) (?P<size>\d+)'
        ),
        'python': re.compile(
            r'(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) - (?P<level>\w+) - (?P<message>.*)'
        ),
        'syslog': re.compile(
            r'(?P<timestamp>\w+\s+\d+\s+\d{2}:\d{2}:\d{2}) (?P<host>\S+) (?P<process>\S+): (?P<message>.*)'
        )
    }
    
    def __init__(self, log_format='python'):
        self.pattern = self.LOG_PATTERNS.get(log_format, self.LOG_PATTERNS['python'])
        self.entries = []
        self.errors = defaultdict(int)
        self.warnings = defaultdict(int)
    
    def open_log_file(self, filepath: Path) -> Iterator[str]:
        if filepath.suffix == '.gz':
            with gzip.open(filepath, 'rt') as f:
                yield from f
        else:
            with open(filepath, 'r', errors='ignore') as f:
                yield from f
    
    def parse_line(self, line: str) -> LogEntry:
        match = self.pattern.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        
        try:
            if 'timestamp' in data:
                ts_str = data['timestamp']
                if ',' in ts_str:
                    timestamp = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S,%f')
                else:
                    timestamp = datetime.strptime(ts_str, '%d/%b/%Y:%H:%M:%S %z')
            else:
                timestamp = datetime.now()
            
            level = data.get('level', 'INFO')
            message = data.get('message', line)
            
            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                source='unknown',
                metadata=data
            )
        except Exception:
            return None
    
    @timing_decorator
    def load_logs(self, filepath: Path, max_lines=None):
        print(f"Loading logs from {filepath}...")
        
        count = 0
        for line in self.open_log_file(filepath):
            if max_lines and count >= max_lines:
                break
            
            entry = self.parse_line(line.strip())
            if entry:
                self.entries.append(entry)
                
                if entry.level == 'ERROR':
                    self.errors[entry.message] += 1
                elif entry.level == 'WARNING':
                    self.warnings[entry.message] += 1
                
                count += 1
        
        print(f"Loaded {len(self.entries)} log entries")
    
    def filter_by_time(self, start: datetime, end: datetime) -> List[LogEntry]:
        return [e for e in self.entries if start <= e.timestamp <= end]
    
    def filter_by_level(self, level: str) -> List[LogEntry]:
        return [e for e in self.entries if e.level == level]
    
    def get_error_timeline(self, interval_minutes=60) -> Dict[datetime, int]:
        timeline = defaultdict(int)
        
        for entry in self.entries:
            if entry.level == 'ERROR':
                bucket = entry.timestamp.replace(
                    minute=(entry.timestamp.minute // interval_minutes) * interval_minutes,
                    second=0,
                    microsecond=0
                )
                timeline[bucket] += 1
        
        return dict(sorted(timeline.items()))
    
    def detect_error_patterns(self, min_occurrences=3) -> Dict[str, int]:
        patterns = {}
        
        for message, count in self.errors.items():
            if count >= min_occurrences:
                cleaned = re.sub(r'\d+', 'N', message)
                cleaned = re.sub(r'0x[0-9a-fA-F]+', '0xHEX', cleaned)
                cleaned = re.sub(r'/\S+/', '/PATH/', cleaned)
                patterns[cleaned] = patterns.get(cleaned, 0) + count
        
        return dict(sorted(patterns.items(), key=lambda x: x[1], reverse=True))
    
    def detect_anomalies(self, threshold=2.0) -> List[Dict]:
        hourly_counts = defaultdict(list)
        
        for entry in self.entries:
            if entry.level == 'ERROR':
                hour = entry.timestamp.hour
                hourly_counts[hour].append(entry)
        
        anomalies = []
        
        for hour, errors in hourly_counts.items():
            counts = [len(errors)]
            
            if len(counts) > 1:
                mean = statistics.mean(counts)
                stdev = statistics.stdev(counts) if len(counts) > 1 else 0
                
                if stdev > 0 and len(errors) > mean + threshold * stdev:
                    anomalies.append({
                        'hour': hour,
                        'count': len(errors),
                        'expected': mean,
                        'deviation': (len(errors) - mean) / stdev if stdev > 0 else 0
                    })
        
        return sorted(anomalies, key=lambda x: x['deviation'], reverse=True)
    
    def search_pattern(self, pattern: str, case_sensitive=False) -> List[LogEntry]:
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
        return [e for e in self.entries if regex.search(e.message)]
    
    def get_ip_statistics(self) -> Dict[str, int]:
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        ip_counts = Counter()
        
        for entry in self.entries:
            ips = ip_pattern.findall(entry.message)
            ip_counts.update(ips)
        
        return dict(ip_counts.most_common(10))
    
    @timing_decorator
    def generate_report(self) -> AnalysisReport:
        if not self.entries:
            return None
        
        timestamps = [e.timestamp for e in self.entries]
        
        error_rate = defaultdict(int)
        for entry in self.entries:
            if entry.level == 'ERROR':
                error_rate[entry.timestamp.hour] += 1
        
        return AnalysisReport(
            total_entries=len(self.entries),
            error_count=sum(self.errors.values()),
            warning_count=sum(self.warnings.values()),
            time_range=(min(timestamps), max(timestamps)),
            top_errors=Counter(self.errors).most_common(10),
            error_rate_by_hour=dict(error_rate),
            anomalies=self.detect_anomalies(),
            patterns=self.detect_error_patterns()
        )
    
    def export_report(self, report: AnalysisReport, filepath: Path):
        data = {
            'total_entries': report.total_entries,
            'error_count': report.error_count,
            'warning_count': report.warning_count,
            'time_range': [t.isoformat() for t in report.time_range],
            'top_errors': report.top_errors,
            'error_rate_by_hour': report.error_rate_by_hour,
            'anomalies': report.anomalies,
            'patterns': report.patterns
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"Report exported to {filepath}")

def create_sample_log(filepath: Path):
    sample_logs = [
        "2024-01-29 10:15:23,123 - INFO - Application started",
        "2024-01-29 10:15:24,456 - INFO - Connected to database",
        "2024-01-29 10:15:30,789 - ERROR - Failed to connect to API endpoint: timeout",
        "2024-01-29 10:16:45,012 - WARNING - High memory usage detected: 85%",
        "2024-01-29 10:17:12,345 - ERROR - Database query failed: connection lost",
        "2024-01-29 10:18:00,678 - ERROR - Failed to connect to API endpoint: timeout",
        "2024-01-29 10:19:30,901 - INFO - Request processed successfully",
        "2024-01-29 10:20:15,234 - ERROR - Failed to connect to API endpoint: timeout",
        "2024-01-29 10:21:45,567 - WARNING - Slow query detected: 5.2s",
        "2024-01-29 10:22:30,890 - ERROR - Out of memory error in module X",
    ]
    
    with open(filepath, 'w') as f:
        f.write('\n'.join(sample_logs))

def main():
    sample_log = Path("sample.log")
    create_sample_log(sample_log)
    
    analyzer = LogAnalyzer(log_format='python')
    analyzer.load_logs(sample_log)
    
    print("\n" + "="*50)
    print("LOG ANALYSIS REPORT")
    print("="*50)
    
    report = analyzer.generate_report()
    
    print(f"\nTotal Entries: {report.total_entries}")
    print(f"Errors: {report.error_count}")
    print(f"Warnings: {report.warning_count}")
    print(f"Time Range: {report.time_range[0]} to {report.time_range[1]}")
    
    print("\nTop Error Messages:")
    for msg, count in report.top_errors[:5]:
        print(f"  [{count}x] {msg[:80]}...")
    
    print("\nError Patterns Detected:")
    for pattern, count in list(report.patterns.items())[:5]:
        print(f"  [{count}x] {pattern[:80]}...")
    
    print("\nSearching for 'timeout' errors:")
    timeout_errors = analyzer.search_pattern('timeout')
    print(f"  Found {len(timeout_errors)} occurrences")
    
    analyzer.export_report(report, Path("log_analysis_report.json"))

if __name__ == "__main__":
    main()
