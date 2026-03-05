"""
SKU 图像背景生成工具
使用混元大模型为产品图像添加背景
"""

from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import dataclass

try:
    from .hunyuan_image import HunyuanImageClient
    from .utils import save_image_from_url
except ImportError:
    from hunyuan_image import HunyuanImageClient
    from utils import save_image_from_url


@dataclass
class SKUConfig:
    """SKU configuration"""
    name: str  # SKU name
    image_path: str  # Product image path (local or URL)
    product_name: str = "product"  # Product name for prompt
    background_key: str = "studio_white"  # Background template key
    background_prompt: Optional[str] = None  # Custom background prompt (overrides background_key)
    count: int = 1  # Number of images to generate per SKU


@dataclass
class SKUResult:
    """SKU 生成结果"""
    sku_name: str
    original_image: str
    generated_urls: List[str]
    success: bool
    error: Optional[str] = None


# Predefined background templates
# Use {product} as placeholder for product name
BACKGROUND_TEMPLATES: Dict[str, str] = {
    # Studio scenes
    "studio_white": "{product} placed in a pure white photography studio, professional commercial photography, soft studio lighting, clean and simple, high-definition product image",
    "studio_gray": "{product} placed in a light gray photography studio, professional commercial photography, soft studio lighting, minimalist and elegant, high-definition product image",
    # Indoor scenes
    "living_room": "{product} placed in a modern minimalist living room, cozy home environment, natural lighting, high-definition product display image",
    "bedroom": "{product} placed in a comfortable bedroom, soft morning light, warm home atmosphere, high-definition product display image",
    # Outdoor nature scenes
    "outdoor_nature": "{product} placed in an outdoor natural environment, bright sunshine, fresh and natural, high-definition product display image",
    "outdoor_garden": "{product} placed on a garden lawn, surrounded by green plants, natural lighting, high-definition product display image",
    "beach": "{product} placed on a sandy beach, blue sky and white clouds, golden sunshine, gentle sea breeze, vacation atmosphere, high-definition product display image",
    "countryside": "{product} placed in a countryside field, lush green grass, blue sky and white clouds, pastoral scenery, natural and serene, high-definition product display image",
    # City street scenes
    "street_modern": "{product} placed on a modern city street, towering buildings, fashionable urban atmosphere, natural lighting, high-definition product display image",
    "street_european": "{product} placed on a European-style street, historic buildings, cobblestone pavement, romantic atmosphere, high-definition product display image",
    "street_asian": "{product} placed on an Asian-style street, traditional architectural elements, cultural atmosphere, natural lighting, high-definition product display image",
    # Shopping scenes
    "shopping_mall": "{product} placed in a modern shopping mall, bright lighting, fashionable atmosphere, high-definition product display image",
    "boutique": "{product} placed in a boutique store, exquisite display, warm lighting, high-end shopping atmosphere, high-definition product display image",
    "market": "{product} placed on a market stall, lively atmosphere, natural lighting, lifestyle vibe, high-definition product display image",
    # Model wearing scenes - Young Caucasian female (20-30 years old)
    "model_female_studio": "Young Caucasian female model (20-30 years old) wearing the {product}, professional studio photography, soft lighting, stylish look, high-definition commercial photography",
    "model_female_outdoor": "Young Caucasian female model (20-30 years old) wearing the {product}, outdoor natural lighting, fresh and stylish, high-definition commercial photography",
    "model_female_street": "Young Caucasian female model (20-30 years old) wearing the {product}, city street background, street fashion style, high-definition commercial photography",
    "model_female_casual": "Young Caucasian female model (20-30 years old) wearing the {product}, casual lifestyle setting, natural pose, high-definition commercial photography",
    # Model wearing scenes - Young Caucasian male (20-30 years old)
    "model_male_studio": "Young Caucasian male model (20-30 years old) wearing the {product}, professional studio photography, soft lighting, stylish look, high-definition commercial photography",
    "model_male_outdoor": "Young Caucasian male model (20-30 years old) wearing the {product}, outdoor natural lighting, fresh and stylish, high-definition commercial photography",
    "model_male_street": "Young Caucasian male model (20-30 years old) wearing the {product}, city street background, street fashion style, high-definition commercial photography",
    "model_male_casual": "Young Caucasian male model (20-30 years old) wearing the {product}, casual lifestyle setting, natural pose, high-definition commercial photography",
    # Abstract backgrounds
    "minimalist": "Minimalist style background, soft gradient colors, professional product photography, high-definition display image",
    "gradient": "Soft gradient background, professional commercial photography, distinct light and shadow layers, high-definition product image",
}


