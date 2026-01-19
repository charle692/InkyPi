import requests
from PIL import Image, ImageEnhance, ImageOps, ImageFilter
from io import BytesIO
import os
import logging
import hashlib
import tempfile
import subprocess
import numpy as np

logger = logging.getLogger(__name__)

def get_image(image_url):
    response = requests.get(image_url)
    img = None
    if 200 <= response.status_code < 300 or response.status_code == 304:
        img = Image.open(BytesIO(response.content))
    else:
        logger.error(f"Received non-200 response from {image_url}: status_code: {response.status_code}")
    return img

def change_orientation(image, orientation, inverted=False):
    if orientation == 'horizontal':
        angle = 0
    elif orientation == 'vertical':
        angle = 90

    if inverted:
        angle = (angle + 180) % 360

    return image.rotate(angle, expand=1)

def resize_image(image, desired_size, image_settings=[]):
    img_width, img_height = image.size
    desired_width, desired_height = desired_size
    desired_width, desired_height = int(desired_width), int(desired_height)

    img_ratio = img_width / img_height
    desired_ratio = desired_width / desired_height

    keep_width = "keep-width" in image_settings

    x_offset, y_offset = 0,0
    new_width, new_height = img_width,img_height
    # Step 1: Determine crop dimensions
    desired_ratio = desired_width / desired_height
    if img_ratio > desired_ratio:
        # Image is wider than desired aspect ratio
        new_width = int(img_height * desired_ratio)
        if not keep_width:
            x_offset = (img_width - new_width) // 2
    else:
        # Image is taller than desired aspect ratio
        new_height = int(img_width / desired_ratio)
        if not keep_width:
            y_offset = (img_height - new_height) // 2

    # Step 2: Crop the image
    image = image.crop((x_offset, y_offset, x_offset + new_width, y_offset + new_height))

    # Step 3: Resize to the exact desired dimensions (if necessary)
    return image.resize((desired_width, desired_height), Image.LANCZOS)

def apply_image_enhancement(img, image_settings={}):
    # Convert image to RGB mode if necessary for enhancement operations
    # ImageEnhance requires RGB mode for operations like blend
    if img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')
        

    # Apply Brightness
    img = ImageEnhance.Brightness(img).enhance(image_settings.get("brightness", 1.0))

    # Apply Contrast
    img = ImageEnhance.Contrast(img).enhance(image_settings.get("contrast", 1.0))

    # Apply Saturation (Color)
    img = ImageEnhance.Color(img).enhance(image_settings.get("saturation", 1.0))

    # Apply Sharpness
    img = ImageEnhance.Sharpness(img).enhance(image_settings.get("sharpness", 1.0))

    return img

def compute_image_hash(image):
    """Compute SHA-256 hash of an image."""
    image = image.convert("RGB")
    img_bytes = image.tobytes()
    return hashlib.sha256(img_bytes).hexdigest()

def dither_to_bw(image):
    """
    Convert image to pure black and white using Floyd-Steinberg dithering.
    This is optimal for e-ink displays.
    """
    # Convert to grayscale
    img_gray = image.convert('L')
    
    # Convert to numpy array for dithering
    img_array = np.array(img_gray, dtype=np.float32)
    
    # Floyd-Steinberg dithering
    h, w = img_array.shape
    
    for y in range(h):
        for x in range(w):
            # Get current pixel value
            old_value = img_array[y, x]
            
            # Quantize to black (0) or white (255)
            new_value = 255 if old_value >= 1 else 0
            img_array[y, x] = new_value
            
            # Calculate error
            error = old_value - new_value
            
            # Distribute error to neighboring pixels
            if x + 1 < w:
                img_array[y, x + 1] += error * 7 / 16
            if y + 1 < h:
                if x - 1 >= 0:
                    img_array[y + 1, x - 1] += error * 3 / 16
                img_array[y + 1, x] += error * 5 / 16
                if x + 1 < w:
                    img_array[y + 1, x + 1] += error * 1 / 16
    
    # Convert back to PIL Image
    result = Image.fromarray(np.uint8(np.clip(img_array, 0, 255)))
    return result

def sharpen_image(image, strength=1.0):
    """
    Sharpen image using unsharp masking.
    
    Args:
        image: PIL Image
        strength: Sharpening strength (1.0 = aggressive, 0.5 = conservative)
    
    Returns:
        Sharpened PIL Image
    """
    if strength <= 0:
        return image
    
    # Apply unsharp mask: (original - blurred) * strength + original
    # This enhances edges without creating too many artifacts
    radius = 2
    percent = 150 * strength  # Aggressiveness controlled by strength parameter
    
    blurred = image.filter(ImageFilter.GaussianBlur(radius))
    
    # Manual unsharp masking for better control
    img_array = np.array(image, dtype=np.float32)
    blur_array = np.array(blurred, dtype=np.float32)
    
    sharpened = img_array + (img_array - blur_array) * (percent / 100)
    sharpened = np.clip(sharpened, 0, 255)
    
    result = Image.fromarray(np.uint8(sharpened))
    return result

