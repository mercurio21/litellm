# mercurio21 fork: official LiteLLM image + our patched source files on top.
# This branch is based on the upstream release tag below; the two patched
# files are taken from the same tag, so they match the installed package.
# No patch logic lives here — all behaviour changes are commits in the tree.
# To upgrade: rebase the fork on the new tag, bump LITELLM_TAG + digest below.
ARG LITELLM_TAG=v1.110.0-rc.2
FROM ghcr.io/berriai/litellm:${LITELLM_TAG}@sha256:56310c2bd785547a370778a9dc8bee7fdb606c3f4f855b36fb4b4c85eb1329c5

USER root

ARG SP=/app/.venv/lib/python3.13/site-packages
COPY litellm/proxy/auth/litellm_license.py ${SP}/litellm/proxy/auth/litellm_license.py
COPY litellm/proxy/management_endpoints/model_management_endpoints.py ${SP}/litellm/proxy/management_endpoints/model_management_endpoints.py

COPY config.yaml /app/config.yaml
COPY anthropic_oauth_identity.py /app/anthropic_oauth_identity.py

# Fail the build if the overlay does not import against the base image.
RUN python -c "import litellm.proxy.proxy_server, litellm.proxy.auth.litellm_license as l; assert l.LicenseCheck().is_premium() is True"

USER 65532:0

# Entrypoint runs plain `litellm` unless given args; load our config explicitly.
CMD ["--config", "/app/config.yaml"]
