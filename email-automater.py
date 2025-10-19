import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

class EmailSender:
    def __init__(self, email, password):
        """Initialize email sender."""
        self.email = email
        self.password = password
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
    
    def send_email(self, to_email, subject, body, attachment_path=None):
        """Send email with optional attachment."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Add attachment if provided
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as file:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(file.read())
                    encoders.encode_base64(part)
                    
                    filename = os.path.basename(attachment_path)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {filename}'
                    )
                    msg.attach(part)
            
            # Connect and send
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            
            text = msg.as_string()
            server.sendmail(self.email, to_email, text)
            server.quit()
            
            print(f"✓ Email sent to {to_email}")
            return True
            
        except Exception as e:
            print(f"✗ Error sending to {to_email}: {e}")
            return False
    
    def send_bulk_emails(self, recipients, subject, body, attachment=None):
        """Send email to multiple recipients."""
        success = 0
        failed = 0
        
        for recipient in recipients:
            if self.send_email(recipient, subject, body, attachment):
                success += 1
            else:
                failed += 1
        
        print(f"\nSummary: {success} sent, {failed} failed")

if __name__ == "__main__":
    # Example usage
    sender = EmailSender("your_email@gmail.com", "your_app_password")
    
    recipients = [
        "recipient1@example.com",
        "recipient2@example.com"
    ]
    
    subject = "Important Update"
    body = "Hello,\n\nThis is an automated email.\n\nBest regards"
    
    sender.send_bulk_emails(recipients, subject, body)
