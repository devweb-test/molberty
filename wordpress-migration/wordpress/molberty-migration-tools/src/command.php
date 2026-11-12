<?php
declare(strict_types=1);

/** Initial import helpers. Every public record is a draft until theme/core are ready. */
final class Molberty_Migration_Command {
    private string $exports;
    private string $source;
    private bool $update = false;
    private array $media = [];
    private array $terms = [];
    private array $counts = ['created' => 0, 'updated' => 0, 'skipped' => 0];

    private function read(string $name): array {
        $file = $this->exports . '/' . $name . '.json';
        if (!is_file($file)) {
            throw new RuntimeException('Missing export: ' . $name);
        }
        $data = json_decode(file_get_contents($file), true, 512, JSON_THROW_ON_ERROR);
        if (!is_array($data)) {
            throw new RuntimeException('Invalid export: ' . $name);
        }
        return $data;
    }

    private function find(string $key): int {
        $ids = get_posts([
            'post_type' => ['product', 'post', 'page', 'molberty_client', 'molberty_review', 'molberty_case'],
            'post_status' => 'any', 'numberposts' => 2, 'fields' => 'ids',
            'meta_key' => '_molberty_source_key', 'meta_value' => $key,
        ]);
        if (count($ids) > 1) {
            throw new RuntimeException('Duplicate stable key: ' . $key);
        }
        return (int) ($ids[0] ?? 0);
    }

    private function meta(int $id, string $key, $value): void {
        update_post_meta($id, $key, wp_slash($value));
    }

    private function existing(int $id): bool {
        if ($id && !$this->update) {
            $this->counts['skipped']++;
            return true;
        }
        return false;
    }

    private function slug_available(string $slug, string $type, int $own_id): void {
        $found = get_page_by_path($slug, OBJECT, $type);
        if ($found && (int) $found->ID !== $own_id) {
            throw new RuntimeException('Slug is owned by another record: ' . $type . '/' . $slug);
        }
    }

    private function upsert(string $key, string $type, string $slug, string $title,
                            string $content, array $payload, array $seo = []): int {
        $id = $this->find($key);
        if ($this->existing($id)) {
            return $id;
        }
        $this->slug_available($slug, $type, $id);
        $args = [
            'ID' => $id, 'post_type' => $type, 'post_name' => $slug, 'post_title' => $title,
            'post_content' => $content, 'post_status' => $id ? get_post_status($id) : 'draft',
        ];
        $result = wp_insert_post(wp_slash($args), true);
        if (is_wp_error($result)) {
            throw new RuntimeException($result->get_error_message());
        }
        $result = (int) $result;
        $this->meta($result, '_molberty_source_key', $key);
        $this->meta($result, '_molberty_payload', $payload);
        if ($seo) {
            $this->meta($result, '_molberty_seo', $seo);
        }
        $this->counts[$id ? 'updated' : 'created']++;
        return $result;
    }

    private function asset_url(string $path): string {
        return isset($this->media[$path])
            ? (string) wp_get_attachment_url($this->media[$path])
            : get_stylesheet_directory_uri() . '/assets/' . $path;
    }

    private function markup(string $value): string {
        $value = preg_replace_callback('~\{\{asset\}\}/([^"\'<>\s]+)~',
            fn($m) => esc_url($this->asset_url(html_entity_decode($m[1], ENT_QUOTES, 'UTF-8'))), $value);
        return str_replace('{{site}}', untrailingslashit(home_url('/')), $value);
    }

    private function load_media_map(): void {
        $this->media = [];
        $ids = get_posts(['post_type' => 'attachment', 'post_status' => 'inherit',
            'numberposts' => -1, 'fields' => 'ids', 'meta_key' => '_molberty_asset_path']);
        foreach ($ids as $id) {
            $key = (string) get_post_meta($id, '_molberty_asset_path', true);
            if (isset($this->media[$key])) {
                throw new RuntimeException('Duplicate media key: ' . $key);
            }
            $this->media[$key] = (int) $id;
        }
    }

