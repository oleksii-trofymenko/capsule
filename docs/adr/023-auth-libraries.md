# ADR-023: Auth libraries: PyJWT (no extras) and argon2-cffi

- Status: proposed
- Date: 2026-10-27
- Deciders: Orchestrator, security-engineer, project owner
- Related: E1-02, E1-05, E1-07; ADR-005, ADR-014, ADR-018, ADR-019, ADR-020

## Context

ADR-014 decides HS256 access JWTs and argon2id password hashes. Blueprint §4 names neither a JWT nor a password-hashing library, so this ADR names them. Every runtime dependency adds pip-audit scope and image size. Releases must be at least 7 days old (ADR-018, ADR-019). `apps/api/pyproject.toml` resolves with `exclude-newer = 2026-10-19T00:00:00Z`. Release dates and vulnerabilities were checked on PyPI and OSV on 2026-10-27.

## Options

1. **PyJWT 2.15.1 without the `[crypto]` extra + argon2-cffi 25.1.0 (chosen).**
   - PyJWT: the most widely used Python JWT library. HS256 uses only the standard library. It has an explicit `algorithms=` allow-list and required-claim options, and no dependencies on Python 3.13.
   - argon2-cffi: binds the reference Argon2 C code and releases the GIL. Its `PasswordHasher` takes explicit parameters and has `check_needs_rehash`.
   - Runtime transitive dependencies: argon2-cffi-bindings 26.1.0 (abi3 manylinux wheel), cffi 2.1.1 and pycparser 3.11.
   - Release dates: PyJWT 2.15.1 on 2026-09-28; argon2-cffi 25.1.0 on 2025-06-03; argon2-cffi-bindings 26.1.0 on 2026-08-20; cffi 2.1.1 on 2026-08-03; pycparser 3.11 on 2026-10-09. All are before the cutoff.
   - OSV lists no vulnerabilities for any of them.
   - Cons: native-adjacent packages (cffi, the bindings) in the runtime image.
2. **joserfc.** A modern JOSE library. Lost:
   - it always pulls in `cryptography`, a large native package;
   - its current release, 1.7.7, was uploaded on 2026-10-19 at 00:30 UTC, after the `exclude-newer` cutoff of 2026-10-19 00:00, so the lock would resolve 1.7.6 instead, and taking 1.7.7 would mean moving the cutoff.
3. **pwdlib 0.3.1 over argon2-cffi.** Lost: a wrapper layer with no benefit for one algorithm.
4. **passlib, python-jose, Authlib, fastapi-users.** passlib is unmaintained and breaks with bcrypt 4.1+. python-jose is stale, with a CVE history. Authlib and fastapi-users bring framework weight the cards do not need.
5. **No new dependencies: a hand-written HS256 JWT with `hmac`/`hashlib`, and `hashlib.scrypt`.** Lost: header, base64url and claim edge cases are exactly where JWT bugs live. We would own the scrypt parameter encoding. argon2id is OWASP's first choice and ADR-014's decision.

## Decision

Add `pyjwt>=2.15.1,<3` (no extras) and `argon2-cffi>=25.1.0,<26` to the runtime `dependencies` of `apps/api`, pinned in `apps/api/uv.lock` under the existing `exclude-newer` cutoff.

### Rules

- Tokens are verified only through `jwt.decode` with `algorithms=["HS256"]`, the expected `audience` and `issuer`, and `options={"require": ["exp", "iat", "iss", "aud", "sub", "kind", "jti"]}`.
- `kid` and `typ` are read with `jwt.get_unverified_header` only to pick the key by exact `kid` match and to check `typ == "at+jwt"`, never to choose the algorithm.
- Passwords are hashed only through `argon2.PasswordHasher` built with the ADR-014 parameters (`type=Type.ID`), behind the ADR-014 semaphore.
- No other module of either package is used without a new ADR.

## Consequences

- Easier: one small, well-known library per concern. Neither pulls in `cryptography`.
- Harder: five more runtime packages in pip-audit's scope (pyjwt, argon2-cffi, argon2-cffi-bindings, cffi, pycparser). Bumps follow ADR-018 and ADR-019: their own PR, a release at least 7 days old, release notes linked, security-engineer review.
- We will monitor: pip-audit and OSV findings for these packages, and PyJWT changes to algorithm or claim validation defaults in release notes.
- Revisit when: ADR-014 moves to an asymmetric algorithm (PyJWT `[crypto]` or joserfc), a package is unmaintained for 12 months or has an unfixed advisory, or a free-threaded Python build needs different wheels.
