#!/usr/bin/env python3
"""Build the GlueX rucio-clients wheel (published as `rucio-clients-gluex`).

Steps:
  1. read config from pyproject.toml ([tool.gluex-rucio])
  2. download the matching upstream rucio-clients *source* dist from PyPI
  3. verify its sha256 against PyPI's recorded digest
  4. apply every patch in ./patches (sorted by filename)
  5. rewrite the distribution name and add extra dependencies
  6. stamp lib/rucio/vcsversion.py with <upstream>.post<build-number>
  7. rebuild wheel + sdist with `uv build` into ./dist

Requires only the standard library plus `uv` and `patch` on PATH.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATCHES = ROOT / "patches"
DIST = ROOT / "dist"
WORK = ROOT / ".work"
UPSTREAM_NAME = "rucio-clients"


def read_config() -> dict:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    return data["tool"]["gluex-rucio"]


def find_sdist(version: str) -> tuple[str, str]:
    url = f"https://pypi.org/pypi/{UPSTREAM_NAME}/{version}/json"
    with urllib.request.urlopen(url) as resp:
        meta = json.load(resp)
    for f in meta["urls"]:
        if f["packagetype"] == "sdist":
            return f["url"], f["digests"]["sha256"]
    raise SystemExit(f"no sdist published for {UPSTREAM_NAME} {version}")


def download(url: str, sha256: str, dest: Path) -> None:
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    got = hashlib.sha256(data).hexdigest()
    if got != sha256:
        raise SystemExit(f"sha256 mismatch for {url}\n  expected {sha256}\n  got      {got}")
    dest.write_bytes(data)


def extract(tarball: Path, into: Path) -> Path:
    with tarfile.open(tarball) as tf:
        try:
            tf.extractall(into, filter="data")  # py3.12+ (and 3.11.4+)
        except TypeError:
            tf.extractall(into)
    return next(p for p in into.iterdir() if p.is_dir() and p.name.startswith("rucio_clients-"))


def apply_patches(src: Path) -> None:
    patches = sorted(PATCHES.glob("*.patch"))
    if not patches:
        print("==> no patches found — rebuilding upstream unchanged (except name/deps/version)")
        return
    for p in patches:
        print(f"==> applying {p.name}")
        subprocess.run(["patch", "-p1", "-i", str(p)], cwd=src, check=True)


def rebrand(src: Path, dist_name: str, extra_deps: list[str]) -> None:
    pp = src / "pyproject.toml"
    text = pp.read_text()

    text, n = re.subn(r'(?m)^name = "rucio-clients"[ \t]*$', f'name = "{dist_name}"', text)
    if n != 1:
        raise SystemExit(f"expected exactly one project name line, replaced {n}")

    if extra_deps:
        inject = "".join(f"        '{d}',\n" for d in extra_deps)
        text, n = re.subn(r'(?m)^dependencies = \[[ \t]*\n',
                          lambda m: m.group(0) + inject, text, count=1)
        if n != 1:
            raise SystemExit(f"could not locate the dependencies array (matched {n})")

    pp.write_text(text)
    print(f"==> distribution renamed to {dist_name}")
    if extra_deps:
        print(f"==> added dependencies: {', '.join(extra_deps)}")


def stamp_version(src: Path, version: str) -> None:
    vcs = src / "lib" / "rucio" / "vcsversion.py"
    text = vcs.read_text()
    new, n = re.subn(r"^VERSION = .*$", f"VERSION = '{version}'", text, flags=re.M)
    if n != 1:
        raise SystemExit(f"expected exactly one VERSION line in {vcs}, replaced {n}")
    vcs.write_text(new)
    print(f"==> stamped VERSION = {version}")


def main() -> None:
    cfg = read_config()
    upstream = str(cfg["upstream-version"])
    build_no = int(cfg["build-number"])
    dist_name = str(cfg["distribution-name"])
    extra_deps = list(cfg.get("extra-dependencies", []))
    version = f"{upstream}.post{build_no}"

    print(f"==> {dist_name} {version}  (upstream rucio-clients {upstream})")

    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    DIST.mkdir(exist_ok=True)

    url, sha = find_sdist(upstream)
    tarball = WORK / "upstream.tar.gz"
    print(f"==> downloading {url}")
    download(url, sha, tarball)

    src = extract(tarball, WORK)
    print(f"==> source tree: {src.name}")

    apply_patches(src)
    rebrand(src, dist_name, extra_deps)
    stamp_version(src, version)

    print("==> building with uv")
    subprocess.run(["uv", "build", "--out-dir", str(DIST), str(src)], check=True)

    print("==> artifacts in dist/:")
    artifacts = sorted(p for p in DIST.iterdir() if p.suffix in {".whl", ".gz"})
    for f in artifacts:
        print("   ", f.name)
    if not artifacts:
        raise SystemExit("build produced no artifacts")


if __name__ == "__main__":
    sys.exit(main())
