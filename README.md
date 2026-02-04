# droidian phosh network monitor service
Since the network-stack for wifi and mobile-data is a bit flacky, I decided to inform myself about issues, without countermeasures for now.

Monitors network connection via wifi or mobile-data every 3minutes.
Start, stop and monitor service via Phosh Gui. With addiitonal basic network quailty indicators.
If the network is gone, a notification is fired. And the other way around.

Software needed:
```
sudo apt update
sudo apt install \
  python3 \
  python3-dbus \
  python3-gi \
  gir1.2-gtk-4.0 \
  gir1.2-adw-1 \
  gir1.2-notify-0.7 \
  network-manager \
  modemmanager \
  upower
```

Where to put your files:
```~/.local/share/applications/internet-watcher.desktop```
```~/.config/systemd/user/internet-watcher.timer```
