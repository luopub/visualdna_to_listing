from crewai.tools import BaseTool
from typing import Type, Optional, List
from pydantic import BaseModel, Field


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


class HunyuanImageToolInput(BaseModel):
    """Input schema for HunyuanImageTool."""
    prompt: str = Field(..., description="Text description for the image to generate. Chinese is recommended. Max 8192 characters.")
    resolution: str = Field(default="1024:1024", description="Image resolution in 'width:height' format. Default is 1024:1024.")
    reference_images: Optional[List[str]] = Field(default=None, description="Reference image URLs for image-to-image generation. Max 3 images. Supports http/https URLs or local file paths.")
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
    args_schema: Type[BaseModel] = HunyuanImageToolInput

    def _run(self, prompt: str, resolution: str = "1024:1024", reference_images: list[str] | None=None, saved_images: list[str] | None=None) -> str:
        import requests
        from pathlib import Path
        from .hunyuan_image import HunyuanImageClient
        import json

        # QWEN3.5 plus call tools with string parameters
        if reference_images:
            reference_images = json.loads(reference_images)
        else:
            reference_images = []

        if saved_images:
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
                        content = 'Reference Images:' + '\n'.join(reference_images) if reference_images else 'None'
                        content += '\n' + 'Prompt:' + prompt
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
