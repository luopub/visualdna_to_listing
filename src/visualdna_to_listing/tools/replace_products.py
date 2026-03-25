"""
产品图片批量替换工具
根据JSON配置文件，使用HunyuanImageClient进行产品图片的批量替换
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
import urllib.request

from PIL import Image

# 导入HunyuanImageClient
try:
    from .utils import save_image_from_url
    from .hunyuan_image import HunyuanImageClient
except ImportError:
    from hunyuan_image import HunyuanImageClient
    from utils import save_image_from_url

def load_json_config(json_path: str) -> Dict[str, Any]:
    """
    加载JSON配置文件

    Args:
        json_path: JSON文件路径

    Returns:
        JSON配置字典

    Raises:
        Exception: 文件不存在或解析失败时抛出异常
    """
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {json_path}")

    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def process_replace_task(task: Dict[str, str], client: HunyuanImageClient, index: int, total: int) -> bool:
    """
    处理单个图片替换任务

    Args:
        task: 任务配置字典
        client: HunyuanImageClient实例
        index: 当前任务索引
        total: 总任务数

    Returns:
        是否处理成功
    """
    name = task.get("名称", f"任务{index + 1}")
    prompt = task.get("提示词", "")
    original_file = task.get("原始文件", "")
    new_product_image = task.get("新产品图", "")
    output_file = task.get("输出文件", "")

    print(f"\n[{index + 1}/{total}] 处理: {name}")
    print(f"  提示词: {prompt}")
    print(f"  原始文件: {original_file}")
    print(f"  新产品图: {new_product_image}")
    print(f"  输出文件: {output_file}")

    # 验证输入文件是否存在
    if not Path(original_file).exists():
        print(f"  错误: 原始文件不存在: {original_file}")
        return False

    if not Path(new_product_image).exists():
        print(f"  错误: 新产品图不存在: {new_product_image}")
        return False

    try:
        # 调用混元生图API
        # 将原始文件和新产品图作为垫图传入
        result = client.generate_image_intern(
            prompt=prompt,
            resolution="1024:1024",
            images=[original_file, new_product_image],  # 两张垫图：原始场景图 + 新产品图
            logo_add=0,  # 不添加水印
            revise=1,    # 开启提示词改写
            poll_interval=2,
            max_retries=60
        )

        if result.is_completed and result.image_urls:
            # 下载生成的图片
            saved_path = save_image_from_url(result.image_urls[0], str(Path(output_file).parent), Path(output_file).stem)
            print(f"  图片已保存: {saved_path}")

            # 如果是 PNG 文件，转换为 JPG 并删除原始文件
            saved_path_obj = Path(saved_path)
            if saved_path_obj.suffix.lower() == '.png':
                jpg_path = saved_path_obj.with_suffix('.jpg')
                try:
                    with Image.open(saved_path_obj) as img:
                        # 转换为 RGB 模式（JPG 不支持透明度）
                        if img.mode in ('RGBA', 'LA', 'P'):
                            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                            rgb_img.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                            img = rgb_img
                        else:
                            img = img.convert('RGB')
                        img.save(jpg_path, 'JPEG', quality=95)
                    # 删除原始 PNG 文件
                    saved_path_obj.unlink()
                    print(f"  已转换为 JPG: {jpg_path}")
                except Exception as e:
                    print(f"  转换 JPG 失败: {e}")

            return True
        else:
            print(f"  生成失败: {result.error_msg or '未知错误'}")
            return False

    except Exception as e:
        print(f"  处理异常: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("产品图片批量替换工具")
    print("=" * 60)

    # 提示用户输入JSON文件路径
    json_path = input("\n请输入JSON配置文件路径: ").strip()

    # 移除可能的引号
    json_path = re.sub("(^')|('$)|(^\")|(\"$)", '', json_path)

    if not json_path or not json_path.endswith(".json") or not Path(json_path).exists():
        print("错误: 未输入文件路径或文件不存在，请提供有效的JSON文件路径")
        sys.exit(1)

    try:
        # 加载配置
        print(f"\n正在加载配置文件: {json_path}")
        config = load_json_config(json_path)

        # 获取图片替换任务列表
        tasks = config.get("图片替换", [])

        if not tasks:
            print("错误: 配置文件中未找到'图片替换'任务列表")
            sys.exit(1)

        print(f"找到 {len(tasks)} 个替换任务")

        # 初始化HunyuanImageClient
        print("\n初始化混元生图客户端...")
        client = HunyuanImageClient()

        # 处理每个任务
        success_count = 0
        fail_count = 0

        for i, task in enumerate(tasks):
            if process_replace_task(task, client, i, len(tasks)):
                success_count += 1
            else:
                fail_count += 1

            # 任务之间添加短暂延迟，避免API限流
            if i < len(tasks) - 1:
                print("  等待3秒后处理下一个任务...")
                time.sleep(3)

        # 输出统计结果
        print("\n" + "=" * 60)
        print("处理完成!")
        print(f"  成功: {success_count}")
        print(f"  失败: {fail_count}")
        print(f"  总计: {len(tasks)}")
        print("=" * 60)

    except FileNotFoundError as e:
        print(f"错误: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON文件解析失败 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
