<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Observability Dashboard</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Courier New',monospace;background:#0f0f1e;color:#0ff;min-height:100vh}
.container{max-width:1400px;margin:0 auto;padding:20px}
header{border-bottom:2px solid #0f0;padding:20px 0;margin-bottom:30px}
h1{color:#0f0;font-size:2.5em;text-shadow:0 0 10px #0f0}
.subtitle{color:#0ff;font-size:0.9em}
.metrics-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px;margin-bottom:30px}
.metric-card{background:linear-gradient(135deg,#1a1a3e,#0f0f1e);border:2px solid #0f0;border-radius:8px;padding:20px;box-shadow:0 0 20px rgba(0,255,0,0.2)}
.metric-card:hover{border-color:#0ff;box-shadow:0 0 30px rgba(0,255,255,0.3)}
.metric-label{color:#888;font-size:0.85em;margin-bottom:10px;text-transform:uppercase}
.metric-value{font-size:2.5em;color:#0f0;font-weight:bold}
.metric-change{font-size:0.85em;margin-top:5px}
.up{color:#0f0}
.down{color:#f00}
.chart-container{background:linear-gradient(135deg,#1a1a3e,#0f0f1e);border:2px solid #0ff;border-radius:8px;padding:25px;margin-bottom:30px;box-shadow:0 0 20px rgba(0,255,255,0.1)}
.chart-title{color:#0ff;font-size:1.3em;margin-bottom:20px;font-weight:bold}
.alerts{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin-bottom:30px}
.alert{border-left:4px solid;padding:15px;border-radius:4px;background:rgba(255,255,255,0.02)}
.alert-critical{border-color:#f00;background:rgba(255,0,0,0.1)}
.alert-warning{border-color:#ff0;background:rgba(255,255,0,0.1)}
.alert-info{border-color:#0ff;background:rgba(0,255,255,0.1)}
.alert-title{color:#fff;font-weight:bold;margin-bottom:5px}
.alert-time{color:#888;font-size:0.8em;margin-top:8px}
.logs-container{background:linear-gradient(135deg,#1a1a3e,#0f0f1e);border:2px solid #0f0;border-radius:8px;padding:20px;max-height:400px;overflow-y:auto}
.logs-title{color:#0f0;font-size:1.2em;margin-bottom:15px;font-weight:bold}
.log-entry{border-left:3px solid #0f0;padding:10px 15px;margin-bottom:10px;font-size:0.85em;line-height:1.4}
.log-time{color:#888}
.log-level-error{border-left-color:#f00;color:#f99}
.log-level-warn{border-left-color:#ff0;color:#ffd700}
.log-level-info{border-left-color:#0ff;color:#0ff}
::-webkit-scrollbar{width:8px}
::-webkit-scrollbar-thumb{background:#0f0;border-radius:4px}
</style>
</head>
<body>
<div class="container">
<header>
<h1>🔍 OBSERVABILITY COMMAND CENTER</h1>
<p class="subtitle">Real-time System Monitoring & Analytics</p>
</header>

<div class="metrics-grid">
<div class="metric-card">
<div class="metric-label">CPU Usage</div>
<div class="metric-value" id="cpu">68%</div>
<div class="metric-change"><span class="down">↓ 2.3% from last hour</span></div>
</div>
<div class="metric-card">
<div class="metric-label">Memory</div>
<div class="metric-value" id="memory">4.2 GB</div>
<div class="metric-change"><span class="up">↑ 512MB</span></div>
</div>
<div class="metric-card">
<div class="metric-label">Requests/sec</div>
<div class="metric-value" id="rps">12.4K</div>
<div class="metric-change"><span class="up">↑ 1.2K peak</span></div>
</div>
<div class="metric-card">
<div class="metric-label">Error Rate</div>
<div class="metric-value" id="errors">0.3%</div>
<div class="metric-change"><span class="up">↑ Watch</span></div>
</div>
<div class="metric-card">
<div class="metric-label">Latency P95</div>
<div class="metric-value" id="latency">245ms</div>
<div class="metric-change"><span class="down">↓ 12ms SLA OK</span></div>
</div>
<div class="metric-card">
<div class="metric-label">Services Healthy</div>
<div class="metric-value">24/24 ✓</div>
<div class="metric-change"><span class="up">All Green</span></div>
</div>
</div>

<div class="alerts">
<div class="alert alert-warning">
<div class="alert-title">⚠ High Memory Usage</div>
<div class="alert-message">Payment Service at 85% - trending upward</div>
<div class="alert-time">2 minutes ago</div>
</div>
<div class="alert alert-info">
<div class="alert-title">ℹ Deployment v2.4.1</div>
<div class="alert-message">Rolled out to all regions - 5ms latency improvement</div>
<div class="alert-time">15 minutes ago</div>
</div>
<div class="alert alert-critical">
<div class="alert-title">🔴 DB Connection Pool Exhausted</div>
<div class="alert-message">Read replica at max connections (1000/1000)</div>
<div class="alert-time">32 minutes ago</div>
</div>
</div>

<div class="chart-container">
<div class="chart-title">📊 Request Latency (P50, P95, P99)</div>
<canvas id="latencyChart"></canvas>
</div>

<div class="chart-container">
<div class="chart-title">📈 Error Rate Trend</div>
<canvas id="errorChart"></canvas>
</div>

<div class="chart-container">
<div class="chart-title">🔄 Service Health</div>
<canvas id="serviceChart"></canvas>
</div>

<div class="logs-container">
<div class="logs-title">📋 Real-time Log Stream</div>
<div class="log-entry log-level-info"><span class="log-time">[14:32:45]</span> Cache hit ratio improved to 94.2%</div>
<div class="log-entry log-level-info"><span class="log-time">[14:31:22]</span> Auto-scaling triggered - 3 new pods deployed</div>
<div class="log-entry log-level-warn"><span class="log-time">[14:29:18]</span> Query latency 2.3s - above threshold</div>
<div class="log-entry log-level-warn"><span class="log-time">[14:28:45]</span> Memory pressure on node-5 detected</div>
<div class="log-entry log-level-error"><span class="log-time">[14:27:33]</span> Failed to connect to Elasticsearch - retrying</div>
<div class="log-entry log-level-info"><span class="log-time">[14:26:10]</span> Batch job completed - 50K records in 3.2s</div>
</div>
</div>

<script>
function initCharts(){
  const latencyCtx=document.getElementById('latencyChart').getContext('2d');
  new Chart(latencyCtx,{
    type:'line',
    data:{
      labels:['00:00','04:00','08:00','12:00','16:00','20:00','23:59'],
      datasets:[
        {label:'P50',data:[120,130,145,160,155,140,125],borderColor:'#0f0',backgroundColor:'rgba(0,255,0,0.1)',borderWidth:2,tension:0.4},
        {label:'P95',data:[245,260,280,310,290,265,245],borderColor:'#ff0',backgroundColor:'rgba(255,255,0,0.1)',borderWidth:2,tension:0.4},
        {label:'P99',data:[450,480,520,580,550,480,450],borderColor:'#f00',backgroundColor:'rgba(255,0,0,0.1)',borderWidth:2,tension:0.4}
      ]
    },
    options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{labels:{color:'#0ff'}}},scales:{x:{ticks:{color:'#888'}},y:{ticks:{color:'#888'}}}}
  });

  const errorCtx=document.getElementById('errorChart').getContext('2d');
  new Chart(errorCtx,{
    type:'bar',
    data:{
      labels:['Mon','Tue','Wed','Thu','Fri','Sat','Sun'],
      datasets:[{label:'Error Rate %',data:[0.1,0.15,0.2,0.25,0.18,0.12,0.3],backgroundColor:'rgba(255,0,0,0.6)',borderColor:'#f00',borderWidth:2}]
    },
    options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{labels:{color:'#0ff'}}},scales:{x:{ticks:{color:'#888'}},y:{ticks:{color:'#888'}}}}
  });

  const serviceCtx=document.getElementById('serviceChart').getContext('2d');
  new Chart(serviceCtx,{
    type:'doughnut',
    data:{
      labels:['Healthy (24)','Degraded (0)','Down (0)'],
      datasets:[{data:[24,0,0],backgroundColor:['#0f0','#ff0','#f00'],borderColor:'#0f0f1e',borderWidth:2}]
    },
    options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{labels:{color:'#0ff'}}}}
  });
}

function updateMetrics(){
  document.getElementById('cpu').textContent=Math.floor(Math.random()*100)+'%';
  document.getElementById('memory').textContent=(Math.random()*8+2).toFixed(1)+' GB';
  document.getElementById('rps').textContent+(Math.floor(Math.random()*5000)+8000)/1000+'K';
  document.getElementById('errors').textContent=(Math.random()*0.5).toFixed(2)+'%';
  document.getElementById('latency').textContent=Math.floor(Math.random()*100)+200+'ms';
}

initCharts();
setInterval(updateMetrics,3000);
</script>
</body>
</html>
