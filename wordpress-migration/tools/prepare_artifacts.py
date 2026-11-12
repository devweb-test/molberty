#!/usr/bin/env python3
"""Build Office summaries, redirect templates and installable helper ZIPs."""
import csv, hashlib, json, re, shutil, zipfile
from pathlib import Path
from xml.sax.saxutils import escape
from export_snapshot import source_path, write_csv, write_json
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent

FORMS = [
    ["F01", "Общий запрос", "Все страницы", "Имя; контакт; задача; согласие", "name/contact/consent", "request"],
    ["F02", "Заказать звонок", "Шапка", "Имя; телефон; время; согласие", "name/phone/consent", "callback"],
    ["F03", "Выход курсора", "Desktop через 8 секунд", "Как у обратного звонка", "name/phone/consent", "exit-intent"],
    ["F04", "Корзина", "Все страницы", "Имя; телефон; e-mail; получение; город; адрес; согласие", "name/phone/delivery/consent; address for shipping", "checkout"],
    ["F05", "Интерьерный подбор", "/molberty-dekorativnye/", "Габариты; высота; вес; глубина; контакты; согласие", "Контакты и согласие на финальном шаге", "interior-quiz"],
    ["F06", "Оптовый заказ", "/contacts/ и /delivery/", "Организация; имя; телефон; e-mail; заказ; адрес; согласие", "company/name/phone/email/order/consent", "wholesale"],
    ["F07", "Розничный заказ", "/contacts/ и /delivery/", "Имя; телефон; e-mail; заказ; адрес; согласие", "name/phone/email/order/consent", "retail"],
]
ACCEPTANCE = [
    ("A01", "Окружение", "Staging закрыт от индексации; версии и резервная копия зафиксированы"),
    ("A02", "Эталон", "v129 неизменён; checksums проходят; полный build не запускался"),
    ("A03", "Импорт", "91 товар по sourceId, повторный запуск без дубликатов"),
    ("A04", "Импорт", "34 категории, точная иерархия и 202 элемента галерей"),
    ("A05", "Импорт", "4 оригинальные статьи и 12 страниц"),
    ("A06", "Импорт", "49 клиентов, 7 отзывов, 3 примера пространств"),
    ("A07", "Медиа", "Локальные фото, PDF, логотипы, шрифты и фавиконы доступны"),
    ("A08", "Маршруты", "142 эталонных маршрута, неизвестный URL возвращает 404"),
    ("A09", "Редиректы", "91 известный 301; список дополнен фактическими URL старого сайта"),
    ("A10", "Tilda", "Известные #!/tproduct ссылки открывают конкретное изделие"),
    ("A11", "Цена", "Все 717 fixtures проходят на серверном сервисе"),
    ("A12", "Цена", "Режим опт/розница, absolute/delta/none и планшет дают верную цену"),
    ("A13", "Цена", "Минимальная партия, wholesaleOnly и индексы проверяются сервером"),
    ("A14", "Корзина", "Разные комплектации не склеиваются; сумму из POST нельзя подменить"),
    ("A15", "Корзина", "Заказать из списка добавляет без модального окна; есть SVG корзины"),
    ("A16", "Корзина", "Заметное удаление; Очистить корзину; изображения и итоги"),
    ("A17", "Заказ", "Доставка/самовывоз проверяются; неизвестная доставка не объявляется бесплатной"),
    ("A18", "Формы", "7 сценариев; согласие обязательно и не предустановлено"),
    ("A19", "Формы", "Нет ИНН/реквизитов в оптовой форме; есть e-mail и формы на двух страницах"),
    ("A20", "Формы", "Реальный успех/ошибка; SMTP проверен; нет дубликатов при повторе"),
    ("A21", "Cookie", "Текущий текст, ссылки policy/consent, сохранение выбора"),
    ("A22", "Exit-intent", "8 секунд; повтор только при новом выходе после 6 минут; нет автопоказа без мыши"),
    ("A23", "Шапка", "Только меню sticky; графики 08–17, 08–16 и суббота; логотип Лира"),
    ("A24", "Мобильная", "Телефон в шапке; корзина в нижнем меню; sidebar скрыт"),
    ("A25", "Главная", "H1 Мольберты, пять баннеров, сообщение обновления"),
    ("A26", "Главная", "Каталог: ссылки одной строкой без стрелок; тематические SVG вопросов"),
    ("A27", "Главная", "О компании без переписывания; стандарты и производственные изображения"),
    ("A28", "Главная", "Кейсы и следующий блок видимы, переключатели и редактирование работают"),
    ("A29", "Главная", "Нет плашки Концепция на фото кейсов; статьи разделены рамками"),
    ("A30", "Главная", "Клиенты без внешних ссылок, 7 отзывов со стрелками без счётчика/скроллбара"),
    ("A31", "Категории", "Точное дерево, уникальные тексты, документы, руководства и сортировка"),
    ("A32", "Товар", "Имя/H1/slug/SEO из данных, без кавычек; новые товары помечены"),
    ("A33", "Товар", "Вся галерея, увеличение и второй снимок на hover/focus"),
    ("A34", "Прайс", "7 разделов/106 строк, 105 ссылок на 88 товаров; Модерн без ссылки"),
    ("A35", "Контакты", "Карта, продажи, формы; после продаж документы и реквизиты"),
    ("A36", "Статьи", "Оригинальный текст, оформление/содержание, фото Лиры и А-стиля, без внешних ссылок"),
    ("A37", "SEO", "Один title/description/h1, keywords где заданы, exact baseline"),
    ("A38", "Schema", "Product/Organization/BreadcrumbList без дублей, реальные URL и цены"),
    ("A39", "Production", "Снята глобальная noindex; canonical/sitemap не содержат staging/GitHub"),
    ("A40", "Семантика", "Сохранены согласованные div/span и noindex-комментарии"),
    ("A41", "Адаптив", "320/390/768/1024/1440/1920, нет переполнения/наложений"),
    ("A42", "Доступность", "Клавиатура, фокус, aria и prefers-reduced-motion"),
    ("A43", "Производительность", "Lazy loading кроме важного первого изображения; кэш не кеширует корзину/личные данные"),
    ("A44", "Редактор", "Контент, опции, документы и общие настройки редактируются без изменения кода"),
    ("A45", "Выпуск", "Staging-отчёт, резервная копия, проверенный откат, решение оператора"),
    ("A46", "После выпуска", "Проверены заявки/заказы/301/404/robots/sitemap; повтор на следующий рабочий день"),
]

