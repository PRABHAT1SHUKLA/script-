#!/usr/bin/env python3

import subprocess
import time
import re
from collections import defaultdict, deque
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
import sys

class DDoSDetector:
    def __init__(self, config_file='ddos_config.json'):
        self.load_config(config_file)
        self.connection_history = deque(maxlen=self.config['history_window'])
        self.ip_counters = defaultdict(int)
        self.blocked_ips = set()
        self.alert_cooldown = {}
        
    def load_config(self, config_file):
        default_config = {
            'check_interval': 5,
            'connections_threshold': 100,
            'spike_multiplier': 3.0,
            'ip_connection_threshold': 50,
            'history_window': 60,
            'alert_email': '',
            'smtp_server': 'localhost',
            'smtp_port': 25,
            'auto_block': False,
            'whitelist_ips': [],
            'ports_to_monitor': [80, 443],
            'alert_cooldown_seconds': 300
        }
        
        try:
            with open(config_file, 'r') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        except FileNotFoundError:
            print(f"Config file not found, using defaults. Creating {config_file}...")
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
        
        self.config = default_config
    
    def get_active_connections(self):
        try:
            result = subprocess.run(
                ['netstat', '-an'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout
        except Exception as e:
            print(f"Error getting connections: {e}")
            return ""
    
    def parse_connections(self, netstat_output):
        connections = []
        ip_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+):(\d+)')
        
        for line in netstat_output.split('\n'):
            if 'ESTABLISHED' in line or 'SYN_RECV' in line:
                match = ip_pattern.findall(line)
                if match:
                    for ip, port in match:
                        if int(port) in self.config['ports_to_monitor']:
                            connections.append({'ip': ip, 'port': int(port)})
        
        return connections
    
    def analyze_connections(self, connections):
        current_count = len(connections)
        self.connection_history.append(current_count)
        
        if len(self.connection_history) < 10:
            return None
        
        avg_connections = sum(self.connection_history) / len(self.connection_history)
        
        alerts = []
        
        if current_count > self.config['connections_threshold']:
            spike_ratio = current_count / (avg_connections + 1)
            
            if spike_ratio > self.config['spike_multiplier']:
                alerts.append({
                    'type': 'CONNECTION_SPIKE',
                    'severity': 'HIGH',
                    'current': current_count,
                    'average': round(avg_connections, 2),
                    'ratio': round(spike_ratio, 2)
                })
        
        self.ip_counters.clear()
        for conn in connections:
            ip = conn['ip']
            if ip not in self.config['whitelist_ips']:
                self.ip_counters[ip] += 1
        
        suspicious_ips = []
        for ip, count in self.ip_counters.items():
            if count > self.config['ip_connection_threshold']:
                suspicious_ips.append({'ip': ip, 'connections': count})
        
        if suspicious_ips:
            suspicious_ips.sort(key=lambda x: x['connections'], reverse=True)
            alerts.append({
                'type': 'SUSPICIOUS_IPS',
                'severity': 'MEDIUM',
                'ips': suspicious_ips[:10]
            })
        
        return alerts if alerts else None
    
    def block_ip(self, ip):
        if ip in self.blocked_ips or ip in self.config['whitelist_ips']:
            return
        
        try:
            subprocess.run(
                ['iptables', '-A', 'INPUT', '-s', ip, '-j', 'DROP'],
                check=True,
                timeout=5
            )
            self.blocked_ips.add(ip)
            print(f"[BLOCKED] IP {ip} has been blocked via iptables")
        except Exception as e:
            print(f"Error blocking IP {ip}: {e}")
    
    def send_alert(self, alert_message):
        if not self.config['alert_email']:
            return
        
        alert_key = alert_message[:50]
        current_time = time.time()
        
        if alert_key in self.alert_cooldown:
            if current_time - self.alert_cooldown[alert_key] < self.config['alert_cooldown_seconds']:
                return
        
        self.alert_cooldown[alert_key] = current_time
        
        try:
            msg = MIMEText(alert_message)
            msg['Subject'] = 'DDoS Alert - Suspicious Activity Detected'
            msg['From'] = 'ddos-detector@localhost'
            msg['To'] = self.config['alert_email']
            
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as server:
                server.send_message(msg)
            print("[EMAIL] Alert sent successfully")
        except Exception as e:
            print(f"Error sending email alert: {e}")
    
    def format_alert(self, alerts):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = f"\n{'='*60}\n[ALERT] DDoS Detection Alert - {timestamp}\n{'='*60}\n"
        
        for alert in alerts:
            if alert['type'] == 'CONNECTION_SPIKE':
                message += f"\n⚠️  CONNECTION SPIKE DETECTED\n"
                message += f"   Severity: {alert['severity']}\n"
                message += f"   Current connections: {alert['current']}\n"
                message += f"   Average connections: {alert['average']}\n"
                message += f"   Spike ratio: {alert['ratio']}x\n"
            
            elif alert['type'] == 'SUSPICIOUS_IPS':
                message += f"\n🔍 SUSPICIOUS IP ADDRESSES\n"
                message += f"   Severity: {alert['severity']}\n"
                message += f"   Top offenders:\n"
                for ip_info in alert['ips'][:5]:
                    message += f"      {ip_info['ip']}: {ip_info['connections']} connections\n"
                    
                    if self.config['auto_block']:
                        self.block_ip(ip_info['ip'])
        
        message += f"\n{'='*60}\n"
        return message
    
    def run(self):
        print(f"DDoS Detector Started - Monitoring ports: {self.config['ports_to_monitor']}")
        print(f"Check interval: {self.config['check_interval']}s")
        print(f"Auto-block enabled: {self.config['auto_block']}")
        print(f"Press Ctrl+C to stop\n")
        
        try:
            while True:
                netstat_output = self.get_active_connections()
                connections = self.parse_connections(netstat_output)
                alerts = self.analyze_connections(connections)
                
                if alerts:
                    alert_message = self.format_alert(alerts)
                    print(alert_message)
                    self.send_alert(alert_message)
                else:
                    current_count = len(connections)
                    avg = sum(self.connection_history) / len(self.connection_history) if self.connection_history else 0
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Connections: {current_count} (avg: {avg:.1f}) - Normal", end='\r')
                
                time.sleep(self.config['check_interval'])
                
        except KeyboardInterrupt:
            print("\n\nDDoS Detector stopped by user")
            sys.exit(0)

if __name__ == '__main__':
    detector = DDoSDetector()
    detector.run()
