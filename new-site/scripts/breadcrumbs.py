"""Compact mobile counterpart of the full desktop breadcrumb trail."""
from html import escape


def mobile_breadcrumb(href, label):
    title = escape(label, quote=True)
    return '<a class="mobile-breadcrumb" href="' + escape(href, quote=True) + '" title="' + title + '" aria-label="Назад: ' + title + '"><svg class="icon " viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6"></path></svg><span>' + escape(label) + '</span></a>'
