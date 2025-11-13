from prometheus_client import start_http_server, Gauge
import psutil
import time

CPU = Gauge('system_cpu_usage_percent', 'CPU usage')
MEM = Gauge('system_memory_usage_percent', 'Memory usage')
DISK = Gauge('system_disk_usage_percent', 'Disk usage', ['mount'])

def collect_metrics():
    CPU.set(psutil.cpu_percent())
    MEM.set(psutil.virtual_memory().percent)
    for part in psutil.disk_partitions():
        usage = psutil.disk_usage(part.mountpoint)
        DISK.labels(mount=part.mountpoint).set(usage.percent)

if __name__ == "__main__":
    start_http_server(8000)
    while True:
        collect_metrics()
        time.sleep(10)
