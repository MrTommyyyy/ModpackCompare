# ModpackCompare

Version: **0.2.0**

Offline comparisons for Minecraft mod folders. Save a snapshot before changing
a pack, save another afterwards, and see which JARs were added, removed,
changed, or renamed. Python 3.11+, no external packages, MIT licensed.


[Download the latest release](https://github.com/MrTommyyyy/ModpackCompare/releases/latest) · [Report an issue](https://github.com/MrTommyyyy/ModpackCompare/issues)

![Tests](https://github.com/MrTommyyyy/ModpackCompare/actions/workflows/tests.yml/badge.svg)

**Download format:** a portable Windows x64 ZIP with an executable, plus a separate Python source ZIP.

## Why I'm building this

I enjoy modded Minecraft, but keeping track of changes to a pack can be a pain.
A filename alone doesn't tell me whether two copies contain the same bytes.
I want a small tool that makes those changes easier to see and gives me a
report I can use when troubleshooting a pack update.

This is a new project. The current release is a working starting point, and
real bug reports will guide what comes next.

## Quick start from Python source

Download the source ZIP under **Assets** on the latest release page, extract it, and open a
terminal in the extracted folder. Install Python 3.11 or newer first. On Windows
use `py` instead of `python` if that is your Python launcher.

```sh
python modpack_compare.py snapshot "/path/to/instance/mods" --output before.json
# After you deliberately update your modpack:
python modpack_compare.py snapshot "/path/to/instance/mods" --output after.json
python modpack_compare.py compare before.json after.json
python modpack_compare.py compare before.json after.json --json
```

Snapshot output must be a `.json` file. Choosing an existing report replaces
that report; the tool never modifies or deletes JARs. Close the launcher and
finish downloads before scanning. Add `--recursive` to include nested folders.
An empty folder produces a valid empty manifest, so check the JAR count printed
by the command.

## What it detects

- Added and removed paths.
- Changed contents even when the filename stays the same, using SHA-256.
- Renames when exactly one removed file and one added file share the same hash
  and size. Ambiguous copies stay in the added/removed lists.
- Unchanged files, with structured JSON output for scripts.

The manifest contains only relative paths, sizes and hashes. It doesn't include
your account, absolute folder path, or JAR contents. Review filenames before
sharing a manifest. Scans are offline and deterministic. If file metadata
changes during hashing, the scan fails instead of saving a misleading report.
This is a best-effort check, not an atomic filesystem snapshot.

## Exit codes and report format

| Command result | Exit code |
| --- | --- |
| Snapshot saved, or compared manifests match | 0 |
| Invalid input or read/write failure | 1 |
| Comparison found additions, removals, changes or renames | 2 |

Reports use `modpack-compare/v1` with a `files` array of `path`, `size` and
`sha256` entries. Invalid paths, sizes, hashes and duplicate paths are rejected.
Case differences in filenames are treated as path changes. Symbolic links are
not supported.

## Limits

This compares bytes, not mod compatibility. It does not validate JAR archives,
interpret mod-loader dependencies, identify malware, or decide which version
to install. JarCheck is the companion project for duplicate and archive checks.

## Development

```sh
python -m unittest discover -v
```

Eleven tests cover real changes, renames, ambiguous copies, recursive scanning,
manifest validation, changed files during scanning, exit codes and protection
against writing a report over a JAR. GitHub Actions runs the suite on Windows,
macOS and Ubuntu with Python 3.11 and 3.13.

## Next steps

- Optional mod ID and version metadata alongside byte comparisons.
- A simple desktop view of a comparison.
- Sample reports from real modpack updates, with private paths removed.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [LICENSE](LICENSE).

## Check a folder against a saved baseline

```bash
python modpack_compare.py verify before.json mods --recursive --output differences.json
```

Use the same subfolder setting as your original snapshot. No second manifest is needed. Both `compare` and `verify` can save differences with `--output`. Input manifests cannot be replaced by the differences report; symbolic-link outputs are refused. Exit code 2 means differences, 1 means an error, and 0 means a match.

## Portable Windows download

Choose the `Windows-x64.zip` release asset and extract it. Python is bundled. These are terminal tools: open PowerShell in the extracted folder and run `.\ModpackCompare.exe --help`. The separate source ZIP supports Python 3.11+ on other platforms.
