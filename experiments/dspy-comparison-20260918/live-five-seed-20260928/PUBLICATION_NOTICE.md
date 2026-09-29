# Raw evidence rights and attribution

The release ZIPs contain research evidence: requests, model responses,
proposal traces, predictions, and source excerpts. They are **not covered as a
whole by the repository's AGPL-3.0-only code license**. The code license covers
original project code only; [RIGHTS.md](../../../RIGHTS.md) explains this
boundary. No blanket reuse license is granted here for the mixed raw journals.

- SciFact claims and evidence annotations come from Wadden et al.'s SciFact
  dataset and carry [CC BY 4.0](https://github.com/allenai/scifact/blob/master/LICENSE.md).
  Preserve its attribution and transformation notice.
- SciFact's evidence abstracts derive from S2ORC. The SciFact notice labels
  its `corpus.jsonl` abstracts [ODC-By 1.0](https://github.com/allenai/scifact/blob/master/LICENSE.md).
  The [ODC-By legal text](https://opendatacommons.org/licenses/by/1-0/)
  covers database rights and does not itself clear independent rights in an
  individual abstract. Preserve the S2ORC attribution and assess any such
  rights for further redistribution.
- The transformed DBLP–ACM benchmark is credited to the Database Group Leipzig
  under its [CC BY 4.0 notice](https://dbs.uni-leipzig.de/research/projects/benchmark-datasets-for-entity-resolution).
  The [project's detailed data notes](../../../supplementary/REFERENCES_AND_DATA.md)
  identify the benchmark's downstream serialization and transformation.
- The [TypeSafe customer agreement](https://typesafe.ai/legal/mca) assigns any
  TypeSafe interest in output to its customer, subject to law and third-party
  rights. The [Ollama terms](https://registry.ollama.com/terms) do not claim
  ownership of user inputs or outputs. Neither service term clears upstream
  research-text rights embedded in an input or output.

This notice records the applicable source claims and cautions; it is not an
ownership claim for underlying articles or a sublicense to use model output
for a prohibited purpose. Cite the [repository](../../../CITATION.cff),
SciFact, S2ORC, and DBLP–ACM separately when using the evidence. The raw
artifacts are supplied for audit and reproduction with the exact source,
protocol, and transformation hashes in `RUN_RECEIPTS.json` and the ZIPs.
