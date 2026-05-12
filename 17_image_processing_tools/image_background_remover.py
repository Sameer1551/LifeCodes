#!/usr/bin/env python3
"""
Image Background Remover Tool
Remove backgrounds from images automatically using AI.
"""

import argparse
from pathlib import Path
from PIL import Image

try:
    from rembg import remove
    from rembg.session_factory import new_session
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False


SUPPORTED_FORMATS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff')

AVAILABLE_MODELS = ['u2net', 'u2netp', 'u2net_human_seg', 'isnet-general-use']


def remove_background(
    input_path: str,
    output_path: str,
    model: str = 'u2net',
    background_color: str | None = None
) -> str:
    """
    Remove background from an image.

    Args:
        input_path: Path to input image.
        output_path: Path to save output image.
        model: AI model to use (u2net/u2netp/isnet-general-use).
        background_color: Optional background color (hex or name).

    Returns:
        Path to output image.
    """
    if not HAS_REMBG:
        raise ImportError(
            "rembg library is required. Install with: pip install rembg"
        )

    # Read input image
    with open(input_path, 'rb') as f:
        input_data = f.read()

    # Remove background using rembg
    session = new_session(model)
    from io import BytesIO
    with open(input_path, 'rb') as f:
        output_bytes = remove(f.read(), session=session)

    img = Image.open(BytesIO(output_bytes))

    # Apply background color if specified
    if background_color:
        from PIL import ImageColor
        bg_color = ImageColor.getrgb(background_color)

        # Create background layer
        background = Image.new('RGB', img.size, bg_color)

        # Composite: background behind foreground
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
            img = background
        else:
            img = background

    # Ensure PNG format for transparency
    if output_path.lower().endswith(('.jpg', '.jpeg')):
        # Convert to RGB for JPEG (no transparency)
        if img.mode == 'RGBA':
            if background_color is None:
                # Default to white background for JPEG
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                img = background
            else:
                img = img.convert('RGB')

    img.save(output_path)
    return output_path


def remove_background_directory(
    input_dir: str,
    output_dir: str,
    model: str = 'u2net',
    background_color: str | None = None,
    verbose: bool = False
) -> list[str]:
    """
    Remove background from all images in a directory.

    Args:
        input_dir: Path to input directory.
        output_dir: Path to output directory.
        model: AI model to use.
        background_color: Optional background color.
        verbose: Print progress information.

    Returns:
        List of paths to processed images.
    """
    if not HAS_REMBG:
        raise ImportError(
            "rembg library is required. Install with: pip install rembg"
        )

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    processed_files = []
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in SUPPORTED_FORMATS]

    for img_file in image_files:
        # Output as PNG to preserve transparency
        out_file = output_path / f"{img_file.stem}.png"

        if verbose:
            print(f"Processing: {img_file.name}")

        try:
            remove_background(
                str(img_file),
                str(out_file),
                model=model,
                background_color=background_color
            )
            processed_files.append(str(out_file))
        except Exception as e:
            print(f"Error processing {img_file.name}: {e}")

    return processed_files


def main():
    parser = argparse.ArgumentParser(
        description="Remove backgrounds from images using AI."
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
        "-m", "--model",
        type=str,
        choices=AVAILABLE_MODELS,
        default='u2net',
        help="AI model to use (default: u2net). Options: u2net, u2netp (faster), isnet-general-use"
    )
    parser.add_argument(
        "--background",
        type=str,
        help="Background color to apply (hex: #FFFFFF or name: white, blue, etc.)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print progress information"
    )

    args = parser.parse_args()

    if not args.input and not args.directory:
        parser.error("Either --input or --directory is required")

    if not HAS_REMBG:
        print("Error: rembg library is required.")
        print("Install with: pip install rembg")
        print("\nOn first run, the model will be downloaded automatically.")
        return

    try:
        if args.directory:
            files = remove_background_directory(
                args.directory,
                args.output,
                model=args.model,
                background_color=args.background,
                verbose=args.verbose
            )
            print(f"Processed {len(files)} images")
        else:
            remove_background(
                args.input,
                args.output,
                model=args.model,
                background_color=args.background
            )
            print(f"Background removed. Saved to {args.output}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()