class SKUCreator:
    """SKU 图像背景生成器"""

    def __init__(self, output_dir: Optional[str] = None):
        """
        初始化 SKU 创建器

        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir) if output_dir else Path("generated_images/sku")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_background_prompt(self, background_key: Optional[str] = None, product_name: str = "product") -> str:
        """
        Get background prompt with product name replaced.

        Args:
            background_key: Background template key, defaults to studio_white
            product_name: Product name to replace {product} placeholder

        Returns:
            Background prompt with product name
        """
        if background_key and background_key in BACKGROUND_TEMPLATES:
            template = BACKGROUND_TEMPLATES[background_key]
        else:
            template = BACKGROUND_TEMPLATES["studio_white"]

        return template.replace("{product}", product_name)

    def create_sku_images(
        self,
        sku_configs: List[SKUConfig],
        resolution: str = "1024:1024",
        logo_add: int = 0,
        download_images: bool = True
    ) -> List[SKUResult]:
        """
        Generate SKU images with backgrounds.

        Args:
            sku_configs: List of SKU configurations
            resolution: Output resolution
            logo_add: Add watermark (0=no, 1=yes)
            download_images: Download generated images to local

        Returns:
            List of SKU results
        """
        results = []

        for config in sku_configs:
            # Get background prompt (custom or from template)
            if config.background_prompt:
                # Use custom prompt, replace {product} if present
                bg_prompt = config.background_prompt.replace("{product}", config.product_name)
            else:
                # Use template
                bg_prompt = self.get_background_prompt(config.background_key, config.product_name)

            print(f"\nProcessing SKU: {config.name}")
            print(f"  Image: {config.image_path}")
            print(f"  Product: {config.product_name}")
            print(f"  Background: {bg_prompt}")
            print(f"  Count: {config.count}")

            for i in range(config.count):
                print(f"\n  [{i+1}/{config.count}] Generating...")
                result = self._generate_single_sku(
                    config=config,
                    background_prompt=bg_prompt,
                    index=i + 1,
                    resolution=resolution,
                    logo_add=logo_add,
                    download_images=download_images
                )
                results.append(result)

                if result.success:
                    print(f"  Success: {result.generated_urls}")
                else:
                    print(f"  Failed: {result.error}")

        return results

    def _generate_single_sku(
        self,
        config: SKUConfig,
        background_prompt: str,
        index: int,
        resolution: str,
        logo_add: int,
        download_images: bool
    ) -> SKUResult:
        """Generate a single SKU image."""
        try:
            # Call Hunyuan image generation
            gen_result = HunyuanImageClient.generate_image(
                prompt=background_prompt,
                resolution=resolution,
                images=[config.image_path],
                logo_add=logo_add,
                revise=1,
                poll_interval=2,
                max_retries=60
            )

            generated_urls = gen_result.image_urls

            # Download images to local
            if download_images and generated_urls:
                local_paths = self._download_images(
                    urls=generated_urls,
                    sku_name=config.name,
                    index=index
                )
                if local_paths:
                    print(f"  已保存到: {local_paths}")

            return SKUResult(
                sku_name=f"{config.name}_{index}",
                original_image=config.image_path,
                generated_urls=generated_urls,
                success=True
            )

        except Exception as e:
            return SKUResult(
                sku_name=f"{config.name}_{index}",
                original_image=config.image_path,
                generated_urls=[],
                success=False,
                error=str(e)
            )

    def _download_images(
        self,
        urls: List[str],
        sku_name: str,
        index: int
    ) -> List[str]:
        """
        下载生成的图像到本地

        Args:
            urls: 图像 URL 列表
            sku_name: SKU 名称
            index: 序号

        Returns:
            本地文件路径列表
        """
        local_paths = []

        for i, url in enumerate(urls):
            try:
                filename = f"{sku_name}_{index}_{i+1}"
                filepath = save_image_from_url(
                    data_url=url,
                    output_dir=str(self.output_dir),
                    filename=filename
                )
                local_paths.append(filepath)

            except Exception as e:
                print(f"  Failed to download image: {e}")

        return local_paths


def create_sku_with_background(
    sku_name: str,
    image_path: str,
    product_name: str = "product",
    background: str = "studio_white",
    count: int = 1,
    output_dir: Optional[str] = None
) -> List[SKUResult]:
    """
    Convenience function: Generate SKU images with background.

    Args:
        sku_name: SKU name
        image_path: Product image path
        product_name: Product name for prompt (replaces {product} placeholder)
        background: Background type or custom description
        count: Number of images to generate
        output_dir: Output directory

    Returns:
        List of SKU results
    """
    creator = SKUCreator(output_dir=output_dir)

    # Check if background is a predefined template
    if background in BACKGROUND_TEMPLATES:
        background_key = background
        background_prompt = None
    else:
        background_key = "studio_white"
        background_prompt = background  # Custom prompt

    config = SKUConfig(
        name=sku_name,
        image_path=image_path,
        product_name=product_name,
        background_key=background_key,
        background_prompt=background_prompt,
        count=count
    )

    return creator.create_sku_images([config])


# ========== 示例 SKU 产品列表 ==========
# 用户可以修改此列表定义要处理的产品
EXAMPLE_SKU_LIST: List[SKUConfig] = [
    # 示例：豆袋产品
    # SKUConfig(
    #     name="beanbag_heart",
    #     image_path=r"D:\ps-workspace\temu\其它包\豆袋定制\爱心\simulate-1-253232249.jpg",
    #     background_prompt="产品放置在现代简约客厅中，温馨家居环境，自然光线，高清产品展示图",
    #     count=2
    # ),
    # SKUConfig(
    #     name="beanbag_star",
    #     image_path=r"D:\ps-workspace\temu\其它包\豆袋定制\星星\product-001.jpg",
    #     background_prompt="产品放置在舒适卧室中，柔和的晨光，温馨居家氛围，高清产品展示图",
    #     count=1
    # ),
]


def _strip_quotes(text: str) -> str:
    """Remove surrounding quotes (single or double) from a string."""
    if len(text) >= 2:
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            return text[1:-1]
    return text


def main():
    """Command line entry point"""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="SKU Image Background Generator")
    parser.add_argument("--sku_name", "-n", default=None, help="SKU name")
    parser.add_argument("--image", "-i", default=None, help="Product image path")
    parser.add_argument("--product", "-p", default=None, help="Product name for prompt")
    parser.add_argument("--background", "-b", default=None,
                        help=f"Background type: {', '.join(BACKGROUND_TEMPLATES.keys())} or custom description")
    parser.add_argument("--count", "-c", type=int, default=None, help="Number of images to generate")
    parser.add_argument("--output", "-o", default=None, help="Output directory")

    args = parser.parse_args()

    print("=" * 50)
    print("SKU Image Background Generator")
    print("=" * 50)

    product_name = args.product
    if not product_name:
        product_input = input("Enter product name for prompt [default: product]: ").strip()
        product_name = product_input if product_input else "product"

    # Prompt for missing required parameters
    sku_name = args.sku_name
    if not sku_name:
        sku_name = input("Enter SKU name: ").strip()
        if not sku_name:
            print("Error: SKU name is required")
            sys.exit(1)

    image_path = args.image
    if not image_path:
        image_path = input("Enter product image path: ").strip()
        image_path = _strip_quotes(image_path)
        if not image_path:
            print("Error: Image path is required")
            sys.exit(1)

    background = args.background
    if not background:
        print(f"\nAvailable background templates:")
        for i, key in enumerate(BACKGROUND_TEMPLATES.keys(), 1):
            print(f"  {i}. {key}")
        print(f"  Or enter a custom background description")
        bg_input = input("\nEnter background type or custom description [default: studio_white]: ").strip()
        background = bg_input if bg_input else "studio_white"

    count = args.count
    if count is None:
        count_input = input("Enter number of images to generate [default: 1]: ").strip()
        count = int(count_input) if count_input else 1

    output_dir = args.output
    if not output_dir:
        output_input = input("Enter output directory [default: generated_images/sku]: ").strip()
        output_input = _strip_quotes(output_input)
        output_dir = output_input if output_input else None

    print("\n" + "-" * 50)
    print("Configuration:")
    print(f"  SKU name: {sku_name}")
    print(f"  Image path: {image_path}")
    print(f"  Product name: {product_name}")
    print(f"  Background: {background}")
    print(f"  Count: {count}")
    print(f"  Output: {output_dir or 'generated_images/sku'}")
    print("-" * 50)

    confirm = input("\nProceed? [Y/n]: ").strip().lower()
    if confirm == 'n':
        print("Cancelled")
        sys.exit(0)

    print("\nGenerating...")
    results = create_sku_with_background(
        sku_name=sku_name,
        image_path=image_path,
        product_name=product_name,
        background=background,
        count=count,
        output_dir=output_dir
    )

    print("\n" + "=" * 50)
    print("Results")
    print("=" * 50)

    for result in results:
        status = "Success" if result.success else f"Failed: {result.error}"
        print(f"{result.sku_name}: {status}")
        if result.generated_urls:
            for url in result.generated_urls:
                print(f"  - {url}")


if __name__ == "__main__":
    main()
