import psutil
import plyer  # For notifications; pip install plyer

battery = psutil.sensors_battery()
if battery is None:
    print("No battery info available (e.g., on desktop)")
elif battery.percent < 20 and not battery.power_plugged:
    plyer.notification.notify(
        title="Low Battery Alert",
        message=f"Battery at {battery.percent}% - Plug in soon!",
        timeout=10
    )
else:
    print(f"Battery: {battery.percent}% - {'Charging' if battery.power_plugged else 'OK'}")
