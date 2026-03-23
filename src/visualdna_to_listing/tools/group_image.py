import os
import json
import csv
from pathlib import Path
import re
from typing import Optional
from datetime import datetime

try:
    from .custom_tool import GetImageDescTool
    from .llm_provider import LLMProvider
except ImportError:
    from custom_tool import GetImageDescTool
    from llm_provider import LLMProvider


class ImageGrouper:
    """图片分组工具类，用于分析目录中的图片并根据描述进行分组。"""

    # 默认获取图片描述的提示词
    DEFAULT_IMAGE_DESC_PROMPT = """图片是亚马逊商品列表图片，请分析图片所展示的卖点，然后输出图片卖点和图片结构"""

    # 默认分组提示词
    DEFAULT_GROUPING_PROMPT = """对下面的产品描述根据卖点和结构进行分组，为每组给一个简短名称。然后输出每组所包含的文件路径。

请按以下JSON格式输出：
{
    "groups": [
        {
            "name": "组名称",
            "files": ["文件路径1", "文件路径2"]
        }
    ]
}

产品描述数据如下："""

    def __init__(
        self,
        image_desc_prompt: Optional[str] = None,
        grouping_prompt: Optional[str] = None,
        image_extensions: tuple = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp')
    ):
        """
        初始化图片分组器。

        Args:
            image_desc_prompt: 自定义图片描述提示词，默认为 DEFAULT_IMAGE_DESC_PROMPT
            grouping_prompt: 自定义分组提示词，默认为 DEFAULT_GROUPING_PROMPT
            image_extensions: 支持的图片扩展名元组
        """
        self.image_desc_prompt = image_desc_prompt or self.DEFAULT_IMAGE_DESC_PROMPT
        self.grouping_prompt = grouping_prompt or self.DEFAULT_GROUPING_PROMPT
        self.image_extensions = image_extensions
        self.image_desc_tool = GetImageDescTool()

    def get_image_files(self, directory: str) -> list[str]:
        """
        获取指定目录中的所有图片文件路径。

        Args:
            directory: 图片目录路径

        Returns:
            图片文件路径列表
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise ValueError(f"目录不存在: {directory}")

        image_files = []
        for ext in self.image_extensions:
            image_files.extend(dir_path.glob(f"*{ext}"))
            image_files.extend(dir_path.glob(f"*{ext.upper()}"))

        # 去重并排序
        unique_files = sorted(set(str(f) for f in image_files))
        return unique_files

    def analyze_images(
        self,
        directory: str,
        output_json_path: Optional[str] = None
    ) -> dict[str, str]:
        """
        分析目录中的所有图片并获取描述，即时保存到JSON文件。

        Args:
            directory: 图片目录路径
            output_json_path: 描述结果JSON文件路径，默认为目录下的 image_descriptions_时间戳.json

        Returns:
            图片路径到描述的字典
        """
        image_files = self.get_image_files(directory)

        if not image_files:
            print(f"在目录 '{directory}' 中未找到图片文件")
            return {}

        print(f"找到 {len(image_files)} 张图片，开始分析...")

        # 初始化描述字典
        descriptions = {}

        # 如果json文件已经存在，先加载已有的描述（避免重复分析）
        if output_json_path and os.path.exists(output_json_path):
            with open(output_json_path, 'r', encoding='utf-8') as f:
                descriptions = json.load(f).get("descriptions", {})
            # 过滤掉已分析的图片，只保留需要重新分析的
            image_files = [img for img in image_files if img not in descriptions]

        # 设置默认输出路径
        if output_json_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_json_path = os.path.join(directory, f"image_descriptions_{timestamp}.json")

        for i, image_path in enumerate(image_files, 1):
            print(f"[{i}/{len(image_files)}] 正在分析: {image_path}")

            try:
                # 使用 GetImageDescTool 获取图片描述
                description = self.image_desc_tool._run(
                    image_source=image_path,
                    base_prompt=self.image_desc_prompt
                )

                descriptions[image_path] = description
                print(f"  ✓ 描述: {description[:100]}...")

                # 即时保存到JSON文件（避免丢失）
                self._save_descriptions_incremental(output_json_path, descriptions)

            except Exception as e:
                print(f"  ✗ 分析失败: {str(e)}")
                descriptions[image_path] = f"ERROR: {str(e)}"
                self._save_descriptions_incremental(output_json_path, descriptions)

        print(f"\n图片描述已保存到: {output_json_path}")
        return descriptions

    def _save_descriptions_incremental(self, json_path: str, descriptions: dict):
        """增量保存描述到JSON文件。"""
        output_data = {
            "generated_at": datetime.now().isoformat(),
            "prompt_used": self.image_desc_prompt,
            "total_images": len(descriptions),
            "descriptions": descriptions
        }

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)

    def group_images(
        self,
        descriptions: dict[str, str],
        output_csv_path: Optional[str] = None,
        directory: Optional[str] = None
    ) -> list[dict]:
        """
        根据图片描述进行分组。

        Args:
            descriptions: 图片路径到描述的字典
            output_csv_path: 分组结果CSV文件路径，默认为目录下的 image_groups_时间戳.csv
            directory: 用于生成默认输出路径的目录

        Returns:
            分组结果列表，每个分组包含 name 和 files
        """
        if not descriptions:
            print("没有图片描述可供分组")
            return []

        print(f"\n开始对 {len(descriptions)} 张图片进行分组...")

        # 构建分组提示词
        descriptions_text = json.dumps(descriptions, ensure_ascii=False, indent=2)
        full_prompt = f"{self.grouping_prompt}\n\n{descriptions_text}"

        try:
            # 使用 LLMProvider.get_llm_main 获取大模型进行分组
            llm = LLMProvider.get_llm_main()
            response = llm.call(
                messages=[
                    {"role": "user", "content": full_prompt}
                ]
            )

            # 解析JSON响应
            groups = self._parse_grouping_response(response)

            # 设置默认输出路径
            if output_csv_path is None and directory:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_csv_path = os.path.join(directory, f"image_groups_{timestamp}.csv")

            # 保存分组结果到CSV
            if output_csv_path:
                self._save_groups_to_csv(output_csv_path, groups)
                print(f"\n分组结果已保存到: {output_csv_path}")

            return groups

        except Exception as e:
            print(f"分组失败: {str(e)}")
            return []

    def _parse_grouping_response(self, response: str) -> list[dict]:
        """解析大模型的分组响应。"""
        try:
            # 尝试直接解析JSON
            data = json.loads(response)
            if "groups" in data:
                return data["groups"]
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            # 尝试从markdown代码块中提取JSON
            import re

            # 查找 ```json ... ``` 或 ``` ... ``` 格式的代码块
            json_pattern = r'```(?:json)?\s*([\s\S]*?)```'
            matches = re.findall(json_pattern, response)

            for match in matches:
                try:
                    data = json.loads(match.strip())
                    if "groups" in data:
                        return data["groups"]
                    if isinstance(data, list):
                        return data
                except json.JSONDecodeError:
                    continue

            # 尝试查找方括号或花括号包裹的内容
            bracket_pattern = r'(\[[\s\S]*\]|\{[\s\S]*\})'
            matches = re.findall(bracket_pattern, response)

            for match in matches:
                try:
                    data = json.loads(match.strip())
                    if "groups" in data:
                        return data["groups"]
                    if isinstance(data, list):
                        return data
                except json.JSONDecodeError:
                    continue

            print(f"无法解析分组响应，原始响应:\n{response}")
            return []

    def _save_groups_to_csv(self, csv_path: str, groups: list[dict]):
        """保存分组结果到CSV文件。"""
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['group_name', 'file_path'])

            for group in groups:
                group_name = group.get('name', '未命名组')
                files = group.get('files', [])

                for file_path in files:
                    writer.writerow([group_name, file_path])

    def process_directory(
        self,
        directory: str,
        output_json_path: Optional[str] = None,
        output_csv_path: Optional[str] = None,
        skip_analysis: bool = False,
        existing_json_path: Optional[str] = None
    ) -> tuple[dict, list]:
        """
        处理目录中的图片：分析描述并分组。

        Args:
            directory: 图片目录路径
            output_json_path: 描述结果JSON文件路径
            output_csv_path: 分组结果CSV文件路径
            skip_analysis: 是否跳过分析，直接加载已有的JSON文件
            existing_json_path: 已有的描述JSON文件路径（当skip_analysis=True时使用）

        Returns:
            (descriptions, groups) 元组
        """
        # 获取图片描述
        if skip_analysis and existing_json_path:
            print(f"加载已有描述文件: {existing_json_path}")
            with open(existing_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                descriptions = data.get('descriptions', {})
        else:
            descriptions = self.analyze_images(directory, output_json_path)

        # 分组图片
        groups = self.group_images(descriptions, output_csv_path, directory)

        print(f"\n处理完成！")
        print(f"  - 图片数量: {len(descriptions)}")
        print(f"  - 分组数量: {len(groups)}")

        return descriptions, groups


def main():
    """命令行入口函数。"""
    import argparse

    parser = argparse.ArgumentParser(description='图片分组工具 - 分析图片并根据描述进行分组')
    parser.add_argument('--directory', help='图片目录路径')
    parser.add_argument('--desc-prompt', help='自定义图片描述提示词')
    parser.add_argument('--group-prompt', help='自定义分组提示词')
    parser.add_argument('--json-output', help='描述结果JSON文件路径')
    parser.add_argument('--csv-output', help='分组结果CSV文件路径')
    parser.add_argument('--skip-analysis', action='store_true', help='跳过分析，使用已有的JSON文件')
    parser.add_argument('--existing-json', help='已有的描述JSON文件路径')

    args = parser.parse_args()

    # 对于未提供的参数，提示用户输入
    # directory 是必须参数
    if args.directory is None:
        user_input = input('请输入图片目录路径 (必填): ').strip()
        if user_input:
            args.directory = user_input

    # 去除路径两端的引号（如果有）
    if args.directory:
        args.directory = re.sub("(^')|('$)|(^\")|(\"$)", '', args.directory)
    
    # 验证 directory 参数
    if not args.directory:
        print("错误: 图片目录路径是必填参数，未提供有效路径。")
        exit(1)
    
    if not os.path.exists(args.directory):
        print(f"错误: 指定的目录不存在: {args.directory}")
        exit(1)
    
    if not os.path.isdir(args.directory):
        print(f"错误: 指定的路径不是目录: {args.directory}")
        exit(1)

    if args.desc_prompt is None:
        user_input = input('请输入自定义图片描述提示词 (直接回车使用默认值): ').strip()
        if user_input:
            args.desc_prompt = user_input

    if args.group_prompt is None:
        user_input = input('请输入自定义分组提示词 (直接回车使用默认值): ').strip()
        if user_input:
            args.group_prompt = user_input

    if args.json_output is None:
        user_input = input('请输入描述结果JSON文件路径 (直接回车使用默认值): ').strip()
        if user_input:
            args.json_output = user_input

    if args.csv_output is None:
        user_input = input('请输入分组结果CSV文件路径 (直接回车使用默认值): ').strip()
        if user_input:
            args.csv_output = user_input

    if not args.skip_analysis:
        user_input = input('是否跳过分析，使用已有的JSON文件? (y/n, 直接回车默认为n): ').strip().lower()
        if user_input == 'y':
            args.skip_analysis = True

    if args.existing_json is None:
        user_input = input('请输入已有的描述JSON文件路径 (直接回车使用默认值): ').strip()
        if user_input:
            args.existing_json = user_input

    # 创建图片分组器
    grouper = ImageGrouper(
        image_desc_prompt=args.desc_prompt,
        grouping_prompt=args.group_prompt
    )

    # 处理目录
    descriptions, groups = grouper.process_directory(
        directory=args.directory,
        output_json_path=args.json_output,
        output_csv_path=args.csv_output,
        skip_analysis=args.skip_analysis,
        existing_json_path=args.existing_json
    )

    # 显示分组结果
    if groups:
        print("\n" + "=" * 50)
        print("分组结果:")
        print("=" * 50)
        for i, group in enumerate(groups, 1):
            group_name = group.get('name', f'组{i}')
            files = group.get('files', [])
            print(f"\n【{group_name}】({len(files)} 张图片)")
            for file_path in files:
                print(f"  - {file_path}")


if __name__ == "__main__":
    main()