def take_screenshot_html(html_str, dimensions, timeout_ms=None, upscale_factor=1, sharpen_strength=0, dither_bw=False):
    """
    Take a screenshot of HTML content with optional quality enhancements.
    
    Args:
        html_str: HTML content to render
        dimensions: Target dimensions (width, height)
        timeout_ms: Optional timeout in milliseconds
        upscale_factor: Device scale factor for crisp rendering (default 1, use 2-3 for high quality)
                       Higher values render at higher internal DPI while preserving layout
        sharpen_strength: Sharpening strength 0-1+ (default 0 = disabled, 1.0 = aggressive)
        dither_bw: Apply Floyd-Steinberg dithering for black/white e-ink displays (default False)
    
    Returns:
        PIL Image or None
    """
    image = None
    try:
        # Create a temporary HTML file
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as html_file:
            html_file.write(html_str.encode("utf-8"))
            html_file_path = html_file.name

        image = take_screenshot(html_file_path, dimensions, timeout_ms, upscale_factor=upscale_factor)

        # Apply post-processing enhancements
        if image:
            if sharpen_strength > 0:
                image = sharpen_image(image, strength=sharpen_strength)
            
            if dither_bw:
                image = dither_to_bw(image)

        # Remove html file
        os.remove(html_file_path)

    except Exception as e:
        logger.error(f"Failed to take screenshot: {str(e)}")

    return image

def take_screenshot(target, dimensions, timeout_ms=None, upscale_factor=1):
    """
    Take a screenshot of HTML content using Chromium headless.
    
    Args:
        target: Path to HTML file or URL to render
        dimensions: Target dimensions (width, height) as tuple
        timeout_ms: Optional timeout in milliseconds
        upscale_factor: Device scale factor for crisp rendering (default 1, use 2-3 for high quality)
                       Controls internal DPI rendering while maintaining layout at target dimensions
    
    Returns:
        PIL Image or None
    """
    image = None
    try:
        # Create a temporary output file for the screenshot
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_file:
            img_file_path = img_file.name

        command = [
            "chromium-headless-shell",
            target,
            "--headless",
            f"--screenshot={img_file_path}",
            f"--window-size={dimensions[0]},{dimensions[1]}",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--use-gl=swiftshader",
            "--hide-scrollbars",
            "--in-process-gpu",
            "--js-flags=--jitless",
            "--disable-zero-copy",
            "--disable-gpu-memory-buffer-compositor-resources",
            "--disable-extensions",
            "--disable-plugins",
            "--mute-audio",
            "--no-sandbox",
            # Enhanced flags for better image quality and reduced compression
            "--force-color-profile=srgb",                    # Force consistent color profile
            "--disable-font-subpixel-positioning",          # Eliminate subpixel font artifacts
            "--disable-lcd-text",                           # Disable LCD text optimizations
            "--font-render-hinting=none",                   # Disable font hinting compression
            "--disable-subpixel-font-rendering",             # Prevent subpixel font compression
            f"--force-device-scale-factor={upscale_factor}", # DPI scale for crisp rendering
            "--disable-features=VizDisplayCompositor",       # Disable compositor compression
            "--disable-accelerated-2d-canvas",              # Use software 2D rendering
            "--disable-threaded-animation",                  # Prevent animation compression artifacts
            "--disable-checker-imaging",                     # Disable image tiling/compression
            "--run-all-compositor-stages-before-draw",       # Complete rendering before capture
            "--disable-new-content-rendering-timeout"        # Ensure full quality rendering
        ]
        if timeout_ms:
            command.append(f"--timeout={timeout_ms}")
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Check if the process failed or the output file is missing
        if result.returncode != 0 or not os.path.exists(img_file_path):
            logger.error("Failed to take screenshot:")
            logger.error(result.stderr.decode('utf-8'))
            return None

        # Load the image using PIL
        with Image.open(img_file_path) as img:
            image = img.copy()

        # Remove image files
        os.remove(img_file_path)

    except Exception as e:
        logger.error(f"Failed to take screenshot: {str(e)}")

    return image

def pad_image_blur(img: Image, dimensions: tuple[int, int]) -> Image:
    bkg = ImageOps.fit(img, dimensions)
    bkg = bkg.filter(ImageFilter.BoxBlur(8))
    img = ImageOps.contain(img, dimensions)

    img_size = img.size
    bkg.paste(img, ((dimensions[0] - img_size[0]) // 2, (dimensions[1] - img_size[1]) // 2))
    return bkg
