"""One icon head block for all depths, the Pages subdirectory and future CMS root."""
from html import escape
import re

VERSION = '114'
BLOCK_PATTERN = r'<!-- site-icons:start -->.*?<!-- site-icons:end -->'


def icon_links(prefix=''):
    def asset(path):
        return escape(prefix + path + '?v=' + VERSION, quote=True)

    links = [
        '<!-- site-icons:start -->',
        f'<link rel="icon" href="{asset("favicon.ico")}" type="image/x-icon" sizes="16x16 24x24 32x32 48x48 64x64 128x128 256x256">',
    ]
    for size in (16, 32, 48, 96):
        links.append(f'<link rel="icon" href="{asset(f"assets/icons/favicon-{size}x{size}.png")}" type="image/png" sizes="{size}x{size}">')
    links.append(f'<link rel="icon" href="{asset("assets/favicon.svg")}" type="image/svg+xml" sizes="any">')
    for size in (120, 152, 167, 180):
        path = 'apple-touch-icon.png' if size == 180 else f'assets/icons/apple-touch-icon-{size}x{size}.png'
        links.append(f'<link rel="apple-touch-icon" href="{asset(path)}" sizes="{size}x{size}">')
    links.extend([
        f'<link rel="mask-icon" href="{asset("assets/icons/safari-pinned-tab.svg")}" color="#344b3f">',
        f'<link rel="manifest" href="{asset("site.webmanifest")}">',
        '<meta name="application-name" content="Мольберты.ру">',
        '<meta name="apple-mobile-web-app-title" content="Мольберты.ру">',
        '<meta name="msapplication-TileColor" content="#34483d">',
        f'<meta name="msapplication-TileImage" content="{asset("assets/icons/mstile-150x150.png")}">',
        f'<meta name="msapplication-config" content="{asset("browserconfig.xml")}">',
        '<!-- site-icons:end -->',
    ])
    return '\n'.join(links)


def apply_icon_links(document, prefix=''):
    document = re.sub(BLOCK_PATTERN, '', document, flags=re.S)
    document = re.sub(r'<link\b(?=[^>]*\brel="(?:icon|shortcut icon|apple-touch-icon|mask-icon|manifest)")[^>]*>', '', document, flags=re.I)
    document = re.sub(r'<meta\b(?=[^>]*\bname="(?:application-name|apple-mobile-web-app-title|msapplication-[^"]*)")[^>]*>', '', document, flags=re.I)
    assert document.count('</head>') == 1
    return document.replace('</head>', icon_links(prefix) + '</head>', 1)
