"""Exercise the packaged executable against disposable inputs."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

EXE = Path("dist/ModpackCompare.exe").resolve()

def run(*args, code=0):
    result = subprocess.run([str(EXE), *map(str, args)], capture_output=True, text=True, timeout=60)
    if result.returncode != code:
        raise RuntimeError(f"Unexpected exit {result.returncode}: {result.stdout} {result.stderr}")
    return result.stdout

assert run("--version").strip() == "0.2.0"
with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    (folder / "first.jar").write_bytes(b"old")
    baseline = folder / "before.json"
    run("snapshot", folder, "--output", baseline)
    run("verify", baseline, folder)
    (folder / "first.jar").write_bytes(b"new")
    assert json.loads(run("verify", baseline, folder, "--json", code=2))["changed"] == ["first.jar"]
    run("verify", baseline, folder, "--output", baseline, code=1)
print("Packaged executable smoke checks passed")
