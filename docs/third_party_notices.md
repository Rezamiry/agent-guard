# Third-party notices for release review

This inventory covers the direct runtime dependencies declared in `pyproject.toml`.
License identifiers below were read from installed distribution metadata on
2026-09-28 in the locked Python 3.12 environment. The final package and every
transitive dependency still need a distribution review before publication.

| Direct dependency | Observed installed version | Observed license |
| --- | --- | --- |
| pydantic | 2.13.5 | MIT |
| presidio-analyzer | 2.2.364 | MIT |
| spacy | 3.8.16 | MIT |
| tldextract | 5.3.2 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| anyio | 4.15.1 | MIT |
| langchain | 1.4.2 | MIT |
| langchain-core | 1.6.4 | MIT |
| langgraph | 1.2.12 | MIT |
| agent-framework-core | 1.19.0 | MIT (package classifier and bundled LICENSE) |

The `en_core_web_lg==3.8.0` spaCy model is a separately provisioned optional
asset. It is not included in this repository or the planned wheel/sdist. Its
installed distribution reports MIT, but model redistribution terms and notices
must be checked against the actual asset before any bundling is proposed.

The proposed project source license is Apache-2.0; `LICENSE` contains the
[Apache Software Foundation's published 2.0 text](https://www.apache.org/licenses/LICENSE-2.0.txt).
The maintainer has not yet recorded license acceptance. This document is an
inventory for review, not evidence that publication or redistribution is approved.
