#!/usr/bin/env python3
import gi
import subprocess
import sys
import dbus
import threading
import time

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Notify", "0.7")
from gi.repository import Gtk, Adw, Notify, GLib

Adw.init()
Notify.init("Internet Watcher")


# ---------------- Network Functions ----------------
def get_active_connections():
    """Return a list of active connection types: ['wifi', 'gsm']"""
    bus = dbus.SystemBus()
    nm = bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager')
    nm_props = dbus.Interface(nm, dbus.PROPERTIES_IFACE)
    active_paths = nm_props.Get('org.freedesktop.NetworkManager', 'ActiveConnections')
    types = []
    for path in active_paths:
        conn = bus.get_object('org.freedesktop.NetworkManager', path)
        conn_props = dbus.Interface(conn, dbus.PROPERTIES_IFACE)
        ctype = conn_props.Get('org.freedesktop.NetworkManager.Connection.Active', 'Type')
        if ctype == "802-11-wireless":
            types.append("Wi-Fi")
        elif ctype in ("gsm", "cdma", "mobile"):
            types.append("Mobile")
    return types


def get_wifi_quality():
    """
    Return (strength%, max_bitrate Mbps) for the currently connected Wi-Fi.
    Returns (None, None) if no Wi-Fi is active.
    If max_bitrate cannot be determined, it returns None.
    """
    try:
        # Use nmcli to get Wi-Fi info
        output = subprocess.check_output(
            ["nmcli", "-t", "-f", "IN-USE,SIGNAL,RATE,SSID", "dev", "wifi"],
            text=True
        )

        for line in output.splitlines():
            parts = line.strip().split(":")
            if len(parts) < 4:
                continue
            in_use, signal, rate, ssid = parts

            if in_use == "*":  # currently connected Wi-Fi
                # Signal strength 0-100
                strength = int(signal)

                # Max bitrate may not be reported on mobile; handle gracefully
                try:
                    max_bitrate_mbps = int(float(rate.split()[0]))
                    if max_bitrate_mbps == 0:
                        max_bitrate_mbps = None
                except Exception:
                    max_bitrate_mbps = None

                return strength, max_bitrate_mbps

    except Exception:
        pass

    # No Wi-Fi active
    return None, None




def ping_latency(host="8.8.8.8"):
    """Return latency in ms or None"""
    try:
        output = subprocess.check_output(
            ["ping", "-c", "1", "-W", "1", host],
            stderr=subprocess.DEVNULL
        )
        for line in output.decode().splitlines():
            if "time=" in line:
                time_ms = line.split("time=")[1].split(" ")[0]
                return float(time_ms)
    except subprocess.CalledProcessError:
        return None
    return None


# ---------------- GUI Application ----------------
class InternetWatcherApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="org.example.InternetWatcher")
        self.connect("activate", self.on_activate)
        self.last_network_status = None
        self.updater_thread = None
        self.running = True

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
            types = get_active_connections()
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

            # Notify only once per outage
            if status_text != self.last_network_status:
                if not types:
                    Notify.Notification.new("Internet disconnected").show()
                elif self.last_network_status is not None:
                    Notify.Notification.new(f"Internet connected: {', '.join(types)}").show()
                self.last_network_status = status_text

            # Update GUI labels
            GLib.idle_add(self.status_label.set_text, status_text)
            GLib.idle_add(self.wifi_label.set_text, wifi_text)
            GLib.idle_add(self.latency_label.set_text, latency_text)

            time.sleep(5)

    # ---------------- Button Callbacks ----------------
    def on_service_start(self, button):
        subprocess.run(["systemctl", "--user", "start", "internet-watcher.service"])
        Notify.Notification.new("Service started").show()

    def on_service_stop(self, button):
        subprocess.run(["systemctl", "--user", "stop", "internet-watcher.service"])
        Notify.Notification.new("Service stopped").show()

    def on_refresh(self, button):
        # Force immediate refresh
        self.last_network_status = None

    def on_exit(self, button):
        self.running = False
        Notify.Notification.new("Exiting Internet Watcher").show()
        self.quit()
        sys.exit(0)


if __name__ == "__main__":
    app = InternetWatcherApp()
    app.run()
