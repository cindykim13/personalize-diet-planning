"""
Django management command to backfill recipe images from Unsplash API.
Pre-populates image URLs for all recipes that don't have images yet.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from planner.models import Recipe
from planner.image_utils import get_or_fetch_image_url


class Command(BaseCommand):
    help = 'Backfill recipe images from Unsplash API for all recipes without image URLs'

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

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("RECIPE IMAGE BACKFILL")
        self.stdout.write("=" * 80)
        
        limit = options.get('limit')
        force = options.get('force', False)
        
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
        
        for i, recipe in enumerate(queryset, 1):
            try:
                # Skip if image already exists and not forcing
                if not force and recipe.image_url:
                    skipped_count += 1
                    if i % 50 == 0:
                        self.stdout.write(f"Processed {i}/{len(queryset)} recipes... (Skipped: {skipped_count}, Success: {success_count}, Failed: {failed_count})")
                    continue
                
                # Fetch image URL
                image_url = get_or_fetch_image_url(recipe)
                
                if image_url and image_url != '/static/planner/images/placeholder.png':
                    success_count += 1
                    status = self.style.SUCCESS("✓")
                else:
                    failed_count += 1
                    status = self.style.WARNING("✗")
                
                # Progress update every 50 recipes
                if i % 50 == 0:
                    self.stdout.write(f"Processed {i}/{len(queryset)} recipes... (Success: {success_count}, Failed: {failed_count}, Skipped: {skipped_count})")
                    
            except Exception as e:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f"Error processing recipe '{recipe.name}' (ID: {recipe.id}): {e}"))
        
        # Final summary
        self.stdout.write("")
        self.stdout.write("=" * 80)
        self.stdout.write("BACKFILL COMPLETE")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total processed: {len(queryset)}")
        self.stdout.write(self.style.SUCCESS(f"Successfully fetched: {success_count}"))
        self.stdout.write(self.style.WARNING(f"Failed/Placeholder: {failed_count}"))
        if skipped_count > 0:
            self.stdout.write(f"Skipped (already have images): {skipped_count}")
        self.stdout.write("=" * 80)

