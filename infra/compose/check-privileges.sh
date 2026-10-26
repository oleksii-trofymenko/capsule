#!/usr/bin/env bash
# Fails when a Compose service could run with more privilege than E0-12 allows. For every service
# in compose.base.yml, alone and with the compose.test.yml overlay, the resolved config must have:
# a non-root `user`, `cap_drop` containing ALL, no `cap_add`, and `no-new-privileges:true`.
# Called by check-pins.sh (CI lint job). Run from the repo root. Needs docker compose and python3.
set -euo pipefail

dir=infra/compose
status=0

for overlay in "" "$dir/compose.test.yml"; do
  files=(-f "$dir/compose.base.yml")
  [ -z "$overlay" ] || files+=(-f "$overlay")
  label="compose.base.yml${overlay:+ + ${overlay##*/}}"
  # test.env holds test-only values; they only satisfy the required variables.
  docker compose --env-file "$dir/test.env" "${files[@]}" config --format json |
    python3 -I -c '
import json, sys
label, bad = sys.argv[1], 0
for name, svc in sorted(json.load(sys.stdin)["services"].items()):
    problems, user = [], str(svc.get("user", ""))
    uid = user.split(":")[0]
    if uid in ("", "0", "root"):
        problems.append("user is root or unset")
    if "ALL" not in [c.upper() for c in svc.get("cap_drop") or []]:
        problems.append("cap_drop lacks ALL")
    if svc.get("cap_add"):
        problems.append("cap_add " + ",".join(svc["cap_add"]))
    if "no-new-privileges:true" not in (svc.get("security_opt") or []):
        problems.append("no no-new-privileges:true")
    if problems:
        bad = 1
        print(f"check-privileges: {label}: {name}: " + "; ".join(problems), file=sys.stderr)
    else:
        print(f"check-privileges: {label}: {name} ok (user {user})")
sys.exit(bad)
' "$label" || status=1
done

exit "$status"
