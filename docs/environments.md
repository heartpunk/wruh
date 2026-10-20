# WRUH environments

The Docker image includes Nix, a writable WRUH checkout, and compiled Lean
objects. The host needs Docker only. The development shell and dependency
versions come from the repository's existing `flake.nix` and `flake.lock`.

```sh
docker run --rm -it ghcr.io/heartpunk/wruh-dev:latest
# Or run a command directly:
docker run --rm ghcr.io/heartpunk/wruh-dev:latest python3 -c 'import angr'
```

The default user is `wruh` (UID 1000). Nix runs locally inside the container;
no host Nix store, daemon socket, or privileged mode is needed. Work in a named
container to retain edits between sessions, and push changes before removing it.
Agent CLIs can be installed inside it; supply their authentication at runtime.

## Build locally

Use a standalone Git clone (including `.git`), then run:

```sh
docker build -t ghcr.io/heartpunk/wruh-dev:latest .
docker compose run --rm dev
```

The `tools` Dockerfile target provides Ubuntu and usable Nix without copying
a checkout. Providers that manage their own checkout can use that target and
run the same bootstrap afterward. The default `ready` target includes WRUH.

## Hosted agents

In a provider-managed WRUH checkout, configure setup to run `./scripts/bootstrap`.
It installs Nix on Ubuntu if needed, enables the public WRUH/IFRL/AYXG Cachix
caches, downloads the Lake cache, and runs the ordinary project build. Commands
then run through `./scripts/wruh-env COMMAND ...`; environment activation does
not depend on shell exports surviving setup. Re-run bootstrap after pin changes.

- Codex: use bootstrap in the environment install script and publish the prepared
  filesystem. Put the command wrapper in project agent instructions.
- Claude Code: use bootstrap during environment setup. Its hosted image cannot
  be replaced; setup caching has a roughly five-minute budget. Measure cold
  setup before relying on it; a Nix cache miss may exceed that budget.
- Cursor: use the `tools` target or its supplied Ubuntu image, and run bootstrap
  as the install command after Cursor checks out the task's revision.

Allow HTTPS access to GitHub, the three Cachix caches, cache.nixos.org, and the
Lake cache endpoints. A GitHub connection alone does not grant access to private
transitive dependencies. Never embed credentials in an image.

Provider recipes describe the supported integration points; verify bootstrap in
an actual provider environment before declaring that provider validated.
