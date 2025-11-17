# planner/management/commands/verify_image_cache.py

from django.core.management.base import BaseCommand
from planner.models import Recipe
from planner.image_service import get_or_fetch_image_url
import random


class Command(BaseCommand):
    help = 'Verify that the image caching mechanism correctly saves image URLs to the database'

    def handle(self, *args, **kwargs):
        self.stdout.write("=" * 80)
        self.stdout.write("IMAGE CACHE VERIFICATION")
        self.stdout.write("=" * 80)
        self.stdout.write("Purpose: Verify that get_or_fetch_image_url correctly saves URLs to database")
        self.stdout.write("=" * 80)
        
        # Step 1: Find a recipe with null image_url
        self.stdout.write("\n[STEP 1] Finding recipe with null image_url...")
        recipes_without_image = Recipe.objects.filter(image_url__isnull=True) | Recipe.objects.filter(image_url='')
        
        if not recipes_without_image.exists():
            self.stdout.write(self.style.WARNING("  ⚠ No recipes with null image_url found. Testing with a random recipe..."))
            # Pick a random recipe and clear its image_url for testing
            all_recipes = Recipe.objects.all()
            if not all_recipes.exists():
                self.stdout.write(self.style.ERROR("  ✗ No recipes found in database. Please run 'python manage.py load_recipes' first."))
                return
            
            test_recipe = random.choice(all_recipes)
            original_image_url = test_recipe.image_url
            test_recipe.image_url = None
            test_recipe.save(update_fields=['image_url'])
            self.stdout.write(self.style.SUCCESS(f"  ✓ Selected recipe: ID {test_recipe.id} ('{test_recipe.name}')"))
            self.stdout.write(f"    Original image_url: {original_image_url or 'None'}")
            self.stdout.write(f"    Cleared image_url for testing")
        else:
            test_recipe = recipes_without_image.order_by('?').first()
            self.stdout.write(self.style.SUCCESS(f"  ✓ Found recipe: ID {test_recipe.id} ('{test_recipe.name}')"))
            self.stdout.write(f"    Current image_url: {test_recipe.image_url or 'None'}")
        
        # Step 2: Verify image_url is null before calling the function
        self.stdout.write("\n[STEP 2] Verifying initial state...")
        test_recipe.refresh_from_db()
        if test_recipe.image_url:
            self.stdout.write(self.style.ERROR(f"  ✗ FAILURE: Recipe already has image_url: {test_recipe.image_url}"))
            self.stdout.write(self.style.ERROR("  ✗ Cannot verify caching - recipe already has an image URL"))
            return
        else:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Verified: Recipe image_url is null/empty"))
        
        # Step 3: Call get_or_fetch_image_url
        self.stdout.write("\n[STEP 3] Calling get_or_fetch_image_url...")
        try:
            fetched_url = get_or_fetch_image_url(test_recipe.id)
            self.stdout.write(self.style.SUCCESS(f"  ✓ Function returned URL: {fetched_url}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ FAILURE: Error calling get_or_fetch_image_url: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            return
        
        # Step 4: Re-query the recipe from database and verify image_url is populated
        self.stdout.write("\n[STEP 4] Verifying database persistence...")
        try:
            # Re-query from database (fresh query, not using cached object)
            verified_recipe = Recipe.objects.get(id=test_recipe.id)
            
            if verified_recipe.image_url:
                self.stdout.write(self.style.SUCCESS(f"  ✓ SUCCESS: Recipe image_url is now populated"))
                self.stdout.write(f"    Cached URL: {verified_recipe.image_url}")
                
                # Verify it matches the returned URL (if not a placeholder)
                if fetched_url != '/static/planner/images/placeholder.png':
                    if verified_recipe.image_url == fetched_url:
                        self.stdout.write(self.style.SUCCESS(f"  ✓ SUCCESS: Cached URL matches returned URL"))
                    else:
                        self.stdout.write(self.style.WARNING(f"  ⚠ WARNING: Cached URL does not match returned URL"))
                        self.stdout.write(f"    Returned: {fetched_url}")
                        self.stdout.write(f"    Cached: {verified_recipe.image_url}")
                
                # Final verification: Check if URL is valid (starts with http)
                if verified_recipe.image_url.startswith('http'):
                    self.stdout.write(self.style.SUCCESS(f"  ✓ SUCCESS: Cached URL is a valid HTTP URL"))
                else:
                    self.stdout.write(self.style.WARNING(f"  ⚠ WARNING: Cached URL is not an HTTP URL (might be placeholder)"))
                
                self.stdout.write("\n" + "=" * 80)
                self.stdout.write(self.style.SUCCESS("[SUCCESS] Image caching mechanism is working correctly!"))
                self.stdout.write("=" * 80)
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ FAILURE: Recipe image_url is still null/empty after function call"))
                self.stdout.write(self.style.ERROR("  ✗ The caching mechanism is NOT working correctly"))
                self.stdout.write("\n" + "=" * 80)
                self.stdout.write(self.style.ERROR("[FAILURE] Image caching mechanism is NOT saving URLs to database"))
                self.stdout.write("=" * 80)
        except Recipe.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"  ✗ FAILURE: Recipe ID {test_recipe.id} not found in database"))
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR("[FAILURE] Cannot verify - recipe not found"))
            self.stdout.write("=" * 80)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ FAILURE: Error verifying database: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.ERROR("[FAILURE] Error during verification"))
            self.stdout.write("=" * 80)

