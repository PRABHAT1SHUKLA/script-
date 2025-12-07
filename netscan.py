#!/usr/bin/env python3
"""
Network Device Health Monitoring Script
Simulates common network engineering tasks for practice
"""

import socket
import subprocess
import platform
import concurrent.futures
from datetime import datetime
import json

class NetworkHealthChecker:
    def __init__(self):
        self.results = []
        
    def ping_host(self, host, count=4):
        """Ping a host to check connectivity"""
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        command = ['ping', param, str(count), host]
        
        try:
            output = subprocess.run(
                command, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            success = output.returncode == 0
            return {
                'host': host,
                'status': 'UP' if success else 'DOWN',
                'response_time': self._parse_ping_time(output.stdout)
            }
        except subprocess.TimeoutExpired:
            return {'host': host, 'status': 'TIMEOUT', 'response_time': None}
        except Exception as e:
            return {'host': host, 'status': 'ERROR', 'error': str(e)}
    
    def _parse_ping_time(self, output):
        """Extract average ping time from output"""
        try:
            if 'Average' in output:  # Windows
                return output.split('Average = ')[1].split('ms')[0]
            elif 'avg' in output:  # Linux/Mac
                return output.split('avg')[1].split('/')[1]
        except:
            return 'N/A'
        return 'N/A'
    
    def check_port(self, host, port, timeout=3):
        """Check if a specific port is open"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            return {
                'host': host,
                'port': port,
                'status': 'OPEN' if result == 0 else 'CLOSED'
            }
        except socket.gaierror:
            return {'host': host, 'port': port, 'status': 'DNS_ERROR'}
        except Exception as e:
            return {'host': host, 'port': port, 'status': 'ERROR', 'error': str(e)}
    
    def scan_common_ports(self, host):
        """Scan common network service ports"""
        common_ports = {
            22: 'SSH',
            23: 'Telnet',
            80: 'HTTP',
            443: 'HTTPS',
            3389: 'RDP',
            53: 'DNS',
            21: 'FTP'
        }
        
        results = []
        for port, service in common_ports.items():
            result = self.check_port(host, port, timeout=2)
            result['service'] = service
            results.append(result)
        
        return results
    
    def dns_lookup(self, hostname):
        """Perform DNS lookup"""
        try:
            ip = socket.gethostbyname(hostname)
            return {'hostname': hostname, 'ip': ip, 'status': 'SUCCESS'}
        except socket.gaierror:
            return {'hostname': hostname, 'status': 'FAILED'}
    
    def get_local_info(self):
        """Get local network information"""
        hostname = socket.gethostname()
        try:
            local_ip = socket.gethostbyname(hostname)
        except:
            local_ip = 'Unable to determine'
        
        return {
            'hostname': hostname,
            'local_ip': local_ip,
            'platform': platform.system()
        }
    
    def run_full_check(self, targets):
        """Run comprehensive network checks"""
        print("=" * 60)
        print("NETWORK HEALTH CHECK REPORT")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Local info
        print("\n[LOCAL SYSTEM INFO]")
        local_info = self.get_local_info()
        for key, value in local_info.items():
            print(f"  {key.title()}: {value}")
        
        # Connectivity checks
        print("\n[CONNECTIVITY CHECKS]")
        for target in targets:
            print(f"\nChecking {target}...")
            
            # DNS lookup
            dns_result = self.dns_lookup(target)
            if dns_result['status'] == 'SUCCESS':
                print(f"  DNS: {dns_result['ip']}")
                
                # Ping test
                ping_result = self.ping_host(target, count=3)
                print(f"  Ping: {ping_result['status']} (Avg: {ping_result['response_time']} ms)")
                
                # Port scan
                print(f"  Port Scan:")
                port_results = self.scan_common_ports(dns_result['ip'])
                for pr in port_results:
                    if pr['status'] == 'OPEN':
                        print(f"    Port {pr['port']} ({pr['service']}): {pr['status']}")
            else:
                print(f"  DNS: FAILED - Cannot resolve hostname")
        
        print("\n" + "=" * 60)
        print("Health check completed!")
        print("=" * 60)

def main():
    """Main execution function"""
    checker = NetworkHealthChecker()
    
    # Example targets - modify these for your practice
    targets = [
        'google.com',
        'cloudflare.com',
        '8.8.8.8'  # Google DNS
    ]
    
    print("\nNetwork Engineering Practice Script")
    print("This script demonstrates common network monitoring tasks\n")
    
    # Run the full health check
    checker.run_full_check(targets)
    
    print("\nPractice Tips:")
    print("1. Modify the 'targets' list to check your own servers")
    print("2. Add custom ports to scan in scan_common_ports()")
    print("3. Extend with SNMP monitoring or bandwidth tests")
    print("4. Add logging functionality to track changes over time")

if __name__ == "__main__":
    main()
