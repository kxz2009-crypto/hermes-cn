# Experimental Intel macOS dependency — r2

LocalVRAM-built cryptography 50.0.0 for the pinned Hermes adaptation.
This is an experimental prerelease, not an official PyCA or Nous Research
distribution and not a production support commitment.

## Download

Prefer cryptography-50.0.0-macos15-intel-r2-bundle.zip.
Verify it against BUNDLE_SHA256SUMS before extraction.
Keep its accompanying notices and provenance with the wheel.

The standalone wheel is also provided for controlled integration;
obtain and retain THIRD_PARTY_NOTICES.draft.txt with it.

## Identity

- Tested platform: macOS 15 x86_64.
- Tested Python: 3.11.17.
- Hermes upstream: f97608f178d1ffeca59860195ab7da295f7c8e5f.
- Build commit: 1b3d7ea78cdc8f86150028c7a31959fee6e56005.
- Wheel SHA256:
  11504d18f54d3435a799f70febb3001b1efbab30d6d05570e447d4c571318a6f

## Validation

Build, native linkage audit, encryption and signature tests:
https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37719594029

Intel candidate integration using PyPI and TUNA:
https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37720428375

Main installer regression, three platforms and two package indexes:
https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37722274542

## Notices and limitations

Original license texts and build provenance accompany the bundle.
The notices document retains its original draft/evidence status.
It includes Cargo.lock candidates, not a proven linked-component SBOM.
Completeness of redistribution review is not claimed.

The OpenSSL installation license matched the archived official license.
NOTICEREF man-page entries in raw provenance are not legal notices.

Intel physical-device model conversations and complete mainland-China
installation have not been validated.
GitHub availability varies by network.
This release provides dependency assets; it is not a complete Hermes
installer release.
