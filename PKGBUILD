# Maintainer: Michal Krenek (Mikos) <m.krenek@gmail.com>
# Modified: Pete Alexandrou (ozmartian) <pete@ozmartians.com>
pkgname=qopenvpn
pkgver=2.0.0
pkgrel=2
pkgdesc="Simple OpenVPN GUI written in PyQt for systemd based distributions"
arch=('any')
license=('GPL3')
url="https://github.com/xmikos/qopenvpn"
source=(qopenvpn-git::git+https://github.com/ozmartian/${pkgname}.git)
depends=('python-pyqt5' 'openvpn' 'systemd')
makedepends=('python-setuptools')
provides=('qopenvpn')
md5sums=('SKIP')

build() {
  cd "${srcdir}/${pkgname}-git"
  python setup.py build
}

package() {
  cd "${srcdir}/${pkgname}-git"
  python setup.py install --root="$pkgdir" --optimize=1 --skip-build
}

# vim:set ts=2 sw=2 et:
