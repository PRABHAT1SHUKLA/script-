import socket
import sys

def scan_port(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
ports = range(1, 1025)

open_ports = []
for port in ports:
    if scan_port(host, port):
        open_ports.append(port)

for port in open_ports:
    print(f"Port {port} is open")
