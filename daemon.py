#!/usr/bin/env python3

from gi.repository import Notify
from configparser import ConfigParser

from nm_signals import NMWatcher
from connections import active_types
from power import battery_percentage

Notify.init("Internet Watcher")

cfg = ConfigParser()
cfg.read(f"{__import__('os').path.expanduser('~')}/.config/internet-watcher/config.ini")

NOTIFY_WIFI = cfg.getboolean("notifications", "wifi", fallback=True)
NOTIFY_MOBILE = cfg.getboolean("notifications", "mobile", fallback=True)

SUPPRESS_LOW_BATT = cfg.getboolean("power", "suppress_on_low_battery", fallback=True)
LOW_BATT = cfg.getint("power", "low_battery_threshold", fallback=20)

last_state = set()

def notify(title, body, icon):
    Notify.Notification.new(title, body, icon).show()

def on_nm_change():
    global last_state

    if SUPPRESS_LOW_BATT and battery_percentage() < LOW_BATT:
        last_state = active_types()
        return

    current = active_types()

    # Wi-Fi outage
    if NOTIFY_WIFI and "wifi" in last_state and "wifi" not in current:
        notify(
            "Wi-Fi disconnected",
            "Wi-Fi connection lost",
            "network-wireless-offline-symbolic"
        )

    # Mobile outage
    if NOTIFY_MOBILE and "mobile" in last_state and "mobile" not in current:
        notify(
            "Mobile data disconnected",
            "Mobile connection lost",
            "network-cellular-offline-symbolic"
        )

    last_state = current

if __name__ == "__main__":
    last_state = active_types()
    NMWatcher(on_nm_change).run()
