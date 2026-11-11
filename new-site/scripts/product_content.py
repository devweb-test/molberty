"""Shared product headings, metadata and public URL slugs."""
import re
import unicodedata

EASEL_ROOTS = {'molberty-dlya-risovaniya-hudozhnikov', 'molberty-dlya-vystavki', 'molberty-dekorativnye'}
TRANSLITERATION = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
 ['a','b','v','g','d','e','e','zh','z','i','y','k','l','m','n','o','p','r','s','t','u','f','kh','ts','ch','sh','shch','','y','','e','yu','ya']))


def is_easel(product):
    return bool(EASEL_ROOTS.intersection(product['categories']))


def product_heading(product):
    if not is_easel(product) or re.search('мольберт', product['name'], re.I):
        return product['name']
    if product['id'] == 'planshet-nastolnyy-grafika':
        return 'Мольберт-планшет настольный "Графика"'
    if product['id'] == 'trenogi-dlya-foto-ramok':
        return 'Мольберты-треноги для фото-рамок'
    return 'Мольберт ' + product['name']


def product_meta_description(product):
    return product_heading(product) + ' купить по выгодной цене от производителя Мольберты.ру. Описание и характеристики. Доставка по Москве и во все регионы России.'


def product_slug(product):
    if not is_easel(product):
        return product['id']
    heading = unicodedata.normalize('NFKC', product_heading(product)).lower()
    latin = ''.join(TRANSLITERATION.get(char, char) for char in heading)
    return re.sub('[^a-z0-9]+', '-', latin).strip('-')


def product_route(product):
    return 'product/' + product_slug(product) + '/'
