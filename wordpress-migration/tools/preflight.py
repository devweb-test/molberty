#!/usr/bin/env python3
"""Run preparation checks; explicitly distinguish them from a real WordPress acceptance."""
import json, subprocess, sys, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from export_snapshot import source_path, write_json
ROOT = Path(__file__).resolve().parents[1]

def run(arguments):
    result = subprocess.run(arguments, cwd=ROOT, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("Failed: " + " ".join(arguments) + "\n" + result.stdout + result.stderr)
    return result.stdout.strip()

def main():
    checks = []
    source = source_path()
    for file in sorted((ROOT / "wordpress").rglob("*.php")):
        run(["php", "-l", str(file)])
    checks.append({"check":"PHP syntax","passed":True})
    for file in sorted((ROOT / "tools").glob("*.py")):
        compile(file.read_text(), str(file), "exec")
    for file in sorted((ROOT / "integration").glob("*.js")):
        run(["node", "--check", str(file)])
    checks.append({"check":"Python and JavaScript syntax","passed":True})
    for command, name in [
        (["php", str(ROOT/"tools/test_pricing.php")], "PHP reference price calculation"),
        (["php", str(ROOT/"tests/test_import_dry_run.php")], "Importer dry-run contract"),
        (["node", str(ROOT/"tests/test_legacy.cjs")], "Legacy fragment adapter"),
        ([sys.executable, str(ROOT/"tests/test_check_target.py")], "HTTP checker on frozen mock server"),
        ([sys.executable, str(ROOT/"tools/validate_package.py"), "--source", str(source)], "Data and reference integrity"),
    ]:
        stdout = run(command)
        checks.append({"check":name, "passed":True, "result":json.loads(stdout)})
    office = []
    for file in [ROOT/"Карта переноса.xlsx", ROOT/"План переноса на WordPress.docx"]:
        with zipfile.ZipFile(file) as archive:
            assert archive.testzip() is None
            for name in archive.namelist():
                if name.endswith((".xml",".rels")):
                    ET.fromstring(archive.read(name))
        office.append(file.name)
    checks.append({"check":"Office package XML and ZIP integrity","passed":True,"files":office})
    report = {"preparedOn":"2026-11-12","referenceVersion":"v129","passed":True,
              "checks":checks, "realWordPressImportExecuted":False,
              "realWordPressThemeImplemented":False,"realFormsAndSMTPConfigured":False,
              "productionChanged":False,
              "remainingValidation":"Run importer and complete theme/core/cart/forms acceptance in the target WordPress."}
    write_json(ROOT/"checks/preparation-report.json",report)
    print(json.dumps({"passed":True,"checks":len(checks),"targetWordPressTested":False}))

if __name__ == "__main__":
    main()
