"""
Image fetching and caching utilities for recipe images.
Handles Unsplash API integration and database caching.
"""
import requests
from django.conf import settings
from django.core.files.storage import default_storage
import os

# Unsplash API Configuration
UNSPLASH_API_KEY = 'gFAbd5nVq8tjPmYKvbk5WfNWRpnCDc6a1PUwSavF3DY'
UNSPLASH_API_URL = 'https://api.unsplash.com/search/photos'
DEFAULT_PLACEHOLDER = '/static/planner/images/placeholder.png'


def get_or_fetch_image_url(recipe):
    """
    Get or fetch image URL for a recipe from Unsplash API.
    
    Caching Strategy:
    1. Check if recipe.image_url is already populated (Cache Hit)
    2. If empty, fetch from Unsplash API and save to database (Cache Miss)
    3. If API fails, return placeholder image path
    
    :param recipe: Recipe model instance
    :return: Image URL string (either cached, newly fetched, or placeholder)
    """
    # Cache Hit: Return existing URL if available
    if recipe.image_url:
        return recipe.image_url
    
    # Cache Miss: Fetch from Unsplash API
    try:
        # Construct search query: recipe name + "food" for better results
        query = f"{recipe.name} food"
        
        # Prepare API request
        headers = {
            'Authorization': f'Client-ID {UNSPLASH_API_KEY}'
        }
        params = {
            'query': query,
            'per_page': 1,  # Only need first result
            'orientation': 'landscape',  # Better for food photography
        }
        
        # Make API request
        response = requests.get(UNSPLASH_API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract image URL from first result
        if data.get('results') and len(data['results']) > 0:
            first_result = data['results'][0]
            # Use 'regular' size (1080px width) for good quality/performance balance
            image_url = first_result.get('urls', {}).get('regular')
            
            if image_url:
                # Save to database for future cache hits
                recipe.image_url = image_url
                recipe.save(update_fields=['image_url'])
                return image_url
        
        # No results found - use placeholder
        return DEFAULT_PLACEHOLDER
        
    except requests.exceptions.RequestException as e:
        # API call failed - use placeholder
        print(f"[IMAGE_UTILS] Error fetching image for recipe '{recipe.name}': {e}")
        return DEFAULT_PLACEHOLDER
    except Exception as e:
        # Unexpected error - use placeholder
        print(f"[IMAGE_UTILS] Unexpected error fetching image for recipe '{recipe.name}': {e}")
        return DEFAULT_PLACEHOLDER


def get_image_url_for_recipe_dict(recipe_dict, recipe_obj=None):
    """
    Get image URL for a recipe dictionary (from plan data).
    
    This function is used when we have recipe dictionaries from plan data
    but need to fetch/cache images. It tries to get the Recipe object first,
    then falls back to API call if object not available.
    
    :param recipe_dict: Dictionary with recipe data (must have 'id' or 'name')
    :param recipe_obj: Optional Recipe model instance (if already fetched)
    :return: Image URL string
    """
    from .models import Recipe
    
    # Try to get Recipe object if not provided
    if recipe_obj is None:
        recipe_id = recipe_dict.get('id')
        if recipe_id:
            try:
                recipe_obj = Recipe.objects.get(id=recipe_id)
            except Recipe.DoesNotExist:
                recipe_obj = None
    
    # If we have the object, use the caching function
    if recipe_obj:
        return get_or_fetch_image_url(recipe_obj)
    
    # Fallback: Try API call with recipe name
    recipe_name = recipe_dict.get('name', 'food')
    try:
        query = f"{recipe_name} food"
        headers = {
            'Authorization': f'Client-ID {UNSPLASH_API_KEY}'
        }
        params = {
            'query': query,
            'per_page': 1,
            'orientation': 'landscape',
        }
        
        response = requests.get(UNSPLASH_API_URL, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data.get('results') and len(data['results']) > 0:
            first_result = data['results'][0]
            image_url = first_result.get('urls', {}).get('regular')
            if image_url:
                return image_url
    except Exception as e:
        print(f"[IMAGE_UTILS] Error fetching image for recipe '{recipe_name}': {e}")
    
    # Final fallback: placeholder
    return DEFAULT_PLACEHOLDER

