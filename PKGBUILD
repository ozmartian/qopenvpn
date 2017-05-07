# Maintainer: Michal Krenek (Mikos) <m.krenek@gmail.com>
# Modified: Pete Alexandrou (ozmartian) <pete@ozmartians.com>
pkgname=qopenvpn
pkgver=2.0.0
pkgrel=2
pkgdesc="Simple OpenVPN GUI written in PyQt for systemd based distributions"
arch=('any')
url="https://github.com/xmikos/qopenvpn"
license=('GPL3')
depends=('python-pyqt5' 'openvpn' 'systemd')
makedepends=('python-setuptools')
source=(qopenvpn::https://github.com/ozmartian/${pkgname}.git)
md5sums=('SKIP')

build() {
  cd "${srcdir}/${pkgname}"
  python setup.py build
}

package() {
  cd "${srcdir}/${pkgname}"
  python setup.py install --root="$pkgdir" --optimize=1 --skip-build
}

# vim:set ts=2 sw=2 et:
