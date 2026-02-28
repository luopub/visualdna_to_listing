import base64
import os
from typing import Optional, Union

from openai import OpenAI

OPENROUTER_IMGEN_API_KEY = os.environ.get("OPENROUTER_IMGEN_API_KEY")

_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    """获取或创建 OpenRouter 客户端实例"""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_IMGEN_API_KEY,
        )
    return _client


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


def generate_image(
    prompt: str,
    model: str = "google/gemini-3.1-flash-image-preview",
    images: Optional[Union[str, list[str]]] = None,
) -> list[str]:
    """
    使用 OpenRouter 生成图片

    Args:
        prompt: 图片生成提示词
        model: 使用的模型名称
        images: 参考图片，可以是本地文件路径或 URL，支持单个或多个

    Returns:
        生成的图片 URL 列表 (Base64 data URLs)
    """
    client = _get_client()

    # 构建消息内容
    content = []

    # 添加参考图片
    if images:
        image_list = [images] if isinstance(images, str) else images
        for img in image_list:
            image_url = _load_image_as_url(img)
            content.append({
                "type": "image_url",
                "image_url": {"url": image_url},
            })

    # 添加文本提示
    content.append({"type": "text", "text": prompt})

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        extra_body={"modalities": ["image", "text"]},
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
    test_image = "path/to/your/image.jpg"  # 本地路径或 URL
    urls = generate_image("根据参考图片生成一个变体", images=test_image)
    if urls:
        print(f"成功生成 {len(urls)} 张图片 (带参考图):")
        for i, url in enumerate(urls, 1):
            print(f"  图片 {i}: {url[:80]}...")