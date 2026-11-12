#!/usr/bin/env python3
"""Compare server-rendered WordPress HTML against approved v129 metadata."""
import argparse, base64, concurrent.futures, json, os, sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, urlopen
from export_snapshot import Document, text
ROOT = Path(__file__).resolve().parents[1]

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def schema_types(value):
    result = []
    if isinstance(value, dict):
        kind = value.get("@type", [])
        result.extend(kind if isinstance(kind, list) else [kind])
        for key, child in value.items():
            if key != "@type":
                result.extend(schema_types(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(schema_types(child))
    return result

def objects_of_type(value, kind):
    result = []
    if isinstance(value, dict):
        types = value.get("@type", [])
        if kind in (types if isinstance(types, list) else [types]):
            result.append(value)
        for child in value.values():
            if isinstance(child, (dict, list)):
                result.extend(objects_of_type(child, kind))
    elif isinstance(value, list):
        for child in value:
            result.extend(objects_of_type(child, kind))
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--mode", choices=["staging", "production"], default="staging")
    parser.add_argument("--check-redirects", action="store_true")
    parser.add_argument("--output", default="target-check.json")
    args = parser.parse_args()
    base = args.base.rstrip("/") + "/"
    if urlsplit(base).scheme not in ("http", "https"):
        raise SystemExit("Expected http(s) --base")
    headers = {"User-Agent": "MolbertyMigrationCheck/1.0"}
    if os.environ.get("MOLBERTY_BASIC_AUTH"):
        headers["Authorization"] = "Basic " + base64.b64encode(
            os.environ["MOLBERTY_BASIC_AUTH"].encode()).decode()
    pages = json.loads((ROOT / "exports/routes.json").read_text())
    def check(page):
        route = page["route"]
        url = urljoin(base, route.lstrip("/"))
        errors = []
        try:
            try:
                response = urlopen(Request(url, headers=headers), timeout=20)
            except HTTPError as error:
                response = error
            status, final = response.status, response.geturl()
            source = response.read().decode("utf-8")
            response_headers = response.headers
            if status != page["expectedStatus"]:
                errors.append("HTTP " + str(status))
            if page["kind"] != "error" and final.rstrip("/") != url.rstrip("/"):
                errors.append("Unexpected redirect: " + final)
            dom = Document(source)
            titles = [text(dom.inner(n)) for n in dom.find("title")]
            headings = [text(dom.inner(n)) for n in dom.find("h1")]
            if titles != [page["title"]]:
                errors.append("title mismatch or duplicate")
            if headings != [page["h1"]]:
                errors.append("h1 mismatch or duplicate")
            metas = {}
            for node in dom.find("meta"):
                name = node["attrs"].get("name", "").lower()
                if name:
                    metas.setdefault(name, []).append(node["attrs"].get("content", ""))
            for name in ("description", "keywords"):
                expected = [page[name]] if page[name] else []
                if metas.get(name, []) != expected:
                    errors.append(name + " mismatch or duplicate")
            robots = ",".join(metas.get("robots", [])) + "," + response_headers.get("X-Robots-Tag", "")
            if page["kind"] != "error":
                if args.mode == "production" and "noindex" in robots.lower():
                    errors.append("Production noindex")
                if args.mode == "staging" and "noindex" not in robots.lower():
                    errors.append("Staging missing noindex")
                canonical = [n["attrs"].get("href") for n in dom.find("link", rel="canonical")]
                if canonical != [url]:
                    errors.append("canonical mismatch")
            schemas = [json.loads(dom.inner(n)) for n in dom.find("script", type="application/ld+json")]
            actual_types = schema_types(schemas)
            expected_types = schema_types(page["schemas"])
            for name in ("Organization", "Product", "BreadcrumbList"):
                expected_count = expected_types.count(name)
                if actual_types.count(name) != expected_count:
                    errors.append(name + " count mismatch")
            if page["kind"] == "product":
                product_nodes = objects_of_type(schemas, "Product")
                if len(product_nodes) == 1:
                    if product_nodes[0].get("name") != page["h1"]:
                        errors.append("Product.name must match H1")
                    if product_nodes[0].get("description") != page["description"]:
                        errors.append("Product.description must match meta description")
            if "devweb-test.github.io/molberty/new-site" in "".join(
                    str(value) for value in [titles, metas, schemas]):
                errors.append("Prototype URL in metadata/schema")
            return {"route": route, "passed": not errors, "errors": errors}
        except Exception as error:
            return {"route": route, "passed": False, "errors": [str(error)]}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(check, pages))
    if args.check_redirects:
        opener = build_opener(NoRedirect)
        for rule in json.loads((ROOT / "exports/redirects.json").read_text()):
            url = urljoin(base, rule["source"].lstrip("/"))
            try:
                try:
                    response = opener.open(Request(url, headers=headers), timeout=20)
                except HTTPError as error:
                    response = error
                expected = urljoin(base, rule["target"].lstrip("/"))
                location = urljoin(url, response.headers.get("Location", ""))
                ok = response.status == 301 and location == expected
                results.append({"route": rule["source"], "passed": ok,
                    "errors": [] if ok else ["Expected exact 301 to " + expected]})
            except Exception as error:
                results.append({"route": rule["source"], "passed": False, "errors": [str(error)]})
    # An actual unknown route must stay an HTTP 404 instead of a soft-404 home page.
    try:
        response = urlopen(Request(urljoin(base, "molberty-migration-missing-page-7f249/"), headers=headers), timeout=20)
        ok = response.status == 404
    except HTTPError as error:
        ok = error.code == 404
    except Exception:
        ok = False
    results.append({"route": "__unknown__", "passed": ok, "errors": [] if ok else ["Missing true HTTP 404"]})
    report = {"mode": args.mode, "base": base, "passed": all(r["passed"] for r in results),
              "checked": len(results), "results": results}
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "checked": len(results),
                      "failed": sum(not row["passed"] for row in results), "output": args.output}))
    return 0 if report["passed"] else 1
if __name__ == "__main__":
    sys.exit(main())
