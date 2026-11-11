# Набор favicon и иконок устройств

Основа — светлая буква **М** с засечками на зелёном фоне, как на исходном molberty.ru. Начертание взято из локального Prata и переведено в контуры. Вкладки используют компактный вариант с небольшим скруглением; иконки устройств имеют полностью закрашенный квадратный фон, чтобы система сама применила форму. Мелкие размеры имеют оптическую поправку толщины штрихов.

| Назначение | Файлы и размеры |
|---|---|
| Современные браузеры | `assets/favicon.svg`, масштабируемый |
| Резервный favicon | `favicon.ico`: 16, 24, 32, 48, 64, 128, 256 px |
| PNG для вкладок и ярлыков | `assets/icons/favicon-*`: 16, 32, 48, 96 px |
| iPhone и iPad | `apple-touch-icon.png`: 180 px; `assets/icons/apple-touch-icon-*`: 120, 152, 167 px |
| Android, Chrome и Edge | `assets/icons/android-chrome-*`: 192 и 512 px |
| Android с системной маской | `assets/icons/maskable-*`: 192 и 512 px; буква вписана в безопасную центральную область |
| Закреплённые вкладки Safari | `assets/icons/safari-pinned-tab.svg`, одноцветный знак |
| Дополнительная совместимость Windows | `assets/icons/mstile-150x150.png`, `browserconfig.xml` |
| Векторные исходники | `assets/icons/icon-master.svg`, `assets/icons/maskable-master.svg` |

`site.webmanifest` содержит отдельные варианты `any` и `maskable`. Все URL в нём относительные: набор работает в `/molberty/new-site/` на GitHub Pages, в локальном корне и после переноса на основной домен. Manifest задаёт ярлык сайта; офлайн-режим и сервис-воркер не добавлялись.

Общий блок `<head>` формирует `scripts/icon_links.py`. Он подключён ко всем страницам, старым адресам с перенаправлением и 404 с корректной базой. При изменении набора обновите `VERSION`, чтобы браузеры получили новые файлы.

При переносе в CMS скопируйте root-файлы `favicon.ico`, `apple-touch-icon.png`, `site.webmanifest`, `browserconfig.xml` и каталог `assets/icons/` вместе с `assets/favicon.svg`. В WordPress можно использовать PNG 512 px как Иконку сайта; при ручном подключении полного набора избегайте повторных ссылок от темы и SEO-плагинов. Общий логотип «Лира» в шапке, футере и Organization сохранён.

Обычная сборка использует готовые файлы и не требует графических библиотек. Для повторного создания: установить `Pillow`, `CairoSVG`, `fonttools`, затем выполнить `python3 scripts/create-icons.py`. Источник и перечень файлов записаны в `data/icons.json`. Проверка: `python3 scripts/validate-icons.py` или `npm run check`.

Справочные требования: [иконки Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest/Reference/icons), [иконки для iPhone и iPad](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/ConfiguringWebApplications/ConfiguringWebApplications.html).
