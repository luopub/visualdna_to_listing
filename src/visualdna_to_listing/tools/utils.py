
import base64
from datetime import datetime
import os
import re
from typing import Optional


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
