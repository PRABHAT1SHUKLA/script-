import re
import smtplib
from email.mime.text import MIMEText
from collections import Counter
from datetime import datetime

def analyze_logs(log_file, error_pattern=r"ERROR|Exception|Failed", alert_threshold=10):
    error_count = 0
    error_lines = []
    ip_counter = Counter()

    with open(log_file) as f:
        for line in f:
            if re.search(error_pattern, line, re.I):
                error_count += 1
                error_lines.append(line.strip())
                ip = line.split()[0] if line.split() else "unknown"
                ip_counter[ip] += 1

    if error_count >= alert_threshold:
        send_alert(error_count, ip_counter.most_common(3), error_lines[:5])

def send_alert(count, top_ips, sample_errors):
    msg = MIMEText(f"""
    High Error Rate Detected!
    Time: {datetime.now()}
    Errors in last scan: {count}
    Top IPs: {top_ips}
    Sample:
    {chr(10).join(sample_errors)}
    """)
    msg['Subject'] = f"[ALERT] {count} Errors Detected"
    msg['From'] = "monitor@company.com"
    msg['To'] = "admin@company.com"

    with smtplib.SMTP("smtp.company.com") as server:
        server.send_message(msg)

# Run every 5 minutes via cron
analyze_logs("/var/log/app.log")
