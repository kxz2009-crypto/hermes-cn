# v0.23.0 candidate upgrade inputs — not a customer release

Release ID: `LV-HERMES-0230-FIRST-UPGRADE-20261109`.
Target: Hermes `v0.23.0`, `2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19`.

This additive PR prepares the next upgrade for the existing distribution pipeline. It
does not replace either the current public installer or the pending R3 implementation.
It is based on public `main` commit `809ed796cffaf4a89af730eda5ff81560854ae8d`, not on
unpublished local R3 history. Merge does not publish installer/CDN artifacts. R3 integration
must reconcile its own approved changes separately; this PR is not stacked on that branch.

## Actual changes requiring review

| Input | Existing R3 contract | Pinned v0.23.0 source |
| --- | --- | --- |
| Upstream | v0.22.2 / d923a5eb487a17c0a68801bba9ef0f56c81040a8 | v0.23.0 / 2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19 |
| Python PM build | 3.14.7+20260901 | 3.14.9+20261021 |
| uv | 0.12.3 | 0.13.5 |
| Python runtime line | 3.14 | 3.14 |
| Python metadata | >=3.11,<3.15 | >=3.11,<3.15 |
| Node package engines | ^22.22.0 or ^24.11.0 or >=26.0.0 | >=26 |

The target `pyproject.toml` package version is `0.0.0`; it is not the release authority.
Tag and full Git commit are authoritative. Node package engines must not be applied
blindly to every Python CLI installation; Electron OS limits concern Desktop only.
Existing v0.22.2 download receipts do not validate new Python/uv artifacts or the new
source bundle. No new domestic URL, artifact size or download hash is invented here.

## Reproducible offline input build

Use an official-origin clone containing the exact reviewed tag:

```sh
python3 scripts/prepare-upstream-candidate.py \
  --upstream-clone /absolute/official-hermes-clone \
  --out /absolute/new-private-candidate
```

The tool reads immutable Git objects, not worktree settings, credentials or customer
files. It cross-checks the official installer uv pins against the PM lock, retains exact
source bytes and hashes, and emits `UNSIGNED_REVIEW_ONLY_NOT_INSTALLABLE` inputs. Source
archive publication, signatures, Mac/WSL installation and domestic network acceptance
remain blocked. Existing output paths and symlink ancestors are refused.

## Real self-contained source bundle build

```sh
python3 scripts/build-upstream-bundle.py \
  --upstream-clone /absolute/complete-official-hermes-clone \
  --out /absolute/new-private-bundle-build
```

This reads the complete object store without fetch/unshallow/ref updates. It builds a
bundle, restores it into an empty bare repository, checks the exact peeled target SHA,
and runs full fsck. Only then are actual bytes and SHA-256 written to its receipt.
No installer, model, Gateway, signing operation, cloud upload or production request runs.

A shallow source clone is **rejected before writing output**. During engineering review,
`git bundle verify` alone reported a shallow-created bundle as okay, while restoration
failed due to a missing parent. Therefore bundle verification alone is insufficient and
must never be used to claim a complete customer artifact.

A successful receipt means `LOCAL_RESTORE_VERIFIED_NOT_PUBLISHED`, not a domestic
network, signed release or installation PASS. The restored verification repository is
retained locally; do not upload it or the large bundle through this source PR.

## Workflow gates

- A / CN Windows-WSL2: new candidate pins prepared; requires R3 integration, scoped test
  signing, new exact dependency transfers, clean WSL installation, upgrade/rollback and
  real task evidence before customer GO. No existing Gateway may be modified.
- B / CN macOS: Apple Silicon and Intel inputs are separate. No physical Mac acceptance
  is present in this task. Existing CI evidence or M1-M6 labels do not establish support.
- C / CN distribution: complete local bundle restore is necessary but insufficient.
  Approved immutable upload, actual HTTPS download/hash, signed descriptor, retention and
  authorized rollback target still require separate approval and verification.

The existing default signed manifest, trust root, installation entries, website,
mini-program, payment settings and production cloud resources are unchanged.

## Validation

`python3 scripts/test-upstream-candidate.py -v` (12 synthetic boundary tests).
`python3 scripts/test-upstream-bundle.py -v` (5 synthetic boundary tests).
Actual Git-object input build and full bundle restore are separate integration evidence.
No Mock result is installation acceptance. Historical installer suites are not repeated.
