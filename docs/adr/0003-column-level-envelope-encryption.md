# 0003. Encrypt sensitive columns with envelope encryption and a blind index

- **Status:** Accepted
- **Date:** 2026-10-14

## Context
The personal identity code (henkilötunnus) is the most sensitive field we store: it
identifies a person nationally and enables identity theft. Disk-level encryption (TDE)
protects lost disks but not database dumps, backups copied elsewhere, SQL injection or an
over-privileged reporting user. We also need uniqueness and exact lookup on the code.

## Decision
`careslot.shared.crypto` implements application-level **envelope encryption**:

1. every value gets a fresh 256-bit data key (DEK) and is encrypted with AES-256-GCM;
2. the DEK is wrapped with a **key-encryption key (KEK)** and stored with the ciphertext;
3. KEKs are versioned (`CARESLOT_KEKS="v1:...,v2:..."`, last one active) and come only from
   the environment, populated from the secret store / KMS in production;
4. **associated data (AAD)** binds each ciphertext to its table, column and row id, so a
   ciphertext copied onto another patient's row fails to decrypt;
5. a **blind index** (HMAC-SHA256 under a separate key) supports uniqueness and lookup
   without decryption.

Clinicians only ever receive a masked form (`DDMMYY-****`); `repr()` of the value object is
masked too, so it cannot leak through logs or tracebacks.

## Alternatives considered
- **TDE / disk encryption only:** necessary but not sufficient (see Context).
- **pgcrypto in SQL:** keys would travel to and be visible in the database session and its logs.
- **Deterministic encryption for lookup:** leaks equality and is weaker than a keyed blind
  index, which reveals nothing without its key.

## Consequences
- A database dump or backup alone reveals no identity codes.
- **Key rotation is cheap:** add a KEK version; new values use it immediately; a re-wrap job
  re-encrypts only the small DEKs (find stale rows with `kek_id_of`). Data is never
  re-encrypted in bulk.
- Moving KEK operations into a cloud KMS (Azure Key Vault, AWS KMS) changes one module.
- No `LIKE` or range queries on encrypted columns. That's acceptable: we only need exact lookup.
- Losing the KEK means losing the data. KEKs need the same backup and DR discipline as the
  database (see docs/non-functional-requirements.md).
