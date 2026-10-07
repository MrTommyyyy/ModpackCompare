## What changed

- Added `verify` to check a current mods folder against a saved manifest.
- Both comparison commands can save JSON differences with `--output`.
- Prevents difference reports from overwriting input manifests and refuses symbolic-link outputs.

## Download

Extract the Windows ZIP, open PowerShell in that folder, and run `.\ModpackCompare.exe --help`. No separate Python installation required. This is a terminal tool.

Choose `ModpackCompare-0.2.0-Windows-x64.zip` for 64-bit Windows or `ModpackCompare-0.2.0-Source.zip` for Python 3.11+ on Windows, macOS or Linux. The Windows ZIP includes executable SHA-256 hashes and the MIT licence.

## Validation

Source regression tests and packaged executable behaviour checks run on the Windows build before publishing. The JarCheck desktop interaction still needs manual testing; no claim is made that every desktop configuration has been tested.
