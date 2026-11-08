pkgname=tomos-premiumgen
pkgver=0.2.0
pkgrel=3
pkgdesc="TomOS SIP Premium lifetime licence generator with GTK 4 desktop app"
arch=('any')
url="https://github.com/Spruhantom/tomos-premiumgen"
license=('MIT')
depends=('python' 'python-cryptography' 'python-qrcode' 'python-pillow' 'python-textual' 'python-gobject' 'gtk4')
makedepends=('git' 'python-build' 'python-installer' 'python-setuptools')
# Pin the source to the reviewed GTK GUI merge commit. This avoids depending on
# a release tag that may not exist yet and makes the package source reproducible.
source=("${pkgname}::git+https://github.com/Spruhantom/tomos-premiumgen.git#commit=a7d88fa85ccd84ad2c4aeb4a80789b8563c97381")
sha256sums=('SKIP')

build() {
  cd "${srcdir}/${pkgname}"
  python -m build --wheel --no-isolation
}

package() {
  cd "${srcdir}/${pkgname}"
  python -m installer --destdir="${pkgdir}" dist/*.whl
  install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
  install -Dm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"
  install -Dm644 data/tomos-premiumgen.desktop "${pkgdir}/usr/share/applications/tomos-premiumgen.desktop"
}
