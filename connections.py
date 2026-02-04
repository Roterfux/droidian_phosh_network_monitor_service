import dbus

NM = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"

def active_types() -> set[str]:
    bus = dbus.SystemBus()
    nm = bus.get_object(NM, NM_PATH)
    props = dbus.Interface(nm, "org.freedesktop.DBus.Properties")

    active = props.Get("org.freedesktop.NetworkManager", "ActiveConnections")
    types = set()

    for path in active:
        ac = bus.get_object(NM, path)
        ac_props = dbus.Interface(ac, "org.freedesktop.DBus.Properties")

        ctype = ac_props.Get(
            "org.freedesktop.NetworkManager.Connection.Active", "Type"
        )

        if ctype == "802-11-wireless":
            types.add("wifi")
        elif ctype in ("gsm", "cdma", "lte"):
            types.add("mobile")

    return types
