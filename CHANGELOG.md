# Changelog

## [0.3.0](https://github.com/the-hcma/cloudflare-dns-updater/compare/v0.2.2...v0.3.0) (2026-05-23)


### Features

* use exit code 2 for hard failures and improve cron docs ([#19](https://github.com/the-hcma/cloudflare-dns-updater/issues/19)) ([6ba2ad5](https://github.com/the-hcma/cloudflare-dns-updater/commit/6ba2ad5d94fdd5bc2fc3756a2a081caf6a73a29f))

## [0.2.2](https://github.com/the-hcma/cloudflare-dns-updater/compare/v0.2.1...v0.2.2) (2026-05-23)


### Bug Fixes

* **ci:** harden merged-pr-closer against transient gh 401 errors ([#17](https://github.com/the-hcma/cloudflare-dns-updater/issues/17)) ([8f70a31](https://github.com/the-hcma/cloudflare-dns-updater/commit/8f70a31e71ee00091aaad881f379a406baea0d27))
* discover globally addressable IPv6 from host interfaces ([#15](https://github.com/the-hcma/cloudflare-dns-updater/issues/15)) ([d908d43](https://github.com/the-hcma/cloudflare-dns-updater/commit/d908d43f02e070bc80b8b70775f7b5d4f8048a06))
* use PyPI-backed badge that reflects latest release ([#13](https://github.com/the-hcma/cloudflare-dns-updater/issues/13)) ([10027e4](https://github.com/the-hcma/cloudflare-dns-updater/commit/10027e40a2f57ecee61fb84d26521354e1b6c555))


### Documentation

* expand AGENTS.md with session startup and PR workflow ([#14](https://github.com/the-hcma/cloudflare-dns-updater/issues/14)) ([7cc41b0](https://github.com/the-hcma/cloudflare-dns-updater/commit/7cc41b0ec43219bd04386afc0e74a6d3ddadcd42))

## [0.2.1](https://github.com/the-hcma/cloudflare-dns-updater/compare/v0.2.0...v0.2.1) (2026-05-23)


### Bug Fixes

* quiet missing-config errors and write starter config ([#12](https://github.com/the-hcma/cloudflare-dns-updater/issues/12)) ([4c91172](https://github.com/the-hcma/cloudflare-dns-updater/commit/4c9117241bfddbae1053c618e96d0e204298caba))
* run release-please PR checks in parallel ([#10](https://github.com/the-hcma/cloudflare-dns-updater/issues/10)) ([8b516df](https://github.com/the-hcma/cloudflare-dns-updater/commit/8b516df935bf483b8be7567627089f6e6ccfebb2))

## [0.2.0](https://github.com/the-hcma/cloudflare-dns-updater/compare/v0.1.0...v0.2.0) (2026-05-23)


### Features

* show version and commit in --help and --version ([#7](https://github.com/the-hcma/cloudflare-dns-updater/issues/7)) ([99204a7](https://github.com/the-hcma/cloudflare-dns-updater/commit/99204a7767bdc2746ffe90ef0c48b40cec00353b))


### Bug Fixes

* publish required CI checks on release-please PRs ([#9](https://github.com/the-hcma/cloudflare-dns-updater/issues/9)) ([cfe0f61](https://github.com/the-hcma/cloudflare-dns-updater/commit/cfe0f611d82efa1420cd32ece1cb7b5152c2595c))


### Documentation

* clarify PyPI trusted publisher setup ([#5](https://github.com/the-hcma/cloudflare-dns-updater/issues/5)) ([d019da8](https://github.com/the-hcma/cloudflare-dns-updater/commit/d019da8eeeee917b2aab77a18e65d186dd3c1a53))
* README badges and version in help description ([#8](https://github.com/the-hcma/cloudflare-dns-updater/issues/8)) ([38ef1ad](https://github.com/the-hcma/cloudflare-dns-updater/commit/38ef1ad21bd7589730925c5cfe2a1d83bca46bfe))

## 0.1.0 (2026-05-23)


### Features

* add release-please, PyPI publish, and pipx install docs ([#1](https://github.com/the-hcma/cloudflare-dns-updater/issues/1)) ([95ec4a4](https://github.com/the-hcma/cloudflare-dns-updater/commit/95ec4a4fe93bcda3d2e82c2978a1014e35f74dde))


### Bug Fixes

* grant checks write for release PR ci check ([#4](https://github.com/the-hcma/cloudflare-dns-updater/issues/4)) ([c7986f6](https://github.com/the-hcma/cloudflare-dns-updater/commit/c7986f6ef965d47de79d510a95c19720ffa582ab))
