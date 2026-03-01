import time
import winsound  # Windows only
# For cross-platform, use: import pygame or playsound

def play_alarm(duration=3, frequency=1000):
    """Play a beep alarm (Windows)"""
    for _ in range(5):
        winsound.Beep(frequency, 500)
        time.sleep(0.2)

def check_event():
    """Define your event condition here"""
    # Example: trigger at a specific time
    current_time = time.strftime("%H:%M")
    return current_time == "08:00"  # Change to your desired time

def monitor():
    print("Monitoring for event... Press Ctrl+C to stop.")
    while True:
        if check_event():
            print("🔔 EVENT TRIGGERED! Alarm going off!")
            play_alarm()
            break  # Remove to keep monitoring
        time.sleep(30)  # Check every 30 seconds

if __name__ == "__main__":
    monitor()
