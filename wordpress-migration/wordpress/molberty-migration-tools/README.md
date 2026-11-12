# Подготовительный импорт WP-CLI

Это вспомогательный плагин для начального наполнения staging. Он не включает тему, конечный storefront, обработку заказов или редактор всех пользовательских полей. Новые записи создаются черновиками.

Проверено в передаче: PHP syntax и 717 расчётов эталонного калькулятора. В целевой установленной WordPress/WooCommerce импорт необходимо выполнить и проверить отдельно; тест реальной CMS в ходе подготовки пакета не выполнялся.

## Установка

Скопировать папку molberty-migration-tools в wp-content/plugins/. Либо установить ZIP из этой же папки передачи через админку.

    wp plugin activate woocommerce
    wp plugin activate molberty-migration-tools

В wp-config.php staging задать окружение через стандартную константу WP_ENVIRONMENT_TYPE со значением staging; не записывать в команду реальные пароли.

## Первый запуск

Сначала выполнить резервное копирование staging. Абсолютные пути ниже заменить на свои. Запускать команды из каталога установленного WordPress или с его обычным --path.

    wp molberty-migration import /work/wordpress-migration/exports \
      --source=/work/wordpress-migration/reference/new-site --dry-run

    wp molberty-migration import /work/wordpress-migration/exports \
      --source=/work/wordpress-migration/reference/new-site \
      --report=/work/import-report.json

    wp molberty-migration verify /work/wordpress-migration/exports \
      --report=/work/import-verification.json

Порядок: локальные медиа, категории, товары, статьи, страницы, коллекции и общие настройки. При повторе принадлежащие импортеру записи пропускаются, медиа сверяются по пути/SHA256. Независимый этап:

    wp molberty-migration import /work/wordpress-migration/exports \
      --source=/work/wordpress-migration/reference/new-site --only=media

Допустимые этапы --only: media,categories,products,articles,pages,collections,settings. Для товаров категории должны быть уже импортированы. Повторное заполнение существующих собственных записей включается явно --update-existing. Оно заменяет исходные поля; сначала проверить diff/резервную копию. Производственная среда по умолчанию отвергается; --allow-production — отдельное явное действие оператора, не часть обычного начального запуска.

## Что делает импорт

- WooCommerce products: draft, SKU=id, post_name=slug, title=h1, исходное имя отдельно. Опции, режимы, размеры, цены и первичная категория сохраняются в _molberty_payload.
- Категории: product_cat с parent/slug, _molberty_payload и _molberty_seo. Нельзя присвоить чужой терм только из-за совпадения slug.
- Галереи и обложки: локальная медиатека; исходная последовательность и повторные связи полностью остаются в payload.
- Статьи: исходный оформленный текст, локальные URL, draft.
- Страницы: пустые черновики и referenceMainHtml в payload, чтобы будущая тема использовала исходную разметку, а не неуправляемую копию целого прототипа в редакторе.
- Клиенты/отзывы/кейсы: административные CPT с черновиками и исходными полями. Для отзывов сохранён внутренний is_demo; для кейсов fictional.
- Общие данные: option molberty_migration_source_settings без autoload. Окончательная админка/настройки темы создаются molberty-core.

Не меняются автоматически настройки front/posts/shop, структура постоянных ссылок, SMTP, robots, публичный статус, SEO-плагин и платёжные методы. Не удаляется стандартная категория WooCommerce и существующий контент; пустые системные записи при необходимости убираются вебмастером отдельно.

## Медиа и SVG

Импортируются 277 используемых растровых изображений/PDF по exports/media.json. Все 401 файла assets переданы в эталоне. SVG, иконки, стили, шрифты и прочие ресурсы переносить в тему как доверенные локальные файлы. Если медиа пропущены, fallback URL рассчитывается относительно assets активной темы: эти файлы требуется туда скопировать.

## После импорта

Сделать настоящий сервис цены на основе pricing-reference.php, проверить fixtures через tools/test_pricing.php, реализовать шаблоны, URL и поля администратора. _molberty_migration_ready=false — напоминание, что созданный товар ещё не готов к публикации как рабочий магазин. verify проверяет данные, а не готовность интерфейса/форм/корзины.

Калькулятор можно использовать без WordPress:

    php tools/test_pricing.php

Адаптер конечной реализации должен определить функцию molberty_quote_for_test($product,$tier,$indices,$quantity):

    php tools/test_pricing.php /path/to/production-pricing-adapter.php
