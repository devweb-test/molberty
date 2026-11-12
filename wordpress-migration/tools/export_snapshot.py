#!/usr/bin/env python3
"""Export the approved static site without rebuilding or changing it (stdlib only)."""
from __future__ import annotations
import argparse, csv, hashlib, html, json, mimetypes, re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote

ROOT = Path(__file__).resolve().parents[1]
VOID = set("area base br col embed hr img input link meta param source track wbr".split())

class Document(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source, self.nodes, self.stack = source, [], []
        self.lines = [0]
        for match in re.finditer("\n", source):
            self.lines.append(match.end())
        self.feed(source)

    def pos(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.pos()
        node = {"tag": tag, "attrs": dict(attrs), "start": start,
                "inner_start": start + len(self.get_starttag_text()),
                "parent": self.stack[-1] if self.stack else None}
        self.nodes.append(node)
        if tag in VOID:
            node.update(end=node["inner_start"], inner_end=node["inner_start"])
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1]["start"] == self.pos():
            node = self.stack.pop()
            node.update(end=node["inner_start"], inner_end=node["inner_start"])

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                end = self.source.find(">", self.pos()) + 1
                for node in self.stack[index:]:
                    node.update(inner_end=self.pos(), end=end)
                del self.stack[index:]
                break

    def find(self, tag=None, **attrs):
        return [node for node in self.nodes if (not tag or node["tag"] == tag)
                and all(node["attrs"].get(key) == value for key, value in attrs.items())]

    def classes(self, name):
        return [node for node in self.nodes if name in node["attrs"].get("class", "").split()]

    def inner(self, node):
        return self.source[node["inner_start"]:node["inner_end"]]

    def outer(self, node):
        return self.source[node["start"]:node["end"]]

def text(fragment):
    fragment = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", "", fragment, flags=re.S | re.I)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list))
                             else value for key, value in row.items() if key in fields})

def source_path(requested=None):
    candidates = [Path(requested)] if requested else [ROOT / "reference/new-site", ROOT.parent / "new-site"]
    for candidate in candidates:
        if (candidate / "data/catalog.json").is_file():
            return candidate.resolve()
    raise SystemExit("Use --source /absolute/path/to/new-site")

