"""
LK888 GPT Image 2 API 封装
基于 LK888 AI大模型聚合平台 GPT Image 2 模型

API 文档:
- 创建任务: POST https://api.lk888.ai/v1/media/generate
- 查询任务: GET https://api.lk888.ai/v1/media/status?task_id={task_id}

调用流程: POST 创建 → 拿响应里的 task_id → 定时 GET 查询 → is_final=true 后从 result_url 拿结果

注意: 图片参考需要传入 http/https URL，本地文件会自动上传
"""

import json
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

import requests

import os
try:
    from .image_uploader import upload_local_image_to_tc
except ImportError:
    from image_uploader import upload_local_image_to_tc

# Configuration loaded from environment variables
LK888_API_KEY = os.environ.get("LK888_API_KEY", "")


@dataclass
class Lk888ImageResult:
    """LK888图片生成结果"""
    task_id: str
    state: str
    is_final: bool
    result_url: str
    error: str
    status: str = ""
    progress: str = ""
    cost: float = 0.0

    @property
    def is_completed(self) -> bool:
        """是否处理完成（is_final 为 True 且 state 为 success）"""
        return self.is_final and self.state == "success"

    @property
    def is_failed(self) -> bool:
        """是否处理失败（is_final 为 True 且 state 为 failed）"""
        return self.is_final and self.state == "failed"

    @property
    def is_processing(self) -> bool:
        """是否处理中（未终态且 state 为 pending 或 running）"""
        return not self.is_final and self.state in ("pending", "running")

    @property
    def is_waiting(self) -> bool:
        """是否等待中（state 为 pending）"""
        return self.state == "pending"


