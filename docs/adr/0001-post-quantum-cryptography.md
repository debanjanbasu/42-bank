# ADR-0001: Post-Quantum Cryptography (ML-DSA-44)

**Status:** Accepted  
**Date:** 2024-01-15

## Context
Banking transactions require strong cryptographic signatures. Classical algorithms (ECDSA, RSA) are vulnerable to quantum computers via Shor's algorithm. NIST finalized ML-DSA (Module-Lattice-Based Digital Signature Algorithm) in FIPS 204 (2024).

## Decision
Use **ML-DSA-44** (the 128-bit security parameter set of ML-DSA) for transaction signing:
- Mobile: `@noble/post-quantum` (JavaScript/WASM)
- Backend: `pqcrypto` (Python bindings)

## Rationale
- **Future-proof:** Resistant to quantum attacks
- **NIST-standardized:** FIPS 204, no royalties
- **Performance:** ML-DSA-44 signs in ~1ms on modern hardware
- **Key sizes:** Public key 1312 bytes, signature 2420 bytes — acceptable for banking use

## Consequences
- Larger key and signature sizes vs ECDSA (P-256: 64-byte sig vs 2420 bytes)
- Library ecosystem is younger; bugs possible in early implementations
- Private keys never leave the device (Keychain/Keystore)
