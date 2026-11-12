<?php
declare(strict_types=1);
/**
 * php tools/test_pricing.php [implementation.php]
 * Optional implementation file must define molberty_quote_for_test($p,$tier,$indices,$qty).
 */
$root = dirname(__DIR__);
if (isset($argv[1])) {
    require $argv[1];
    if (!function_exists('molberty_quote_for_test')) {
        throw new RuntimeException('Implementation must define molberty_quote_for_test');
    }
    $calculator = 'molberty_quote_for_test';
} else {
    require $root . '/wordpress/molberty-migration-tools/pricing-reference.php';
    $calculator = [Molberty_Reference_Pricing::class, 'quote'];
}
$products = json_decode(file_get_contents($root . '/exports/products.json'), true, 512, JSON_THROW_ON_ERROR);
$fixtures = json_decode(file_get_contents($root . '/exports/pricing-fixtures.json'), true, 512, JSON_THROW_ON_ERROR);
$by_id = array_column($products, null, 'id');
$failures = [];
foreach ($fixtures as $index => $fixture) {
    try {
        $actual = $calculator($by_id[$fixture['productId']], $fixture['tier'], $fixture['indices'], $fixture['quantity']);
        foreach (['unitPrice', 'minQuantity', 'total'] as $key) {
            if (!isset($actual[$key]) || abs($actual[$key] - $fixture[$key]) > 0.000001) {
                throw new RuntimeException('Mismatch ' . $key);
            }
        }
        if ($actual['displayFrom'] !== $fixture['displayFrom']) {
            throw new RuntimeException('Mismatch displayFrom');
        }
    } catch (Throwable $error) {
        $failures[] = ['fixture' => $index, 'id' => $fixture['productId'], 'error' => $error->getMessage()];
    }
}
$negative = 0;
$must_fail = static function ($product, $tier, $indices, $qty) use ($calculator, &$negative, &$failures) {
    try {
        $calculator($product, $tier, $indices, $qty);
        $failures[] = ['id' => $product['id'], 'error' => 'Invalid input was accepted'];
    } catch (InvalidArgumentException $expected) {
        $negative++;
    }
};
foreach ($fixtures as $fixture) {
    if ($fixture['minQuantity'] > 1 && $fixture['tier'] === 'wholesale') {
        $must_fail($by_id[$fixture['productId']], 'wholesale', $fixture['indices'], $fixture['minQuantity'] - 1);
        break;
    }
}
$first = $fixtures[0];
$p = $by_id[$first['productId']];
$must_fail($p, 'unknown', $first['indices'], $first['quantity']);
$must_fail($p, $first['tier'], $first['indices'], 1000);
$bad = $first['indices']; $bad[0] = 99999;
$must_fail($p, $first['tier'], $bad, $first['quantity']);
foreach ($fixtures as $fixture) {
    if (!empty($by_id[$fixture['productId']]['wholesaleOnly'])) {
        $must_fail($by_id[$fixture['productId']], 'retail', $fixture['indices'], $fixture['quantity']);
        break;
    }
}
$report = ['passed' => !$failures, 'fixtures' => count($fixtures),
           'negativeTests' => $negative, 'failures' => $failures];
echo json_encode($report, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT) . PHP_EOL;
exit($failures ? 1 : 0);
