package main

import (
	"fmt"
	"math/rand"
	"sync"
	"time"
)

type Metric struct {
	Name      string
	Value     float64
	Timestamp time.Time
	Tags      map[string]string
}

type MetricsCollector struct {
	metrics chan Metric
	mu      sync.RWMutex
	store   map[string][]Metric
}

func NewMetricsCollector() *MetricsCollector {
	mc := &MetricsCollector{
		metrics: make(chan Metric, 1000),
		store:   make(map[string][]Metric),
	}
	go mc.processMetrics()
	return mc
}

func (mc *MetricsCollector) Record(name string, value float64, tags map[string]string) {
	mc.metrics <- Metric{
		Name:      name,
		Value:     value,
		Timestamp: time.Now(),
		Tags:      tags,
	}
}

func (mc *MetricsCollector) processMetrics() {
	for metric := range mc.metrics {
		mc.mu.Lock()
		mc.store[metric.Name] = append(mc.store[metric.Name], metric)
		if len(mc.store[metric.Name]) > 10000 {
			mc.store[metric.Name] = mc.store[metric.Name][1:]
		}
		mc.mu.Unlock()
	}
}

func (mc *MetricsCollector) GetStats(name string) map[string]float64 {
	mc.mu.RLock()
	defer mc.mu.RUnlock()

	metrics := mc.store[name]
	if len(metrics) == 0 {
		return nil
	}

	var min, max, sum float64 = metrics[0].Value, metrics[0].Value, 0
	for _, m := range metrics {
		if m.Value < min {
			min = m.Value
		}
		if m.Value > max {
			max = m.Value
		}
		sum += m.Value
	}

	avg := sum / float64(len(metrics))
	p95 := calculatePercentile(metrics, 95)

	return map[string]float64{
		"min":  min,
		"max":  max,
		"avg":  avg,
		"p95":  p95,
		"p99":  calculatePercentile(metrics, 99),
		"p50":  calculatePercentile(metrics, 50),
	}
}

func calculatePercentile(metrics []Metric, percentile float64) float64 {
	if len(metrics) == 0 {
		return 0
	}
	idx := int(float64(len(metrics)) * percentile / 100)
	if idx >= len(metrics) {
		idx = len(metrics) - 1
	}
	return metrics[idx].Value
}

type SystemMonitor struct {
	collector *MetricsCollector
	ticker    *time.Ticker
	stopChan  chan bool
}

func NewSystemMonitor(collector *MetricsCollector) *SystemMonitor {
	return &SystemMonitor{
		collector: collector,
		ticker:    time.NewTicker(1 * time.Second),
		stopChan:  make(chan bool),
	}
}

func (sm *SystemMonitor) Start() {
	go func() {
		for {
			select {
			case <-sm.ticker.C:
				sm.collectMetrics()
			case <-sm.stopChan:
				return
			}
		}
	}()
}

func (sm *SystemMonitor) Stop() {
	sm.ticker.Stop()
	sm.stopChan <- true
}

func (sm *SystemMonitor) collectMetrics() {
	cpuUsage := 30 + rand.Float64()*40
	memUsage := 40 + rand.Float64()*35
	latency := 50 + rand.Float64()*150
	errorRate := rand.Float64() * 0.5
	requestsPerSec := 5000 + rand.Float64()*5000

	sm.collector.Record("cpu.usage", cpuUsage, map[string]string{"host": "server-1"})
	sm.collector.Record("memory.usage", memUsage, map[string]string{"host": "server-1"})
	sm.collector.Record("http.request.latency", latency, map[string]string{"service": "api", "endpoint": "/v1/users"})
	sm.collector.Record("error.rate", errorRate, map[string]string{"service": "api"})
	sm.collector.Record("http.requests.total", requestsPerSec, map[string]string{"service": "api"})
}

type AlertManager struct {
	thresholds map[string]float64
	alerts     []string
	mu         sync.Mutex
}

func NewAlertManager() *AlertManager {
	return &AlertManager{
		thresholds: map[string]float64{
			"cpu.usage":              85.0,
			"memory.usage":           90.0,
			"http.request.latency":   500.0,
			"error.rate":             1.0,
		},
		alerts: []string{},
	}
}

func (am *AlertManager) Check(metric Metric) bool {
	threshold, exists := am.thresholds[metric.Name]
	if !exists {
		return false
	}

	if metric.Value > threshold {
		alert := fmt.Sprintf("[ALERT] %s exceeded threshold: %.2f > %.2f at %s",
			metric.Name, metric.Value, threshold, metric.Timestamp.Format(time.RFC3339))
		am.mu.Lock()
		am.alerts = append(am.alerts, alert)
		if len(am.alerts) > 1000 {
			am.alerts = am.alerts[1:]
		}
		am.mu.Unlock()
		return true
	}
	return false
}

func (am *AlertManager) GetRecentAlerts(count int) []string {
	am.mu.Lock()
	defer am.mu.Unlock()
	if count > len(am.alerts) {
		count = len(am.alerts)
	}
	return am.alerts[len(am.alerts)-count:]
}

type MetricsAggregator struct {
	collector *MetricsCollector
	window    time.Duration
}

func NewMetricsAggregator(collector *MetricsCollector, window time.Duration) *MetricsAggregator {
	return &MetricsAggregator{
		collector: collector,
		window:    window,
	}
}

func (ma *MetricsAggregator) GetAggregatedMetrics() map[string]map[string]float64 {
	result := make(map[string]map[string]float64)

	metricsToCheck := []string{
		"cpu.usage",
		"memory.usage",
		"http.request.latency",
		"error.rate",
		"http.requests.total",
	}

	for _, metricName := range metricsToCheck {
		stats := ma.collector.GetStats(metricName)
		if stats != nil {
			result[metricName] = stats
		}
	}

	return result
}

func main() {
	rand.Seed(time.Now().UnixNano())

	collector := NewMetricsCollector()
	monitor := NewSystemMonitor(collector)
	alertMgr := NewAlertManager()
	aggregator := NewMetricsAggregator(collector, 5*time.Minute)

	monitor.Start()

	fmt.Println("=== Metrics Collector Started ===")
	fmt.Println("CPU, Memory, Latency, Error Rate, and Request metrics being collected...")
	fmt.Println("")

	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()

		for range ticker.C {
			metrics := aggregator.GetAggregatedMetrics()
			fmt.Println("\n--- Metrics Report ---")
			for name, stats := range metrics {
				fmt.Printf("%s - AVG: %.2f, P95: %.2f, P99: %.2f, MIN: %.2f, MAX: %.2f\n",
					name, stats["avg"], stats["p95"], stats["p99"], stats["min"], stats["max"])
			}

			alerts := alertMgr.GetRecentAlerts(3)
			if len(alerts) > 0 {
				fmt.Println("\n--- Recent Alerts ---")
				for _, alert := range alerts {
					fmt.Println(alert)
				}
			}
		}
	}()

	time.Sleep(30 * time.Second)
	monitor.Stop()
	fmt.Println("\n=== Monitoring Stopped ===")
}
