pkgname=tomos-premiumgen
pkgver=0.2.0
pkgrel=1
pkgdesc="TomOS SIP Premium lifetime licence generator with GTK 4 desktop app"
arch=('any')
url="https://github.com/Spruhantom/tomos-premiumgen"
license=('MIT')
depends=('python' 'python-cryptography' 'python-qrcode' 'python-pillow' 'python-textual' 'python-gobject' 'gtk4')
makedepends=('python-setuptools')
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/Spruhantom/tomos-premiumgen/archive/refs/tags/v${pkgver}.tar.gz")
sha256sums=('SKIP') # Run updpkgsums before publishing a tagged package.

package() {
  cd "${srcdir}/tomos-premiumgen-${pkgver}"
  python -m pip install --root="${pkgdir}" --prefix=/usr --no-deps --no-build-isolation .
  install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
  install -Dm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"
  install -Dm644 data/tomos-premiumgen.desktop "${pkgdir}/usr/share/applications/tomos-premiumgen.desktop"
}
