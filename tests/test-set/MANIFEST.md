# Test set

Fetched 2026-11-23, about 8:00 PM ET. All four articles are open access, CC-BY. Check a file with `shasum -a 256 test-set/<file>`.

## The four articles (scored in every phase)

| File | Kind | Article | DOI | Source link | Pages | SHA-256 |
|---|---|---|---|---|---|---|
| `caprolace.pdf` | Excavation report, PDF | Alessandri et al. 2019, "Salt or fish (or salted fish)? … Caprolace settlement", PLoS ONE 14(11) | 10.1371/journal.pone.0224435 | https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0224435&type=printable | 41 | `4fb807e12e6b32c7f368245bb946177c4b343b0f749d5086fca4c09da376bfa2` |
| `caprolace.html` | its web page | same | same | https://doi.org/10.1371/journal.pone.0224435 | no page numbers | `57743c6fe5c1660bc035649a782d829c9fbdd2a3ff82a9673e4285446583debd` |
| `leprosy-adna.pdf` | Lab science (aDNA), PDF | Krause-Kyora et al. 2018, "Ancient DNA study reveals HLA susceptibility locus for leprosy in medieval Europeans", Nature Communications 9:1569 | 10.1038/s41467-018-03857-x | https://www.nature.com/articles/s41467-018-03857-x.pdf | 11 | `f157da9fd22956b3988c8fcb61f44d2516f5f3480a7cd0bd7df14108fab2668d` |
| `leprosy-adna.html` | its web page | same | same | https://doi.org/10.1038/s41467-018-03857-x | no page numbers | `f77f652b9f35cd110bc6bb4b8b43c7891320d8e6b224aaa234875c983938ad0b` |
| `caa-theory.pdf` | Theory, PDF | Rajala 2026, "Theory in Archaeology, Theory in Computing 1", JCAA 9(1):366–384 | 10.5334/jcaa.263 | https://journal.caa-international.org/articles/263/files/6ace00a65cb3e.pdf | 19 (printed 366–384) | `5e8da110c57e67284fb49e3387485ebc63f0d3ee8950f95e8e7c7033c3d310cf` |
| `caa-theory.html` | its web page | same | same | https://doi.org/10.5334/jcaa.263 | no page numbers | `06f51aed2b3bbe938dac530b4407d6901ec1c41c1d7bc4781c1ed0b1fbe0a2a7` |
| `south-america.pdf` | Review / synthesis, PDF | de Souza et al. 2020, "Archaeological expansions in tropical South America during the late Holocene", PLoS ONE 15(4) | 10.1371/journal.pone.0232367 | https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0232367&type=printable | 32 | `3d89d0d3c23b92ffa07c73e9b44b5561a9a723751050cd5906a913391d75655c` |
| `south-america.html` | its web page | same | same | https://doi.org/10.1371/journal.pone.0232367 | no page numbers | `371bcb3308696250766ae6e74f3f296bb70e3528b62e69cb1f08baf0b5056680` |

The `.html` files are the pages the DOIs redirect to, saved as served. A publisher may change a page later (related-article boxes, scripts), so a fresh download can have a different checksum; the headings and article text are what the checker reads.

## Page-image copy

| File | Kind | Made from | Pages | SHA-256 |
|---|---|---|---|---|
| `caprolace-scanned.pdf` | Stand-in for a scanned article: 41 page images at 130 dpi (1105×1430 px JPEG), no text layer | `caprolace.pdf`, by `uv run tools/make_scanned.py test-set/caprolace.pdf test-set/caprolace-scanned.pdf` (same bytes on every run) | 41 | `f12b9fe6eef37e05a53e1423aa33675bf6e61715fb9f633e7395d1a4a4d04364` |

## Paywalled DOI

| DOI | Article | Status |
|---|---|---|
| 10.1179/pan.2005.033 | "Excavations, Archaeological Stratigraphy, and Cultural Components", Plains Anthropologist, 2005 | closed, abstract only, used from phase 2. No file: OpenAlex lists `is_oa: false`, no open copy (checked 2026-11-23, about 8:05 PM ET) |

## Earlier set, not scored

Kept because the transcripts in phases 2 to 4 cite them.

| File | What | Pages | SHA-256 |
|---|---|---|---|
| `rsos.241776.pdf` | Peters & Chin-Yee 2025, Royal Society Open Science, DOI 10.1098/rsos.241776 | 18 | `8d36281540a5a6a3b99b799dc3f1717d9018afd25df7e7c59bf4617a61c03f40` |
| `rsos.241776-scanned.pdf` | page-image copy of the above | 18 | `9cc9f5e1b354909bb6ef31feb7516d19cd6ec11fa365e50442b4b2f5bfef0dbd` |
| `nature25738.pdf` | Olalde et al. 2018, accepted manuscript, DOI 10.1038/nature25738 | 32 | `4ecf4f4124fa676b6296a91ba6d1f4eb3f91dd0ac1d77e236e4522316b513bd0` |
| `openalex-closed-fixture.json` | OpenAlex record of a closed article, DOI 10.5615/bullamerschoorie.375.0119 | – | `32cc3a9d8d583c1d758c4ec479518988d35a297973352c55cff3160586c11fdc` |
