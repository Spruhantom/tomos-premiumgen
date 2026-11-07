pkgname=tomos-premiumgen
pkgver=0.1.0
pkgrel=1
pkgdesc="TomOS SIP Premium lifetime licence generator"
arch=('any')
url="https://github.com/Spruhantom/tomos-premiumgen"
license=('MIT')
depends=('python' 'python-cryptography')
makedepends=('python-setuptools')
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/Spruhantom/tomos-premiumgen/archive/refs/tags/v${pkgver}.tar.gz")
sha256sums=('SKIP') # Replace with updpkgsums output before publishing a tagged package

package() {
  cd "${srcdir}/tomos-premiumgen-${pkgver}"
  python -m pip install --root="${pkgdir}" --prefix=/usr --no-deps --no-build-isolation .
  install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/${pkgname}/LICENSE"
  install -Dm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"
}
