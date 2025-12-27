"""
OpenTelemetry Metrics Agent - Send System Metrics to OTEL Collector

Prerequisites:
pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp psutil

This agent collects system metrics (CPU, Memory, Disk) and sends them to an OTEL Collector.
"""

import time
import psutil
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource

# Configuration
OTEL_COLLECTOR_ENDPOINT = "localhost:4317"  # gRPC endpoint
SERVICE_NAME = "system-metrics-agent"
EXPORT_INTERVAL_SECONDS = 10  # How often to send metrics

def setup_metrics():
    """Initialize OpenTelemetry metrics with OTLP exporter"""
    
    # Define resource attributes (metadata about the service)
    resource = Resource.create({
        "service.name": SERVICE_NAME,
        "service.version": "1.0.0",
        "deployment.environment": "development",
        "host.name": psutil.os.uname().nodename
    })
    
    # Configure OTLP exporter to send metrics to collector
    exporter = OTLPMetricExporter(
        endpoint=OTEL_COLLECTOR_ENDPOINT,
        insecure=True  # Use insecure for local development
    )
    
    # Create metric reader that exports periodically
    reader = PeriodicExportingMetricReader(
        exporter=exporter,
        export_interval_millis=EXPORT_INTERVAL_SECONDS * 1000
    )
    
    # Set up the MeterProvider
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    
    return metrics.get_meter(__name__)

def collect_system_metrics(meter):
    """Create callback functions to collect system metrics"""
    
    # CPU Usage Gauge
    def cpu_callback(options):
        cpu_percent = psutil.cpu_percent(interval=1)
        yield metrics.Observation(cpu_percent, {"cpu.type": "system"})
    
    # Memory Usage Gauge
    def memory_callback(options):
        mem = psutil.virtual_memory()
        yield metrics.Observation(mem.percent, {"memory.type": "physical"})
        yield metrics.Observation(mem.used, {"memory.type": "used_bytes"})
        yield metrics.Observation(mem.available, {"memory.type": "available_bytes"})
    
    # Disk Usage Gauge
    def disk_callback(options):
        disk = psutil.disk_usage('/')
        yield metrics.Observation(disk.percent, {"disk.mount": "/", "disk.type": "percent"})
        yield metrics.Observation(disk.used, {"disk.mount": "/", "disk.type": "used_bytes"})
        yield metrics.Observation(disk.free, {"disk.mount": "/", "disk.type": "free_bytes"})
    
    # Network I/O Counter
    def network_callback(options):
        net = psutil.net_io_counters()
        yield metrics.Observation(net.bytes_sent, {"network.direction": "sent"})
        yield metrics.Observation(net.bytes_recv, {"network.direction": "received"})
    
    # Register observable gauges with callbacks
    meter.create_observable_gauge(
        name="system.cpu.usage",
        callbacks=[cpu_callback],
        description="CPU usage percentage",
        unit="%"
    )
    
    meter.create_observable_gauge(
        name="system.memory.usage",
        callbacks=[memory_callback],
        description="Memory usage metrics",
        unit="bytes"
    )
    
    meter.create_observable_gauge(
        name="system.disk.usage",
        callbacks=[disk_callback],
        description="Disk usage metrics",
        unit="bytes"
    )
    
    meter.create_observable_counter(
        name="system.network.io",
        callbacks=[network_callback],
        description="Network I/O bytes",
        unit="bytes"
    )
    
    # Example: Custom counter for application events
    request_counter = meter.create_counter(
        name="app.requests.total",
        description="Total application requests",
        unit="1"
    )
    
    return request_counter

def main():
    """Main function to run the metrics agent"""
    
    print(f"Starting OpenTelemetry Metrics Agent...")
    print(f"Sending metrics to: {OTEL_COLLECTOR_ENDPOINT}")
    print(f"Export interval: {EXPORT_INTERVAL_SECONDS} seconds")
    print("Press Ctrl+C to stop\n")
    
    try:
        # Initialize OpenTelemetry
        meter = setup_metrics()
        
        # Set up system metric collection
        request_counter = collect_system_metrics(meter)
        
        # Simulate application activity
        print("Agent is running and collecting metrics...")
        counter = 0
        while True:
            time.sleep(5)
            
            # Simulate some application activity
            counter += 1
            request_counter.add(1, {"endpoint": "/api/data", "status": "200"})
            
            if counter % 2 == 0:
                print(f"✓ Metrics collected and queued (iteration {counter})")
            
    except KeyboardInterrupt:
        print("\n\nStopping agent...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        print("Agent stopped.")

if __name__ == "__main__":
    main()
