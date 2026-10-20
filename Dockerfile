FROM ubuntu:24.04 AS tools
RUN apt-get update && apt-get install -y --no-install-recommends \
      bash ca-certificates curl git nix-bin xz-utils \
    && rm -rf /var/lib/apt/lists/* \
    && userdel ubuntu \
    && useradd --uid 1000 --create-home --shell /bin/bash wruh \
    && mkdir -p /nix /workspace \
    && chown -R wruh:wruh /nix /workspace
# Single-user Nix works without systemd, a host daemon, or privileged containers.
ENV USER=wruh HOME=/home/wruh NIX_REMOTE=local
ENV NIX_CONFIG="sandbox = false
build-users-group ="
USER wruh
WORKDIR /workspace
RUN nix-store --init
CMD ["bash"]

FROM tools AS ready
# Build context is one clean WRUH clone, including usable Git metadata.
COPY --chown=wruh:wruh . /workspace
RUN ./scripts/bootstrap
ENTRYPOINT ["/workspace/scripts/wruh-env"]
CMD ["bash", "--noprofile", "--norc"]
