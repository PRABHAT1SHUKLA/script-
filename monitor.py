#!/usr/bin/env python3
"""
Advanced System Monitor & Log Analyzer
A production-grade monitoring tool with real-time analytics and anomaly detection
"""

import psutil
import asyncio
import threading
import json
import re
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import statistics
import argparse


@dataclass
class SystemMetrics:
    """Immutable system metrics snapshot"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float
    process_count: int
    
    def to_dict(self) -> dict:
        return asdict(self)


class CircularBuffer:
    """Thread-safe circular buffer for time-series data"""
    def __init__(self, maxlen: int = 1000):
        self._buffer = deque(maxlen=maxlen)
        self._lock = threading.RLock()
    
    def append(self, item):
        with self._lock:
            self._buffer.append(item)
    
    def get_snapshot(self) -> List:
        with self._lock:
            return list(self._buffer)
    
    def __len__(self):
        return len(self._buffer)


class AnomalyDetector:
    """Statistical anomaly detection using Z-score method"""
    def __init__(self, threshold: float = 2.5):
        self.threshold = threshold
        self.history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
    
    def detect(self, metric_name: str, value: float) -> Tuple[bool, float]:
        """Returns (is_anomaly, z_score)"""
        hist = self.history[metric_name]
        hist.append(value)
        
        if len(hist) < 10:
            return False, 0.0
        
        mean = statistics.mean(hist)
        try:
            stdev = statistics.stdev(hist)
            if stdev == 0:
                return False, 0.0
            z_score = abs((value - mean) / stdev)
            return z_score > self.threshold, z_score
        except statistics.StatisticsError:
            return False, 0.0


class LogPatternMatcher:
    """Advanced log pattern matching with compiled regex"""
    PATTERNS = {
        'error': re.compile(r'\b(error|exception|fatal|critical)\b', re.IGNORECASE),
        'warning': re.compile(r'\b(warn|warning|alert)\b', re.IGNORECASE),
        'security': re.compile(r'\b(auth|authentication|unauthorized|forbidden|denied)\b', re.IGNORECASE),
        'performance': re.compile(r'\b(slow|timeout|latency|delay)\b', re.IGNORECASE),
    }
    
    @classmethod
    def analyze(cls, log_line: str) -> List[str]:
        """Returns list of matched categories"""
        matches = []
        for category, pattern in cls.PATTERNS.items():
            if pattern.search(log_line):
                matches.append(category)
        return matches


class SystemMonitor:
    """Main monitoring engine with async operations"""
    
    def __init__(self, interval: float = 1.0, buffer_size: int = 1000):
        self.interval = interval
        self.metrics_buffer = CircularBuffer(buffer_size)
        self.anomaly_detector = AnomalyDetector()
        self.running = False
        self._last_disk_io = None
        self._last_net_io = None
        
    def _get_disk_io_delta(self) -> Tuple[float, float]:
        """Calculate disk I/O delta in MB"""
        current = psutil.disk_io_counters()
        if self._last_disk_io is None:
            self._last_disk_io = current
            return 0.0, 0.0
        
        read_mb = (current.read_bytes - self._last_disk_io.read_bytes) / (1024 * 1024)
        write_mb = (current.write_bytes - self._last_disk_io.write_bytes) / (1024 * 1024)
        self._last_disk_io = current
        return read_mb, write_mb
    
    def _get_network_delta(self) -> Tuple[float, float]:
        """Calculate network I/O delta in MB"""
        current = psutil.net_io_counters()
        if self._last_net_io is None:
            self._last_net_io = current
            return 0.0, 0.0
        
        sent_mb = (current.bytes_sent - self._last_net_io.bytes_sent) / (1024 * 1024)
        recv_mb = (current.bytes_recv - self._last_net_io.bytes_recv) / (1024 * 1024)
        self._last_net_io = current
        return sent_mb, recv_mb
    
    def collect_metrics(self) -> SystemMetrics:
        """Collect system metrics snapshot"""
        disk_read, disk_write = self._get_disk_io_delta()
        net_sent, net_recv = self._get_network_delta()
        
        return SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=psutil.cpu_percent(interval=0.1),
            memory_percent=psutil.virtual_memory().percent,
            disk_io_read_mb=disk_read,
            disk_io_write_mb=disk_write,
            network_sent_mb=net_sent,
            network_recv_mb=net_recv,
            process_count=len(psutil.pids())
        )
    
    async def monitor_loop(self):
        """Async monitoring loop"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] System monitoring started...")
        self.running = True
        
        while self.running:
            try:
                metrics = self.collect_metrics()
                self.metrics_buffer.append(metrics)
                
                # Anomaly detection
                anomalies = []
                for metric in ['cpu_percent', 'memory_percent']:
                    value = getattr(metrics, metric)
                    is_anomaly, z_score = self.anomaly_detector.detect(metric, value)
                    if is_anomaly:
                        anomalies.append(f"{metric}: {value:.1f}% (z-score: {z_score:.2f})")
                
                if anomalies:
                    print(f"⚠️  ANOMALY DETECTED: {', '.join(anomalies)}")
                
                await asyncio.sleep(self.interval)
                
            except Exception as e:
                print(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(self.interval)
    
    def generate_report(self) -> Dict:
        """Generate statistical report from collected metrics"""
        snapshot = self.metrics_buffer.get_snapshot()
        if not snapshot:
            return {"error": "No data collected"}
        
        cpu_values = [m.cpu_percent for m in snapshot]
        mem_values = [m.memory_percent for m in snapshot]
        
        return {
            "report_time": datetime.now().isoformat(),
            "duration_seconds": len(snapshot) * self.interval,
            "samples_collected": len(snapshot),
            "cpu": {
                "avg": round(statistics.mean(cpu_values), 2),
                "max": round(max(cpu_values), 2),
                "min": round(min(cpu_values), 2),
                "stdev": round(statistics.stdev(cpu_values), 2) if len(cpu_values) > 1 else 0,
            },
            "memory": {
                "avg": round(statistics.mean(mem_values), 2),
                "max": round(max(mem_values), 2),
                "min": round(min(mem_values), 2),
                "stdev": round(statistics.stdev(mem_values), 2) if len(mem_values) > 1 else 0,
            },
            "total_disk_read_mb": round(sum(m.disk_io_read_mb for m in snapshot), 2),
            "total_disk_write_mb": round(sum(m.disk_io_write_mb for m in snapshot), 2),
            "total_network_sent_mb": round(sum(m.network_sent_mb for m in snapshot), 2),
            "total_network_recv_mb": round(sum(m.network_recv_mb for m in snapshot), 2),
        }
    
    def stop(self):
        """Stop monitoring"""
        self.running = False


class LogAnalyzer:
    """Analyze log files for patterns and anomalies"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.pattern_matcher = LogPatternMatcher()
    
    def analyze(self, tail_lines: int = 100) -> Dict:
        """Analyze recent log entries"""
        if not self.log_file.exists():
            return {"error": f"Log file not found: {self.log_file}"}
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = deque(f, maxlen=tail_lines)
            
            analysis = {
                "total_lines": len(lines),
                "categories": defaultdict(int),
                "issues": []
            }
            
            for line in lines:
                categories = self.pattern_matcher.analyze(line)
                for cat in categories:
                    analysis["categories"][cat] += 1
                    if cat in ['error', 'security']:
                        analysis["issues"].append({
                            "category": cat,
                            "preview": line[:100]
                        })
            
            analysis["categories"] = dict(analysis["categories"])
            return analysis
            
        except Exception as e:
            return {"error": str(e)}


async def main():
    """Main entry point with CLI"""
    parser = argparse.ArgumentParser(description="Advanced System Monitor & Log Analyzer")
    parser.add_argument('-d', '--duration', type=int, default=30, help='Monitoring duration in seconds')
    parser.add_argument('-i', '--interval', type=float, default=1.0, help='Sampling interval in seconds')
    parser.add_argument('-l', '--logfile', type=str, help='Log file to analyze')
    parser.add_argument('-o', '--output', type=str, help='Output JSON report file')
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = SystemMonitor(interval=args.interval)
    
    # Start monitoring
    print("=" * 60)
    print("🚀 Advanced System Monitor & Log Analyzer")
    print("=" * 60)
    print(f"⏱️  Duration: {args.duration}s | Interval: {args.interval}s")
    print("=" * 60)
    
    try:
        # Run monitoring
        monitor_task = asyncio.create_task(monitor.monitor_loop())
        await asyncio.sleep(args.duration)
        monitor.stop()
        await monitor_task
        
        print("\n" + "=" * 60)
        print("📊 Generating Report...")
        print("=" * 60)
        
        # Generate report
        report = monitor.generate_report()
        
        # Log analysis if specified
        if args.logfile:
            log_path = Path(args.logfile)
            analyzer = LogAnalyzer(log_path)
            report["log_analysis"] = analyzer.analyze()
        
        # Pretty print report
        print(json.dumps(report, indent=2))
        
        # Save to file if specified
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n✅ Report saved to: {args.output}")
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
        monitor.stop()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        monitor.stop()


if __name__ == "__main__":
    asyncio.run(main())
