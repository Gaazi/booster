"""Package and verify compressed distributions tied to an exact Git commit."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def check_sha(sha: str) -> str:
    """Accept only a full lowercase Git commit identifier."""
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("A full Git commit SHA is required")
    return sha


def package_kind(name: str) -> str:
    """Reject unsafe names and identify the three expected distributions."""
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        raise ValueError("Unsafe distribution filename")
    if name.startswith("booster-") and name.endswith(".whl"):
        return "wheel"
    if name.startswith("booster-") and name.endswith(".tar.gz"):
        return "source"
    if name.startswith("booster-node-") and name.endswith(".tgz"):
        return "node"
    raise ValueError("Unexpected distribution filename")


def check_packages(names: list[str]) -> None:
    """Require exactly one wheel, source distribution and Node archive."""
    if len(names) != 3 or {package_kind(name) for name in names} != {
        "wheel", "source", "node"
    }:
        raise ValueError("Expected one Python wheel, Python source and Node package")


def create_bundle(directory: Path, sha: str) -> Path:
    """Create a compressed download containing distributions and their hashes."""
    check_sha(sha)
    packages = sorted(path for path in directory.iterdir() if path.is_file())
    check_packages([path.name for path in packages])
    hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in packages}
    manifest = {"schema": 1, "commit": sha, "sha256": hashes}
    target = directory.parent / f"booster-{sha}.zip"
    with ZipFile(target, "x", compression=ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
        for path in packages:
            archive.write(path, path.name)
    verify_bundle(target, sha)
    return target


def read_manifest(archive: ZipFile, sha: str) -> dict[str, str]:
    """Validate commit provenance and the archive's complete file inventory."""
    names = archive.namelist()
    if len(names) != 4 or len(set(names)) != 4 or "manifest.json" not in names:
        raise ValueError("Unexpected or duplicate archive members")
    if any(item.file_size > 64 * 1024 * 1024 for item in archive.infolist()):
        raise ValueError("Archive member exceeds the verification size limit")
    manifest = json.loads(archive.read("manifest.json"))
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        raise ValueError("Unsupported build manifest")
    if manifest.get("commit") != check_sha(sha):
        raise ValueError("Build commit does not match the requested commit")
    hashes = manifest.get("sha256")
    if not isinstance(hashes, dict):
        raise ValueError("Missing distribution checksums")
    check_packages(list(hashes))
    if set(names) != {"manifest.json", *hashes}:
        raise ValueError("Archive files differ from the manifest")
    return hashes


def verify_bundle(bundle: Path, sha: str, destination: Path | None = None) -> None:
    """Check every package hash before optionally writing verified files."""
    with ZipFile(bundle) as archive:
        hashes = read_manifest(archive, sha)
        payloads = {name: archive.read(name) for name in hashes}
    for name, payload in payloads.items():
        if hashlib.sha256(payload).hexdigest() != hashes[name]:
            raise ValueError(f"Distribution checksum mismatch: {name}")
    if destination is not None:
        destination.mkdir(parents=True, exist_ok=False)
        for name, payload in payloads.items():
            with (destination / name).open("xb") as output:
                output.write(payload)


def main() -> None:
    """Create a bundle or verify a downloaded build from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--extract-to", type=Path)
    args = parser.parse_args()
    if args.action == "create":
        print(create_bundle(args.path, args.sha))
    else:
        verify_bundle(args.path, args.sha, args.extract_to)
        print(f"Verified compressed build for {args.sha}")


if __name__ == "__main__":
    main()
