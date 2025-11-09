#!/usr/bin/env python
"""
Quick test script to verify TheMealDB integration works correctly.
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from planner.models import Recipe
from planner.utils import get_or_fetch_image_url

# Test with a sample recipe
try:
    # Get first recipe without image
    recipe = Recipe.objects.filter(image_url__isnull=True).first()
    
    if recipe:
        print(f"Testing with recipe: {recipe.name}")
        print(f"Current image_url: {recipe.image_url}")
        
        # Fetch image
        image_url = get_or_fetch_image_url(recipe)
        
        print(f"Fetched image_url: {image_url}")
        
        # Reload from database
        recipe.refresh_from_db()
        print(f"Cached image_url: {recipe.image_url}")
        
        if image_url and image_url != '/static/planner/images/placeholder.png':
            print("✅ SUCCESS: Image URL fetched and cached!")
        else:
            print("⚠ WARNING: Placeholder image returned (recipe may not exist in TheMealDB)")
    else:
        print("ℹ INFO: No recipes without images found. All recipes already have images.")
        
except Exception as e:
    print(f"✗ ERROR: {e}")
    import traceback
    traceback.print_exc()
