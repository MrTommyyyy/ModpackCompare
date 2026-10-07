ModpackCompare 0.2.0 — Windows x64 portable download

Extract the whole ZIP first. No separate Python installation required.
Open PowerShell in the extracted folder.
.\ModpackCompare.exe snapshot "C:\path\to\mods" --output before.json
.\ModpackCompare.exe verify before.json "C:\path\to\mods" --output changes.json

MIT licensed; see LICENSE. SHA256SUMS.txt lists executable hashes.
No network requests are made by the tool.
