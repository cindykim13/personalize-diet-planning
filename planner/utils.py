"""
Utility functions for image processing and other helper functions.
"""
import os
from PIL import Image
from django.conf import settings
from django.core.files.storage import default_storage


def process_logo_transparency(image_path, output_path=None):
    """
    Process logo image to remove checkered background and make it transparent.
    
    Strategy: Convert RGB to RGBA, identify checkered pattern pixels (typically
    white/light gray checkered pattern), and make them transparent using numpy
    for efficient processing.
    
    :param image_path: Path to the input image file
    :param output_path: Path to save the processed image (if None, overwrites original)
    :return: Path to the processed image
    """
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Use numpy for faster processing
        try:
            import numpy as np
            img_array = np.array(img)
            
            # Create mask for background pixels
            # Checkered backgrounds are typically very light (close to white)
            # Threshold: pixels with all RGB values > 230 are considered background
            mask = (img_array[:, :, 0] > 230) & (img_array[:, :, 1] > 230) & (img_array[:, :, 2] > 230)
            
            # Make background pixels transparent
            img_array[mask, 3] = 0
            
            # Convert back to PIL Image
            img = Image.fromarray(img_array, 'RGBA')
        except ImportError:
            # Fallback to pixel-by-pixel processing if numpy is not available
            data = img.getdata()
            new_data = []
            for item in data:
                r, g, b, a = item
                
                # Remove pixels that are very light (typical checkered background)
                is_background = (r > 230 and g > 230 and b > 230)
                
                if is_background:
                    new_data.append((r, g, b, 0))
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
        
        # Save processed image
        if output_path is None:
            output_path = image_path
        
        img.save(output_path, 'PNG')
        return output_path
        
    except Exception as e:
        print(f"[UTILS] Error processing image {image_path}: {e}")
        return image_path


def process_brand_name_transparency(image_path, output_path=None):
    """
    Process brand name image to remove checkered background and make it transparent.
    
    Similar to process_logo_transparency but optimized for text-based images.
    Uses more aggressive background removal.
    
    :param image_path: Path to the input image file
    :param output_path: Path to save the processed image (if None, overwrites original)
    :return: Path to the processed image
    """
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Convert to RGBA if not already
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Use numpy for faster processing
        try:
            import numpy as np
            img_array = np.array(img)
            
            # More aggressive mask for text images
            # Remove pixels that are light (typical checkered/text background)
            mask = (img_array[:, :, 0] > 220) & (img_array[:, :, 1] > 220) & (img_array[:, :, 2] > 220)
            
            # Make background pixels transparent
            img_array[mask, 3] = 0
            
            # Convert back to PIL Image
            img = Image.fromarray(img_array, 'RGBA')
        except ImportError:
            # Fallback to pixel-by-pixel processing
            data = img.getdata()
            new_data = []
            for item in data:
                r, g, b, a = item
                
                # More aggressive background removal for text images
                is_background = (r > 220 and g > 220 and b > 220)
                
                if is_background:
                    new_data.append((r, g, b, 0))
                else:
                    new_data.append(item)
            
            img.putdata(new_data)
        
        # Save processed image
        if output_path is None:
            output_path = image_path
        
        img.save(output_path, 'PNG')
        return output_path
        
    except Exception as e:
        print(f"[UTILS] Error processing image {image_path}: {e}")
        return image_path


def get_processed_logo_path():
    """
    Get the path to the processed logo with transparent background.
    Creates processed version if it doesn't exist.
    
    :return: Static URL path to the processed logo
    """
    base_dir = settings.BASE_DIR
    static_dir = base_dir / 'static'
    original_logo = static_dir / 'Logo.png'
    processed_logo = static_dir / 'Logo_transparent.png'
    
    # Process logo if processed version doesn't exist
    if not processed_logo.exists() and original_logo.exists():
        process_logo_transparency(str(original_logo), str(processed_logo))
    
    return 'Logo_transparent.png' if processed_logo.exists() else 'Logo.png'


def get_processed_brand_name_path():
    """
    Get the path to the processed brand name with transparent background.
    Creates processed version if it doesn't exist.
    
    :return: Static URL path to the processed brand name
    """
    base_dir = settings.BASE_DIR
    static_dir = base_dir / 'static'
    original_brand = static_dir / 'BrandName.png'
    processed_brand = static_dir / 'BrandName_transparent.png'
    
    # Process brand name if processed version doesn't exist
    if not processed_brand.exists() and original_brand.exists():
        process_brand_name_transparency(str(original_brand), str(processed_brand))
    
    return 'BrandName_transparent.png' if processed_brand.exists() else 'BrandName.png'
