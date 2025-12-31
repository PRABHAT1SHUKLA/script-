# OpenTelemetry Collector Configuration
# This config scrapes system metrics, logs, and traces from the host

receivers:
  # Host Metrics Receiver - Collects system metrics
  hostmetrics:
    collection_interval: 30s
    scrapers:
      # CPU metrics
      cpu:
        metrics:
          system.cpu.utilization:
            enabled: true
      # Memory metrics
      memory:
        metrics:
          system.memory.utilization:
            enabled: true
      # Disk I/O metrics
      disk:
      # Filesystem metrics
      filesystem:
        metrics:
          system.filesystem.utilization:
            enabled: true
      # Network metrics
      network:
      # Load average
      load:
      # Paging/swap metrics
      paging:
      # Process metrics
      processes:
      # Process-specific metrics
      process:
        mute_process_name_error: true
        mute_process_exe_error: true
        mute_process_io_error: true

  # Prometheus Receiver - Scrapes metrics from Prometheus endpoints
  prometheus:
    config:
      scrape_configs:
        - job_name: 'otel-collector'
          scrape_interval: 30s
          static_configs:
            - targets: ['localhost:8888']
        - job_name: 'node-exporter'
          scrape_interval: 30s
          static_configs:
            - targets: ['localhost:9100']

  # Filelog Receiver - Collects logs from files
  filelog:
    include:
      - /var/log/syslog
      - /var/log/auth.log
      - /var/log/nginx/*.log
      - /var/log/apache2/*.log
      - /var/log/app/*.log
    exclude:
      - /var/log/syslog.*.gz
    start_at: end
    include_file_path: true
    include_file_name: false
    operators:
      # Parse JSON logs
      - type: json_parser
        id: parser-json
        if: 'body matches "^\\{"'
      # Parse syslog format
      - type: regex_parser
        id: parser-syslog
        regex: '^<(?P<priority>\d+)>(?P<timestamp>\w+\s+\d+\s+\d+:\d+:\d+)\s+(?P<hostname>\S+)\s+(?P<app>\S+):\s+(?P<message>.*)$'
        timestamp:
          parse_from: attributes.timestamp
          layout: '%b %d %H:%M:%S'
      # Add severity
      - type: severity_parser
        parse_from: attributes.priority

  # OTLP Receiver - Receives traces, metrics, and logs via OTLP protocol
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

  # Journald Receiver - Collects systemd journal logs (Linux)
  journald:
    directory: /var/log/journal
    units:
      - sshd
      - docker
      - kubelet
      - nginx

processors:
  # Batch Processor - Batches telemetry data
  batch:
    timeout: 10s
    send_batch_size: 1024

  # Memory Limiter - Prevents OOM
  memory_limiter:
    check_interval: 1s
    limit_mib: 512
    spike_limit_mib: 128

  # Resource Processor - Adds resource attributes
  resource:
    attributes:
      - key: host.name
        value: ${HOST_NAME}
        action: upsert
      - key: environment
        value: production
        action: upsert
      - key: service.name
        value: host-metrics
        action: upsert

  # Resource Detection - Auto-detects cloud/host attributes
  resourcedetection:
    detectors: [env, system, docker, ec2, gcp, azure]
    timeout: 5s

  # Attributes Processor - Modifies attributes
  attributes:
    actions:
      - key: environment
        value: production
        action: insert
      - key: dropped_attribute
        action: delete

  # Filter Processor - Filters metrics/logs
  filter/exclude_high_cardinality:
    metrics:
      exclude:
        match_type: regexp
        metric_names:
          - process.cpu.*
          - process.memory.*

  # Metrics Transform - Renames/aggregates metrics
  metricstransform:
    transforms:
      - include: system.cpu.utilization
        action: update
        new_name: cpu.usage.percent

exporters:
  # Logging Exporter - Outputs to console (for debugging)
  logging:
    verbosity: detailed
    sampling_initial: 5
    sampling_thereafter: 200

  # OTLP Exporter - Sends to OTLP backend
  otlp:
    endpoint: otelcol.example.com:4317
    tls:
      insecure: false
      cert_file: /etc/otel/cert.pem
      key_file: /etc/otel/key.pem
    headers:
      api-key: ${OTLP_API_KEY}

  # OTLP HTTP Exporter
  otlphttp:
    endpoint: https://otlp.example.com
    headers:
      Authorization: Bearer ${OTLP_TOKEN}

  # Prometheus Exporter - Exposes metrics for Prometheus
  prometheus:
    endpoint: 0.0.0.0:8889
    namespace: otel
    const_labels:
      environment: production

  # File Exporter - Writes to files (for testing)
  file:
    path: /var/log/otel/output.json
    rotation:
      max_megabytes: 100
      max_days: 7
      max_backups: 3

  # Elasticsearch Exporter - Sends logs to Elasticsearch
  elasticsearch:
    endpoints: 
      - http://elasticsearch:9200
    index: otel-logs
    logs_index: otel-logs-%{+yyyy.MM.dd}
    user: elastic
    password: ${ELASTIC_PASSWORD}

extensions:
  # Health Check
  health_check:
    endpoint: 0.0.0.0:13133

  # Performance Profiler
  pprof:
    endpoint: 0.0.0.0:1777

  # zPages for debugging
  zpages:
    endpoint: 0.0.0.0:55679

service:
  extensions: [health_check, pprof, zpages]
  
  pipelines:
    # Metrics Pipeline
    metrics:
      receivers: [hostmetrics, prometheus, otlp]
      processors: [memory_limiter, resourcedetection, resource, batch]
      exporters: [logging, prometheus, otlp]

    # Logs Pipeline
    logs:
      receivers: [filelog, journald, otlp]
      processors: [memory_limiter, resource, batch]
      exporters: [logging, otlphttp, elasticsearch]

    # Traces Pipeline
    traces:
      receivers: [otlp]
      processors: [memory_limiter, resourcedetection, resource, batch]
      exporters: [logging, otlp]

  telemetry:
    logs:
      level: info
    metrics:
      level: detailed
      address: 0.0.0.0:8888
