"""Shared static document and cookie-notice markup; no build side effects."""
from pathlib import Path
import json
from html import escape

ROOT=Path(__file__).resolve().parents[1]

def cookie_markup(prefix=''):
 data=json.loads((ROOT/'data/cookie-notice.json').read_text())
 text=escape(data['text']);linked=escape(data['linkText'])
 text=text.replace(linked,'<a href="'+prefix+'privacy/">'+linked+'</a>')
 return '<aside id="cookie-notice" class="cookie-notice" role="region" aria-label="Использование файлов cookie" aria-describedby="cookie-message" hidden><p id="cookie-message">'+text+'</p><div class="cookie-actions"><button type="button" class="btn" data-cookie-accept>'+escape(data['button'])+'</button></div></aside>'

def document_markup(id,prefix='../'):
 pages=json.loads((ROOT/'data/legal-pages.json').read_text());page=pages[id];title=escape(page['title'])
 controls=('<a class="text-link" href="'+prefix+'consent/">Соглашение на обработку персональных данных</a><button type="button" class="text-link" data-clear>Удалить сохранённые данные</button>') if id=='privacy' else '<a class="text-link" href="'+prefix+'privacy/">Политика конфиденциальности</a>'
 return '<div id="'+id+'"><section class="wrap page-intro legal-intro"><div class="breadcrumbs"><a href="'+prefix+'index.html">Главная</a><span>/</span>'+title+'</div><div class="eyebrow"><span>Мольберты.ру</span> ДОКУМЕНТЫ</div><h1>'+title+'</h1></section><section class="wrap reading legal-document">'+page['html']+'<div class="legal-actions">'+controls+'</div></section></div>'
