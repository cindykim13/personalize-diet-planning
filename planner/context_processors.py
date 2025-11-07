"""
Context processors for the planner application.
"""
from pathlib import Path
from django.conf import settings


def brand_assets(request):
    """
    Add processed brand asset paths to template context.
    Checks for new processed images first, falls back to existing ones.
    """
    base_dir = settings.BASE_DIR
    static_dir = base_dir / 'static'
    
    # Check for processed images (prefer transparent versions, fall back to originals)
    logo_transparent = static_dir / 'Logo_transparent.png'
    logo_original = static_dir / 'Logo.png'
    
    brand_transparent = static_dir / 'BrandName_transparent.png'
    brand_original = static_dir / 'BrandName.png'
    
    # Determine logo path with fallback chain
    if logo_transparent.exists():
        logo_path = 'Logo_transparent.png'
    elif logo_original.exists():
        logo_path = 'Logo.png'
    else:
        logo_path = 'Logo.png'  # Default fallback
    
    # Determine brand name path with fallback chain
    if brand_transparent.exists():
        brand_path = 'BrandName_transparent.png'
    elif brand_original.exists():
        brand_path = 'BrandName.png'
    else:
        brand_path = 'BrandName.png'  # Default fallback
    
    return {
        'logo_transparent': logo_path,
        'brand_name_transparent': brand_path,
    }
