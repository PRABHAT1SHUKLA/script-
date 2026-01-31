#!/usr/bin/env python3
"""
Advanced System Monitor & Performance Analyzer
A comprehensive monitoring tool with real-time metrics, alerts, and visualization
"""

import psutil
import time
import json
import sqlite3
import threading
import argparse
import logging
from datetime import datetime, timedelta
from collections import deque, defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
import statistics
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('system_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Data class for system metrics"""
    timestamp: str
    cpu_percent: float
    cpu_per_core: List[float]
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float
    active_processes: int
    cpu_temp: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


class MetricsDatabase:
    """SQLite database for storing historical metrics"""
    
    def __init__(self, db_path: str = "system_metrics.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize database and create tables"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                cpu_percent REAL,
                memory_percent REAL,
                disk_percent REAL,
                network_sent_mb REAL,
                network_recv_mb REAL,
                active_processes INTEGER,
                data_json TEXT
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                alert_type TEXT,
                severity TEXT,
                message TEXT,
                value REAL
            )
        ''')
        
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON metrics(timestamp)
        ''')
        
        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    def insert_metrics(self, metrics: SystemMetrics):
        """Insert metrics into database"""
        try:
            self.cursor.execute('''
                INSERT INTO metrics 
                (timestamp, cpu_percent, memory_percent, disk_percent, 
                 network_sent_mb, network_recv_mb, active_processes, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metrics.timestamp,
                metrics.cpu_percent,
                metrics.memory_percent,
                metrics.disk_percent,
                metrics.network_sent_mb,
                metrics.network_recv_mb,
                metrics.active_processes,
                json.dumps(metrics.to_dict())
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error inserting metrics: {e}")
    
    def insert_alert(self, alert_type: str, severity: str, message: str, value: float):
        """Insert alert into database"""
        try:
            self.cursor.execute('''
                INSERT INTO alerts (timestamp, alert_type, severity, message, value)
                VALUES (?, ?, ?, ?, ?)
            ''', (datetime.now().isoformat(), alert_type, severity, message, value))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error inserting alert: {e}")
    
    def get_recent_metrics(self, hours: int = 1) -> List[Dict]:
        """Get metrics from the last N hours"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        self.cursor.execute('''
            SELECT data_json FROM metrics 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC
        ''', (cutoff,))
        
        return [json.loads(row[0]) for row in self.cursor.fetchall()]
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """Get alerts from the last N hours"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        self.cursor.execute('''
            SELECT timestamp, alert_type, severity, message, value 
            FROM alerts 
            WHERE timestamp > ? 
            ORDER BY timestamp DESC
        ''', (cutoff,))
        
        return [
            {
                'timestamp': row[0],
                'type': row[1],
                'severity': row[2],
                'message': row[3],
                'value': row[4]
            }
            for row in self.cursor.fetchall()
        ]
    
    def cleanup_old_data(self, days: int = 7):
        """Remove data older than N days"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        self.cursor.execute('DELETE FROM metrics WHERE timestamp < ?', (cutoff,))
        self.cursor.execute('DELETE FROM alerts WHERE timestamp < ?', (cutoff,))
        self.conn.commit()
        logger.info(f"Cleaned up data older than {days} days")
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


class AlertManager:
    """Manages system alerts based on thresholds"""
    
    def __init__(self, db: MetricsDatabase):
        self.db = db
        self.thresholds = {
            'cpu': {'warning': 70, 'critical': 90},
            'memory': {'warning': 75, 'critical': 90},
            'disk': {'warning': 80, 'critical': 95},
        }
        self.alert_cooldown = defaultdict(lambda: datetime.min)
        self.cooldown_period = timedelta(minutes=5)
    
    def check_alerts(self, metrics: SystemMetrics):
        """Check metrics against thresholds and generate alerts"""
        alerts = []
        
        checks = [
            ('cpu', metrics.cpu_percent, 'CPU Usage'),
            ('memory', metrics.memory_percent, 'Memory Usage'),
            ('disk', metrics.disk_percent, 'Disk Usage'),
        ]
        
        for alert_type, value, label in checks:
            severity = self._check_threshold(alert_type, value)
            if severity:
                alert_key = f"{alert_type}_{severity}"
                if self._should_alert(alert_key):
                    message = f"{label} {severity.upper()}: {value:.1f}%"
                    alerts.append({
                        'type': alert_type,
                        'severity': severity,
                        'message': message,
                        'value': value
                    })
                    self.db.insert_alert(alert_type, severity, message, value)
                    self.alert_cooldown[alert_key] = datetime.now()
                    logger.warning(message)
        
        return alerts
    
    def _check_threshold(self, alert_type: str, value: float) -> Optional[str]:
        """Check if value exceeds threshold"""
        thresholds = self.thresholds.get(alert_type, {})
        if value >= thresholds.get('critical', 100):
            return 'critical'
        elif value >= thresholds.get('warning', 100):
            return 'warning'
        return None
    
    def _should_alert(self, alert_key: str) -> bool:
        """Check if enough time has passed since last alert"""
        return datetime.now() - self.alert_cooldown[alert_key] > self.cooldown_period


class SystemMonitor:
    """Main system monitoring class"""
    
    def __init__(self, interval: int = 5, db_path: str = "system_metrics.db"):
        self.interval = interval
        self.db = MetricsDatabase(db_path)
        self.alert_manager = AlertManager(self.db)
        self.running = False
        self.monitor_thread = None
        
        self.metrics_history = deque(maxlen=720)
        
        self.network_io_last = psutil.net_io_counters()
        self.last_check_time = time.time()
    
    def collect_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
        
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024**3)
        memory_available_gb = memory.available / (1024**3)
        
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024**3)
        disk_free_gb = disk.free / (1024**3)
        
        current_time = time.time()
        time_delta = current_time - self.last_check_time
        
        network_io = psutil.net_io_counters()
        network_sent_mb = (network_io.bytes_sent - self.network_io_last.bytes_sent) / (1024**2)
        network_recv_mb = (network_io.bytes_recv - self.network_io_last.bytes_recv) / (1024**2)
        
        self.network_io_last = network_io
        self.last_check_time = current_time
        
        active_processes = len(psutil.pids())
        
        cpu_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        cpu_temp = entries[0].current
                        break
        except:
            pass
        
        return SystemMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            cpu_per_core=cpu_per_core,
            memory_percent=memory_percent,
            memory_used_gb=memory_used_gb,
            memory_available_gb=memory_available_gb,
            disk_percent=disk_percent,
            disk_used_gb=disk_used_gb,
            disk_free_gb=disk_free_gb,
            network_sent_mb=network_sent_mb,
            network_recv_mb=network_recv_mb,
            active_processes=active_processes,
            cpu_temp=cpu_temp
        )
    
    def display_metrics(self, metrics: SystemMetrics):
        """Display current metrics in a formatted way"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("=" * 80)
        print(f"{'ADVANCED SYSTEM MONITOR':^80}")
        print(f"{'Last Update: ' + metrics.timestamp:^80}")
        print("=" * 80)
        print()
        
        print(f"🖥️  CPU Usage: {metrics.cpu_percent:6.2f}% " + self._get_bar(metrics.cpu_percent))
        print(f"   Cores: {', '.join([f'{c:.1f}%' for c in metrics.cpu_per_core])}")
        if metrics.cpu_temp:
            print(f"   Temperature: {metrics.cpu_temp:.1f}°C")
        print()
        
        print(f"💾 Memory Usage: {metrics.memory_percent:6.2f}% " + self._get_bar(metrics.memory_percent))
        print(f"   Used: {metrics.memory_used_gb:.2f} GB | Available: {metrics.memory_available_gb:.2f} GB")
        print()
        
        print(f"💿 Disk Usage: {metrics.disk_percent:6.2f}% " + self._get_bar(metrics.disk_percent))
        print(f"   Used: {metrics.disk_used_gb:.2f} GB | Free: {metrics.disk_free_gb:.2f} GB")
        print()
        
        print(f"🌐 Network:")
        print(f"   ↑ Sent: {metrics.network_sent_mb:.2f} MB/s | ↓ Received: {metrics.network_recv_mb:.2f} MB/s")
        print()
        
        print(f"⚙️  Active Processes: {metrics.active_processes}")
        print()
        
        recent_alerts = self.db.get_recent_alerts(hours=1)
        if recent_alerts:
            print("⚠️  Recent Alerts:")
            for alert in recent_alerts[:5]:
                emoji = "🔴" if alert['severity'] == 'critical' else "🟡"
                print(f"   {emoji} {alert['message']} [{alert['timestamp'][:19]}]")
        
        print("=" * 80)
        print("Press Ctrl+C to stop monitoring")
    
    def _get_bar(self, percent: float, width: int = 40) -> str:
        """Generate a visual progress bar"""
        filled = int(width * percent / 100)
        bar = '█' * filled + '░' * (width - filled)
        
        if percent >= 90:
            color = '\033[91m'
        elif percent >= 70:
            color = '\033[93m'
        else:
            color = '\033[92m'
        
        reset = '\033[0m'
        return f"{color}[{bar}]{reset}"
    
    def generate_report(self, hours: int = 24) -> Dict:
        """Generate statistical report from historical data"""
        metrics_list = self.db.get_recent_metrics(hours)
        
        if not metrics_list:
            return {'error': 'No data available for the specified period'}
        
        cpu_values = [m['cpu_percent'] for m in metrics_list]
        memory_values = [m['memory_percent'] for m in metrics_list]
        disk_values = [m['disk_percent'] for m in metrics_list]
        
        report = {
            'period_hours': hours,
            'total_samples': len(metrics_list),
            'cpu': {
                'average': statistics.mean(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values),
                'stdev': statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
            },
            'memory': {
                'average': statistics.mean(memory_values),
                'max': max(memory_values),
                'min': min(memory_values),
                'stdev': statistics.stdev(memory_values) if len(memory_values) > 1 else 0
            },
            'disk': {
                'average': statistics.mean(disk_values),
                'max': max(disk_values),
                'min': min(disk_values),
                'stdev': statistics.stdev(disk_values) if len(disk_values) > 1 else 0
            },
            'alerts': self.db.get_recent_alerts(hours)
        }
        
        return report
    
    def export_report(self, filename: str, hours: int = 24):
        """Export report to JSON file"""
        report = self.generate_report(hours)
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Report exported to {filename}")
        print(f"\n✅ Report exported to {filename}")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting system monitor")
        
        while self.running:
            try:
                metrics = self.collect_metrics()
                
                self.metrics_history.append(metrics)
                
                self.db.insert_metrics(metrics)
                
                self.alert_manager.check_alerts(metrics)
                
                self.display_metrics(metrics)
                
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.interval)
    
    def start(self):
        """Start monitoring in a separate thread"""
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
    
    def stop(self):
        """Stop monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
        self.db.close()
        logger.info("System monitor stopped")


def main():
    parser = argparse.ArgumentParser(description='Advanced System Monitor')
    parser.add_argument('-i', '--interval', type=int, default=5,
                        help='Monitoring interval in seconds (default: 5)')
    parser.add_argument('-r', '--report', type=str,
                        help='Generate report and save to specified file')
    parser.add_argument('--hours', type=int, default=24,
                        help='Hours of data for report (default: 24)')
    parser.add_argument('--cleanup', type=int,
                        help='Cleanup data older than N days')
    
    args = parser.parse_args()
    
    monitor = SystemMonitor(interval=args.interval)
    
    if args.cleanup:
        monitor.db.cleanup_old_data(days=args.cleanup)
        print(f"Cleaned up data older than {args.cleanup} days")
        return
    
    if args.report:
        monitor.export_report(args.report, hours=args.hours)
        return
    
    try:
        monitor.start()
        monitor.monitor_thread.join()
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        monitor.stop()
        print("Monitor stopped. Goodbye!")


if __name__ == "__main__":
    main()
