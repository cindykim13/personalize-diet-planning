"""
Django management command to process logo and brand name images to remove checkered backgrounds.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
from planner.utils import process_logo_transparency, process_brand_name_transparency


class Command(BaseCommand):
    help = 'Process logo and brand name images to remove checkered backgrounds and make them transparent'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("LOGO IMAGE PROCESSING")
        self.stdout.write("=" * 80)
        
        base_dir = settings.BASE_DIR
        static_dir = base_dir / 'static'
        
        # Process Logo.png
        logo_path = static_dir / 'Logo.png'
        logo_output = static_dir / 'Logo_transparent.png'
        
        if logo_path.exists():
            self.stdout.write(f"\nProcessing Logo.png...")
            try:
                process_logo_transparency(str(logo_path), str(logo_output))
                self.stdout.write(self.style.SUCCESS(f"✓ Logo processed successfully: {logo_output}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error processing Logo.png: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠ Logo.png not found at {logo_path}"))
        
        # Process BrandName.png
        brand_path = static_dir / 'BrandName.png'
        brand_output = static_dir / 'BrandName_transparent.png'
        
        if brand_path.exists():
            self.stdout.write(f"\nProcessing BrandName.png...")
            try:
                process_brand_name_transparency(str(brand_path), str(brand_output))
                self.stdout.write(self.style.SUCCESS(f"✓ Brand name processed successfully: {brand_output}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"✗ Error processing BrandName.png: {e}"))
        else:
            self.stdout.write(self.style.WARNING(f"⚠ BrandName.png not found at {brand_path}"))
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("IMAGE PROCESSING COMPLETE")
        self.stdout.write("=" * 80)

