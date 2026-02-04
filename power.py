from pydbus import SystemBus

UP = "org.freedesktop.UPower"
UP_PATH = "/org/freedesktop/UPower/devices/DisplayDevice"

def battery_percentage() -> float:
    bus = SystemBus()
    dev = bus.get(UP, UP_PATH)
    return dev.Percentage