    private function import_media(): void {
        require_once ABSPATH . 'wp-admin/includes/file.php';
        require_once ABSPATH . 'wp-admin/includes/media.php';
        require_once ABSPATH . 'wp-admin/includes/image.php';
        $assets = realpath($this->source . '/assets');
        if (!$assets) {
            throw new RuntimeException('Missing local assets');
        }
        foreach ($this->read('media') as $item) {
            if (!$item['importToMediaLibrary']) {
                continue;
            }
            $key = $item['path'];
            $file = realpath($assets . '/' . $key);
            if (!$file || !str_starts_with($file, $assets . DIRECTORY_SEPARATOR) ||
                hash_file('sha256', $file) !== $item['sha256']) {
                throw new RuntimeException('Missing or changed asset: ' . $key);
            }
            if (isset($this->media[$key])) {
                if (get_post_meta($this->media[$key], '_molberty_asset_sha256', true) !== $item['sha256']) {
                    throw new RuntimeException('Media key changed; prepare an explicit update: ' . $key);
                }
                $this->counts['skipped']++;
                continue;
            }
            $tmp = wp_tempnam(basename($file));
            if (!$tmp || !copy($file, $tmp)) {
                throw new RuntimeException('Cannot copy media: ' . $key);
            }
            $id = media_handle_sideload(['name' => basename($file), 'tmp_name' => $tmp], 0, $item['alt']);
            if (is_wp_error($id)) {
                @unlink($tmp);
                throw new RuntimeException('Media error ' . $key . ': ' . $id->get_error_message());
            }
            $id = (int) $id;
            $this->media[$key] = $id;
            $this->meta($id, '_molberty_asset_path', $key);
            $this->meta($id, '_molberty_asset_sha256', $item['sha256']);
            $this->meta($id, '_wp_attachment_image_alt', $item['alt']);
            $this->counts['created']++;
        }
    }

    private function import_categories(bool $write): void {
        $categories = $this->read('categories');
        usort($categories, static fn($a, $b) => $a['depth'] <=> $b['depth']);
        foreach ($categories as $item) {
            $term = get_term_by('slug', $item['id'], 'product_cat');
            if ($term && get_term_meta($term->term_id, '_molberty_category_id', true) !== $item['id']) {
                throw new RuntimeException('Unowned category slug: ' . $item['id']);
            }
            if (!$write && !$term) {
                continue;
            }
            if ($write && (!$term || $this->update)) {
                $parent = $item['parentId'] === null ? 0 : ($this->terms[$item['parentId']] ?? null);
                if ($parent === null) {
                    throw new RuntimeException('Missing parent: ' . $item['parentId']);
                }
                $args = ['slug' => $item['id'], 'parent' => $parent, 'description' => $item['description']];
                $result = $term
                    ? wp_update_term($term->term_id, 'product_cat', array_merge($args, ['name' => $item['name']]))
                    : wp_insert_term($item['name'], 'product_cat', $args);
                if (is_wp_error($result)) {
                    throw new RuntimeException($result->get_error_message());
                }
                $term_id = (int) $result['term_id'];
                update_term_meta($term_id, '_molberty_category_id', $item['id']);
                update_term_meta($term_id, '_molberty_payload', wp_slash($item));
                update_term_meta($term_id, '_molberty_seo', wp_slash($item['seo']));
                if (isset($this->media[$item['image']])) {
                    update_term_meta($term_id, 'thumbnail_id', $this->media[$item['image']]);
                }
                $this->counts[$term ? 'updated' : 'created']++;
            } else {
                $term_id = (int) $term->term_id;
                if ($write) {
                    $this->counts['skipped']++;
                }
            }
            $this->terms[$item['id']] = $term_id;
        }
    }

