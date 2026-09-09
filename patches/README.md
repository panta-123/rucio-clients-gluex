# GlueX patches

Every `*.patch` in this directory is applied (in filename order) to the upstream
`rucio-clients` source tree before the wheel is rebuilt. Name them with a numeric
prefix so the order is deterministic, e.g. `0001-…`, `0002-…`.

Patches are applied with `patch -p1` from the root of the extracted source tree,
so use `a/` `b/` prefixes — i.e. plain `git diff` output.

## Authoring a patch against the pinned version

```bash
# match the version pinned in ../pyproject.toml ([tool.gluex-rucio] upstream-version)
git clone https://github.com/rucio/rucio
cd rucio
git checkout 41.2.2

# edit files under lib/rucio/... (this is the same layout as the client sdist)
$EDITOR lib/rucio/common/config.py

git diff > ../patches/0001-gluex-config-defaults.patch
```

## When you bump `upstream-version`

Re-check that each patch still applies. If one is rejected, recreate it against
the new tag (same recipe as above) and bump `build-number` in `../pyproject.toml`.
