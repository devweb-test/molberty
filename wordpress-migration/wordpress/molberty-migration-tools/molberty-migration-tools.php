<?php
/**
 * Plugin Name: Мольберты.ру — подготовительный импорт
 * Description: WP-CLI импорт согласованного каталога и контента в черновики. Не является темой или модулем магазина.
 * Version: 0.1.0
 * Requires PHP: 8.3
 */
defined('ABSPATH') || exit;

add_action('init', static function () {
    foreach ([
        'molberty_client' => 'Клиенты',
        'molberty_review' => 'Отзывы',
        'molberty_case' => 'Примеры пространств',
    ] as $type => $label) {
        register_post_type($type, [
            'label' => $label, 'public' => false, 'show_ui' => true, 'show_in_rest' => true,
            'supports' => ['title', 'editor', 'excerpt', 'thumbnail', 'custom-fields'],
            'capability_type' => 'post', 'map_meta_cap' => true,
        ]);
    }
});

if (defined('WP_CLI') && WP_CLI) {
    require_once __DIR__ . '/src/command.php';
    WP_CLI::add_command('molberty-migration', Molberty_Migration_Command::class);
}
