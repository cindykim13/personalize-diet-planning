"""
Django management command to backfill recipe images using multi-source Chain of Responsibility.
Pre-populates image URLs for all recipes that don't have images yet.

Uses:
1. Spoonacular API (Primary - food-specific)
2. Unsplash API (Fallback - general food photography)
3. Placeholder (Final fallback)

Includes robust rate limit handling and graceful error recovery.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
import time
from planner.models import Recipe
from planner.image_service import get_or_fetch_image_url


class Command(BaseCommand):
    help = 'Backfill recipe images using multi-source Chain of Responsibility (Spoonacular + Unsplash)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of recipes to process (useful for testing)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-fetching images even if they already exist',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Delay in seconds between API calls to avoid rate limiting (default: 0.5)',
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("RECIPE IMAGE BACKFILL")
        self.stdout.write("=" * 80)
        
        limit = options.get('limit')
        force = options.get('force', False)
        delay = options.get('delay', 0.5)
        
        # Query recipes without images
        if force:
            queryset = Recipe.objects.all()
            self.stdout.write(self.style.WARNING("Force mode: Re-fetching images for ALL recipes"))
        else:
            queryset = Recipe.objects.filter(Q(image_url__isnull=True) | Q(image_url=''))
            self.stdout.write("Fetching images for recipes without image URLs...")
        
        total_recipes = queryset.count()
        
        if limit:
            queryset = queryset[:limit]
            self.stdout.write(f"Processing {min(limit, total_recipes)} of {total_recipes} recipes")
        else:
            self.stdout.write(f"Processing {total_recipes} recipes")
        
        self.stdout.write("")
        
        # Process recipes
        success_count = 0
        failed_count = 0
        skipped_count = 0
        rate_limit_hit = False
        processed_count = 0
        total_count = queryset.count() if hasattr(queryset, 'count') else len(queryset)
        
        for i, recipe in enumerate(queryset, 1):
            processed_count = i
            try:
                # Skip if image already exists and not forcing
                if not force and recipe.image_url:
                    skipped_count += 1
                    if i % 50 == 0:
                        self.stdout.write(f"Processed {i}/{len(queryset)} recipes... (Skipped: {skipped_count}, Success: {success_count}, Failed: {failed_count})")
                    continue
                
                # Fetch image URL (uses recipe_id for Chain of Responsibility pattern)
                # This will try Spoonacular first, then Unsplash, then placeholder
                image_url = get_or_fetch_image_url(recipe.id)
                
                if image_url and image_url != '/static/planner/images/placeholder.png':
                    success_count += 1
                    status = self.style.SUCCESS("✓")
                else:
                    failed_count += 1
                    status = self.style.WARNING("✗")
                
                # Progress update every 50 recipes
                if i % 50 == 0:
                    self.stdout.write(f"Processed {i}/{len(queryset)} recipes... (Success: {success_count}, Failed: {failed_count}, Skipped: {skipped_count})")
                
                # Rate limiting: delay between API calls (except for last item)
                if i < total_count and delay > 0:
                    time.sleep(delay)
                    
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING("\n\nBackfill interrupted by user"))
                break
            except Exception as e:
                error_msg = str(e).lower()
                # Check for rate limit errors (403)
                if '403' in error_msg or 'rate limit' in error_msg:
                    rate_limit_hit = True
                    self.stdout.write(self.style.ERROR(f"\n⚠ RATE LIMIT HIT (403) at recipe '{recipe.name}' (ID: {recipe.id})"))
                    self.stdout.write(self.style.WARNING("Stopping gracefully. You can resume later with --limit"))
                    break
                else:
                    failed_count += 1
                    self.stdout.write(self.style.ERROR(f"Error processing recipe '{recipe.name}' (ID: {recipe.id}): {e}"))
        
        # Final summary
        self.stdout.write("")
        self.stdout.write("=" * 80)
        if rate_limit_hit:
            self.stdout.write(self.style.WARNING("BACKFILL STOPPED (RATE LIMIT)"))
        else:
            self.stdout.write("BACKFILL COMPLETE")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total processed: {processed_count}")
        self.stdout.write(self.style.SUCCESS(f"Successfully fetched: {success_count}"))
        self.stdout.write(self.style.WARNING(f"Failed/Placeholder: {failed_count}"))
        if skipped_count > 0:
            self.stdout.write(f"Skipped (already have images): {skipped_count}")
        if rate_limit_hit:
            self.stdout.write(self.style.WARNING("\n⚠ Rate limit reached. Wait before resuming."))
            self.stdout.write("   Tip: Use --limit to process in smaller batches")
        self.stdout.write("=" * 80)

