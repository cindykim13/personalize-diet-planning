"""
Multi-source image fetching and caching service using Chain of Responsibility pattern.

This module implements a robust, two-tier image retrieval system:
1. Database Cache (fastest - no API calls)
2. Spoonacular API (primary source - food-specific)
3. Unsplash API (fallback - general food photography)
4. Placeholder (final fallback - always available)

All fetched URLs are cached in the database to minimize API calls and improve performance.
"""
import requests
import time
from typing import Optional
from django.core.exceptions import ObjectDoesNotExist

# API Configuration
SPOONACULAR_API_KEY = '4c44d698ce9b4acf88bf7d3207570df2'
SPOONACULAR_API_URL = 'https://api.spoonacular.com/recipes/complexSearch'
UNSPLASH_API_KEY = 'gFAbd5nVq8tjPmYKvbk5WfNWRpnCDc6a1PUwSavF3DY'
UNSPLASH_API_URL = 'https://api.unsplash.com/search/photos'
DEFAULT_PLACEHOLDER = '/static/planner/images/placeholder.png'

# Request timeout (seconds)
API_TIMEOUT = 10

# Rate limiting: delay between API calls (seconds)
API_DELAY = 0.5


def get_or_fetch_image_url(recipe_id: int) -> str:
    """
    Get or fetch image URL for a recipe using Chain of Responsibility pattern.
    
    Execution Flow:
    1. Check Database Cache (Cache Hit) - Return immediately if found
    2. Attempt Spoonacular API (Primary Source) - Food-specific, high quality
    3. Attempt Unsplash API (Fallback Source) - General food photography
    4. Return Placeholder (Final Fallback) - Always available
    
    CRITICAL: All successful API fetches are cached in the database for future use.
    
    :param recipe_id: Integer ID of the Recipe object
    :return: Image URL string (cached, fetched, or placeholder)
    """
    from .models import Recipe
    
    # Step 1: Check Database Cache (Cache Hit)
    try:
        recipe = Recipe.objects.get(id=recipe_id)
        
        # Cache Hit: Return existing URL immediately (no API calls)
        if recipe.image_url:
            return recipe.image_url
        
        # Cache Miss: Proceed to API fetching
        recipe_name = recipe.name
        
    except Recipe.DoesNotExist:
        # Recipe doesn't exist - return placeholder
        print(f"[IMAGE_SERVICE] Recipe ID {recipe_id} not found in database")
        return DEFAULT_PLACEHOLDER
    
    # Step 2: Attempt Spoonacular API (Primary Source)
    spoonacular_url = _fetch_from_spoonacular(recipe_name)
    if spoonacular_url and spoonacular_url != DEFAULT_PLACEHOLDER:
        # Cache Write: Save to database
        recipe.image_url = spoonacular_url
        recipe.save(update_fields=['image_url'])
        print(f"[IMAGE_SERVICE] ✓ Cached Spoonacular image for '{recipe_name}' (ID: {recipe_id})")
        return spoonacular_url
    
    # Step 3: Attempt Unsplash API (Fallback Source)
    unsplash_url = _fetch_from_unsplash(recipe_name)
    if unsplash_url and unsplash_url != DEFAULT_PLACEHOLDER:
        # Cache Write: Save to database
        recipe.image_url = unsplash_url
        recipe.save(update_fields=['image_url'])
        print(f"[IMAGE_SERVICE] ✓ Cached Unsplash image for '{recipe_name}' (ID: {recipe_id})")
        return unsplash_url
    
    # Step 4: Final Fallback - Placeholder
    print(f"[IMAGE_SERVICE] ✗ No image found for '{recipe_name}' (ID: {recipe_id}), using placeholder")
    return DEFAULT_PLACEHOLDER