class Lk888ImageClient:
    """LK888 GPT Image 2 客户端"""

    # 支持的图片尺寸枚举
    VALID_SIZES = {
        "auto", "1024x1024", "1024x1536", "1536x1024", "960x1280", "1280x960",
        "1088x1920", "1920x1088", "2048x2048", "2048x3072", "3072x2048",
        "1920x2560", "2560x1920", "1440x2560", "2560x1440", "2880x2880",
        "2304x3456", "3456x2304", "2400x3200", "3200x2400", "2160x3840", "3840x2160",
    }

    # 支持的图片质量枚举
    VALID_QUALITIES = {"auto", "high", "medium", "low"}

    def __init__(self, api_key: str = LK888_API_KEY, base_url: str = "https://api.lk888.ai"):
        """
        初始化客户端

        Args:
            api_key: LK888 API Key
            base_url: API 基础 URL，默认 https://api.lk888.ai
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._uploaded_urls: dict = {}  # 缓存已上传的URL，避免重复上传

    def _is_url(self, path: str) -> bool:
        """
        检查字符串是否为 URL 格式（http/https）

        Args:
            path: 待检查的字符串

        Returns:
            如果是 URL 则返回 True
        """
        return path.startswith("http://") or path.startswith("https://")

    def _build_headers(self) -> dict:
        """构建请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def submit_job(
        self,
        prompt: str,
        size: str = "auto",
        images: Optional[List[str]] = None,
        quality: str = "auto",
        model: str = "gpt-image-2",
        n: int = 1,
        notify_url: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        提交图片生成任务

        Args:
            prompt: 文本描述，描述画面中的物体、风格及文字排版
            size: 生成图片尺寸，默认 auto（由模型自动决定）。
                  支持枚举值或自定义尺寸（宽高均为16的倍数、宽高比1:3~3:1、总像素655360~8294400）
            images: 参考图片 URL 列表，最多 14 张。支持以下格式：
                   - HTTP/HTTPS URL
                   - 本地文件路径（会自动上传到免费图床获取URL）
            quality: 图片质量，默认 auto。可选: auto / high / medium / low
            model: 模型名称，默认 gpt-image-2
            n: 生成图片数量，默认 1
            notify_url: 任务回调地址（webhook），可选。
                       任务完成后平台会 POST 推送结果到此地址
            **kwargs: 其他参数，会合并到 params 中

        Returns:
            任务 ID (task_id)

        Raises:
            Exception: 提交失败时抛出异常
        """
        url = f"{self.base_url}/v1/media/generate"

        # 构建 params
        params = {
            "size": size,
            "quality": quality,
            "n": n,
            "response_format": "url",
        }

        if images:
            # 处理图片：URL直接使用，本地文件上传后使用
            processed_images = []
            for img in images:
                if self._is_url(img):
                    processed_images.append(img)
                else:
                    # 本地文件路径，上传到图床
                    print(f"上传本地图片: {img}")
                    url_uploaded = upload_local_image_to_tc(img)
                    print(f"上传成功，URL: {url_uploaded}")
                    processed_images.append(url_uploaded)
            params["images"] = processed_images

        # 合并额外参数
        params.update(kwargs)

        body = {
            "model": model,
            "prompt": prompt,
            "params": params,
        }

        if notify_url:
            body["notify_url"] = notify_url

        try:
            resp = requests.post(url, headers=self._build_headers(), json=body, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"提交任务失败: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"解析响应失败: {e}，原始响应: {resp.text}")

        # 提取 task_id
        if 'data' not in data:
            raise Exception(f"提交任务响应中未找到 data 字段，响应: {data}")
        data = data['data']
        task_id = data.get("task_id")
        if not task_id:
            # 某些情况下可能直接返回结果（同步响应），尝试从 data 中获取
            if "data" in data and len(data["data"]) > 0:
                result_url = data["data"][0].get("url")
                if result_url:
                    # 同步返回了结果，直接存入
                    print(f"同步返回结果: {result_url}")
                    # 返回一个假的 task_id 用于标识已完成
                    return f"__sync__{int(time.time())}"
            raise Exception(f"提交任务响应中未找到 task_id，响应: {data}")

        return str(task_id)

    def query_job(self, task_id: str) -> Lk888ImageResult:
        """
        查询图片生成任务状态

        Args:
            task_id: 任务 ID

        Returns:
            Lk888ImageResult 对象

        Raises:
            Exception: 查询失败时抛出异常
        """
        url = f"{self.base_url}/v1/media/status"
        params = {"task_id": task_id}

        try:
            resp = requests.get(url, headers=self._build_headers(), params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"查询任务失败: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"解析响应失败: {e}，原始响应: {resp.text}")

        return Lk888ImageResult(
            task_id=str(data.get("task_id", task_id)),
            state=data.get("state", ""),
            is_final=data.get("is_final", False),
            result_url=data.get("result_url", ""),
            error=data.get("error", ""),
            status=data.get("status", ""),
            progress=data.get("progress", ""),
            cost=float(data.get("cost", 0)),
        )

    def generate_image_intern(
        self,
        prompt: str,
        size: str = "auto",
        images: Optional[List[str]] = None,
        quality: str = "auto",
        model: str = "gpt-image-2",
        n: int = 1,
        notify_url: Optional[str] = None,
        poll_interval: int = 5,
        max_retries: int = 60,
        **kwargs
    ) -> Lk888ImageResult:
        """
        生成图片（提交任务并轮询等待结果）

        Args:
            prompt: 文本描述
            size: 生成图片尺寸，默认 auto
            images: 参考图片 URL 列表
            quality: 图片质量，默认 auto
            model: 模型名称，默认 gpt-image-2
            n: 生成图片数量，默认 1
            notify_url: 任务回调地址（webhook），可选
            poll_interval: 轮询间隔（秒），默认 5 秒
            max_retries: 最大轮询次数，默认 60 次

        Returns:
            Lk888ImageResult 对象

        Raises:
            Exception: 生成失败或超时时抛出异常
        """
        # 提交任务
        task_id = self.submit_job(
            prompt=prompt,
            size=size,
            images=images,
            quality=quality,
            model=model,
            n=n,
            notify_url=notify_url,
            **kwargs
        )

        # 处理同步返回的情况
        if task_id.startswith("__sync__"):
            return Lk888ImageResult(
                task_id=task_id,
                state="success",
                is_final=True,
                result_url="",
                error="",
                status="已完成（同步返回）",
                progress="100%",
            )

        print(f"任务已提交，TaskId: {task_id}")

        # 轮询等待结果
        for i in range(max_retries):
            result = self.query_job(task_id)

            if result.is_completed:
                print(f"任务处理完成，结果URL: {result.result_url}")
                return result
            elif result.is_failed:
                raise Exception(f"任务处理失败: {result.error}")
            else:
                print(f"任务处理中，状态: {result.status} ({result.progress})")

            print(f"[{i+1}/{max_retries}] 任务状态: {result.status} ({result.progress})，等待 {poll_interval} 秒...")
            time.sleep(poll_interval)

        raise Exception(f"等待任务完成超时，TaskId: {task_id}")

    @staticmethod
    def generate_image(
        prompt: str,
        api_key: str = LK888_API_KEY,
        base_url: str = "https://api.lk888.ai",
        size: str = "auto",
        images: Optional[List[str]] = None,
        quality: str = "auto",
        model: str = "gpt-image-2",
        n: int = 1,
        notify_url: Optional[str] = None,
        poll_interval: int = 5,
        max_retries: int = 60,
        **kwargs
    ) -> Lk888ImageResult:
        """
        便捷的图片生成函数（提交任务并轮询等待结果）

        Args:
            prompt: 文本描述
            api_key: LK888 API Key
            base_url: API 基础 URL，默认 https://api.lk888.ai
            size: 生成图片尺寸，默认 auto
            images: 参考图片 URL 列表
            quality: 图片质量，默认 auto
            model: 模型名称，默认 gpt-image-2
            n: 生成图片数量，默认 1
            notify_url: 任务回调地址（webhook），可选
            poll_interval: 轮询间隔（秒），默认 5 秒
            max_retries: 最大轮询次数，默认 60 次

        Returns:
            Lk888ImageResult 对象

        Example:
            >>> result = Lk888ImageClient.generate_image(
            ...     api_key="your-api-key",
            ...     prompt="一只可爱的小猫在草地上玩耍",
            ...     size="1024x1024"
            ... )
            >>> print(result.result_url)
        """
        client = Lk888ImageClient(api_key=api_key, base_url=base_url)
        return client.generate_image_intern(
            prompt=prompt,
            size=size,
            images=images,
            quality=quality,
            model=model,
            n=n,
            notify_url=notify_url,
            poll_interval=poll_interval,
            max_retries=max_retries,
            **kwargs
        )


if __name__ == "__main__":
    # ========== 测试代码 ==========
    # 注意：运行测试前需要设置环境变量 LK888_API_KEY

    # 测试配置
    TEST_PROMPT = "一只可爱的金毛犬在豆袋上睡觉，背景是温馨的儿童房，光线柔和，风格卡通"
    TEST_SIZE = "1024x1024"

    print("=" * 50)
    print("LK888 GPT Image 2 API 测试")
    print("=" * 50)
    print(f"提示词: {TEST_PROMPT}")
    print(f"尺寸: {TEST_SIZE}")
    print()

    if not LK888_API_KEY:
        print("警告: 未设置 LK888_API_KEY 环境变量，测试将跳过")
        print("请先设置: export LK888_API_KEY=your-api-key")
        exit(0)

    try:
        # 方法 1: 使用便捷函数
        print("方法 1: 使用便捷函数 generate_image()")
        result = Lk888ImageClient.generate_image(
            prompt=TEST_PROMPT,
            size=TEST_SIZE,
            quality="auto",
            poll_interval=5,
            max_retries=60,
        )
        print("\n生成成功!")
        print(f"任务 ID: {result.task_id}")
        print(f"状态: {result.status}")
        print(f"结果 URL: {result.result_url}")
        print(f"费用: {result.cost}")

    except Exception as e:
        print(f"\n生成失败: {e}")

    print("\n" + "=" * 50)
    print("测试结束")
    print("=" * 50)

    # 方法 2: 使用客户端类（更灵活的控制）
    print("\n方法 2: 使用 Lk888ImageClient 客户端类")
    print("-" * 50)

    try:
        client = Lk888ImageClient()

        prompt = """Subject: A candid over-the-shoulder shot from behind a young woman with wavy brown hair. 
Action: Wearing a cozy, light-grey ribbed knit sweater and a white skirt, she is carrying the bag under her arm. 
Product: A pastel pink suede baguette-style shoulder bag with a horizontal belt strap containing silver metal grommets and a silver buckle. 
A matching pink suede star-shaped charm on a fine silver chain hangs gracefully from the strap (as referenced in image 1). 
Style: [Ultra-realistic, professional e-commerce product photography. 
Soft, diffused, natural winter light coming from a side window, casting gentle shadows. 
Clean, minimalist composition. High-definition details capturing the tactile texture of the fabric and the polished metallic sheen of the silver buckle and eyelets. 
Film-like, slightly muted color grading with high contrast. No text or graphic watermarks.]"""
        images = [
            r"D:\ps-workspace\temu\箱包\参考图\秋冬女包-1066408860395-高碑店市新城菲兔箱包厂-14.8\1066408860395-detail-9.png"
        ]

        # 步骤 1: 提交任务
        print("步骤 1: 提交任务...")
        task_id = client.submit_job(
            prompt=prompt,
            size="1024x1024",
            images=images
        )
        print(f"任务已提交，TaskId: {task_id}")

        # 步骤 2: 轮询查询任务状态
        print("\n步骤 2: 轮询查询任务状态...")
        max_retries = 60
        for i in range(max_retries):
            result = client.query_job(task_id)
            print(f"  [{i+1}/{max_retries}] 状态: {result.status} ({result.progress})")

            if result.is_completed:
                print("\n任务处理完成!")
                print(f"结果 URL: {result.result_url}")
                break
            elif result.is_failed:
                print(f"\n任务处理失败: {result.error}")
                break

            time.sleep(5)

    except Exception as e:
        print(f"测试失败: {e}")
