import smtplib
from email.message import EmailMessage
import requests

# Replace with your details
CITY = "New York"  # Change to your city
EMAIL = "your_email@gmail.com"
PASSWORD = "your_app_password"  # Use app password for Gmail
API_KEY = "your_openweathermap_key"  # Free from openweathermap.org

url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY}&appid={API_KEY}&units=metric"
response = requests.get(url).json()
weather = f"Today's weather in {CITY}: {response['weather'][0]['description']}, {response['main']['temp']}°C"

msg = EmailMessage()
msg['Subject'] = "Daily Weather Update"
msg['From'] = EMAIL
msg['To'] = EMAIL
msg.set_content(weather)

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
    server.login(EMAIL, PASSWORD)
    server.send_message(msg)
print("Weather email sent!")
