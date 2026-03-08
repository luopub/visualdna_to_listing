"""
Batch SKU Image Creator
Generate SKU images with backgrounds for multiple SKUs of a single product.
"""

import sys
from pathlib import Path
from typing import List, Optional

try:
    from .sku_creator import SKUCreator, SKUConfig, BACKGROUND_TEMPLATES
except ImportError:
    from sku_creator import SKUCreator, SKUConfig, BACKGROUND_TEMPLATES


def _strip_quotes(text: str) -> str:
    """Remove surrounding quotes (single or double) from a string."""
    if len(text) >= 2:
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            return text[1:-1]
    return text


def _get_image_dir(image_path: str) -> str:
    """Get the directory of an image file."""
    path = Path(image_path)
    if path.exists():
        return str(path.parent.resolve())
    return str(path.parent)


def batch_create_sku_images(
    product_name: str,
    sku_list: List[dict],
    background: str = "studio_white",
    output_dir: Optional[str] = None
) -> dict:
    """
    Batch create SKU images for a single product.

    Args:
        product_name: Product name for prompt
        sku_list: List of SKU configs, each with 'name' and 'image_path'
        background: Background template key or custom description
        output_dir: Output directory (if None, use input image directory)

    Returns:
        Dict with 'success' and 'failed' lists
    """
    # Determine background settings
    if background in BACKGROUND_TEMPLATES:
        background_key = background
        background_prompt = None
    else:
        background_key = "studio_white"
        background_prompt = background

    all_results = []

    # Process each SKU individually to set output directory
    for sku in sku_list:
        # Determine output directory for this SKU
        sku_output_dir = output_dir if output_dir else _get_image_dir(sku['image_path'])

        # Create creator with specific output directory
        creator = SKUCreator(output_dir=sku_output_dir)

        config = SKUConfig(
            name=sku['name'],
            image_path=sku['image_path'],
            product_name=product_name,
            background_key=background_key,
            background_prompt=background_prompt,
            count=sku.get('count', 1)
        )

        # Generate images for this SKU
        results = creator.create_sku_images([config])
        all_results.extend(results)

    # Categorize results
    success_list = [r for r in all_results if r.success]
    failed_list = [r for r in all_results if not r.success]

    return {
        'success': success_list,
        'failed': failed_list,
        'total': len(all_results)
    }


def interactive_mode():
    """Interactive mode for batch SKU creation."""
    print("=" * 60)
    print("Batch SKU Image Creator")
    print("=" * 60)
    print()

    # Get product name
    product_name = input("Enter product name (e.g., 'beanbag', 'backpack'): ").strip()
    if not product_name:
        print("Error: Product name is required")
        sys.exit(1)

    # Get SKU list
    print("\nEnter SKU information (one per line, format: SKU_NAME IMAGE_PATH [COUNT])")
    print("Press Enter with empty line to finish")
    print("Example: beige_leaf_1 D:\\images\\leaf1.jpg 2")
    print("-" * 60)

    sku_list = []
    line_num = 0
    while True:
        line_num += 1
        line = input(f"SKU {line_num}: ").strip()
        if not line:
            break

        parts = line.split()
        if len(parts) < 2:
            print(f"  Warning: Invalid format, skipping line {line_num}")
            continue

        sku_name = parts[0]
        image_path = _strip_quotes(parts[1])
        count = int(parts[2]) if len(parts) > 2 else 1

        sku_list.append({
            'name': sku_name,
            'image_path': image_path,
            'count': count
        })
        print(f"  Added: {sku_name} -> {image_path} (x{count})")

    if not sku_list:
        print("Error: No SKU provided")
        sys.exit(1)

    # Get background
    print(f"\nAvailable background templates:")
    for i, key in enumerate(BACKGROUND_TEMPLATES.keys(), 1):
        print(f"  {i}. {key}")
    print("  Or enter a custom background description")

    bg_input = input("\nEnter background [default: studio_white]: ").strip()
    background = bg_input if bg_input else "studio_white"

    # Get output directory
    print("\nOutput directory options:")
    print("  - Press Enter to use input image directory (each SKU to its source folder)")
    print("  - Or enter a specific output directory")
    output_input = input("Enter output directory [default: same as input image]: ").strip()
    output_input = _strip_quotes(output_input)
    output_dir = output_input if output_input else None

    # Confirm
    print("\n" + "=" * 60)
    print("Configuration Summary:")
    print(f"  Product: {product_name}")
    print(f"  Background: {background}")
    print(f"  Output: {output_dir or 'same as input image directory'}")
    print(f"  SKU count: {len(sku_list)}")
    print("-" * 60)
    print("SKUs:")
    for sku in sku_list:
        img_dir = _get_image_dir(sku['image_path'])
        print(f"  - {sku['name']}: {sku['image_path']} (x{sku['count']}) -> {output_dir or img_dir}")

    confirm = input("\nProceed? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("Cancelled")
        sys.exit(0)

    # Run
    print("\n" + "=" * 60)
    print("Generating...")
    print("=" * 60)

    results = batch_create_sku_images(
        product_name=product_name,
        sku_list=sku_list,
        background=background,
        output_dir=output_dir
    )

    # Print summary
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)
    print(f"Total: {results['total']}")
    print(f"Success: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")

    if results['failed']:
        print("\nFailed items:")
        for r in results['failed']:
            print(f"  - {r.sku_name}: {r.error}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Batch SKU Image Creator")
    parser.add_argument("--product", "-p", default=None, help="Product name")
    parser.add_argument("--background", "-b", default=None, help="Background template or custom description")
    parser.add_argument("--output", "-o", default=None, help="Output directory")
    parser.add_argument("--file", "-f", default=None, help="File containing image paths (one per line)")
    parser.add_argument("--count", "-c", type=int, default=1, help="Number of images to generate per SKU (default: 1)")

    args = parser.parse_args()

    # If no args, run interactive mode
    if not args.product and not args.file:
        interactive_mode()
        return

    # File mode
    if args.file:
        product_name = args.product
        if not product_name:
            product_name = input("Enter product name: ").strip()
            if not product_name:
                print("Error: Product name is required")
                sys.exit(1)

        # Read image paths from file and construct SKU list
        sku_list = []
        sku_index = 0
        with open(args.file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                sku_list.append({
                    'name': f'sku_{sku_index}',
                    'image_path': _strip_quotes(line),
                    'count': args.count
                })
                sku_index += 1

        if not sku_list:
            print("Error: No SKU found in file")
            sys.exit(1)

        background = args.background or "studio_white"
        output_dir = args.output

        print(f"Loaded {len(sku_list)} SKUs from file")
        results = batch_create_sku_images(
            product_name=product_name,
            sku_list=sku_list,
            background=background,
            output_dir=output_dir
        )

        print(f"\nDone! Success: {len(results['success'])}, Failed: {len(results['failed'])}")


if __name__ == "__main__":
    main()
