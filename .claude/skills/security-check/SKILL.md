---
name: security-check
description: Security review checklist for a diff or feature — OWASP API Top 10, secrets, media, prompt injection, dependencies, mobile storage and store privacy. Use on PRs touching auth, media, prompts, secrets, dependencies or infra.
---

# Security check

Go through each item that applies to the diff. Report findings with severity, location, exploit scenario and fix.

**API**
- Every endpoint requires auth unless the contract says otherwise.
- Object-level authorisation: a user can only reach their own consultations, media and profile.
- All input validated (types, lengths, ranges, enums); no mass assignment.
- Rate limits on auth, upload and generation endpoints.
- No SSRF: outgoing URLs come from an allow-list.

**Secrets**
- `gitleaks` clean on the diff and history; nothing in images, logs or the mobile bundle.

**Media**
- Size and type limits enforced server-side; EXIF stripped; files deleted after processing (TTL); never logged or traced.

**LLM**
- Untrusted text (user, web, product feeds) is delimited as data and cannot change tool use.
- Model output is validated before it is stored, shown or used for links and prices.

**Dependencies**
- `npm audit --audit-level=high` clean; `pip-audit` clean of any known vulnerability, or an `--ignore-vuln <ID>` line with reason and review date (ADR-019).
- Bumps (ADR-018, ADR-019): each in its own PR with release notes linked and a security-engineer review; releases ≥ 7 days old — images and actions pinned by tag + digest/SHA, Python/npm packages by lockfile with `exclude-newer`; only vendor security releases of runtime images skip the wait, after security-engineer reads the notes. The `litellm` PyPI package is never a direct or transitive dependency (ADR-010).

**Mobile**
- Tokens only in SecureStore; certificate pinning for the API; permissions requested at use with a reason.
- Privacy manifest (iOS) and Data safety (Google Play) match what the app actually collects.

**GDPR**
- Personal data minimised; deletion of account and data works end to end.
