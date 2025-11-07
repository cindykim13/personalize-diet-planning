"""
Django management command to process logo and brand name images with advanced background removal.
This command creates production-ready transparent versions of brand assets.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from pathlib import Path
from PIL import Image
import numpy as np


class Command(BaseCommand):
    help = 'Process logo and brand name images with advanced background removal to create transparent versions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing even if transparent versions already exist',
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("ADVANCED IMAGE PROCESSING: TRANSPARENCY CREATION")
        self.stdout.write("=" * 80)
        
        base_dir = settings.BASE_DIR
        static_dir = base_dir / 'static'
        
        force = options.get('force', False)
        
        # Process Logo.png
        self.process_logo(static_dir, force)
        
        # Process BrandName.png
        self.process_brand_name(static_dir, force)
        
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("IMAGE PROCESSING COMPLETE"))
        self.stdout.write("=" * 80)

    def process_logo(self, static_dir, force=False):
        """Process Logo.png with advanced background removal."""
        logo_path = static_dir / 'Logo.png'
        logo_output = static_dir / 'Logo_transparent.png'
        
        if not logo_path.exists():
            self.stdout.write(self.style.WARNING(f"⚠ Logo.png not found at {logo_path}"))
            return
        
        if logo_output.exists() and not force:
            self.stdout.write(f"\n✓ Logo already processed: {logo_output}")
            self.stdout.write("  (Use --force to reprocess)")
            return
        
        self.stdout.write(f"\nProcessing Logo.png...")
        try:
            # Open and convert to RGBA
            img = Image.open(logo_path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Convert to numpy array
            img_array = np.array(img)
            height, width = img_array.shape[:2]
            
            # Advanced background detection using multiple strategies
            r, g, b, a = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2], img_array[:, :, 3]
            
            # Strategy 1: Detect very light/white pixels (common in checkered backgrounds)
            light_mask = (r > 240) & (g > 240) & (b > 240)
            
            # Strategy 2: Detect pixels that are nearly grayscale and very light
            grayscale_threshold = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
            grayscale_light = (grayscale_threshold < 20) & (r > 230) & (g > 230) & (b > 230)
            
            # Strategy 3: Detect checkered pattern (alternating light squares)
            # Sample corners and edges to identify background color
            corner_samples = np.concatenate([
                img_array[0:50, 0:50].reshape(-1, 4),
                img_array[0:50, -50:].reshape(-1, 4),
                img_array[-50:, 0:50].reshape(-1, 4),
                img_array[-50:, -50:].reshape(-1, 4)
            ])
            # Find most common light color in corners (likely background)
            light_samples = corner_samples[(corner_samples[:, 0] > 230) & 
                                          (corner_samples[:, 1] > 230) & 
                                          (corner_samples[:, 2] > 230)]
            if len(light_samples) > 0:
                bg_color = light_samples.mean(axis=0)[:3]
                # Create mask for pixels similar to background color
                color_distance = np.sqrt(
                    np.square(r - bg_color[0]) + 
                    np.square(g - bg_color[1]) + 
                    np.square(b - bg_color[2])
                )
                similar_to_bg = color_distance < 30
            else:
                similar_to_bg = np.zeros_like(r, dtype=bool)
            
            # Combine all strategies
            background_mask = light_mask | grayscale_light | similar_to_bg
            
            # Apply feathering to edges for smoother transparency
            from scipy import ndimage
            try:
                # Create distance transform for smooth edges
                distance = ndimage.distance_transform_edt(~background_mask)
                # Feather edges within 3 pixels
                feather_mask = distance < 3
                alpha = np.where(feather_mask, 
                                np.clip(distance / 3.0 * 255, 0, 255).astype(np.uint8),
                                np.where(background_mask, 0, 255))
            except ImportError:
                # Fallback if scipy not available
                alpha = np.where(background_mask, 0, 255).astype(np.uint8)
            
            # Update alpha channel
            img_array[:, :, 3] = alpha
            
            # Convert back to PIL Image
            processed_img = Image.fromarray(img_array, 'RGBA')
            
            # Save with high quality
            processed_img.save(logo_output, 'PNG', optimize=True)
            
            self.stdout.write(self.style.SUCCESS(f"✓ Logo processed successfully"))
            self.stdout.write(f"  Input: {logo_path}")
            self.stdout.write(f"  Output: {logo_output}")
            self.stdout.write(f"  Size: {width}x{height}")
            self.stdout.write(f"  Background pixels removed: {background_mask.sum()}/{height*width} ({100*background_mask.sum()/(height*width):.1f}%)")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error processing Logo.png: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

    def process_brand_name(self, static_dir, force=False):
        """Process BrandName.png with advanced background removal."""
        brand_path = static_dir / 'BrandName.png'
        brand_output = static_dir / 'BrandName_transparent.png'
        
        if not brand_path.exists():
            self.stdout.write(self.style.WARNING(f"⚠ BrandName.png not found at {brand_path}"))
            return
        
        if brand_output.exists() and not force:
            self.stdout.write(f"\n✓ Brand name already processed: {brand_output}")
            self.stdout.write("  (Use --force to reprocess)")
            return
        
        self.stdout.write(f"\nProcessing BrandName.png...")
        try:
            # Open and convert to RGBA
            img = Image.open(brand_path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Convert to numpy array
            img_array = np.array(img)
            height, width = img_array.shape[:2]
            
            r, g, b, a = img_array[:, :, 0], img_array[:, :, 1], img_array[:, :, 2], img_array[:, :, 3]
            
            # More aggressive background removal for text images
            # Strategy 1: Very light pixels
            light_mask = (r > 235) & (g > 235) & (b > 235)
            
            # Strategy 2: Near-white grayscale
            grayscale_threshold = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
            grayscale_light = (grayscale_threshold < 15) & (r > 225) & (g > 225) & (b > 225)
            
            # Strategy 3: Sample edges (text images often have consistent background)
            edge_samples = np.concatenate([
                img_array[0:20, :].reshape(-1, 4),
                img_array[-20:, :].reshape(-1, 4),
                img_array[:, 0:20].reshape(-1, 4),
                img_array[:, -20:].reshape(-1, 4)
            ])
            light_edge_samples = edge_samples[(edge_samples[:, 0] > 220) & 
                                             (edge_samples[:, 1] > 220) & 
                                             (edge_samples[:, 2] > 220)]
            if len(light_edge_samples) > 0:
                bg_color = light_edge_samples.mean(axis=0)[:3]
                color_distance = np.sqrt(
                    np.square(r - bg_color[0]) + 
                    np.square(g - bg_color[1]) + 
                    np.square(b - bg_color[2])
                )
                similar_to_bg = color_distance < 25
            else:
                similar_to_bg = np.zeros_like(r, dtype=bool)
            
            # Combine strategies
            background_mask = light_mask | grayscale_light | similar_to_bg
            
            # Smooth edge feathering
            from scipy import ndimage
            try:
                distance = ndimage.distance_transform_edt(~background_mask)
                feather_mask = distance < 2
                alpha = np.where(feather_mask,
                                np.clip(distance / 2.0 * 255, 0, 255).astype(np.uint8),
                                np.where(background_mask, 0, 255))
            except ImportError:
                alpha = np.where(background_mask, 0, 255).astype(np.uint8)
            
            # Update alpha channel
            img_array[:, :, 3] = alpha
            
            # Convert back to PIL Image
            processed_img = Image.fromarray(img_array, 'RGBA')
            
            # Save with high quality
            processed_img.save(brand_output, 'PNG', optimize=True)
            
            self.stdout.write(self.style.SUCCESS(f"✓ Brand name processed successfully"))
            self.stdout.write(f"  Input: {brand_path}")
            self.stdout.write(f"  Output: {brand_output}")
            self.stdout.write(f"  Size: {width}x{height}")
            self.stdout.write(f"  Background pixels removed: {background_mask.sum()}/{height*width} ({100*background_mask.sum()/(height*width):.1f}%)")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error processing BrandName.png: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