def column(index):
    name = ""
    while index:
        index, rest = divmod(index - 1, 26)
        name = chr(65 + rest) + name
    return name

def xlsx(path, sheets):
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        types = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
                 '<Default Extension="xml" ContentType="application/xml"/>',
                 '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
                 '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
        for index in range(1, len(sheets) + 1):
            types.append(f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        archive.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' + "".join(types) + '</Types>')
        archive.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        sheet_tags = "".join(f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>' for i, (name, rows) in enumerate(sheets, 1))
        archive.writestr("xl/workbook.xml", f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{sheet_tags}</sheets></workbook>')
        rels = "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(sheets) + 1))
        rels += '<Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        archive.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + rels + '</Relationships>')
        archive.writestr("xl/styles.xml", f'''<styleSheet xmlns="{ns}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF344B3F"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs><cellXfs count="2"><xf fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="top" wrapText="1"/></xf><xf fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"><alignment vertical="top" wrapText="1"/></xf></cellXfs></styleSheet>''')
        for index, (name, rows) in enumerate(sheets, 1):
            cols = len(rows[0]) if rows else 1
            dimensions = f"A1:{column(cols)}{len(rows)}"
            columns = "".join(f'<col min="{i}" max="{i}" width="{min(80, max(14, max(len(str(row[i-1])) for row in rows[:120] if len(row)>=i) * .85)):.1f}" customWidth="1"/>' for i in range(1, cols + 1))
            xml_rows = []
            for row_index, row in enumerate(rows, 1):
                cells = []
                for col_index, value in enumerate(row, 1):
                    if value is None:
                        value = ""
                    ref = f"{column(col_index)}{row_index}"
                    style = 1 if row_index == 1 else 0
                    if isinstance(value, (float, int)) and not isinstance(value, bool):
                        cells.append(f'<c r="{ref}" s="{style}"><v>{value}</v></c>')
                    else:
                        value = json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)
                        cells.append(f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{escape(value[:32767])}</t></is></c>')
                xml_rows.append(f'<row r="{row_index}">' + "".join(cells) + '</row>')
            archive.writestr(f"xl/worksheets/sheet{index}.xml", f'<worksheet xmlns="{ns}"><dimension ref="{dimensions}"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols>{columns}</cols><sheetData>{"".join(xml_rows)}</sheetData><autoFilter ref="{dimensions}"/></worksheet>')

def docx(path):
    body = []
    def paragraph(value, style="Normal"):
        body.append('<w:p><w:pPr><w:pStyle w:val="' + style + '"/></w:pPr><w:r><w:t xml:space="preserve">' + escape(value) + '</w:t></w:r></w:p>')
    paragraph("Мольберты.ру", "Title")
    paragraph("План переноса на WordPress", "Subtitle")
    paragraph("Инструкция для вебмастера и агента Codex")
    paragraph("Согласованная версия v129 • 12 ноября 2026 года")
    paragraph("Полный комплект исходников и данных находится в ZIP-пакете. Сначала прочитать README.md и AGENTS.md.")
    for name in ["docs/01-PLAN.md", "docs/02-ARCHITECTURE.md", "docs/03-DATA-MAP.md",
                 "docs/04-UI-ACCEPTANCE.md", "docs/05-SEO-URLS.md", "docs/06-FORMS-ORDERS.md",
                 "docs/07-RELEASE.md", "docs/08-CODEX-TASKS.md", "docs/09-ADMIN-HANDOVER.md"]:
        for line in (ROOT / name).read_text().splitlines():
            if not line.strip():
                continue
            if re.match(r"^\|[- |]+\|$", line):
                continue
            level = len(line) - len(line.lstrip("#"))
            if level:
                paragraph(line[level:].strip(), "Heading" + str(min(level, 3)))
            elif line.startswith("    "):
                paragraph(line[4:], "Code")
            else:
                paragraph(line.replace("|", "  •  ").strip(), "Normal")
    section = '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>')
        archive.writestr("_rels/.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr("word/_rels/document.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="styles" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>')
        archive.writestr("word/document.xml", '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>' + "".join(body) + section + '</w:body></w:document>')
        styles = '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:pPr><w:spacing w:after="120"/></w:pPr><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:color w:val="253B33"/><w:sz w:val="21"/></w:rPr></w:style>'
        for style, size in [("Title", 42), ("Subtitle", 32), ("Heading1", 32), ("Heading2", 26), ("Heading3", 23)]:
            outline = '<w:outlineLvl w:val="' + str(int(style[-1]) - 1) + '"/>' if style.startswith("Heading") else ''
            styles += f'<w:style w:type="paragraph" w:styleId="{style}"><w:name w:val="{style}"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/>{outline}<w:spacing w:before="260" w:after="140"/></w:pPr><w:rPr><w:b/><w:color w:val="344B3F"/><w:sz w:val="{size}"/></w:rPr></w:style>'
        styles += '<w:style w:type="paragraph" w:styleId="Code"><w:name w:val="Code"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="240"/></w:pPr><w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/><w:sz w:val="18"/></w:rPr></w:style>'
        archive.writestr("word/styles.xml", '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' + styles + '</w:styles>')

def main():
    source = source_path()
    write_csv(ROOT / "tables/forms.csv",
        [dict(zip(["id","scenario","location","fields","required","source"], row)) for row in FORMS],
        ["id","scenario","location","fields","required","source"])
    write_csv(ROOT / "tables/acceptance.csv",
        [dict(id=id, group=group, requirement=task, status="NOT RUN", evidence="", notes="")
         for id, group, task in ACCEPTANCE],
        ["id","group","requirement","status","evidence","notes"])
    load = lambda name: json.loads((ROOT / "exports" / (name + ".json")).read_text())
    redirects = load("redirects")
    nginx = ["# Production example. Put map in http{}; review host and query handling.", 'map $uri $molberty_redirect_path {', '    default "";']
    nginx += ['    "' + row["source"] + '" "' + row["target"] + '";' for row in redirects]
    nginx += ["}", "", "# Put the following inside the production server{}, before WordPress routing:",
              '# if ($molberty_redirect_path != "") {',
              '#     return 301 https://www.molberty.ru$molberty_redirect_path$is_args$args;',
              "# }", ""]
    (ROOT / "integration/redirects.nginx.map.conf").write_text("\n".join(nginx))
    apache = ["# Production .htaccess example, before the WordPress block.",
              "# Review the target domain. These are exact path matches, not prefix Redirect directives.",
              "RewriteEngine On"]
    for row in redirects:
        expression = re.escape(row["source"].lstrip("/"))
        apache.append("RewriteRule ^" + expression + "$ https://www.molberty.ru" + row["target"] + " [R=301,L,NE]")
    (ROOT / "integration/redirects.apache.conf").write_text("\n".join(apache) + "\n")
    (ROOT / "integration/README.md").write_text("""# Интеграционные заготовки

Правила содержат только известные 91 переход. До запуска дополнить фактическим обходом старого сайта. Не включать production-домен на staging без замены домена: оператор должен видеть, что именно он проверяет.

Nginx map подключается в http{}, условие return — в server{} перед правилами WordPress. Apache — перед блоком WordPress в .htaccess. Применять только один соответствующий серверу вариант. Проверить конфигурацию штатными nginx -t/apachectl -t.

Фрагмент #!/tproduct/ требует отдельного JS. На всех страницах WordPress сервер должен вывести JSON-элемент molberty-legacy-products с отображением record-product на абсолютный home_url(target). Данные взять из exports/legacy_fragments.json. После этого подключить legacy-fragments.js. Источник нельзя перенаправить по fragment средствами Nginx/PHP: сервер его не получает.

Пример PHP построения: пройти exports/legacy_fragments.json, взять часть после /tproduct/ из source и сопоставить ей home_url(target); вывести через wp_json_encode с JSON_HEX_TAG/AMP/APOS/QUOT. Не вставлять JSON из пользовательского ввода.

Проверить ссылки с UTM, завершающим слешем и Tilda fragment. Не использовать meta refresh HTML прототипа как замену серверному 301.
""", encoding="utf-8")
    (ROOT / ".gitignore").write_text("/reference/\n/source-documents/\n__pycache__/\n*.pyc\n/target-check*.json\n/progress.md\n", encoding="utf-8")
    raw = ROOT / "source-documents"
    raw.mkdir(exist_ok=True)
    inputs = [
        "Структура.doc", "Контрагенты.doc",
        "molberty.ru - теги и мета-теги 02.xlsx",
        "molberty.ru - теги и мета-теги v2.xlsx",
        "molberty.ru - распределение запросов(1).xlsx",
        "Praiss_total_2026.pdf", "Сертификат ГОСТ Р Мольберты.pdf",
        "docs/Выписка из реестра СМП.pdf", "docs/Выписка ЕГРИП_06_26.pdf", "docs/Реквизиты.pdf",
    ]
    source_documents = []
    for name in inputs:
        file = REPO / name
        if not file.is_file():
            file = raw / Path(name).name
        if not file.is_file():
            raise RuntimeError("Missing original input: " + name)
        target = raw / Path(name).name
        if file.resolve() != target.resolve():
            shutil.copy2(file, target)
        source_documents.append(dict(path="source-documents/" + target.name, bytes=target.stat().st_size,
            sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    (raw / "README.md").write_text("""# Исходные документы заказчика

Эта папка включена в полный передаваемый ZIP, но не добавляется в публичный GitHub вместе с рабочими инструментами. Для самой миграции использовать актуальные exports и HTML v129. Исходные документы и старые SEO-таблицы служат для справки и не отменяют последующие согласованные правки.

Финальные title/description/keywords/h1 — в exports/routes.json, структура — в exports/categories.json. Бизнес-PDF уже есть и в assets/documents эталона.
""", encoding="utf-8")
    source_documents.append(dict(path="source-documents/README.md", bytes=(raw/"README.md").stat().st_size,
        sha256=hashlib.sha256((raw/"README.md").read_bytes()).hexdigest()))
    write_json(ROOT / "checks/source-documents-manifest.json", source_documents)
    plugin = ROOT / "wordpress/molberty-migration-tools"
    with zipfile.ZipFile(ROOT / "wordpress/molberty-migration-tools.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in sorted(plugin.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(plugin.parent).as_posix())
    blocks = source / "cms/wordpress/molberty-home-blocks"
    with zipfile.ZipFile(ROOT / "wordpress/molberty-home-blocks.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in sorted(blocks.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(blocks.parent).as_posix())
    sheets = []
    sheets.append(("Сводка", [["Показатель","Значение"]] + [[key, value] for key, value in json.loads((ROOT/"snapshot.json").read_text()).items()]))
    for title, name in [("URL и SEO","routes-seo"),("Категории","categories"),("Товары","products"),
                        ("Редиректы","redirects"),("Старые Tilda-ссылки","legacy-fragments"),
                        ("Медиа","media"),("Формы","forms"),("Приемка","acceptance")]:
        with (ROOT / "tables" / (name + ".csv")).open(encoding="utf-8-sig") as handle:
            sheets.append((title,list(csv.reader(handle))))
    fixtures = load("pricing-fixtures")
    keys = list(fixtures[0])
    sheets.append(("Проверка цен", [keys] + [[row[key] for key in keys] for row in fixtures]))
    xlsx(ROOT / "Карта переноса.xlsx", sheets)
    docx(ROOT / "План переноса на WordPress.docx")
    print(json.dumps({"officeFiles":2,"sheets":len(sheets),"forms":len(FORMS),
                      "acceptanceChecks":len(ACCEPTANCE),"sourceDocuments":len(source_documents)-1,
                      "pluginZips":2}, ensure_ascii=False))

if __name__ == "__main__":
    main()