def normalize_markup(fragment, route):
    """Preserve text and structure; replace local URLs with explicit import tokens."""
    def replace(match):
        attribute, quote, value = match.groups()
        decoded = html.unescape(value)
        if not decoded or decoded.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
            return match.group(0)
        absolute = urlsplit(urljoin("https://www.molberty.ru" + route, decoded))
        if absolute.netloc not in ("www.molberty.ru", "molberty.ru"):
            return match.group(0)
        local = unquote(absolute.path)
        if "/assets/" in local:
            token = "{{asset}}/" + local.split("/assets/", 1)[1]
        else:
            if local.endswith("/index.html"):
                local = local[:-10]
            if local == "/index.html":
                local = "/"
            token = "{{site}}" + local
        if absolute.query:
            token += "?" + absolute.query
        if absolute.fragment:
            token += "#" + absolute.fragment
        return attribute + "=" + quote + html.escape(token, quote=True) + quote
    return re.sub(r"\b(href|src|poster)=(['\"])(.*?)\2", replace, fragment, flags=re.S | re.I)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source")
    args = parser.parse_args()
    source = source_path(args.source)
    data = lambda name: json.loads((source / "data" / (name + ".json")).read_text())
    catalog = data("catalog")
    categories = catalog["categories"]
    products = catalog["products"]
    category_ids = {item["id"] for item in categories}
    product_ids = {item["slug"]: item["id"] for item in products}
    article_ids = {item["id"] for item in catalog["articles"]}
    pages, documents, assets_usage = [], {}, {}
    content_root = ROOT / "content"
    for file in sorted(source.rglob("*.html")):
        if "qa" in file.relative_to(source).parts:
            continue
        raw = file.read_text(encoding="utf-8")
        dom = Document(raw)
        main_nodes = dom.find("main", id="main")
        if not main_nodes:
            continue
        relative = file.relative_to(source).as_posix()
        route = "/" if relative == "index.html" else "/" + relative.removesuffix("index.html")
        kind = ("home" if route == "/" else "product" if route.startswith("/product/")
                else "category" if route.strip("/") in category_ids
                else "article" if route.startswith("/blog/") and route.strip("/").split("/")[-1] in article_ids
                else "error" if relative == "404.html" else "page")
        headings = [text(dom.inner(node)) for node in dom.find("h1")]
        metas = {}
        for node in dom.find("meta"):
            if node["attrs"].get("name"):
                metas.setdefault(node["attrs"]["name"].lower(), []).append(node["attrs"].get("content", ""))
        titles = [text(dom.inner(node)) for node in dom.find("title")]
        canonical = [node["attrs"].get("href", "") for node in dom.find("link", rel="canonical")]
        schemas = []
        for node in dom.find("script", type="application/ld+json"):
            schemas.append(json.loads(dom.inner(node)))
        content_file = "content/main/" + relative
        destination = ROOT / content_file
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dom.inner(main_nodes[0]), encoding="utf-8")
        page = dict(route=route, kind=kind, reference=relative, contentFile=content_file,
                    title=titles[0] if titles else "", h1=headings[0] if headings else "",
                    description=(metas.get("description") or [""])[0],
                    keywords=(metas.get("keywords") or [""])[0],
                    canonical=canonical[0] if canonical else "",
                    robots=(metas.get("robots") or [""])[0],
                    titleCount=len(titles), h1Count=len(headings),
                    descriptionCount=len(metas.get("description", [])),
                    schemas=schemas, expectedStatus=404 if kind == "error" else 200,
                    sha256=hashlib.sha256(file.read_bytes()).hexdigest())
        pages.append(page)
        documents[route] = dom
        for node in dom.nodes:
            for attribute in ("src", "href", "poster", "data-hover-src"):
                value = node["attrs"].get(attribute)
                if not value or value.startswith(("data:", "#", "mailto:", "tel:")):
                    continue
                resolved = urlsplit(urljoin("https://www.molberty.ru" + route, value))
                if resolved.netloc not in ("www.molberty.ru", "molberty.ru") or "/assets/" not in resolved.path:
                    continue
                key = unquote(resolved.path.split("/assets/", 1)[1])
                usage = assets_usage.setdefault(key, {"routes": set(), "alt": ""})
                usage["routes"].add(route)
                if node["attrs"].get("alt") and not usage["alt"]:
                    usage["alt"] = node["attrs"]["alt"]
    by_route = {item["route"]: item for item in pages}
    exported_categories = []
    for item in categories:
        route = "/" + item["id"] + "/"
        exported_categories.append({**item, "route": route, "editorialSeo": item.get("seo"),
            "seo": {key: by_route[route][key]
            for key in ("title", "description", "keywords", "h1")},
            "resolvedBodyFile": by_route[route]["contentFile"],
            "postListCopy": data("category-copy").get(item["id"]),
            "guide": data("category-guides").get(item["id"])})
    exported_products = []
    for item in products:
        route = "/product/" + item["slug"] + "/"
        exported_products.append({**item, "route": route, "h1": by_route[route]["h1"],
            "seo": {key: by_route[route][key] for key in ("title", "description", "keywords", "h1")}})
    exported_articles = []
    presentation = data("article-presentation")
    for item in catalog["articles"]:
        route = "/blog/" + item["id"] + "/"
        dom = documents[route]
        body = dom.classes("article-original-body")
        if len(body) != 1:
            raise ValueError("Expected one original article body: " + route)
        article_file = "content/articles/" + item["id"] + ".html"
        destination = ROOT / article_file
        destination.parent.mkdir(parents=True, exist_ok=True)
        rendered = dom.inner(body[0])
        destination.write_text(normalize_markup(rendered, route), encoding="utf-8")
        exported_articles.append({**item, "route": route, "presentation": presentation[item["id"]],
            "contentFile": article_file, "contentHtml": normalize_markup(rendered, route),
            "h1": by_route[route]["h1"],
            "seo": {key: by_route[route][key] for key in ("title", "description", "keywords", "h1")}})
    services = []
    for page in pages:
        if page["kind"] not in ("home", "page"):
            continue
        dom = documents[page["route"]]
        host = dom.find("main", id="main")[0]
        services.append({**page, "id": "home" if page["route"] == "/" else page["route"].strip("/"),
                         "referenceMainHtml": normalize_markup(dom.inner(host), page["route"])})
    media = []
    for file in sorted((source / "assets").rglob("*")):
        if not file.is_file():
            continue
        relative = file.relative_to(source / "assets").as_posix()
        usage = assets_usage.get(relative, {"routes": set(), "alt": ""})
        mime = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
        media.append(dict(path=relative, sourcePath="assets/" + relative,
            sha256=hashlib.sha256(file.read_bytes()).hexdigest(), bytes=file.stat().st_size,
            mime=mime, alt=usage["alt"], routes=sorted(usage["routes"]),
            importToMediaLibrary=bool(usage["routes"]) and
            file.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".avif", ".gif", ".pdf")))
    redirects = data("redirects")
    old_site = {
        "/for_artist": "/molberty-dlya-risovaniya-hudozhnikov/",
        "/for_studio": "/oborudovanie-dlya-kabineta-izo/",
        "/for_exibition": "/molberty-dlya-vystavki/",
        "/for_interior": "/molberty-dekorativnye/",
        "/articles": "/blog/",
        "/page2566204.html": "/blog/instrument-dlya-tvorchestva-molbert/",
        "/page2781362.html": "/blog/molbert-v-sovremennom-interere/",
        "/page2781437.html": "/blog/dvadcat-let-plodotvornoj-raboty/",
        "/how_to_make_choice": "/blog/kak-vybrat-molbert/",
    }
    redirect_rows = [dict(source=old, target=new, status=301, origin="prototype",
                         implementation="server") for old, new in redirects.items()]
    for old, new in old_site.items():
        for alias in ({old, old + "/"} if not old.endswith(".html") else {old}):
            if alias not in redirects:
                redirect_rows.append(dict(source=alias, target=new, status=301,
                                          origin="original-site-known", implementation="server"))
    fragment_rows = []
    for item in exported_products:
        match = re.fullmatch(r"(.+)-(\d+)-(\d+)", item["sourceId"])
        if match:
            family, record, product = match.groups()
            fragment_rows.append(dict(source="/" + family + "#!/tproduct/" + record + "-" + product,
                sourceId=item["sourceId"], target=item["route"],
                implementation="browser-compatibility; fragment is not sent to server"))
    exports = ROOT / "exports"
    datasets = dict(categories=exported_categories, products=exported_products,
                    articles=exported_articles, pages=services, routes=pages, media=media,
                    redirects=redirect_rows, legacy_fragments=fragment_rows,
                    clients=data("clients"), reviews=data("reviews"), showcase=data("showcase"))
    for name, value in datasets.items():
        write_json(exports / (name + ".json"), value)
    settings = {name: data(name) for name in (
        "sales", "company", "production", "business-documents", "organization", "home-blocks",
        "cookie-notice", "prices", "price-product-links", "category-guides", "article-presentation",
        "category-copy", "page-seo", "legal-pages", "icons")}
    write_json(exports / "settings.json", settings)
    home = documents["/"]
    shared = content_root / "shared"
    shared.mkdir(parents=True, exist_ok=True)
    for identifier in ("header", "footer", "topbar", "cookie-notice", "mobile-bottom-nav",
                       "request-dialog", "image-dialog"):
        nodes = home.find(id=identifier)
        if nodes:
            (shared / (identifier + ".html")).write_text(home.outer(nodes[0]), encoding="utf-8")
    write_csv(ROOT / "tables/routes-seo.csv", pages,
        ["route", "kind", "h1", "title", "description", "keywords", "expectedStatus", "reference", "contentFile"])
    write_csv(ROOT / "tables/categories.csv", exported_categories,
        ["id", "name", "parentId", "depth", "route", "pathIds", "childIds"])
    write_csv(ROOT / "tables/products.csv", exported_products,
        ["id", "sourceId", "name", "h1", "slug", "route", "primaryCategoryId", "categories",
         "retailPrice", "wholesalePrice", "wholesaleMin", "minimumOrder", "defaultTier",
         "defaultQuantity", "listingPrice", "isNew"])
    write_csv(ROOT / "tables/media.csv", media,
        ["path", "mime", "bytes", "sha256", "importToMediaLibrary", "alt", "routes"])
    write_csv(ROOT / "tables/redirects.csv", redirect_rows,
        ["source", "target", "status", "origin", "implementation"])
    write_csv(ROOT / "tables/legacy-fragments.csv", fragment_rows,
        ["source", "sourceId", "target", "implementation"])
    summary = dict(referenceVersion="v129", referenceCommit="ec47c798c7b939f05f923ce0af0f5a2122fcac3c",
        referenceArchive="molberty-new-site-2026-11-12-v129.zip",
        referenceArchiveSha256="3c29898f583b83533929942033c23243d2e0395099a9702cb13cb66e26f02981",
        approvedOn="2026-11-12", targetOrigin="https://www.molberty.ru",
        products=len(exported_products), categories=len(exported_categories),
        articles=len(exported_articles), contentRoutes=len(pages), pages=len(services),
        errorPages=sum(page["kind"] == "error" for page in pages),
        productGalleryEntries=sum(len(item["gallery"]) for item in products),
        newProducts=sum(bool(item["isNew"]) for item in products),
        clients=len(data("clients")["clients"]), reviews=len(data("reviews")["items"]),
        showcase=len(data("showcase")), assets=len(media),
        mediaImports=sum(item["importToMediaLibrary"] for item in media),
        redirects=len(redirect_rows), originalFragments=len(fragment_rows),
        note="Final HTML and data are authoritative; historical README/CMS-MIGRATION notes may be obsolete.")
    write_json(ROOT / "snapshot.json", summary)
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()
