#!/usr/bin/env python3
import gi
import subprocess
import threading
import time
import sys

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, Adw, Notify, GLib

Adw.init()
Notify.init("Internet Watcher")


# ---------------- Utility Functions ----------------
def get_active_connections():
    """
    Return a list of active connection types: ['Wi-Fi', 'Mobile']
    Also return detected connection names for reconnect button
    """
    try:
        output = subprocess.check_output(
            ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "dev"],
            text=True
        )
        types = []
        names = {}
        for line in output.splitlines():
            parts = line.strip().split(":")
            if len(parts) < 4:
                continue
            device, dtype, state, conn_name = parts
            if state.lower() == "connected":
                if dtype == "wifi":
                    types.append("Wi-Fi")
                    names["wifi"] = conn_name
                elif dtype in ("gsm", "cdma", "mobile"):
                    types.append("Mobile")
                    names["mobile"] = conn_name
        return types, names
    except Exception:
        return [], {}


def get_wifi_quality():
    """
    Return (strength%, max_bitrate Mbps) for the currently connected Wi-Fi.
    Returns (None, None) if no Wi-Fi is active.
    """
    try:
        output = subprocess.check_output(
            ["nmcli", "-t", "-f", "IN-USE,SIGNAL,RATE,SSID", "dev", "wifi"],
            text=True
        )
        for line in output.splitlines():
            parts = line.strip().split(":")
            if len(parts) < 4:
                continue
            in_use, signal, rate, ssid = parts
            if in_use == "*":
                strength = int(signal)
                try:
                    max_bitrate_mbps = int(float(rate.split()[0]))
                    if max_bitrate_mbps == 0:
                        max_bitrate_mbps = None
                except Exception:
                    max_bitrate_mbps = None
                return strength, max_bitrate_mbps
    except Exception:
        pass
    return None, None


def ping_latency(host="8.8.8.8"):
    """
    Return ping latency in ms, or None if unreachable
    """
    try:
        output = subprocess.check_output(
            ["ping", "-c", "1", "-W", "1", host],
            stderr=subprocess.DEVNULL,
            text=True
        )
        for line in output.splitlines():
            if "time=" in line:
                return float(line.split("time=")[1].split()[0])
    except Exception:
        return None
    return None


def battery_percentage():
    """
    Return current battery percentage (0-100), or None if unknown
    """
    try:
        output = subprocess.check_output(
            ["upower", "-i", "/org/freedesktop/UPower/devices/battery_BAT0"],
            text=True
        )
        for line in output.splitlines():
            if "percentage:" in line:
                return int(line.split()[1].replace("%", ""))
    except Exception:
        return None
    return None


def reconnect_wifi(ssid):
    try:
        subprocess.run(["nmcli", "connection", "up", "id", ssid], check=False)
    except Exception:
        pass


def reconnect_mobile(conn_name):
    try:
        subprocess.run(["nmcli", "radio", "wwan", "on"], check=False)
        subprocess.run(["nmcli", "connection", "up", "id", conn_name], check=False)
    except Exception:
        pass


def notify(message):
    """
    Thread-safe notification
    """
    def _show():
        n = Notify.Notification.new(message)
        n.show()
    GLib.idle_add(_show)


