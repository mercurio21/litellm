# mercurio21 fork — overlay our 2-line Team BYOK patch and config onto the
# official published image instead of rebuilding litellm from source
# (rebuilding from source takes 15-20 min and is flaky on apk mirrors here;
# this build takes seconds).
FROM ghcr.io/berriai/litellm:main-stable

USER root

# Patch: unlock Team BYOK (per-team model/credential) without an Enterprise
# license. See litellm/proxy/management_endpoints/model_management_endpoints.py
# in this repo for the annotated source of truth; this script mirrors that
# diff onto the installed package inside the image.
RUN set -eu; \
    f=$(python -c "import os, litellm; print(os.path.join(os.path.dirname(litellm.__file__), 'proxy/management_endpoints/model_management_endpoints.py'))"); \
    python - "$f" <<'EOF'
import re, sys
path = sys.argv[1]
src = open(path).read()

pattern_a = re.compile(
    r'if premium_user is False:\s*\n\s*raise HTTPException\(\s*\n\s*status_code=403,\s*\n\s*detail=\{"error": CommonProxyErrors\.not_premium_user\.value\},\s*\n\s*\)\s*\n'
)
pattern_b = re.compile(
    r'if model_params\.model_info\.team_id is not None and premium_user is not True:\s*\n\s*raise HTTPException\(\s*\n\s*status_code=403,\s*\n\s*detail=\{"error": CommonProxyErrors\.not_premium_user\.value\},\s*\n\s*\)\s*\n'
)

new_src, n1 = pattern_a.subn('', src, count=1)
new_src, n2 = pattern_b.subn('', new_src, count=1)

if n1 != 1 or n2 != 1:
    sys.stderr.write(f"mercurio21 patch FAILED to match (gate_a={n1}, gate_b={n2}) — upstream source changed, update the patch\n")
    sys.exit(1)

open(path, 'w').write(new_src)
sys.stderr.write("mercurio21 Team BYOK patch applied OK\n")
EOF

COPY config.yaml /app/config.yaml
COPY anthropic_oauth_identity.py /app/anthropic_oauth_identity.py

USER 65532:0