    private function import_products(): void {
        foreach ($this->read('products') as $item) {
            $key = 'product:' . $item['sourceId'];
            $id = $this->find($key);
            if ($this->existing($id)) {
                continue;
            }
            $this->slug_available($item['slug'], 'product', $id);
            $sku_owner = wc_get_product_id_by_sku($item['id']);
            if ($sku_owner && $sku_owner !== $id) {
                throw new RuntimeException('SKU collision: ' . $item['id']);
            }
            $category_ids = [];
            foreach ($item['categories'] as $slug) {
                if (!isset($this->terms[$slug])) {
                    throw new RuntimeException('Import categories first: ' . $slug);
                }
                $category_ids[] = $this->terms[$slug];
            }
            $product = $id ? wc_get_product($id) : new WC_Product_Simple();
            if (!$product) {
                throw new RuntimeException('Invalid product ID');
            }
            $product->set_name($item['h1']);
            $product->set_slug($item['slug']);
            $product->set_sku($item['id']);
            $product->set_status($id ? $product->get_status() : 'draft');
            $product->set_description(wp_kses_post($this->markup($item['descriptionHtml'])));
            $product->set_short_description($item['size']);
            $product->set_regular_price((string) $item['listingPrice']);
            $product->set_manage_stock(false);
            $product->set_category_ids($category_ids);
            if (isset($this->media[$item['image']])) {
                $product->set_image_id($this->media[$item['image']]);
            }
            $gallery = [];
            foreach ($item['gallery'] as $image) {
                if (isset($this->media[$image['file']])) {
                    $gallery[] = $this->media[$image['file']];
                }
            }
            // WooCommerce already renders the featured image; do not repeat it in the gallery.
            $featured_id = (int) $product->get_image_id();
            $gallery = array_values(array_filter(array_unique($gallery),
                static fn($image_id) => (int) $image_id !== $featured_id));
            $product->set_gallery_image_ids($gallery);
            $saved = (int) $product->save();
            $this->meta($saved, '_molberty_source_key', $key);
            $this->meta($saved, '_molberty_source_id', $item['sourceId']);
            $this->meta($saved, '_molberty_id', $item['id']);
            $this->meta($saved, '_molberty_original_name', $item['name']);
            $this->meta($saved, '_molberty_payload', $item);
            $this->meta($saved, '_molberty_seo', $item['seo']);
            $this->meta($saved, '_molberty_migration_ready', false);
            $this->meta($saved, '_molberty_stock_unknown', true);
            $this->counts[$id ? 'updated' : 'created']++;
        }
    }

    private function import_articles(): void {
        foreach ($this->read('articles') as $item) {
            if ($this->existing($this->find('article:' . $item['id']))) {
                continue;
            }
            $id = $this->upsert('article:' . $item['id'], 'post', $item['id'], $item['h1'],
                wp_kses_post($this->markup($item['contentHtml'])), $item, $item['seo']);
            $image = $item['presentation']['previewImage'] ?? $item['image'];
            if (isset($this->media[$image])) {
                set_post_thumbnail($id, $this->media[$image]);
            }
        }
    }

    private function import_pages(): void {
        foreach ($this->read('pages') as $item) {
            if ($this->existing($this->find('page:' . $item['route']))) {
                continue;
            }
            // No huge prototype HTML in the editor: the theme/Gutenberg implementation follows.
            $seo = array_intersect_key($item, array_flip(['title', 'description', 'keywords', 'h1']));
            $id = $this->upsert('page:' . $item['route'], 'page', $item['id'], $item['h1'], '', $item, $seo);
            $this->meta($id, '_molberty_route', $item['route']);
        }
    }

    private function import_collections(): void {
        foreach ($this->read('clients')['clients'] as $item) {
            if ($this->existing($this->find('client:' . $item['id']))) {
                continue;
            }
            $id = $this->upsert('client:' . $item['id'], 'molberty_client', $item['id'], $item['name'], '', $item);
            $image = $item['logo']['file'] ?? '';
            if (isset($this->media[$image])) {
                set_post_thumbnail($id, $this->media[$image]);
            }
        }
        foreach ($this->read('reviews')['items'] as $index => $item) {
            $key = sprintf('review-%02d', $index + 1);
            if ($this->existing($this->find('review:' . $key))) {
                continue;
            }
            $id = $this->upsert('review:' . $key, 'molberty_review', $key, $item['name'],
                wp_kses_post(wpautop($item['text'])), array_merge($item, ['is_demo' => true]));
            if (isset($this->media[$item['photo']])) {
                set_post_thumbnail($id, $this->media[$item['photo']]);
            }
        }
        foreach ($this->read('showcase') as $item) {
            if ($this->existing($this->find('case:' . $item['id']))) {
                continue;
            }
            $id = $this->upsert('case:' . $item['id'], 'molberty_case', $item['id'], $item['name'],
                wp_kses_post(wpautop($item['description'])), $item);
            if (isset($this->media[$item['image']])) {
                set_post_thumbnail($id, $this->media[$item['image']]);
            }
        }
    }

