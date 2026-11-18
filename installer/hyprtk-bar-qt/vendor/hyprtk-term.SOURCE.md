# hyprtk-term (vendored)

Source: https://github.com/hyprtk/hyprtk-term
Version: 0.2.6

Vendored source snapshot. The bar installer provisions this copy; the separate
installer in that repository remains the source of truth.

Runtime dependency the bar does not manage: **libvterm** (`libvterm` on
Arch/Fedora/Void/Alpine, `libvterm0` on Debian/Ubuntu/openSUSE). The vendored
installer warns when it is missing; `hypr/packages/terminaltools.sh` in the
suite installs it.
