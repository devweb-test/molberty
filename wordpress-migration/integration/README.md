# Интеграционные заготовки

Правила содержат только известные 91 переход. До запуска дополнить фактическим обходом старого сайта. Не включать production-домен на staging без замены домена: оператор должен видеть, что именно он проверяет.

Nginx map подключается в http{}, условие return — в server{} перед правилами WordPress. Apache — перед блоком WordPress в .htaccess. Применять только один соответствующий серверу вариант. Проверить конфигурацию штатными nginx -t/apachectl -t.

Фрагмент #!/tproduct/ требует отдельного JS. На всех страницах WordPress сервер должен вывести JSON-элемент molberty-legacy-products с отображением record-product на абсолютный home_url(target). Данные взять из exports/legacy_fragments.json. После этого подключить legacy-fragments.js. Источник нельзя перенаправить по fragment средствами Nginx/PHP: сервер его не получает.

Пример PHP построения: пройти exports/legacy_fragments.json, взять часть после /tproduct/ из source и сопоставить ей home_url(target); вывести через wp_json_encode с JSON_HEX_TAG/AMP/APOS/QUOT. Не вставлять JSON из пользовательского ввода.

Проверить ссылки с UTM, завершающим слешем и Tilda fragment. Не использовать meta refresh HTML прототипа как замену серверному 301.
