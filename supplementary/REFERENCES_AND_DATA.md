# Primary sources, data provenance, and attribution

Source review: **2026-09-18 UTC** (2026-09-17 America/New_York). The bibliography is [references.bib](../manuscript/references.bib). This review supports the completed, same-model Jev experiment. It does not certify the broad historical TRACE-GC novelty survey. No full research papers or vendor documentation pages are reproduced here.

## Evidence and claim boundaries

| Citation key | Primary source and verified use | What this source does not establish |
| --- | --- | --- |
| `typesafe_api_2026` | [Official API reference](https://docs.typesafe.ai/api): shared `state`, typed question map, `instructions`/`criteria`, selected Choice string, separate probability map, model and token usage fields. | Correct schema does not establish correct semantic answers. |
| `typesafe_models_2026` | [Official models page](https://docs.typesafe.ai/models): `jev-1.13.0`; documented $0.042 per million input tokens and free output; moving aliases and response model ID. | This is vendor documentation, not an invoice, immutable-weight guarantee, or independent accuracy evaluation. |
| `typesafe_choice_2026` | [Choice](https://docs.typesafe.ai/primitives/choice): bounded options and a distribution. | An unavailable candidate cannot be selected; probability normalization does not establish calibration. |
| `typesafe_noul_2026` | [Noul](https://docs.typesafe.ai/primitives/noul): a yes/no probability-like answer. | Two Noul answers do not automatically supply a coherent three-class truth distribution. The chain mapping in this study is an explicit local construction. |
| `typesafe_confidence_2026` | [Confidence](https://docs.typesafe.ai/confidence): Choice/Score confidence is computed from the returned distribution; Noul has no separate confidence field. | Confidence is not independent evidence and is not multiplied by probability in this study. |
| `typesafe_entity_alignment_2026` | [Entity-alignment cookbook](https://docs.typesafe.ai/cookbooks/entity_alignment): existing Jev use for 450 preselected Magellan Beer pairs, with Score routing and field Nouls; documented run used Jev 1.12. | Prior demonstration prevents a claim that applying Jev to entity alignment is novel. Its routing counts are not this study's independently scored accuracy. |
| `typesafe_extraction_cascade_2026` | [Extraction cascade](https://docs.typesafe.ai/cookbooks/sde_cascade): generative extraction, Jev checks, and escalation are already demonstrated. | Does not validate an end-to-end graph compiler or the present prompts. |
| `wadden2020scifact` | [SciFact paper](https://aclanthology.org/2020.emnlp-main.609/): scientific claims, evidence abstracts, support/refutation labels, and rationales. | The present supplied-abstract task is narrower than official retrieval-plus-rationale evaluation. |
| `li2020ditto` | [Ditto paper](https://www.vldb.org/pvldb/vol14/p50-li.pdf): fine-tuned sequence-pair matching and a relevant specialist approach. | No head-to-head Ditto comparison is performed in this Jev study. |
| `kopcke2010entitymatching` | [Original entity-resolution evaluation](https://www.vldb.org/pvldb/vol3/E04.pdf): DBLP-ACM benchmark context and comparative evaluation. | Published scores on upstream splits cannot be compared directly with this identity-disjoint split. |
| `guo2017calibration` | [Temperature-scaling paper](https://proceedings.mlr.press/v70/guo17a.html): postprocessing calibration with a scalar temperature. | Does not guarantee improvement on every scoring rule or shifted task. Here temperature is applied to clipped log probabilities, since native logits are unavailable. |
| `koehn2004significance`, `dror2018testing` | [Paired resampling in NLP evaluation](https://aclanthology.org/W04-3250/) and [test-selection guidance](https://aclanthology.org/P18-1128/). | Do not remove selection uncertainty or certify small-sample coverage for this exact task. This study's intervals condition on fixed selected prompts and observed calls. |

The API and models pages were checked after the experiment during package preparation. The frozen manifest separately records the rate used when the experiment ran. Documentation is mutable: current context limits are now explicit in the model page, whereas the earlier user-supplied survey said that a maximum was unestablished. That historical sentence is not a current API claim in this paper.

### Bibliographic detail

The Ditto PDF's reference-format block says 2021, while publisher-deposited [Crossref metadata](https://api.crossref.org/works/10.14778/3421424.3421431) records the issue publication as September 2020, volume 14, issue 1, pages 50–60. The bibliography uses the issue year 2020 and preserves the discrepancy in its note. The original DBLP-ACM paper's [deposited metadata](https://api.crossref.org/works/10.14778/1920841.1920904) confirms September 2010, volume 3, issues 1–2, pages 484–493. ACL and PMLR bibliographic fields were verified against their canonical publisher records, rather than inferred from search snippets.

## SciFact source and transformation record

**Attribution:** SciFact was created by David Wadden, Shanchuan Lin, Kyle Lo, Lucy Lu Wang, Madeleine van Zuylen, Arman Cohan, and Hannaneh Hajishirzi; cite [Wadden et al. (2020)](https://aclanthology.org/2020.emnlp-main.609/). Its abstracts derive from S2ORC; also credit Kyle Lo, Lucy Lu Wang, Mark Neumann, Rodney Kinney, and Daniel Weld, [Lo et al. (2020)](https://aclanthology.org/2020.acl-main.447/). The [SciFact repository](https://github.com/allenai/scifact) links the archive used by this study.

| Source | Frozen value |
| --- | --- |
| Download | `https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz` |
| Archive bytes | 3,115,079 |
| Archive SHA-256 | `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be` |
| Loaded members | `corpus.jsonl`, `claims_train.jsonl`, `claims_dev.jsonl`; cross-validation copies excluded |
| Prepared split digest | `cd48ed975a8b02d57be219eef6eec92e384905d4b4d9580afc9026d79504a381` |

The URL contains `latest`, so reproducibility depends on the checked content digest, not that URL alone. The archive is fetched by `scripts/download_datasets.py` into the ignored reproduction data directory and checked against this digest; it is not bundled in Git.

**Changes from upstream:** claims are paired only with their supplied cited abstracts. Labels map `SUPPORT` to `SUPPORTS` and `CONTRADICT` to `REFUTES`; absent evidence labels for a supplied cited document map to `NOT_ENOUGH_INFO`. Complete abstracts are retained. Rationale indices remain audit metadata and are not used to choose model evidence. The official development claims supply the evaluation set. Training claims sharing an evaluation document or duplicate abstract are purged (272 claims); remaining connected claim/document/duplicate-abstract components divide training and calibration. This yields 459 training, 150 calibration, and 339 evaluation rows, with 247 evaluation components. Only six training demonstrations and 60 additional training development examples are used by the Jev selection procedure.

**License observation:** [SciFact's license](https://raw.githubusercontent.com/allenai/scifact/master/LICENSE.md) expressly assigns [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) to claims and evidence annotations, [ODC-By 1.0](https://opendatacommons.org/licenses/by/1-0/) to corpus abstracts, and Apache 2.0 to its code. The short upstream notice is preserved in [licenses/SCIFACT_LICENSE.md](licenses/SCIFACT_LICENSE.md). These are separate layers; the code license does not replace the data notices. ODC-By's own terms distinguish database rights from rights in individual contents. This package retains the dataset publisher's stated terms and original source IDs; it does not certify individual article publishers' rights or apply a new blanket license to the abstract text.

## DBLP-ACM source and transformation record

**Attribution:** credit the Database Group Leipzig, Hanna Köpcke, Andreas Thor, and Erhard Rahm and their [2010 evaluation](https://www.vldb.org/pvldb/vol3/E04.pdf), the [benchmark page](https://dbs.uni-leipzig.de/research/projects/benchmark-datasets-for-entity-resolution), the [DeepMatcher/ER-Magellan preparation](https://github.com/anhaidgroup/deepmatcher/blob/master/Datasets.md), and Yuliang Li, Jinfeng Li, Yoshihiko Suhara, AnHai Doan, and Wang-Chiew Tan for [Ditto](https://www.vldb.org/pvldb/vol14/p50-li.pdf).

The provenance chain is **Leipzig DBLP-ACM benchmark → DeepMatcher/ER-Magellan Structured/DBLP-ACM → Ditto serialization → this study's identity-disjoint preparation**. DeepMatcher's source notes explicitly identify Leipzig and describe derived candidate-pair preparation. Ditto's pinned README identifies ER-Magellan and documents serialization with `COL`, `VAL`, tab-separated records, and binary labels. The experiment downloaded the Ditto files, not the original Leipzig CSVs.

Pinned Ditto revision: `52985564a93fb11308439516d3e17a033d43ec8f`. Each URL has the prefix `https://raw.githubusercontent.com/megagonlabs/ditto/52985564a93fb11308439516d3e17a033d43ec8f/data/er_magellan/Structured/DBLP-ACM/`.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `train.txt` | 2,894,612 | `4f757d2d5dae4f7d7d118b796c683a232b4e11bf000e2012b64f8af95a981a4e` |
| `valid.txt` | 966,837 | `b13444a2bf1a503ed558e782f42b247cf56e16e67be2e58d92d7435161299e2e` |
| `test.txt` | 961,602 | `ded891e469b1d08e21269038c984dc761ae2fd5b142b00c46c30fce45adc6e68` |

Prepared split digest: `faef8f3a423aa7fc22242e901a23bd8c1743517706c006df92273913d26d629a`.

**Changes from upstream:** serialized attributes are parsed and hashed; duplicate record pairs are collapsed; seven conflicting serialized pairs trigger a 92-pair identity-family quarantine. Positive labels define identity components solely for leakage control. Component hashes assign approximately 60/20/20 train/calibration/evaluation buckets; 5,623 pairs crossing buckets are dropped. Deterministic maximal matching then removes repeated held-out identity groups (457 calibration and 536 evaluation pairs). The result contains 4,592 training, 390 calibration, and 413 evaluation pairs. Held-out pairs are identity-disjoint, but the resulting evaluation has 350 `same` and 63 `different` examples, unlike the training class mixture. These scores are not the official Ditto/DeepMatcher split scores or evidence of candidate-retrieval recall.

**License observation:** the [Leipzig benchmark page](https://dbs.uni-leipzig.de/research/projects/benchmark-datasets-for-entity-resolution) states a January 2019 Creative Commons release and links directly to [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), requesting attribution to that page and the 2010 paper. [licenses/DBLP_ACM_NOTICE.md](licenses/DBLP_ACM_NOTICE.md) preserves this attribution and link observation. Ditto's pinned repository contains Apache 2.0 in `LICENSE`, which is preserved separately; it is not taken as permission to erase upstream data attribution. The retrieved DeepMatcher preparation note supplies provenance, not a separately verified grant for every intermediate transformation. No exhaustive rights-chain audit or byte-level comparison with the original Leipzig release was performed.

## Package data notices and gaps

- These attribution and transformation notices apply to copied raw sources, prepared rows, and evidence text embedded in saved plans and payloads. The same source data appears in multiple audit artifacts; duplication does not change its origin or terms.
- The frozen [data-preparation source](../reproduction/pgc/experiments/research_data.py), [data manifest](../reproduction/results/research/data_manifest.json), [Jev protocol](../reproduction/results/jev/PROTOCOL.md), and [run plan](../reproduction/results/jev/run-20260918/plan.json) are the precise executable specifications and membership records. Dataset labels have been visible in earlier repository research; the present freeze is not an independently blinded benchmark or external preregistration.
- Original repository fixtures are secondary diagnostics, not independently expert-adjudicated benchmark data. No new human annotation study or inter-annotator agreement study was conducted for this package.
- Full related-work comparison, independent domain replication, deployment-risk validation, and institutional authorship/ethics disclosures remain manuscript work. Existing vendor examples establish prior use, not Jev superiority. Literature beyond the bibliography is historical context until separately verified.
- Source-review URLs and UTC fetch metadata are preserved in [source_review_metadata.json](source_review_metadata.json). It records source hashes where fetched for archival provenance, without redistributing full documentation pages.

## Suggested attribution text for a paper's data-availability section

The study uses SciFact claims and evidence annotations (Wadden et al., 2020, CC BY 4.0), SciFact's S2ORC-derived abstracts (Lo et al., 2020, dataset notice ODC-By 1.0), and a transformed DBLP-ACM benchmark originally provided by the Database Group Leipzig (Köpcke et al., 2010, benchmark notice CC BY 4.0), accessed through DeepMatcher/ER-Magellan and the pinned Ditto serialization (Li et al., 2020). We provide source attribution, byte hashes, transformation code, split membership, prompts, service responses, and replay instructions. Our derived splits and supplied-candidate tasks differ from the upstream benchmark protocols. Third-party data retain their respective notices and are not relicensed as original project code.
