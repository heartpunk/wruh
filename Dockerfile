FROM ubuntu:24.04 AS tools
RUN apt-get update && apt-get install -y --no-install-recommends \
      bash ca-certificates curl git nix-bin xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && userdel ubuntu \
    && useradd --uid 1000 --create-home --shell /bin/bash wruh \
    && mkdir -p /nix /workspace /etc/nix \
    && chown -R wruh:wruh /nix /workspace \
    && printf '%s\n' 'sandbox = false' 'build-users-group =' > /etc/nix/nix.conf
# Single-user Nix works without systemd, a host daemon, or privileged containers.
ENV USER=wruh HOME=/home/wruh NIX_REMOTE=local
COPY nix/cache.conf /etc/nix/wruh-cache.conf
RUN printf '%s\n' 'include /etc/nix/wruh-cache.conf' >> /etc/nix/nix.conf
USER wruh
WORKDIR /workspace
RUN nix-store --init
CMD ["bash"]

FROM tools AS source
# Build context is one clean WRUH clone, including usable Git metadata.
COPY --chown=wruh:wruh . /workspace
CMD ["bash", "--noprofile", "--norc"]

FROM source AS buildbuddy-rbe
# Remote actions use the same pinned Nix Python and native-library closure as
# the GitHub Actions Bazel client. Realize it into the image so Bazel can send
# those actions to BuildBuddy without rebuilding or downloading Nix at runtime.
RUN nix develop .#buildbuddyRbe --no-write-lock-file --command bash -euo pipefail -c \
      'python3.12 --version && python3.12 -c "import angr, z3"'
# BuildBuddy actions need to write into the executor-provided workspace.
USER root

# Keep the developer image as the default for existing `docker build .` callers.
FROM source