def _fetch_from_spoonacular(recipe_name: str) -> Optional[str]:
    """
    Fetch image URL from Spoonacular API (Primary Source).
    
    Spoonacular API provides food-specific images with high relevance.
    The API returns recipe data including an 'image' field that contains
    the filename. We construct the full URL using the pattern:
    https://img.spoonacular.com/recipes/{IMAGE_FILENAME}
    
    :param recipe_name: Name of the recipe to search for
    :return: Image URL string or None if fetch fails
    """
    try:
        # Prepare API request
        headers = {
            'Content-Type': 'application/json'
        }
        params = {
            'apiKey': SPOONACULAR_API_KEY,
            'query': recipe_name,
            'number': 1,  # Only need first result
            'addRecipeInformation': False,  # We only need image
            'fillIngredients': False,
        }
        
        # Make API request with timeout
        response = requests.get(
            SPOONACULAR_API_URL,
            headers=headers,
            params=params,
            timeout=API_TIMEOUT
        )
        
        # Handle rate limiting (403 Forbidden)
        if response.status_code == 403:
            print(f"[IMAGE_SERVICE] ⚠ Spoonacular API rate limit reached (403)")
            return None
        
        # Raise exception for other HTTP errors
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Extract image URL from first result
        if data.get('results') and len(data['results']) > 0:
            first_result = data['results'][0]
            
            # Spoonacular returns image filename in 'image' field
            image_filename = first_result.get('image')
            recipe_id_spoonacular = first_result.get('id')
            
            if image_filename:
                # Check if it's already a full URL or just a filename
                if image_filename.startswith('http'):
                    # Already a full URL - return as-is
                    return image_filename
                else:
                    # Construct full image URL using Spoonacular's CDN pattern
                    # Pattern: https://img.spoonacular.com/recipes/{IMAGE_FILENAME}
                    image_url = f"https://img.spoonacular.com/recipes/{image_filename}"
                    return image_url
        
        # No results found
        return None
        
    except requests.exceptions.Timeout:
        print(f"[IMAGE_SERVICE] ⚠ Spoonacular API timeout for '{recipe_name}'")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print(f"[IMAGE_SERVICE] ⚠ Spoonacular API rate limit (403) for '{recipe_name}'")
        else:
            print(f"[IMAGE_SERVICE] ⚠ Spoonacular API HTTP error for '{recipe_name}': {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[IMAGE_SERVICE] ⚠ Spoonacular API request error for '{recipe_name}': {e}")
        return None
    except Exception as e:
        print(f"[IMAGE_SERVICE] ⚠ Unexpected error fetching from Spoonacular for '{recipe_name}': {e}")
        return None


def _fetch_from_unsplash(recipe_name: str) -> Optional[str]:
    """
    Fetch image URL from Unsplash API (Fallback Source).
    
    Unsplash provides high-quality general photography. We enhance the query
    by appending "food" or "dish" for better relevance.
    
    :param recipe_name: Name of the recipe to search for
    :return: Image URL string or None if fetch fails
    """
    try:
        # Enhance query for better food-specific results
        query = f"{recipe_name} food dish"
        
        # Prepare API request
        headers = {
            'Authorization': f'Client-ID {UNSPLASH_API_KEY}'
        }
        params = {
            'query': query,
            'per_page': 1,  # Only need first result
            'orientation': 'landscape',  # Better for food photography
        }
        
        # Make API request with timeout
        response = requests.get(
            UNSPLASH_API_URL,
            headers=headers,
            params=params,
            timeout=API_TIMEOUT
        )
        
        # Handle rate limiting (403 Forbidden)
        if response.status_code == 403:
            print(f"[IMAGE_SERVICE] ⚠ Unsplash API rate limit reached (403)")
            return None
        
        # Raise exception for other HTTP errors
        response.raise_for_status()
        
        # Parse JSON response
        data = response.json()
        
        # Extract image URL from first result
        if data.get('results') and len(data['results']) > 0:
            first_result = data['results'][0]
            # Use 'regular' size (1080px width) for good quality/performance balance
            image_url = first_result.get('urls', {}).get('regular')
            
            if image_url:
                return image_url
        
        # No results found
        return None
        
    except requests.exceptions.Timeout:
        print(f"[IMAGE_SERVICE] ⚠ Unsplash API timeout for '{recipe_name}'")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print(f"[IMAGE_SERVICE] ⚠ Unsplash API rate limit (403) for '{recipe_name}'")
        else:
            print(f"[IMAGE_SERVICE] ⚠ Unsplash API HTTP error for '{recipe_name}': {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"[IMAGE_SERVICE] ⚠ Unsplash API request error for '{recipe_name}': {e}")
        return None
    except Exception as e:
        print(f"[IMAGE_SERVICE] ⚠ Unexpected error fetching from Unsplash for '{recipe_name}': {e}")
        return None


def get_image_url_for_recipe_dict(recipe_dict: dict, recipe_obj=None) -> str:
    """
    Get image URL for a recipe dictionary (from plan data).
    
    This function is used when we have recipe dictionaries from plan data
    but need to fetch/cache images. It tries to get the Recipe object first,
    then uses the main caching function.
    
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
    
    # If we have the object, use the main caching function
    if recipe_obj:
        return get_or_fetch_image_url(recipe_obj.id)
    
    # Fallback: Try to get ID from dictionary
    recipe_id = recipe_dict.get('id')
    if recipe_id:
        return get_or_fetch_image_url(recipe_id)
    
    # Final fallback: placeholder
    return DEFAULT_PLACEHOLDER

