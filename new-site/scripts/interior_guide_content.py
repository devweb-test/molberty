"""Page-scoped assets for the interior easel guide and measurement wizard."""

def interior_guide_assets(prefix, content):
    if 'id="category" data-id="molberty-dekorativnye"' not in content:
        return ''
    return (f'<link rel="stylesheet" href="{prefix}assets/interior-guide.css?v=60">'
            f'<script defer src="{prefix}assets/interior-guide.js?v=60"></script>')
