# Test set

Fetched 2026-11-23, about 8:00 PM ET. The article is open access, CC-BY. Check a file with `shasum -a 256 tests/test-set/<file>`.

| File | Kind | Article | DOI | Source link | Pages | SHA-256 |
|---|---|---|---|---|---|---|
| `caprolace.pdf` | Excavation report, PDF | Alessandri et al. 2019, "Salt or fish (or salted fish)? … Caprolace settlement", PLoS ONE 14(11) | 10.1371/journal.pone.0224435 | https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0224435&type=printable | 41 | `4fb807e12e6b32c7f368245bb946177c4b343b0f749d5086fca4c09da376bfa2` |
| `caprolace-scanned.pdf` | Stand-in for a scanned article: 41 page images at 130 dpi (1105×1430 px JPEG), no text layer | made from `caprolace.pdf` by `uv run tests/tools/make_scanned.py tests/test-set/caprolace.pdf tests/test-set/caprolace-scanned.pdf` (same bytes on every run) | same | same | 41 | `f12b9fe6eef37e05a53e1423aa33675bf6e61715fb9f633e7395d1a4a4d04364` |
