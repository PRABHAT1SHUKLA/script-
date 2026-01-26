#!/usr/bin/env python3
"""
Comprehensive System Monitoring Script
Monitors CPU, memory, disk, network, and custom services
"""

import psutil
import time
import json
import logging
from datetime import datetime
from pathlib import Path
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
CONFIG = {
    "check_interval": 60,  # seconds
    "cpu_threshold": 80,   # percentage
    "memory_threshold": 85,  # percentage
    "disk_threshold": 90,   # percentage
    "log_file": "monitoring.log",
    "alert_email": "admin@example.com",
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "your-email@gmail.com",
    "smtp_password": "your-app-password"
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(CONFIG["log_file"]),
        logging.StreamHandler()
    ]
)

class SystemMonitor:
    def __init__(self, config):
        self.config = config
        self.alerts = []
    
    def check_cpu(self):
        """Monitor CPU usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        status = {
            "metric": "CPU",
            "value": cpu_percent,
            "threshold": self.config["cpu_threshold"],
            "status": "OK" if cpu_percent < self.config["cpu_threshold"] else "CRITICAL",
            "cores": cpu_count,
            "timestamp": datetime.now().isoformat()
        }
        
        if status["status"] == "CRITICAL":
            self.alerts.append(f"CPU usage at {cpu_percent}% (threshold: {self.config['cpu_threshold']}%)")
        
        logging.info(f"CPU: {cpu_percent}% ({cpu_count} cores)")
        return status
    
    def check_memory(self):
        """Monitor memory usage"""
        mem = psutil.virtual_memory()
        
        status = {
            "metric": "Memory",
            "used_percent": mem.percent,
            "used_gb": round(mem.used / (1024**3), 2),
            "total_gb": round(mem.total / (1024**3), 2),
            "threshold": self.config["memory_threshold"],
            "status": "OK" if mem.percent < self.config["memory_threshold"] else "CRITICAL",
            "timestamp": datetime.now().isoformat()
        }
        
        if status["status"] == "CRITICAL":
            self.alerts.append(f"Memory usage at {mem.percent}% (threshold: {self.config['memory_threshold']}%)")
        
        logging.info(f"Memory: {mem.percent}% ({status['used_gb']}GB / {status['total_gb']}GB)")
        return status
    
    def check_disk(self):
        """Monitor disk usage"""
        disk_stats = []
        
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                
                status = {
                    "metric": "Disk",
                    "mountpoint": partition.mountpoint,
                    "device": partition.device,
                    "used_percent": usage.percent,
                    "used_gb": round(usage.used / (1024**3), 2),
                    "total_gb": round(usage.total / (1024**3), 2),
                    "threshold": self.config["disk_threshold"],
                    "status": "OK" if usage.percent < self.config["disk_threshold"] else "CRITICAL",
                    "timestamp": datetime.now().isoformat()
                }
                
                if status["status"] == "CRITICAL":
                    self.alerts.append(f"Disk {partition.mountpoint} at {usage.percent}% (threshold: {self.config['disk_threshold']}%)")
                
                logging.info(f"Disk {partition.mountpoint}: {usage.percent}% ({status['used_gb']}GB / {status['total_gb']}GB)")
                disk_stats.append(status)
            except PermissionError:
                continue
        
        return disk_stats
    
    def check_network(self):
        """Monitor network statistics"""
        net_io = psutil.net_io_counters()
        
        status = {
            "metric": "Network",
            "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2),
            "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2),
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errors_in": net_io.errin,
            "errors_out": net_io.errout,
            "timestamp": datetime.now().isoformat()
        }
        
        logging.info(f"Network: Sent {status['bytes_sent_mb']}MB, Recv {status['bytes_recv_mb']}MB")
        return status
    
    def check_processes(self, top_n=5):
        """Monitor top processes by CPU and memory"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Sort by CPU
        top_cpu = sorted(processes, key=lambda x: x['cpu_percent'] or 0, reverse=True)[:top_n]
        top_mem = sorted(processes, key=lambda x: x['memory_percent'] or 0, reverse=True)[:top_n]
        
        return {
            "top_cpu": top_cpu,
            "top_memory": top_mem,
            "total_processes": len(processes)
        }
    
    def send_alert(self, subject, body):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config["smtp_user"]
            msg['To'] = self.config["alert_email"]
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.config["smtp_server"], self.config["smtp_port"])
            server.starttls()
            server.login(self.config["smtp_user"], self.config["smtp_password"])
            server.send_message(msg)
            server.quit()
            
            logging.info(f"Alert sent: {subject}")
        except Exception as e:
            logging.error(f"Failed to send alert: {e}")
    
    def run_checks(self):
        """Run all monitoring checks"""
        logging.info("=" * 50)
        logging.info("Starting monitoring cycle")
        
        self.alerts = []
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "cpu": self.check_cpu(),
            "memory": self.check_memory(),
            "disk": self.check_disk(),
            "network": self.check_network(),
            "processes": self.check_processes()
        }
        
        # Send alerts if any
        if self.alerts:
            subject = f"System Alert - {len(self.alerts)} issue(s) detected"
            body = "Critical issues detected:\n\n" + "\n".join(f"- {alert}" for alert in self.alerts)
            logging.warning(f"Alerts triggered: {len(self.alerts)}")
            # Uncomment to enable email alerts
            # self.send_alert(subject, body)
        
        return results
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logging.info("System monitoring started")
        
        try:
            while True:
                self.run_checks()
                time.sleep(self.config["check_interval"])
        except KeyboardInterrupt:
            logging.info("Monitoring stopped by user")
        except Exception as e:
            logging.error(f"Monitoring error: {e}")

def main():
    monitor = SystemMonitor(CONFIG)
    
    # Run once or in loop
    print("Starting system monitoring...")
    print(f"Check interval: {CONFIG['check_interval']} seconds")
    print(f"Thresholds - CPU: {CONFIG['cpu_threshold']}%, Memory: {CONFIG['memory_threshold']}%, Disk: {CONFIG['disk_threshold']}%")
    print("Press Ctrl+C to stop\n")
    
    monitor.monitor_loop()

if __name__ == "__main__":
    main()
