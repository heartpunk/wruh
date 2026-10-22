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
