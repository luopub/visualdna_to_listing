import os

from crewai import LLM
from crewai.tools import BaseTool
from typing import Type, Optional, List
from pydantic import BaseModel, Field
import base64
from pathlib import Path


class UserInputToolInput(BaseModel):
    """Input schema for UserInputTool."""
    prompt_message: str = Field(..., description="The message to display to the user when asking for input.")


class UserInputTool(BaseTool):
    """Tool for receiving user input from the terminal."""
    name: str = "user_input"
    description: str = (
        "Use this tool to prompt the user for input from the terminal. "
        "Display a message to the user and wait for their response. "
        "Useful for collecting product information, file paths, or any user-provided data."
    )
    args_schema: Type[BaseModel] = UserInputToolInput

    def _run(self, prompt_message: str) -> str:
        print(f"\n{prompt_message}")
        user_input = input("> ")
        return user_input


class ImageToolInput(BaseModel):
    """Input schema for image generation tools."""
    prompt: str = Field(..., description="Text description for the image to generate.")
    resolution: str = Field(default="1024:1024", description="Image resolution in 'width:height' format. Default is 1024:1024.")
    reference_images: Optional[List[str]] = Field(default=None, description="Reference image URLs for image-to-image generation. Supports http/https URLs or local file paths.")
    saved_images: Optional[List[str]] = Field(default=None, description="Filename list for saving generated images. If provided, images will be saved to 'generated_images' directory with these names.")


class HunyuanImageTool(BaseTool):
    """Hunyuan text-to-image tool for generating images from text descriptions."""
    name: str = "hunyuan_image_generator"
    description: str = (
        "Generate images using Hunyuan AI model. "
        "Input a text description (prompt) to generate corresponding images. "
        "Optionally specify resolution (resolution), reference images (reference_images), "
        "and filenames for saving (saved_images). "
        "If saved_images is provided, images will be saved to 'generated_images' directory; "
        "otherwise returns the URLs of generated images."
    )
    args_schema: Type[BaseModel] = ImageToolInput

    def _run(self, prompt: str, resolution: str = "1024:1024", reference_images: list[str] | None=None, saved_images: list[str] | None=None) -> str:
        import requests
        from pathlib import Path
        try:
            from .hunyuan_image import HunyuanImageClient
        except ImportError:
            from hunyuan_image import HunyuanImageClient
        import json

        # QWEN3.5 plus call tools with string parameters
        if reference_images:
            if isinstance(reference_images, str):
                reference_images = json.loads(reference_images)
        else:
            reference_images = []

        if saved_images:
            if isinstance(saved_images, str):
                saved_images = json.loads(saved_images)
        else:
            saved_images = []

        try:
            result = HunyuanImageClient.generate_image(
                prompt=prompt,
                resolution=resolution,
                images=reference_images
            )

            if result.is_failed:
                return f"Image generation failed: {result.error_msg}"

            if result.image_urls:
                if saved_images:
                    # Create output directory
                    output_dir = Path("generated_images")
                    output_dir.mkdir(exist_ok=True)

                    saved_paths = []
                    for url, filename in zip(result.image_urls, saved_images):
                        # Download and save image
                        response = requests.get(url, timeout=30)
                        response.raise_for_status()

                        file_path = output_dir / filename
                        file_path.write_bytes(response.content)
                        saved_paths.append(str(file_path))

                        # Save prompt with the same name (.txt)
                        prompt_path = file_path.with_suffix('.txt')
                        content = 'Reference Images:\n' + ('\n'.join(reference_images) if reference_images else 'None')
                        content += '\n' + 'Prompt:\n' + prompt
                        prompt_path.write_text(content, encoding='utf-8')

                    paths_str = "\n".join(saved_paths)
                    return f"{paths_str}"
                else:
                    urls_str = "\n".join(result.image_urls)
                    return f"{urls_str}"
            else:
                return "Image generation completed but no image URLs were returned."

        except Exception as e:
            return f"Image generation error: {str(e)}"


