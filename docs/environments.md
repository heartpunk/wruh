# WRUH environments

The image contains Nix, public Cachix configuration, and a writable WRUH source
checkout. Dependencies and Lean objects are downloaded or built **after startup**
by `scripts/bootstrap`, using the existing `flake.nix` and `flake.lock`.
The host needs Docker only; first setup needs network access.

```sh
docker run --name wruh-work -it ghcr.io/heartpunk/wruh-dev:latest
# Inside the container:
./scripts/bootstrap
./scripts/wruh-env bash
```

Resume the same prepared container with `docker start -ai wruh-work`.
Its writable filesystem retains the Nix store, Lean objects, and your edits.
Removing the container removes that state; push changes before removing it.
Run commands through `./scripts/wruh-env COMMAND ...` after setup, and rerun
bootstrap after changing dependency pins.

The default user is `wruh` (UID 1000). Nix runs locally inside the container;
no host Nix store, daemon socket, or privileged mode is needed.
Agent CLIs can be installed inside it; supply authentication at runtime.

## Build locally

Use a standalone Git clone (including `.git`), then run:

```sh
docker build -t ghcr.io/heartpunk/wruh-dev:latest .
docker compose run --rm dev
```

The `tools` Dockerfile target provides Ubuntu and usable Nix without copying
a checkout. Providers that manage their own checkout can use that target and
run the same bootstrap afterward. The default `source` target includes WRUH source without prebuilt dependencies.

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
