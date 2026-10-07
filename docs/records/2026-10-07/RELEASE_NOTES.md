# Experimental Intel macOS dependency wheel

LocalVRAM-built cryptography 50.0.0 wheel for the pinned Hermes
v2026.9.24 adaptation experiment.

This is a dependency asset, not a Hermes release and not an official
cryptography or Nous Research binary distribution.

Validated on macOS 15 x86_64 with Python 3.11.17:
- Source archive hash checked against the pinned upstream uv.lock.
- Native-library linkage audit.
- Encryption, decryption and Ed25519 signature verification.
- Core dependency installation using PyPI and TUNA.
- Hermes editable installation and help/version startup.

See provenance.json and SHA256SUMS for exact identity and evidence.

Pending before public distribution:
- Redistribution license and bundled-notice review.
- Durable download integration and download verification.
- China-network installation and model-call tests.

This draft is for preservation and review.
