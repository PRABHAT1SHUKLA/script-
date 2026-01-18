#!/usr/bin/env python3
"""
Network Traffic Spike Monitor
Monitors network traffic and alerts sysadmin on sudden spikes
Supports: Email, Slack, Telegram, Discord, and Log file alerts
"""

import psutil
import time
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from collections import deque
import statistics
import requests

# ==================== CONFIGURATION ====================

CONFIG = {
    # Network interface to monitor (None = all interfaces, or specify like 'eth0', 'wlan0')
    'INTERFACE': None,
    
    # Threshold settings
    'SPIKE_MULTIPLIER': 2.5,  # Alert if traffic is 2.5x the average
    'MIN_THRESHOLD_MBPS': 10,  # Minimum Mbps to consider a spike
    'BASELINE_WINDOW': 30,  # Number of samples for baseline (30 = 5 min at 10s interval)
    'CHECK_INTERVAL': 10,  # Seconds between checks
    
    # Alert settings
    'ALERT_COOLDOWN': 300,  # Seconds before re-alerting (5 minutes)
    'ENABLE_EMAIL': False,
    'ENABLE_SLACK': False,
    'ENABLE_TELEGRAM': False,
    'ENABLE_DISCORD': False,
    'ENABLE_LOG': True,
    
    # Email configuration
    'EMAIL': {
        'SMTP_SERVER': 'smtp.gmail.com',
        'SMTP_PORT': 587,
        'FROM_EMAIL': 'your-email@gmail.com',
        'TO_EMAIL': 'admin@example.com',
        'PASSWORD': 'your-app-password',  # Use app password for Gmail
    },
    
    # Slack webhook
    'SLACK_WEBHOOK': 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
    
    # Telegram bot
    'TELEGRAM': {
        'BOT_TOKEN': 'YOUR_BOT_TOKEN',
        'CHAT_ID': 'YOUR_CHAT_ID',
    },
    
    # Discord webhook
    'DISCORD_WEBHOOK': 'https://discord.com/api/webhooks/YOUR/WEBHOOK/URL',
    
    # Log file
    'LOG_FILE': '/var/log/network_spike_monitor.log',
}

# ==================== MONITORING CLASS ====================

class NetworkMonitor:
    def __init__(self, config):
        self.config = config
        self.baseline_data = deque(maxlen=config['BASELINE_WINDOW'])
        self.last_alert_time = 0
        self.last_bytes_sent = 0
        self.last_bytes_recv = 0
        self.first_run = True
        
    def get_network_stats(self):
        """Get current network statistics"""
        stats = psutil.net_io_counters(pernic=True) if self.config['INTERFACE'] else {
            'total': psutil.net_io_counters()
        }
        
        if self.config['INTERFACE']:
            if self.config['INTERFACE'] in stats:
                return stats[self.config['INTERFACE']]
            else:
                print(f"Interface {self.config['INTERFACE']} not found!")
                return None
        else:
            return stats['total']
    
    def bytes_to_mbps(self, bytes_per_sec):
        """Convert bytes per second to Mbps"""
        return (bytes_per_sec * 8) / (1024 * 1024)
    
    def calculate_traffic_rate(self):
        """Calculate current traffic rate in Mbps"""
        current_stats = self.get_network_stats()
        if not current_stats:
            return None, None
        
        if self.first_run:
            self.last_bytes_sent = current_stats.bytes_sent
            self.last_bytes_recv = current_stats.bytes_recv
            self.first_run = False
            return 0, 0
        
        bytes_sent_diff = current_stats.bytes_sent - self.last_bytes_sent
        bytes_recv_diff = current_stats.bytes_recv - self.last_bytes_recv
        
        interval = self.config['CHECK_INTERVAL']
        upload_rate = self.bytes_to_mbps(bytes_sent_diff / interval)
        download_rate = self.bytes_to_mbps(bytes_recv_diff / interval)
        
        self.last_bytes_sent = current_stats.bytes_sent
        self.last_bytes_recv = current_stats.bytes_recv
        
        return upload_rate, download_rate
    
    def check_for_spike(self, current_rate):
        """Check if current rate is a spike"""
        if len(self.baseline_data) < 5:  # Need minimum data
            return False
        
        avg_rate = statistics.mean(self.baseline_data)
        threshold = max(
            avg_rate * self.config['SPIKE_MULTIPLIER'],
            self.config['MIN_THRESHOLD_MBPS']
        )
