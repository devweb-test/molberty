"""Shared static mobile dock, including usable links before JavaScript loads."""
from html import escape
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def mobile_navigation(prefix='', canonical='https://www.molberty.ru/'):
    route = urlsplit(canonical).path.strip('/')
    categories = {c['id'] for c in json.loads((ROOT / 'data/catalog-structure.json').read_text())['categories']}
    current = 'home' if route in ('', 'index.html') else 'contacts' if route == 'contacts' else 'catalog' if route == 'catalog' or route in categories or route.startswith('product/') else ''
    items = [
        ('home', 'Главная', 'index.html', 'm3 10 9-7 9 7M5 9v12h5v-7h4v7h5V9'),
        ('catalog', 'Каталог', 'catalog/', 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z'),
        ('cart', 'Корзина', None, 'M3 9h18l-2 11H5L3 9Zm4 0 5-6 5 6M9 13v3m6-3v3'),
        ('contacts', 'Контакты', 'contacts/', 'M19 10c0 6-7 11-7 11S5 16 5 10a7 7 0 1 1 14 0ZM15 10a3 3 0 1 1-6 0 3 3 0 0 1 6 0'),
    ]
    links = []
    for key, label, path, drawing in items:
        icon = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="' + drawing + '"/></svg>'
        badge = '<span class="mobile-nav-count" data-mobile-count hidden>0</span>' if key == 'cart' else ''
        content = '<span class="mobile-nav-icon">' + icon + badge + '</span><span>' + label + '</span>'
        if key == 'cart':
            links.append('<button type="button" class="mobile-nav-item" data-mobile-cart disabled aria-label="Открыть корзину">' + content + '</button>')
        else:
            active = (' aria-current="' + ('true' if key == 'catalog' and route != 'catalog' else 'page') + '"') if key == current else ''
            links.append('<a class="mobile-nav-item" href="' + escape(prefix + path, quote=True) + '"' + active + '>' + content + '</a>')
    return '<nav id="mobile-bottom-nav" class="mobile-bottom-nav" aria-label="Быстрая навигация">' + ''.join(links) + '</nav>'
