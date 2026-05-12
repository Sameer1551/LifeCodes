#!/usr/bin/env python3
"""
Image Watermarker Tool
Add text or image watermarks to images.
"""

import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff')

POSITIONS = {
    'center': lambda w, h, ww, wh: ((w - ww) // 2, (h - wh) // 2),
    'topleft': lambda w, h, ww, wh: (10, 10),
    'topright': lambda w, h, ww, wh: (w - ww - 10, 10),
    'bottomleft': lambda w, h, ww, wh: (10, h - wh - 10),
    'bottomright': lambda w, h, ww, wh: (w - ww - 10, h - wh - 10),
}


def _get_font(font_size: int, font_path: str | None = None) -> ImageFont.FreeTypeFont | ImageFont.DefaultImageFont:
    """Get a font for text watermarking."""
    if font_path and Path(font_path).exists():
        return ImageFont.truetype(font_path, font_size)
    # Try common system fonts
    common_fonts = [
        "arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for font_file in common_fonts:
        try:
            return ImageFont.truetype(font_file, font_size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def add_text_watermark(
    input_path: str,
    output_path: str,
    text: str,
    position: str = 'center',
    opacity: float = 0.5,
    font_size: int = 36,
    font_color: str = '#FFFFFF',
    font_path: str | None = None,
    tile: bool = False
) -> str:
    """
    Add text watermark to an image.

    Args:
        input_path: Path to input image.
        output_path: Path to save watermarked image.
        text: Watermark text.
        position: Position (center/topleft/topright/bottomleft/bottomright/tile).
        opacity: Opacity of watermark (0.0-1.0).
        font_size: Font size in pixels.
        font_color: Font color (hex or name).
        font_path: Path to custom font file.
        tile: Tile watermark across image.

    Returns:
        Path to watermarked image.
    """
    img = Image.open(input_path).convert('RGBA')
    txt_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(txt_layer)

    font = _get_font(font_size, font_path)

    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Create semi-transparent color
    from PIL import ImageColor
    base_color = ImageColor.getrgb(font_color)
    alpha = int(255 * opacity)
    color_with_alpha = base_color[:3] + (alpha,)

    if tile:
        # Tile watermark across entire image
        for y in range(0, img.height, text_height + 50):
            for x in range(0, img.width, text_width + 50):
                draw.text((x, y), text, font=font, fill=color_with_alpha)
    else:
        # Single watermark at specified position
        if position not in POSITIONS:
            position = 'center'

        x, y = POSITIONS[position](img.width, img.height, text_width, text_height)
        draw.text((x, y), text, font=font, fill=color_with_alpha)

    # Composite layers
    watermarked = Image.alpha_composite(img, txt_layer)

    # Convert back to appropriate mode for saving
    if output_path.lower().endswith(('.jpg', '.jpeg')):
        watermarked = watermarked.convert('RGB')

    watermarked.save(output_path)
    return output_path


def add_image_watermark(
    input_path: str,
    output_path: str,
    watermark_path: str,
    position: str = 'center',
    opacity: float = 0.5,
    scale: float | None = None,
    tile: bool = False
) -> str:
    """
    Add image watermark (logo) to an image.

    Args:
        input_path: Path to input image.
        output_path: Path to save watermarked image.
        watermark_path: Path to watermark image.
        position: Position (center/topleft/topright/bottomleft/bottomright/tile).
        opacity: Opacity of watermark (0.0-1.0).
        scale: Scale factor for watermark.
        tile: Tile watermark across image.

    Returns:
        Path to watermarked image.
    """
    img = Image.open(input_path).convert('RGBA')
    watermark = Image.open(watermark_path).convert('RGBA')

    # Scale watermark if requested
    if scale:
        new_wm_w = int(watermark.width * scale)
        new_wm_h = int(watermark.height * scale)
        watermark = watermark.resize((new_wm_w, new_wm_h), Image.Resampling.LANCZOS)

    # Apply opacity
    if opacity < 1.0:
        alpha = watermark.split()[-1]
        alpha = alpha.point(lambda p: int(p * opacity))
        watermark.putalpha(alpha)

    if tile:
        # Create tiled watermark layer
        wm_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        for y in range(0, img.height, watermark.height):
            for x in range(0, img.width, watermark.width):
                wm_layer.paste(watermark, (x, y), watermark)
    else:
        # Single watermark at specified position
        if position not in POSITIONS:
            position = 'center'

        x, y = POSITIONS[position](img.width, img.height, watermark.width, watermark.height)
        wm_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        wm_layer.paste(watermark, (x, y), watermark)

    # Composite layers
    watermarked = Image.alpha_composite(img, wm_layer)

    # Convert back to appropriate mode for saving
    if output_path.lower().endswith(('.jpg', '.jpeg')):
        watermarked = watermarked.convert('RGB')

    watermarked.save(output_path)
    return output_path


def watermark_directory(
    input_dir: str,
    output_dir: str,
    text: str | None = None,
    watermark_image: str | None = None,
    position: str = 'center',
    opacity: float = 0.5,
    font_size: int = 36,
    font_color: str = '#FFFFFF',
    scale: float | None = None,
    tile: bool = False,
    verbose: bool = False
) -> list[str]:
    """
    Add watermark to all images in a directory.

    Args:
        input_dir: Path to input directory.
        output_dir: Path to output directory.
        text: Text watermark.
        watermark_image: Image watermark path.
        position: Watermark position.
        opacity: Watermark opacity.
        font_size: Font size for text watermark.
        font_color: Font color for text watermark.
        scale: Scale factor for image watermark.
        tile: Tile watermark across image.
        verbose: Print progress information.

    Returns:
        List of paths to watermarked images.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    watermarked_files = []
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]

    for img_file in image_files:
        out_file = output_path / img_file.name

        if verbose:
            print(f"Watermarking: {img_file.name}")

        try:
            if text:
                add_text_watermark(
                    str(img_file),
                    str(out_file),
                    text=text,
                    position=position,
                    opacity=opacity,
                    font_size=font_size,
                    font_color=font_color,
                    tile=tile
                )
            elif watermark_image:
                add_image_watermark(
                    str(img_file),
                    str(out_file),
                    watermark_path=watermark_image,
                    position=position,
                    opacity=opacity,
                    scale=scale,
                    tile=tile
                )
            watermarked_files.append(str(out_file))
        except Exception as e:
            print(f"Error watermarking {img_file.name}: {e}")

    return watermarked_files


def main():
    parser = argparse.ArgumentParser(
        description="Add text or image watermarks to images."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        help="Input image file"
    )
    parser.add_argument(
        "-d", "--directory",
        type=str,
        help="Input directory (batch mode)"
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        required=True,
        help="Output file or directory"
    )
    parser.add_argument(
        "-t", "--text",
        type=str,
        help="Text watermark content"
    )
    parser.add_argument(
        "-w", "--watermark",
        type=str,
        help="Path to watermark image"
    )
    parser.add_argument(
        "-p", "--position",
        type=str,
        choices=['center', 'topleft', 'topright', 'bottomleft', 'bottomright'],
        default='center',
        help="Watermark position (default: center). Use --tile to repeat watermark across the image."
    )
    parser.add_argument(
        "--opacity",
        type=float,
        default=0.5,
        help="Watermark opacity 0.0-1.0 (default: 0.5)"
    )
    parser.add_argument(
        "--font-size",
        type=int,
        default=36,
        help="Font size for text watermark (default: 36)"
    )
    parser.add_argument(
        "--font-color",
        type=str,
        default='#FFFFFF',
        help="Font color for text watermark (default: #FFFFFF)"
    )
    parser.add_argument(
        "--scale",
        type=float,
        help="Scale factor for image watermark"
    )
    parser.add_argument(
        "--tile",
        action="store_true",
        help="Tile watermark across image"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either --input or --directory is required")

    if not args.text and not args.watermark:
        parser.error("Either --text or --watermark is required")

    if args.directory:
        files = watermark_directory(
            args.directory,
            args.output,
            text=args.text,
            watermark_image=args.watermark,
            position=args.position,
            opacity=args.opacity,
            font_size=args.font_size,
            font_color=args.font_color,
            scale=args.scale,
            tile=args.tile,
            verbose=args.verbose
        )
        print(f"Watermarked {len(files)} images")
    else:
        if args.text:
            add_text_watermark(
                args.input,
                args.output,
                text=args.text,
                position=args.position,
                opacity=args.opacity,
                font_size=args.font_size,
                font_color=args.font_color,
                tile=args.tile
            )
        else:
            add_image_watermark(
                args.input,
                args.output,
                watermark_path=args.watermark,
                position=args.position,
                opacity=args.opacity,
                scale=args.scale,
                tile=args.tile
            )
        print(f"Watermarked image saved to {args.output}")


if __name__ == "__main__":
    main()