class OpenRouterImageTool(BaseTool):
    """OpenRouter text-to-image tool for generating images from text descriptions."""
    name: str = "openrouter_image_generator"
    description: str = (
        "Generate images using OpenRouter AI models (e.g., Gemini). "
        "Input a text description (prompt) to generate corresponding images. "
        "Optionally specify resolution (resolution), reference images (reference_images), "
        "and filenames for saving (saved_images). "
        "If saved_images is provided, images will be saved to 'generated_images' directory; "
        "otherwise returns the data URLs of generated images."
    )
    args_schema: Type[BaseModel] = ImageToolInput

    def _run(self, prompt: str, resolution: str = "1024:1024", reference_images: list[str] | None = None, saved_images: list[str] | None = None) -> str:
        from pathlib import Path
        try:
            from .openrouter_image import OpenRouterImageClient, save_image_from_url
        except ImportError:
            from openrouter_image import OpenRouterImageClient, save_image_from_url
        import json

        # QWEN3.5 plus call tools with string parameters
        if reference_images:
            if isinstance(reference_images, str):
                reference_images = json.loads(reference_images)
        else:
            reference_images = []

        if saved_images:
            if isinstance(saved_images, str):
                saved_images = json.loads(saved_images)
        else:
            saved_images = []

        # Convert resolution (width:height) to aspect ratio
        def resolution_to_aspect_ratio(res: str) -> str | None:
            try:
                width, height = map(int, res.split(':'))
                # Simplify to common aspect ratios
                from math import gcd
                g = gcd(width, height)
                w, h = width // g, height // g
                # Map to supported aspect ratios
                ratio_map = {
                    (1, 1): "1:1",
                    (1, 4): "1:4",
                    (1, 8): "1:8",
                    (2, 3): "2:3",
                    (3, 2): "3:2",
                    (3, 4): "3:4",
                    (4, 1): "4:1",
                    (4, 3): "4:3",
                    (4, 5): "4:5",
                    (5, 4): "5:4",
                    (8, 1): "8:1",
                    (9, 16): "9:16",
                    (16, 9): "16:9",
                    (21, 9): "21:9",
                }
                return ratio_map.get((w, h), "1:1")
            except:
                return "1:1"

        aspect_ratio = resolution_to_aspect_ratio(resolution)
        # Determine image size based on resolution
        def resolution_to_image_size(res: str) -> str:
            try:
                width, height = map(int, res.split(':'))
                max_dim = max(width, height)
                if max_dim <= 512:
                    return "512px"
                elif max_dim <= 1024:
                    return "1K"
                elif max_dim <= 2048:
                    return "2K"
                else:
                    return "4K"
            except:
                return "2K"

        image_size = resolution_to_image_size(resolution)

        try:
            image_urls = OpenRouterImageClient.generate_image(
                prompt=prompt,
                images=reference_images if reference_images else None,
                aspect_ratio=aspect_ratio,
                image_size=image_size,
            )

            if not image_urls:
                return "Image generation completed but no images were returned."

            if saved_images:
                # Create output directory
                output_dir = Path("generated_images")
                output_dir.mkdir(exist_ok=True)

                saved_paths = []
                for url, filename in zip(image_urls, saved_images):
                    filepath = save_image_from_url(url, str(output_dir), filename)
                    saved_paths.append(filepath)

                    # Save prompt with the same name (.txt)
                    prompt_path = Path(filepath).with_suffix('.txt')
                    content = 'Reference Images:\n' + ('\n'.join(reference_images) if reference_images else 'None')
                    content += '\n' + 'Prompt:\n' + prompt
                    prompt_path.write_text(content, encoding='utf-8')

                paths_str = "\n".join(saved_paths)
                return f"{paths_str}"
            else:
                urls_str = "\n".join(image_urls)
                return f"{urls_str}"

        except Exception as e:
            return f"Image generation error: {str(e)}"


# Vision LLM for image description
_vision_llm: LLM | None = None


