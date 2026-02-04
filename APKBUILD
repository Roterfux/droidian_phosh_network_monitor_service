pkgname=internet-watcher
pkgver=1.0
pkgrel=0
pkgdesc="Background internet connectivity watcher for Phosh"
url="https://example.org"
arch="all"
license="GPL-3.0"
depends="python3 py3-pydbus networkmanager libnotify gtk4 libadwaita"
makedepends=""
source=""
build() { :; }

package() {
    install -Dm755 daemon.py \
        "$pkgdir/usr/lib/internet-watcher/daemon.py"

    install -Dm755 gui.py \
        "$pkgdir/usr/bin/internet-watcher"

    install -Dm644 internet-watcher.service \
        "$pkgdir/usr/lib/systemd/user/internet-watcher.service"

    install -Dm644 internet-watcher.desktop \
        "$pkgdir/usr/share/applications/internet-watcher.desktop"
}
