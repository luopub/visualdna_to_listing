import base64
import os
import re
from datetime import datetime
from typing import Literal, Optional, Union

from openai import OpenAI

OPENROUTER_IMGEN_API_KEY = os.environ.get("OPENROUTER_IMGEN_API_KEY")

# 支持的宽高比
AspectRatio = Literal[
    "1:1", "1:4", "1:8", "2:3", "3:2", "3:4", "4:1", "4:3", "4:5", "5:4", "8:1", "9:16", "16:9", "21:9"
]

# 支持的分辨率
ImageSize = Literal["512px", "1K", "2K", "4K"]

class OpenRouterImageClient:
    """OpenRouter 图片生成客户端"""

    _client: Optional[OpenAI] = None

    @classmethod
    def _get_client(cls) -> OpenAI:
        """获取或创建 OpenRouter 客户端实例"""
        if cls._client is None:
            cls._client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=OPENROUTER_IMGEN_API_KEY,
            )
        return cls._client

    @staticmethod
    def _load_image_as_url(image_path_or_url: str) -> str:
        """
        加载图片并返回 data URL 格式

        Args:
            image_path_or_url: 本地文件路径或 URL

        Returns:
            data URL 格式的字符串 (对于本地文件) 或原始 URL
        """
        # 判断是否为 URL
        if image_path_or_url.startswith(("http://", "https://", "data:")):
            return image_path_or_url

        # 本地文件，读取并转换为 base64
        with open(image_path_or_url, "rb") as f:
            image_data = f.read()

        # 根据文件扩展名判断 MIME 类型
        ext = os.path.splitext(image_path_or_url)[1].lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(ext, "image/jpeg")

        base64_data = base64.b64encode(image_data).decode("utf-8")
        return f"data:{mime_type};base64,{base64_data}"

    @staticmethod
    def generate_image(
        prompt: str,
        model: str = "google/gemini-3.1-flash-image-preview",
        images: Optional[Union[str, list[str]]] = None,
        aspect_ratio: Optional[AspectRatio] = None,
        image_size: Optional[ImageSize] = None,
    ) -> list[str]:
        """
        使用 OpenRouter 生成图片

        Args:
            prompt: 图片生成提示词
            model: 使用的模型名称
            images: 参考图片，可以是本地文件路径或 URL，支持单个或多个
            aspect_ratio: 宽高比，可选值: "1:1", "1:4", "1:8", "2:3", "3:2", "3:4", 
                          "4:1", "4:3", "4:5", "5:4", "8:1", "9:16", "16:9", "21:9"
            image_size: 分辨率，可选值: "512px", "1K", "2K", "4K"

        Returns:
            生成的图片 URL 列表 (Base64 data URLs)
        """
        client = OpenRouterImageClient._get_client()

        # 构建消息内容
        content = []

        # 添加参考图片
        if images:
            image_list = [images] if isinstance(images, str) else images
            for img in image_list:
                image_url = OpenRouterImageClient._load_image_as_url(img)
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url},
                })

        # 添加文本提示
        content.append({"type": "text", "text": prompt})

        # 构建 extra_body
        extra_body: dict = {"modalities": ["image", "text"]}
        
        # 添加图片配置
        image_config = {}
        if aspect_ratio:
            image_config["aspectRatio"] = aspect_ratio
        if image_size:
            image_config["imageSize"] = image_size
        
        if image_config:
            extra_body["imageConfig"] = image_config

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            extra_body=extra_body,
        )

        message = response.choices[0].message
        image_urls = []
        # OpenRouter 特有属性，不在标准 OpenAI 类型中
        result_images = getattr(message, "images", None)
        if result_images:
            for image in result_images:
                image_url = image["image_url"]["url"]
                image_urls.append(image_url)
        return image_urls


def save_image_from_url(data_url: str, output_dir: str, filename: Optional[str] = None) -> str:
    """
    将 data URL 保存为图片文件

    Args:
        data_url: data URL 或普通 URL
        output_dir: 输出目录
        filename: 文件名（不含扩展名），默认使用时间戳

    Returns:
        保存的文件路径
    """
    os.makedirs(output_dir, exist_ok=True)

    if data_url.startswith("data:"):
        # 解析 data URL
        match = re.match(r"data:image/(\w+);base64,(.+)", data_url)
        if match:
            ext = match.group(1)
            if ext == "jpeg":
                ext = "jpg"
            base64_data = match.group(2)
            image_data = base64.b64decode(base64_data)
        else:
            raise ValueError(f"Invalid data URL format")
    else:
        # 普通 URL，下载图片
        import urllib.request

        ext = "jpg"
        with urllib.request.urlopen(data_url) as response:
            image_data = response.read()
        # 尝试从 Content-Type 获取扩展名
        content_type = response.headers.get("Content-Type", "")
        if "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"
        elif "gif" in content_type:
            ext = "gif"

    if filename is None:
        filename = datetime.now().strftime("%Y%m%d_%H%M%S")

    filepath = os.path.join(output_dir, f"{filename}.{ext}")

    # 避免文件名冲突
    counter = 1
    while os.path.exists(filepath):
        filepath = os.path.join(output_dir, f"{filename}_{counter}.{ext}")
        counter += 1

    with open(filepath, "wb") as f:
        f.write(image_data)

    return filepath


if __name__ == "__main__":
    # 测试生成图片
    # test_prompt = "Generate a beautiful sunset over mountains"
    # print(f"生成图片: {test_prompt}")

    # 测试1: 无参考图片
    # urls = generate_image(test_prompt)
    # if urls:
    #     print(f"成功生成 {len(urls)} 张图片:")
    #     for i, url in enumerate(urls, 1):
    #         print(f"  图片 {i}: {url[:80]}...")
    # else:
    #     print("未生成图片")

    # 测试2: 带参考图片 (取消注释以测试)
    test_image = [r"D:\ps-workspace\temu\其它包\成品图\儿童豆袋椅收纳包-水滴-灰色星星\英语\儿童-sku-2.jpg",
                  r"D:\ps-workspace\temu\其它包\成品图\儿童豆袋椅收纳包-水滴-灰色星星\英语\提起.jpg"]  # 本地路径或 URL
    prompt = """Product Core: split-screen before/after comparison: Left side shows stuffed animals scattered on bedroom floor (cluttered state), right side shows same stuffed animals stored inside grey crystal velvet bean bag with child sitting comfortably on top, teardrop-shaped silhouette centered, white star pattern visible, carrying loop at top apex. Material Specs: 100% polyester super soft crystal velvet with plush surface matching the exact grey color and texture from reference, visible fabric fold lines demonstrating material flexibility, heavy-duty zipper enabling easy access for storage. Perspective: eye-level camera angle, consistent lighting across both panels, full product visible in "after" panel. Environment: Real bedroom setting on both sides, warm 3000-3500K lighting, lived-in appearance not perfectly staged, addresses 60%+ of reviews mentioning storage function. Quality Tags: Photorealistic, transformation clarity, NO extra accessories, NO text overlays, demonstrates dual-purpose storage, large capacity for stuffed animal organization proven, purchase trigger visually addressed."""
    urls = OpenRouterImageClient.generate_image(prompt, images=test_image, aspect_ratio="1:1", image_size="2K")

    output_dir = r"d:\temp"
    if urls:
        print(f"成功生成 {len(urls)} 张图片 (带参考图):")
        for i, url in enumerate(urls, 1):
            filepath = save_image_from_url(url, output_dir, f"generated_1{i}")
            print(f"  图片 {i} 已保存: {filepath}")
    else:
        print("未生成图片")