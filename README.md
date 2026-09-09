# rucio-clients-gluex

Build repo that produces the **GlueX build of the Rucio client** and publishes it
to the GlueX package index. It does **not** fork Rucio: it pins an upstream
`rucio-clients` release from PyPI, applies GlueX patches, renames the
distribution, adds GlueX-specific dependencies, and rebuilds the wheel.

- Published distribution: **`rucio-clients-gluex`**
- Import name (unchanged): **`rucio`** — code keeps doing `import rucio`
- Version: **`<upstream>.post<build-number>`**, e.g. `41.2.2.post1`
  (PEP 440 forbids free text like "gluex" in a version, so the name carries the
  GlueX identity and the version stays a clean post-release of upstream)
- Extra deps baked in: **`pyjwt`** (edit the list in `pyproject.toml`)
- Managed with **uv**; everything is driven from `pyproject.toml`.

## Layout

```
pyproject.toml              # uv harness: pinned upstream, build number, dist name, extra deps
scripts/build.py            # download upstream sdist -> patch -> rebrand -> stamp -> uv build
patches/                    # 0001-*.patch, 0002-*.patch ... (applied in order)
.github/workflows/build.yml # build on dispatch; build + publish on a v* tag
dist/                       # build output (gitignored)
```

## Configure

Everything lives in `pyproject.toml` under `[tool.gluex-rucio]`:

```toml
[tool.gluex-rucio]
upstream-version = "41.2.2"          # which rucio-clients to base on
build-number = 1                     # -> version 41.2.2.post1
distribution-name = "rucio-clients-gluex"
extra-dependencies = ["pyjwt>=2.0.0"]  # add more here as needed
```

## Build locally

```bash
uv run scripts/build.py
# -> dist/rucio_clients_gluex-41.2.2.post1-py3-none-any.whl (+ .tar.gz)
```

## Patches

See `patches/README.md`. Clone `rucio/rucio` at the pinned tag, edit under
`lib/rucio/...`, `git diff > patches/000N-thing.patch`, then bump `build-number`.

## Track a new upstream release

Set `upstream-version` to the new value and reset `build-number = 1`. Rebuild and
fix any patch that no longer applies.

## Publish (GitHub Actions -> GlueX PyPI)

One-time setup in the repo (**Settings -> Secrets and variables -> Actions**):

- Variable `GLUEX_PYPI_PUBLISH_URL` = your index's upload endpoint
  (e.g. `https://pypi.gluex.example/legacy/` for a Warehouse/devpi, or your
  Artifactory PyPI upload URL).
- Secret `GLUEX_PYPI_USERNAME` and `GLUEX_PYPI_PASSWORD`.
  For token auth, set username to `__token__` and password to the token.

Then cut a release by tagging (keep the tag in step with the config):

```bash
git commit -am "gluex build 1 on rucio-clients 41.2.2"
git tag v41.2.2-gluex.1
git push --tags
```

The workflow builds and runs `uv publish` to your index. `workflow_dispatch`
(the Actions "Run workflow" button) builds without publishing.

## Install (consumers)

Point pip/uv at the GlueX index and install by name:

```bash
uv pip install --index-url https://pypi.gluex.example/simple/ rucio-clients-gluex
```

Or in a consuming project's `pyproject.toml`:

```toml
[project]
dependencies = ["rucio-clients-gluex"]

[[tool.uv.index]]
name = "gluex"
url = "https://pypi.gluex.example/simple/"
```

Don't install `rucio-clients-gluex` alongside stock `rucio-clients`: both provide
the `rucio` import and would clobber each other.
