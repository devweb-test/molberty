#!/usr/bin/env python3
"""Read-only package, data and frozen reference validation (Python stdlib)."""
import argparse, hashlib, json, math, sys
from pathlib import Path
from export_snapshot import source_path
ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source")
    parser.add_argument("--output")
    args = parser.parse_args()
    source = source_path(args.source)
    load = lambda name: json.loads((ROOT / "exports" / (name + ".json")).read_text())
    errors = []
    def require(condition, message):
        if not condition:
            errors.append(message)
    expected = json.loads((ROOT / "snapshot.json").read_text())
    products, categories, routes = load("products"), load("categories"), load("routes")
    require(len(products) == expected["products"] == 91, "Product count")
    require(len(categories) == expected["categories"] == 34, "Category count")
    require(len(routes) == expected["contentRoutes"] == 142, "Route count")
    require(len(load("articles")) == 4, "Article count")
    require(len(load("pages")) == 12, "Page count")
    require(len({p["id"] for p in products}) == 91, "Duplicate product IDs")
    require(len({p["sourceId"] for p in products}) == 91, "Duplicate source IDs")
    require(len({p["route"] for p in routes}) == 142, "Duplicate routes")
    require(len({p["h1"] for p in routes}) == 142, "Duplicate H1 in snapshot")
    require(sum(len(p["gallery"]) for p in products) == 202, "Gallery entry count")
    category_ids = {c["id"] for c in categories}
    for product in products:
        require(set(product["categories"]) <= category_ids, "Unknown category: " + product["id"])
        require(product["primaryCategoryId"] in product["categories"], "Primary category: " + product["id"])
        require(not any(mark in product["name"] for mark in '"«»“”'), "Product quotation marks")
        require((source / product["route"].strip("/") / "index.html").is_file(), "Missing product route")
    for category in categories:
        require(category["parentId"] is None or category["parentId"] in category_ids, "Unknown parent")
        require(category["pathIds"][-1] == category["id"], "Category breadcrumb path")
        require(len(category["pathIds"]) == len(set(category["pathIds"])), "Category cycle")
    actual_routes = {r["route"] for r in routes}
    redirects = load("redirects")
    require(len(redirects) == expected["redirects"], "Redirect count")
    require(len({r["source"] for r in redirects}) == len(redirects), "Duplicate redirects")
    for rule in redirects:
        require(rule["source"] not in actual_routes, "Redirect overwrites active route")
        require(rule["target"] in actual_routes, "Missing redirect target")
        require(rule["source"] != rule["target"], "Self redirect")
    media = load("media")
    for item in media:
        file = source / "assets" / item["path"]
        require(file.is_file(), "Missing asset: " + item["path"])
        if file.is_file():
            require(hashlib.sha256(file.read_bytes()).hexdigest() == item["sha256"],
                    "Changed asset: " + item["path"])
    fixture_rows = load("pricing-fixtures")
    require(len(fixture_rows) == 717, "Pricing fixture count")
    product_ids = {p["id"] for p in products}
    for fixture in fixture_rows:
        require(fixture["productId"] in product_ids, "Fixture product")
        require(math.isfinite(fixture["unitPrice"]), "Fixture numeric price")
        require(fixture["quantity"] >= fixture["minQuantity"] >= 1, "Fixture quantity")
        require(fixture["total"] == fixture["unitPrice"] * fixture["quantity"], "Fixture total")
    reference_manifest = ROOT / "checks/reference-manifest.json"
    if reference_manifest.is_file():
        for item in json.loads(reference_manifest.read_text()):
            rel = item["path"]
            file = source / rel[len("new-site/"):] if rel.startswith("new-site/") else source.parent / rel
            require(file.is_file(), "Reference missing: " + rel)
            if file.is_file():
                require(hashlib.sha256(file.read_bytes()).hexdigest() == item["sha256"],
                        "Reference differs from v129: " + rel)
    original_manifest = ROOT / "checks/source-documents-manifest.json"
    if original_manifest.is_file() and ((ROOT / "source-documents").is_dir()
                                       or (ROOT / "reference/new-site").is_dir()):
        for item in json.loads(original_manifest.read_text()):
            file = ROOT / item["path"]
            require(file.is_file(), "Original input missing: " + item["path"])
            if file.is_file():
                require(hashlib.sha256(file.read_bytes()).hexdigest() == item["sha256"],
                        "Original input changed: " + item["path"])
    checksums = ROOT / "SHA256SUMS.txt"
    checked = 0
    if checksums.is_file():
        for line in checksums.read_text().splitlines():
            digest, name = line.split("  ", 1)
            file = ROOT / name
            require(file.is_file(), "Package missing: " + name)
            if file.is_file():
                require(hashlib.sha256(file.read_bytes()).hexdigest() == digest, "Package checksum: " + name)
            checked += 1
    report = {"passed": not errors, "products": len(products), "categories": len(categories),
              "routes": len(routes), "assets": len(media), "pricingFixtures": len(fixture_rows),
              "packageChecksums": checked, "errors": errors}
    if args.output:
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 1

if __name__ == "__main__":
    sys.exit(main())
