# DBLP-ACM attribution and license-link record

Reviewed 2026-09-18 UTC. This is a locally authored source notice, not a verbatim copy of the benchmark page.

The Database Group Leipzig's [Benchmark datasets for entity resolution](https://dbs.uni-leipzig.de/research/projects/benchmark-datasets-for-entity-resolution) page identifies DBLP-ACM as a bibliographic benchmark and states that its binary entity-resolution datasets were made available under Creative Commons in January 2019. The linked license resolves to [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/) ([legal code](https://creativecommons.org/licenses/by/4.0/legalcode)). The page requests credit to the benchmark page and the following paper:

Hanna Köpcke, Andreas Thor, and Erhard Rahm. 2010. Evaluation of Entity Resolution Approaches on Real-World Match Problems. Proceedings of the VLDB Endowment 3(1–2):484–493. [Paper](https://www.vldb.org/pvldb/vol3/E04.pdf), DOI:10.14778/1920841.1920904.

This study's copy comes through [DeepMatcher's ER-Magellan preparation](https://github.com/anhaidgroup/deepmatcher/blob/master/Datasets.md) and [Ditto revision 52985564a93fb11308439516d3e17a033d43ec8f](https://github.com/megagonlabs/ditto/tree/52985564a93fb11308439516d3e17a033d43ec8f). Credit the respective maintainers and Li et al., Deep Entity Matching with Pre-Trained Language Models, PVLDB14(1):50–60, DOI:10.14778/3421424.3421431.

Changes made in this study include parsing, duplicate-pair collapse, ambiguity quarantine, identity-component grouping, new train/calibration/evaluation assignment, removal of cross-partition pairs, and identity-disjoint held-out subsampling. See [REFERENCES_AND_DATA.md](../REFERENCES_AND_DATA.md) for exact hashes and counts. Original bibliographic strings are retained in the parsed attributes; no endorsement by any source author or organization is implied.
