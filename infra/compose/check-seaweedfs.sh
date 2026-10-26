#!/usr/bin/env bash
# Checks that the running stack's SeaweedFS is not open to other containers (ADR-008, E0-07):
#   1. only the S3 API (8333) and S3 gRPC (18333) listen beyond the container's loopback;
#   2. the S3 IAM gRPC service rejects calls without a valid JWT (GHSA-5fx4-c9qp-36jc);
#   3. S3 rejects unsigned requests and wrong secrets, and accepts the configured identity.
# Probes run from throwaway containers on the internal `backend` network, like a compromised
# neighbour would. Run from the repo root after `make up`: bash infra/compose/check-seaweedfs.sh
#
# grpcurl is used only by this check, never by the stack. v1.9.3 is the newest image the project
# publishes (2025-03-11); it runs for one call on the internal network and gets no secrets.
set -euo pipefail
export MSYS_NO_PATHCONV=1 # Git Bash: keep container paths as they are

GRPCURL=fullstorydev/grpcurl:v1.9.3@sha256:085e183ca334eb4e81ca81ee12cbb2b2737505d1d77f5e33dabc5d066593d998
COMPOSE=(docker compose --project-name capsule --env-file .env -f infra/compose/compose.base.yml)
NETWORK=capsule_backend
status=0

pass() { echo "ok   $1"; }
fail() { echo "FAIL $1" >&2; status=1; }

container=$("${COMPOSE[@]}" ps --quiet seaweedfs)
[ -n "$container" ] || { echo "check-seaweedfs: seaweedfs is not running; run make up" >&2; exit 1; }
image=$(docker inspect --format '{{.Config.Image}}' "$container")
# Same precedence as Compose: values exported in the shell win over .env.
shell_key=${SEAWEEDFS_S3_ACCESS_KEY-} shell_secret=${SEAWEEDFS_S3_SECRET_KEY-}
set -a
# shellcheck disable=SC1091
. ./.env
set +a
[ -z "$shell_key" ] || SEAWEEDFS_S3_ACCESS_KEY=$shell_key
[ -z "$shell_secret" ] || SEAWEEDFS_S3_SECRET_KEY=$shell_secret

# 1. Listeners. Allowed beyond loopback: 8333 and 18333. 127.0.0.11 is Docker's embedded DNS.
exposed=$(docker exec "$container" netstat -tln |
  awk 'NR > 2 { print $4 }' | { grep -Ev '^127\.0\.0\.(1|11):' || true; } | sort -u | tr '\n' ' ')
unexpected=$(tr ' ' '\n' <<<"$exposed" | grep -Ev '^$|:(8333|18333)$' || true)
if [ -n "$unexpected" ]; then
  fail "unexpected listeners: $(tr '\n' ' ' <<<"$unexpected")"
elif ! grep -Eq ':8333( |$)' <<<"$exposed"; then
  fail "S3 API (8333) does not listen beyond loopback: '${exposed% }'"
else
  pass "listeners beyond loopback: ${exposed% }"
fi

# 2. IAM gRPC without a token, and with a forged one.
grpc() { # extra grpcurl args...
  docker run --rm --network "$NETWORK" "$GRPCURL" -plaintext "$@" \
    -d '{"identity":{"name":"check-intruder","actions":["Admin"]}}' \
    seaweedfs:18333 messaging_pb.SeaweedS3IamCache/PutIdentity 2>&1 || true
}
out=$(grpc)
if grep -q 'Code: Unauthenticated' <<<"$out"; then pass "anonymous PutIdentity: Unauthenticated"; else
  fail "anonymous PutIdentity was not rejected: $(tr '\n' ' ' <<<"$out")"; fi
out=$(grpc -H 'authorization: Bearer eyJhbGciOiJIUzI1NiJ9.e30.Zm9yZ2Vk')
if grep -q 'Code: Unauthenticated' <<<"$out"; then pass "forged-token PutIdentity: Unauthenticated"; else
  fail "forged-token PutIdentity was not rejected: $(tr '\n' ' ' <<<"$out")"; fi

# 3. S3 signatures. Credentials reach the probe as environment variables, not command-line text.
s3() { # expected status, description, credentials: none | wrong | configured
  local want=$1 what=$2 creds=$3 got
  got=$(docker run --rm --network "$NETWORK" -e SEAWEEDFS_S3_ACCESS_KEY -e SEAWEEDFS_S3_SECRET_KEY \
    -e CREDS="$creds" --entrypoint sh "$image" -c '
      case $CREDS in
        none) set -- ;;
        wrong) set -- --aws-sigv4 aws:amz:us-east-1:s3 --user "$SEAWEEDFS_S3_ACCESS_KEY:wrong" ;;
        *) set -- --aws-sigv4 aws:amz:us-east-1:s3 \
             --user "$SEAWEEDFS_S3_ACCESS_KEY:$SEAWEEDFS_S3_SECRET_KEY" ;;
      esac
      curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$@" http://seaweedfs:8333/' || true)
  if [ "$got" = "$want" ]; then pass "$what: $got"; else fail "$what: got $got, want $want"; fi
}
s3 403 "unsigned ListBuckets" none
s3 403 "wrong-secret ListBuckets" wrong
s3 200 "signed ListBuckets" configured

exit "$status"
