import dbus
import dbus.mainloop.glib
from gi.repository import GLib

NM = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"

def get_active_connection_types() -> set[str]:
    bus = dbus.SystemBus()
    nm = bus.get_object(NM, NM_PATH)
    props = dbus.Interface(nm, "org.freedesktop.DBus.Properties")

    active = props.Get("org.freedesktop.NetworkManager", "ActiveConnections")
    types = set()

    for path in active:
        ac = bus.get_object(NM, path)
        ac_props = dbus.Interface(ac, "org.freedesktop.DBus.Properties")
        ctype = ac_props.Get("org.freedesktop.NetworkManager.Connection.Active", "Type")

        if ctype == "802-11-wireless":
            types.add("wifi")
        elif ctype in ("gsm", "cdma", "lte"):
            types.add("mobile")

    return types

class NMWatcher:
    """Event-driven NetworkManager watcher using D-Bus signals"""
    def __init__(self, callback):
        self.callback = callback
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        self.bus.add_signal_receiver(
            self._on_properties_changed,
            signal_name="PropertiesChanged",
            dbus_interface="org.freedesktop.DBus.Properties",
            path=NM_PATH
        )

    def _on_properties_changed(self, interface, changed, invalidated):
        self.callback()  # Call GUI update callback

    def run(self):
        GLib.MainLoop().run()
