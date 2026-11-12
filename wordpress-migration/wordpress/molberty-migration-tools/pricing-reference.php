<?php
declare(strict_types=1);
/**
 * Reference calculator ported from v129. No WooCommerce hooks or payment behavior.
 * Reuse in molberty-core only after integration tests with cart and checkout.
 */
final class Molberty_Reference_Pricing {
    public static function values(array $option): array {
        $values = [];
        foreach ($option['values'] as $index => $value) {
            if (trim((string) $value['label']) !== '') {
                $values[$index] = $value;
            }
        }
        $absolute = array_filter($values, static fn($v) => $v['mode'] === 'absolute');
        return $absolute ?: $values;
    }

    public static function quote(array $product, string $tier, array $indices, int $quantity): array {
        $wholesale_only = !empty($product['wholesaleOnly']);
        if (!in_array($tier, ['retail', 'wholesale'], true) ||
            ($tier === 'retail' && $wholesale_only) ||
            ($tier === 'wholesale' && $product['wholesalePrice'] === null && !$wholesale_only)) {
            throw new InvalidArgumentException('Unavailable price tier');
        }
        if (count($indices) !== count($product['options'])) {
            throw new InvalidArgumentException('Invalid option count');
        }
        $minimum = max((int) ($product['minimumOrder'] ?? 1),
            $tier === 'wholesale' ? (int) ($product['wholesaleMin'] ?: 1) : 1);
        if ($quantity < $minimum || $quantity > 999) {
            throw new InvalidArgumentException('Invalid quantity');
        }
        $base = $tier === 'wholesale'
            ? ($product['wholesalePrice'] ?? $product['retailPrice'])
            : $product['retailPrice'];
        $delta = 0;
        $price_index = $product['priceOptionIndex'];
        if ($price_index !== null) {
            foreach ($product['options'][$price_index]['values'] as $value) {
                $pattern = $tier === 'wholesale' ? '/опт/ui' : '/розниц/ui';
                if (preg_match($pattern, $value['label']) && $value['price'] !== null) {
                    $base = $value['price'];
                    break;
                }
            }
        }
        foreach ($product['options'] as $index => $option) {
            $selected = $indices[$index] ?? null;
            if (!is_int($selected) || $selected < 0) {
                throw new InvalidArgumentException('Invalid option index');
            }
            $allowed = self::values($option);
            if ($allowed && !array_key_exists($selected, $allowed)) {
                throw new InvalidArgumentException('Unavailable option value');
            }
            if (!$allowed && $selected !== 0) {
                throw new InvalidArgumentException('Invalid empty option value');
            }
            if ($index === $price_index || (isset($option['priceTier']) && $option['priceTier'] !== $tier)) {
                continue;
            }
            $value = $option['values'][$selected] ?? null;
            if (!$value) {
                continue;
            }
            if ($value['mode'] === 'absolute') {
                $base = $value['price'];
            } elseif ($value['mode'] === 'delta') {
                $delta += $value['price'];
            }
        }
        if (!is_numeric($base) || !is_numeric($delta) || $base + $delta < 0) {
            throw new InvalidArgumentException('Invalid source price');
        }
        // v129 values are integral RUB. Use integer kopecks in order integration.
        $unit = (float) $base + (float) $delta;
        return [
            'unitPrice' => $unit, 'minQuantity' => $minimum,
            'total' => $unit * $quantity,
            'displayFrom' => $tier === 'wholesale' || !empty($product['retailFrom']),
        ];
    }
}
