<?php
/**
 * Plugin Name: Мольберты.ру - блоки главной
 * Description: Редактируемые блоки Кейсы и Творчество объединяет с независимым управлением видимостью.
 * Version: 1.0.0
 * Requires at least: 6.3
 * Requires PHP: 7.4
 * Text Domain: molberty-home-blocks
 */

defined('ABSPATH') || exit;

function molberty_home_blocks_register() {
    wp_register_script(
        'molberty-home-blocks-editor',
        plugins_url('editor.js', __FILE__),
        array('wp-blocks', 'wp-block-editor', 'wp-components', 'wp-element'),
        '1.0.0',
        true
    );
    wp_register_style('molberty-home-blocks', plugins_url('style.css', __FILE__), array(), '1.0.0');

    foreach (array('cases', 'partners') as $kind) {
        register_block_type(__DIR__ . '/blocks/' . $kind, array(
            'render_callback' => static function ($attributes, $content) use ($kind) {
                // Keep saved inner blocks editable, but omit disabled sections from public HTML.
                if (!isset($attributes['enabled']) || true !== $attributes['enabled']) {
                    return '';
                }
                $class = 'molberty-home-block ' . ('cases' === $kind ? 'cases-section' : 'partner-showcase');
                return '<section ' . get_block_wrapper_attributes(array('class' => $class)) . '>' . $content . '</section>';
            },
        ));
    }
}
add_action('init', 'molberty_home_blocks_register');
