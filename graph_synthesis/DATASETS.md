# Acquiring the original dataset bytes

From the repository root, use Python 3.12:

```sh
python -B -m graph_synthesis.datasets
python -B -m graph_synthesis.datasets --check
```

The current acquisition command first verifies or downloads SciFact into the
ignored `reproduction/data/sources/` directory. It then invokes the unchanged
`scripts/download_datasets.py` to acquire the three commit-pinned DBLP-ACM source
files, regenerate both prepared datasets, and check all six original sizes and
SHA-256 hashes in `scripts/datasets.json`. `--check` uses that same six-file
verifier without downloading or preparing anything. The archived command
`python -B scripts/download_datasets.py --check` remains equivalent.

## Official version-pinned SciFact source

The preferred source is the publisher's original S3 object with an explicit
version ID:

<https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz?versionId=8LiW3OUBLBvhehDzrRdGD1ibIaXL.6PQ>

| Property | Verified value |
| --- | --- |
| Source owner | Allen Institute for AI, [SciFact repository](https://github.com/allenai/scifact) |
| S3 object version | `8LiW3OUBLBvhehDzrRdGD1ibIaXL.6PQ` |
| Bytes | 3,115,079 |
| Expected and observed SHA-256 | `11c621288d41ac144d29b13b0f8503b3820b7d6e8b1f6ff24dff335c196d76be` |
| Object Last-Modified | 2021-01-26 02:28:59 UTC |
| Verification date | 2026-09-28 UTC |

The version-specific URL returned those exact archived bytes. Although the key
contains `latest`, the explicit version identifies the existing object:
[S3 versioning](https://docs.aws.amazon.com/AmazonS3/latest/userguide/versioning-workflows.html)
keeps previous versions when an object is replaced or an ordinary delete marker
is added. The object owner can still permanently remove a version or revoke
access; versioning does not promise perpetual availability.

If that version cannot be downloaded or fails integrity validation, the command
reports the rejection and tries the original unversioned `latest` URL. Every
response must match the existing byte count and digest before being installed.
An unavailable or changed unversioned URL therefore does not prevent acquisition
while the preferred pinned object is accessible. Both URLs use the original
publisher's bucket; this change creates no new mirror or bundled data copy.

The publisher's [2021 source change](https://github.com/allenai/scifact/commit/4816a3c7098f7121056276cdfdad228c60daa356)
records the move from `/release/2020-12-17/` to `/release/latest/`. The dated URL
returned HTTP 403 during this review and is not used as a fallback.

## Recovery with existing verified bytes

If the publisher's service is unavailable, obtain the original archive from a
previously verified local copy or another source you trust and run:

```sh
python -B -m graph_synthesis.datasets --scifact-archive /path/to/data.tar.gz
python -B scripts/download_datasets.py --check
python -B -m graph_synthesis.verify --replay --tests
```

Use a Windows path and quotes where appropriate. The supplied file must match
the size and SHA-256 above. The command verifies it before replacing a cached
archive. It also reports the source and observed digest. A bad existing cache
is reported without automatically replacing it; a valid `--scifact-archive`
provides an explicit repair. If the three DBLP-ACM sources are also absent,
their normal commit-pinned downloads still require network access.

Integrity failures include expected and observed sizes and hashes. Never edit
the pinned hashes to accept a different release. Downloads use temporary files
and publish only verified SciFact bytes. Downloaded and prepared datasets remain
ignored and must not be added to Git.

## Attribution and rights

Credit David Wadden and coauthors for [SciFact](https://aclanthology.org/2020.emnlp-main.609/)
and Kyle Lo and coauthors for [S2ORC](https://aclanthology.org/2020.acl-main.447/).
The publisher's [license notice at the reviewed revision](https://github.com/allenai/scifact/blob/68b98a56d93e0f9da0d2aab4e6c3294699a0f72e/LICENSE.md)
assigns CC BY 4.0 to claims/evidence annotations and ODC-By 1.0 to the corpus
abstracts; its Apache 2.0 code license is separate. See the preserved
[SciFact notice](../supplementary/licenses/SCIFACT_LICENSE.md) and
[full source, transformation, and rights record](../supplementary/REFERENCES_AND_DATA.md).
The acquisition change retains the exact original data and those notices.
