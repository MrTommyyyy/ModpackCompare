"""Offline Minecraft JAR inventory and comparison. Python 3.11+."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

VERSION = "0.2.0"
FORMAT = "modpack-compare/v1"


def snapshot(folder: Path, recursive: bool = False) -> dict:
    folder = folder.resolve()
    if not folder.is_dir():
        raise ValueError("Choose an existing mods directory.")
    candidates = folder.rglob("*") if recursive else folder.iterdir()
    files = []
    for path in sorted(candidates):
        if path.suffix.lower() != ".jar" or not path.is_file():
            continue
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != folder):
            raise ValueError(f"Symbolic links are not supported: {path.name}")
        before = path.stat()
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        after = path.stat()
        keys = ("st_size", "st_mtime_ns", "st_ino", "st_dev")
        if any(getattr(before, key) != getattr(after, key) for key in keys):
            raise ValueError(f"File changed during the scan: {path.name}. Retry after downloads finish.")
        files.append({"path": path.relative_to(folder).as_posix(),
                      "size": after.st_size, "sha256": digest.hexdigest()})
    return {"format": FORMAT, "files": files}


def validate_manifest(data: object) -> dict:
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise ValueError("Unsupported manifest format.")
    if not isinstance(data.get("files"), list):
        raise ValueError("Manifest files must be a list.")
    seen = set()
    for item in data["files"]:
        if not isinstance(item, dict):
            raise ValueError("Each manifest entry must be an object.")
        path, size, digest = item.get("path"), item.get("size"), item.get("sha256")
        if (not isinstance(path, str) or not path or path.startswith("/")
                or "\\" in path or ":" in path
                or any(part in ("", ".", "..") for part in path.split("/"))):
            raise ValueError("Manifest paths must be portable relative paths.")
        if path in seen:
            raise ValueError(f"Duplicate manifest path: {path}")
        seen.add(path)
        if type(size) is not int or size < 0:
            raise ValueError(f"Invalid size for {path}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Invalid SHA-256 for {path}")
    return data


def load_manifest(path: Path) -> dict:
    with path.open(encoding="utf-8") as stream:
        return validate_manifest(json.load(stream))


def compare(old: dict, new: dict) -> dict:
    validate_manifest(old)
    validate_manifest(new)
    left = {item["path"]: item for item in old["files"]}
    right = {item["path"]: item for item in new["files"]}
    removed, added = set(left) - set(right), set(right) - set(left)
    renamed = []
    # A rename is reported only when the content match is unambiguous.
    for digest in sorted({left[p]["sha256"] for p in removed}):
        sources = [p for p in removed if left[p]["sha256"] == digest]
        targets = [p for p in added if right[p]["sha256"] == digest]
        if len(sources) == len(targets) == 1 and left[sources[0]]["size"] == right[targets[0]]["size"]:
            renamed.append({"from": sources[0], "to": targets[0]})
            removed.remove(sources[0])
            added.remove(targets[0])
    common = set(left) & set(right)
    unchanged = [p for p in common if (left[p]["sha256"], left[p]["size"]) ==
                 (right[p]["sha256"], right[p]["size"])]
    return {"added": sorted(added), "removed": sorted(removed),
            "changed": sorted(common - set(unchanged)),
            "renamed": sorted(renamed, key=lambda item: item["from"]),
            "unchanged": sorted(unchanged)}


def write_report(path: Path, data: dict) -> None:
    """Replace only the chosen report; preserve the old report if writing fails."""
    if path.suffix.lower() != ".json" or path.is_symlink():
        raise ValueError("Report output must be a .json file and must not be a symbolic link.")
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".modpack-", delete=False) as stream:
            temp_path = Path(stream.name)
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="command", required=True)
    scan = commands.add_parser("snapshot", help="Hash a mods folder into a JSON manifest")
    scan.add_argument("folder", type=Path)
    scan.add_argument("--recursive", action="store_true")
    scan.add_argument("--output", required=True, type=Path)
    diff = commands.add_parser("compare", help="Compare two saved manifests")
    diff.add_argument("old", type=Path)
    diff.add_argument("new", type=Path)
    diff.add_argument("--json", action="store_true")
    verify = commands.add_parser("verify", help="Compare a saved manifest with a current mods folder")
    verify.add_argument("old", type=Path)
    verify.add_argument("folder", type=Path)
    verify.add_argument("--recursive", action="store_true")
    for command in (diff, verify):
        if command is verify:
            command.add_argument("--json", action="store_true")
        command.add_argument("--output", type=Path, help="Save differences to JSON; cannot replace input manifests")
    args = parser.parse_args(argv)
    try:
        if args.command == "snapshot":
            if args.output.suffix.lower() != ".json":
                raise ValueError("The report output must end in .json; JAR files cannot be overwritten.")
            data = snapshot(args.folder, args.recursive)
            write_report(args.output, data)
            print(f"Saved {len(data['files'])} JAR entries to {args.output}")
            return 0
        if args.output:
            inputs = [args.old] + ([args.new] if args.command == "compare" else [])
            if any(args.output.resolve() == source.resolve() for source in inputs):
                raise ValueError("Difference output must not replace an input manifest.")
        new = snapshot(args.folder, args.recursive) if args.command == "verify" else load_manifest(args.new)
        report = compare(load_manifest(args.old), new)
        if args.output:
            write_report(args.output, report)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            for category in ("added", "removed", "changed", "renamed"):
                print(f"{category.title()}: {len(report[category])}")
                for item in report[category]:
                    print(f"  {item['from']} -> {item['to']}" if isinstance(item, dict) else f"  {item}")
            print(f"Unchanged: {len(report['unchanged'])}")
        return 2 if any(report[k] for k in ("added", "removed", "changed", "renamed")) else 0
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
