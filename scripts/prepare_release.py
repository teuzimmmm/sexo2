"""Restore build-only binaries from our previous release; never overwrite source plugins."""

import argparse, json, os, re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("--base", required=True)
p.add_argument("--version", required=True)
a = p.parse_args()
version = a.version.removeprefix("v")
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    raise SystemExit("Invalid release version")
from restore_build_binaries import restore

restore(Path(a.base))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

key = bytes.fromhex(os.environ["SEXO2_SIGNING_KEY_HEX"])
pub = Ed25519PrivateKey.from_private_bytes(key).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
Path("sexo2/update/trust.py").write_text("PUBLIC_KEY = bytes.fromhex(" + repr(pub.hex()) + ")\n", encoding="utf-8")
repo = os.environ["GITHUB_REPOSITORY"]
Path("assets/update-source.json").write_text(
    json.dumps({"repository": repo, "channel": "stable", "private": True}), encoding="utf-8"
)
token = os.environ.get("SEXO2_DOWNLOAD_TOKEN", "")
if token:
    Path("assets/update-access.json").write_text(json.dumps({"token": token}), encoding="utf-8")
p = Path("sexo2/version.py")
s = p.read_text(encoding="utf-8")
s = re.sub(r"RELEASE_VERSION = (['\"])[^'\"]+\1", 'RELEASE_VERSION = "' + version + '"', s)
p.write_text(s, encoding="utf-8")
p = Path("assets/sexo2-version.txt")
s = p.read_text(encoding="utf-8")
s = re.sub(r"(filevers|prodvers)=\([^)]*\)", lambda m: m.group(1) + "=(" + version.replace(".", ",") + ",0)", s)
s = re.sub(
    r"(StringStruct\('(?:FileVersion|ProductVersion)',')[^']+('\))",
    lambda m: m.group(1) + version + ".0" + m.group(2),
    s,
)
p.write_text(s, encoding="utf-8")
p = Path("installer-sexo2.iss")
b = p.read_bytes()
b = re.sub(rb'#define MyAppVersion "[^"]*"', ('#define MyAppVersion "' + version + '.0"').encode(), b)
p.write_bytes(b)
