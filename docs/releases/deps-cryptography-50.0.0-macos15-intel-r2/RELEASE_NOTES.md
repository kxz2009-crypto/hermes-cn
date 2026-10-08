# Experimental Intel macOS dependency wheel — r2

LocalVRAM-built cryptography 50.0.0 dependency for the pinned Hermes
adaptation experiment. This is not an official PyCA or Nous Research release.

## Candidate identity

- Platform: macOS 15 x86_64.
- Tested Python: 3.11.17.
- Hermes upstream: f97608f178d1ffeca59860195ab7da295f7c8e5f.
- Build commit: 1b3d7ea78cdc8f86150028c7a31959fee6e56005.
- Build run: https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37719594029
- Integration run: https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37720428375
- Wheel SHA256: 11504d18f54d3435a799f70febb3001b1efbab30d6d05570e447d4c571318a6f

## Verified scope

Source archive verification against the pinned upstream lock;
native-library linkage audit; encryption and signature tests;
OpenSSL installation receipt and static-library hashes;
Intel PyPI/TUNA dependency, Hermes CLI startup, installer and protection tests.

The installed OpenSSL license matches the archived official license.
NOTICEREF manual pages in the raw provenance are collection false positives,
not legal NOTICE files.

## Draft status

Preservation and review only. Public distribution review remains pending.
The notices document covers dependency candidates, not a complete linked SBOM.
The installer still references r1; r2 is not integrated into public downloads.
Intel physical-device model calls and mainland-China full installation
remain unverified. No claim of bit-for-bit reproducibility is made.