    /**
     * Import approved exports in dependency order.
     *
     * ## OPTIONS
     * <exports>
     * : Absolute path to the exports folder.
     * --source=<source>
     * : Local approved new-site folder.
     * [--dry-run]
     * : Validate inputs and list counts; no writes.
     * [--only=<steps>]
     * : Comma-separated media,categories,products,articles,pages,collections,settings.
     * [--update-existing]
     * : Explicitly overwrite records already owned by this importer.
     * [--allow-production]
     * : Explicit operator override after backup; default production is refused.
     * [--report=<path>]
     * : Write JSON report to a local file.
     */
    public function import(array $args, array $assoc): void {
        try {
            $this->exports = realpath($args[0]) ?: '';
            $this->source = realpath($assoc['source'] ?? '') ?: '';
            if (!$this->exports || !$this->source || !is_file($this->source . '/data/catalog.json')) {
                throw new RuntimeException('Provide valid exports and --source paths');
            }
            $this->update = isset($assoc['update-existing']);
            $steps = isset($assoc['only']) ? explode(',', $assoc['only'])
                : ['media', 'categories', 'products', 'articles', 'pages', 'collections', 'settings'];
            $allowed = ['media', 'categories', 'products', 'articles', 'pages', 'collections', 'settings'];
            if (array_diff($steps, $allowed)) {
                throw new RuntimeException('Unknown --only step');
            }
            $summary = ['products' => count($this->read('products')), 'categories' => count($this->read('categories')),
                'articles' => count($this->read('articles')), 'pages' => count($this->read('pages')),
                'clients' => count($this->read('clients')['clients']), 'reviews' => count($this->read('reviews')['items']),
                'showcase' => count($this->read('showcase')), 'steps' => $steps];
            if (isset($assoc['dry-run'])) {
                WP_CLI::line(wp_json_encode(['dryRun' => true, 'counts' => $summary], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
                return;
            }
            if (wp_get_environment_type() === 'production' && !isset($assoc['allow-production'])) {
                throw new RuntimeException('Refusing production. Use staging or explicit --allow-production after backup.');
            }
            if (!class_exists('WC_Product_Simple') || !taxonomy_exists('product_cat')) {
                throw new RuntimeException('Activate WooCommerce before applying the import');
            }
            $this->load_media_map();
            if (in_array('media', $steps, true)) {
                $this->import_media();
            }
            $this->import_categories(in_array('categories', $steps, true));
            if (in_array('products', $steps, true)) {
                $this->import_products();
            }
            if (in_array('articles', $steps, true)) {
                $this->import_articles();
            }
            if (in_array('pages', $steps, true)) {
                $this->import_pages();
            }
            if (in_array('collections', $steps, true)) {
                $this->import_collections();
            }
            if (in_array('settings', $steps, true)) {
                update_option('molberty_migration_source_settings', $this->read('settings'), false);
            }
            $report = ['success' => true, 'counts' => $this->counts, 'sourceCounts' => $summary,
                       'createdRecordsStatus' => 'draft', 'completeWordPressMigration' => false];
            if (isset($assoc['report'])) {
                if (file_put_contents($assoc['report'], wp_json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE)) === false) {
                    throw new RuntimeException('Cannot write report');
                }
            }
            WP_CLI::line(wp_json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
        } catch (Throwable $error) {
            WP_CLI::error($error->getMessage());
        }
    }

    /**
     * Verify imported stable keys and category assignments (not public page readiness).
     *
     * ## OPTIONS
     * <exports>
     * : Absolute path to exports.
     * [--report=<path>]
     * : Write JSON report.
     */
    public function verify(array $args, array $assoc): void {
        try {
            $this->exports = realpath($args[0]) ?: '';
            $errors = [];
            $this->import_categories(false);
            $this->load_media_map();
            foreach ($this->read('products') as $item) {
                $id = $this->find('product:' . $item['sourceId']);
                if (!$id || get_post_meta($id, '_molberty_id', true) !== $item['id']) {
                    $errors[] = 'Missing product ' . $item['id'];
                    continue;
                }
                if (get_post($id)->post_name !== $item['slug']) {
                    $errors[] = 'Product slug ' . $item['id'];
                }
                $payload = get_post_meta($id, '_molberty_payload', true);
                if (($payload['options'] ?? null) !== $item['options']) {
                    $errors[] = 'Product options ' . $item['id'];
                }
                $actual = wp_get_object_terms($id, 'product_cat', ['fields' => 'slugs']);
                sort($actual); $expected = $item['categories']; sort($expected);
                if ($actual !== $expected) {
                    $errors[] = 'Product categories ' . $item['id'];
                }
                $product = wc_get_product($id);
                $featured = $this->media[$item['image']] ?? 0;
                $gallery = [];
                foreach ($item['gallery'] as $image) {
                    $image_id = $this->media[$image['file']] ?? 0;
                    if ($image_id && $image_id !== $featured) {
                        $gallery[] = $image_id;
                    }
                }
                $gallery = array_values(array_unique($gallery));
                if (!$product || (int) $product->get_image_id() !== $featured ||
                    $product->get_gallery_image_ids() !== $gallery) {
                    $errors[] = 'Product images ' . $item['id'];
                }
            }
            foreach ($this->read('categories') as $item) {
                $id = $this->terms[$item['id']] ?? 0;
                $term = $id ? get_term($id, 'product_cat') : null;
                $parent = $item['parentId'] === null ? 0 : ($this->terms[$item['parentId']] ?? -1);
                if (!$term || (int) $term->parent !== $parent) {
                    $errors[] = 'Category hierarchy ' . $item['id'];
                }
            }
            foreach ($this->read('articles') as $item) {
                if (!$this->find('article:' . $item['id'])) {
                    $errors[] = 'Missing article ' . $item['id'];
                }
            }
            foreach ($this->read('pages') as $item) {
                if (!$this->find('page:' . $item['route'])) {
                    $errors[] = 'Missing page ' . $item['route'];
                }
            }
            foreach ($this->read('clients')['clients'] as $item) {
                if (!$this->find('client:' . $item['id'])) {
                    $errors[] = 'Missing client ' . $item['id'];
                }
            }
            foreach ($this->read('reviews')['items'] as $index => $item) {
                if (!$this->find(sprintf('review:review-%02d', $index + 1))) {
                    $errors[] = 'Missing review ' . ($index + 1);
                }
            }
            foreach ($this->read('showcase') as $item) {
                if (!$this->find('case:' . $item['id'])) {
                    $errors[] = 'Missing case ' . $item['id'];
                }
            }
            foreach ($this->read('media') as $item) {
                if (!$item['importToMediaLibrary']) {
                    continue;
                }
                $media_id = $this->media[$item['path']] ?? 0;
                if (!$media_id || get_post_meta($media_id, '_molberty_asset_sha256', true) !== $item['sha256']) {
                    $errors[] = 'Missing or changed media ' . $item['path'];
                }
            }
            $report = ['passed' => !$errors, 'scope' => 'imported keys, options, category hierarchy',
                       'errors' => $errors, 'frontendAndCheckoutVerified' => false];
            if (isset($assoc['report'])) {
                file_put_contents($assoc['report'], wp_json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
            }
            WP_CLI::line(wp_json_encode($report, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
            if ($errors) {
                WP_CLI::halt(1);
            }
        } catch (Throwable $error) {
            WP_CLI::error($error->getMessage());
        }
    }
}
