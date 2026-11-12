<?php
declare(strict_types=1);
// Minimal contract test only. A real WordPress/WooCommerce installation is still required.
final class WP_CLI {
    public static array $lines = [];
    public static function line(string $value): void { self::$lines[] = $value; }
    public static function error(string $message): void { throw new RuntimeException($message); }
}
function wp_json_encode($value, int $flags = 0): string {
    return json_encode($value, $flags | JSON_THROW_ON_ERROR);
}
$root = dirname(__DIR__);
$source = $root . '/reference/new-site';
if (!is_dir($source)) {
    $source = dirname($root) . '/new-site';
}
require $root . '/wordpress/molberty-migration-tools/src/command.php';
$command = new Molberty_Migration_Command();
$command->import([$root . '/exports'], ['source' => $source, 'dry-run' => true]);
$report = json_decode(WP_CLI::$lines[0], true, 512, JSON_THROW_ON_ERROR);
if (!$report['dryRun'] || $report['counts']['products'] !== 91 || $report['counts']['categories'] !== 34) {
    throw new RuntimeException('Dry run contract failed');
}
echo json_encode(['passed' => true, 'dryRunNoWordPressWrites' => true,
                  'actualWordPressImportTested' => false], JSON_PRETTY_PRINT) . PHP_EOL;