# ---------------- GUI Application ----------------
class InternetWatcherApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.example.InternetWatcher")
        self.connect("activate", self.on_activate)
        self.last_network_status = None
        self.updater_thread = None
        self.running = True

        # Connection names auto-populated
        self.wifi_ssid = None
        self.mobile_conn_name = None

    def on_activate(self, app):
        self.win = Adw.ApplicationWindow(application=app)
        self.win.set_title("Internet Watcher")
        self.win.set_default_size(360, 360)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.box.set_margin_top(24)
        self.box.set_margin_bottom(24)
        self.box.set_margin_start(24)
        self.box.set_margin_end(24)

        # Labels
        self.status_label = Gtk.Label(label="Checking network...")
        self.box.append(self.status_label)

        self.wifi_label = Gtk.Label(label="")
        self.box.append(self.wifi_label)

        self.latency_label = Gtk.Label(label="")
        self.box.append(self.latency_label)
        
        self.spacer_label = Gtk.Label(label="")
        self.box.append(self.spacer_label)

        # Buttons
        self.start_btn = Gtk.Button(label="Start Service (systemd)")
        self.start_btn.connect("clicked", self.on_service_start)
        self.box.append(self.start_btn)

        self.stop_btn = Gtk.Button(label="Stop Service (systemd)")
        self.stop_btn.connect("clicked", self.on_service_stop)
        self.box.append(self.stop_btn)

        self.refresh_btn = Gtk.Button(label="Refresh Status")
        self.refresh_btn.connect("clicked", self.on_refresh)
        self.box.append(self.refresh_btn)
        
        self.spacer_label = Gtk.Label(label="")
        self.box.append(self.spacer_label)

        self.reconnect_btn = Gtk.Button(label="Reconnect Network")
        self.reconnect_btn.connect("clicked", self.on_reconnect)
        self.box.append(self.reconnect_btn)

        self.spacer_label = Gtk.Label(label="")
        self.box.append(self.spacer_label)

        self.exit_btn = Gtk.Button(label="Exit")
        self.exit_btn.connect("clicked", self.on_exit)
        self.box.append(self.exit_btn)

        self.win.set_content(self.box)
        self.win.present()

        # Start background updater thread
        self.updater_thread = threading.Thread(target=self.updater_loop, daemon=True)
        self.updater_thread.start()

    # ---------------- Network Updater ----------------
    def updater_loop(self):
        while self.running:
            types, names = get_active_connections()

            # Auto-populate connection names
            if "wifi" in names:
                self.wifi_ssid = names["wifi"]
            if "mobile" in names:
                self.mobile_conn_name = names["mobile"]

            status_text = "No active connection" if not types else "Active: " + ", ".join(types)

            # Wi-Fi quality
            strength, max_bitrate = get_wifi_quality()
            wifi_text = ""
            if strength is not None:
                wifi_text = f"Wi-Fi Strength: {strength}%"
                if max_bitrate:
                    wifi_text += f" / Max Bitrate: {max_bitrate} Mbps"

            # Ping latency
            latency = ping_latency() if types else None
            latency_text = f"Ping: {latency} ms" if latency is not None else ""

            # Low-battery suppression (<20%)
            battery = battery_percentage()
            suppress_notifications = battery is not None and battery < 20

            # Notify only once per outage
            if status_text != self.last_network_status:
                if not types and not suppress_notifications:
                    notify("Internet disconnected!")
                elif self.last_network_status is not None and not suppress_notifications:
                    notify(f"Internet connected: {', '.join(types)}")
                self.last_network_status = status_text

            # Update GUI labels
            GLib.idle_add(self.status_label.set_text, status_text)
            GLib.idle_add(self.wifi_label.set_text, wifi_text)
            GLib.idle_add(self.latency_label.set_text, latency_text)

            time.sleep(5)

    # ---------------- Button Callbacks ----------------
    def on_service_start(self, button):
        subprocess.run(["systemctl", "--user", "start", "internet-watcher.service"])
        notify("Service started")

    def on_service_stop(self, button):
        subprocess.run(["systemctl", "--user", "stop", "internet-watcher.service"])
        notify("Service stopped")

    def on_refresh(self, button):
        self.last_network_status = None  # Force immediate refresh

    def on_reconnect(self, button):
        if self.wifi_ssid:
            reconnect_wifi(self.wifi_ssid)
            notify(f"Reconnecting Wi-Fi: {self.wifi_ssid}")
        if self.mobile_conn_name:
            reconnect_mobile(self.mobile_conn_name)
            notify(f"Reconnecting Mobile: {self.mobile_conn_name}")

    def on_exit(self, button):
        self.running = False
        notify("Exiting Internet Watcher")
        self.quit()
        sys.exit(0)


if __name__ == "__main__":
    app = InternetWatcherApp()
    app.run()