def get_vision_llm() -> LLM:
    """Get or create the vision LLM instance."""
    global _vision_llm
    if _vision_llm is None:
        _vision_llm = LLM(
            model="qwen3.5-plus",
            api_key=os.environ.get("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    return _vision_llm


class GetImageDescToolInput(BaseModel):
    """Input schema for GetImageDescTool."""
    image_source: str = Field(..., description="Image source: URL (http/https) or local file path.")
    focus_aspect: Optional[str] = Field(default=None, description="Optional aspect to focus on (e.g., 'product features', 'color scheme', 'background', 'style').")


class GetImageDescTool(BaseTool):
    """Tool for getting image descriptions useful for product listing image generation prompts."""
    name: str = "get_image_description"
    description: str = (
        "Analyze an image and generate a detailed description useful for creating product listing image generation prompts. "
        "Supports both URLs and local file paths. "
        "Focuses on visual elements like product features, colors, composition, lighting, and style. "
        "Optionally specify a focus_aspect to concentrate the analysis on specific elements."
    )
    args_schema: Type[BaseModel] = GetImageDescToolInput

    def _run(self, image_source: str, focus_aspect: str | None = None) -> str:
        # Prepare image content
        if image_source.startswith("http://") or image_source.startswith("https://"):
            # URL source
            image_url = image_source
        else:
            # Local file - convert to base64 data URL
            try:
                file_path = Path(image_source)
                if not file_path.exists():
                    return f"Error: Local file not found: {image_source}"

                # Detect image type
                suffix = file_path.suffix.lower()
                mime_types = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }
                mime_type = mime_types.get(suffix, 'image/jpeg')

                with open(file_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                image_url = f"data:{mime_type};base64,{image_data}"
            except Exception as e:
                return f"Error reading local file: {str(e)}"

        # Build the prompt for product listing focused description
        base_prompt = """Analyze this image and provide a detailed description optimized for creating product listing image generation prompts.

Focus on:
1. **Product/Subject**: What is the main subject? Describe its key features, shape, material appearance, and distinctive characteristics.
2. **Colors**: List the main colors present, including exact shades if identifiable.
3. **Composition**: Describe the layout, positioning, and spatial arrangement.
4. **Lighting**: Note the lighting style (natural, studio, soft, dramatic, etc.) and direction.
5. **Background**: Describe the background elements, colors, and setting.
6. **Style/Mood**: Identify the visual style (minimalist, lifestyle, commercial, artistic) and overall mood.
7. **Texture & Details**: Note any visible textures, patterns, or fine details.
Summarize the final description in a clear and concise manner in less than 100 words. Output only the summary. Ensure the output is in English.
"""

# Format the output as a structured description that can be directly used as reference for generating similar product listing images."""

        if focus_aspect:
            base_prompt += f"\n\n**Special Focus**: Pay extra attention to '{focus_aspect}' in your analysis."

        try:
            llm = get_vision_llm()
            response = llm.call(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": base_prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ]
            )
            return response or "No description generated."

        except Exception as e:
            return f"Error analyzing image: {str(e)}"


if __name__ == "__main__":
    # ========== Test GetImageDescTool ==========
    # print("=" * 50)
    # print("GetImageDescTool Test")
    # print("=" * 50)

    # # Check if API key is set
    # if not os.environ.get("DASHSCOPE_API_KEY"):
    #     print("Error: DASHSCOPE_API_KEY environment variable is not set.")
    #     print("Please set it before running the test:")
    #     print("  Windows: set DASHSCOPE_API_KEY=your-api-key")
    #     print("  Linux/Mac: export DASHSCOPE_API_KEY=your-api-key")
    #     exit(1)

    # tool = GetImageDescTool()

    # # Test 1: Analyze a local image file
    # print("\n--- Test 1: Local Image File ---")
    # test_image = input("Enter path to a test image file (or press Enter to skip): ").strip()
    # if test_image:
    #     print(f"\nAnalyzing: {test_image}")
    #     result = tool._run(image_source=test_image)
    #     print(f"\nResult:\n{result}")
    # else:
    #     print("Skipped local file test.")

    # # Test 2: Analyze an image URL
    # print("\n--- Test 2: Image URL ---")
    # test_url = input("Enter an image URL (or press Enter to skip): ").strip()
    # if test_url:
    #     print(f"\nAnalyzing: {test_url}")
    #     result = tool._run(image_source=test_url)
    #     print(f"\nResult:\n{result}")
    # else:
    #     print("Skipped URL test.")

    # # Test 3: Analyze with focus aspect
    # print("\n--- Test 3: With Focus Aspect ---")
    # if test_image or test_url:
    #     source = test_image or test_url
    #     focus = input("Enter focus aspect (e.g., 'colors', 'style', or press Enter to skip): ").strip()
    #     if focus:
    #         print(f"\nAnalyzing with focus on '{focus}': {source}")
    #         result = tool._run(image_source=source, focus_aspect=focus)
    #         print(f"\nResult:\n{result}")
    # else:
    #     print("Skipped focus aspect test (no image provided).")

    # ========== Test OpenRouterImageTool ==========
    print("\n" + "=" * 50)
    print("OpenRouterImageTool Test")
    print("=" * 50)

    if not os.environ.get("OPENROUTER_IMGEN_API_KEY"):
        print("Error: OPENROUTER_IMGEN_API_KEY environment variable is not set.")
        print("Please set it before running the test:")
        print("  Windows: set OPENROUTER_IMGEN_API_KEY=your-api-key")
        print("  Linux/Mac: export OPENROUTER_IMGEN_API_KEY=your-api-key")
    else:
        img_tool = OpenRouterImageTool()

        # Test with reference images
        print("\n--- Test: Generate Image with Reference Images ---")
        ref_images = input("Enter reference image paths (comma-separated, or press Enter to skip): ").strip()
        if ref_images:
            ref_list = [p.strip() for p in ref_images.split(",")]
        else:
            ref_list = []

        gen_prompt = input("Enter generation prompt (or press Enter for default test): ").strip()
        if not gen_prompt:
            gen_prompt = "A beautiful product photo with clean background"

        print(f"\nGenerating image...")
        print(f"  Prompt: {gen_prompt[:80]}...")
        if ref_list:
            print(f"  Reference images: {len(ref_list)}")

        result = img_tool._run(
            prompt=gen_prompt,
            resolution="1024:1024",
            reference_images=ref_list if ref_list else None,
            saved_images=["test_output"]
        )
        print(f"\nResult:\n{result}")

    print("\n" + "=" * 50)
    print("Test completed")
    print("=" * 50)
