#!/usr/bin/env python3
"""Freeze the approved source, verify the handoff and create the complete archive."""
import argparse, hashlib, json, subprocess, sys, zipfile
from pathlib import Path
from export_snapshot import write_json
ROOT = Path(__file__).resolve().parents[1]

def ignored(file):
    parts = file.relative_to(ROOT).parts
    return "__pycache__" in parts or file.suffix == ".pyc" or file.name.startswith("target-check")

def core_files():
    return [file for file in sorted(ROOT.rglob("*")) if file.is_file() and not ignored(file)
            and file.relative_to(ROOT).parts[0] not in ("reference","source-documents")
            and file.name != "SHA256SUMS.txt"]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-archive",
                        help="Approved v129 ZIP; optional if its reference/ copy is already present")
    parser.add_argument("--output", required=True)
    parser.add_argument("--report")
    args = parser.parse_args()
    snapshot = json.loads((ROOT/"snapshot.json").read_text())
    source_files = []
    reference = ROOT/"reference"
    if args.reference_archive:
        original = Path(args.reference_archive).resolve()
        if hashlib.sha256(original.read_bytes()).hexdigest() != snapshot["referenceArchiveSha256"]:
            raise SystemExit("The source ZIP is not the approved v129")
        reference.mkdir(exist_ok=True)
        with zipfile.ZipFile(original) as archive:
            assert archive.testzip() is None
            for item in archive.infolist():
                path = Path(item.filename)
                if path.is_absolute() or ".." in path.parts:
                    raise RuntimeError("Unsafe source ZIP path")
                body = archive.read(item.filename)
                target = reference/path
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(body)
                source_files.append({"path":item.filename,"bytes":len(body),
                    "sha256":hashlib.sha256(body).hexdigest()})
    else:
        source_files = json.loads((ROOT/"checks/reference-manifest.json").read_text())
        for item in source_files:
            target = reference/item["path"]
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
                raise RuntimeError("Missing or modified frozen reference: " + item["path"])
    assert len(source_files)==806
    write_json(ROOT/"checks/reference-manifest.json",source_files)
    # Preflight's validator runs before writing final core checksums.
    checksum = ROOT/"SHA256SUMS.txt"
    if checksum.exists():
        checksum.unlink()
    subprocess.run([sys.executable,str(ROOT/"tools/preflight.py")],cwd=ROOT,check=True)
    checksum.write_text("".join(hashlib.sha256(file.read_bytes()).hexdigest()+"  "+
        file.relative_to(ROOT).as_posix()+"\n" for file in core_files()),encoding="utf-8")
    subprocess.run([sys.executable,str(ROOT/"tools/validate_package.py")],cwd=ROOT,check=True)
    files = [file for file in sorted(ROOT.rglob("*")) if file.is_file() and not ignored(file)]
    output = Path(args.output).resolve()
    if output.is_relative_to(ROOT):
        raise RuntimeError("Output ZIP must be outside the package folder")
    with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for file in files:
            archive.write(file,file.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(files)
        for file in files:
            assert archive.read(file.relative_to(ROOT).as_posix()) == file.read_bytes()
    report = {"path":str(output),"files":len(files),"referenceFiles":len(source_files),
              "size":output.stat().st_size,"sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
              "verified":True,"sourceVersion":"v129"}
    if args.report:
        write_json(Path(args.report),report)
    print(json.dumps(report,ensure_ascii=False))

if __name__ == "__main__":
    main()
