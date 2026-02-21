"""
混元大模型文生图 API 封装
基于腾讯云 AI Art API (混元生图 3.0)

API 文档:
- 提交任务: SubmitTextToImageJob
- 查询任务: QueryTextToImageJob

注意: Images参数不支持data URL，需要传入http/https URL
"""

import json
import time
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.aiart.v20221229 import aiart_client, models

import os

# Configuration loaded from environment variables
SECRET_ID = os.environ.get("TENCENT_CLOUD_SECRET_ID", "")
SECRET_KEY = os.environ.get("TENCENT_CLOUD_SECRET_KEY", "")


@dataclass
class ImageGenerationResult:
    """文生图结果"""
    job_id: str
    status_code: str
    status_msg: str
    image_urls: List[str]
    error_code: Optional[str] = None
    error_msg: Optional[str] = None
    result_details: Optional[List[str]] = None
    revised_prompt: Optional[List[str]] = None
    request_id: Optional[str] = None

    @property
    def is_completed(self) -> bool:
        """是否处理完成"""
        return self.status_code == "5"

    @property
    def is_failed(self) -> bool:
        """是否处理失败"""
        return self.status_code == "4"

    @property
    def is_processing(self) -> bool:
        """是否处理中"""
        return self.status_code == "2"

    @property
    def is_waiting(self) -> bool:
        """是否等待中"""
        return self.status_code == "1"


class HunyuanImageClient:
    """混元生图客户端"""

    def __init__(self, secret_id: str = SECRET_ID, secret_key: str = SECRET_KEY, region: str = "ap-guangzhou"):
        """
        初始化客户端

        Args:
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
            region: 地域，默认 ap-guangzhou
        """
        cred = credential.Credential(secret_id, secret_key)
        
        httpProfile = HttpProfile()
        httpProfile.endpoint = "aiart.tencentcloudapi.com"
        
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        
        self.client = aiart_client.AiartClient(cred, region, clientProfile)
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

    def _upload_local_image(self, file_path: str) -> str:
        """
        上传本地图片并返回URL

        Args:
            file_path: 本地文件路径

        Returns:
            图片URL

        Raises:
            Exception: 上传失败时抛出异常
        """
        # 检查缓存
        abs_path = str(Path(file_path).resolve())
        if abs_path in self._uploaded_urls:
            return self._uploaded_urls[abs_path]
        
        # 导入上传模块
        import sys
        sys.path.append(str(Path(__file__).parent))
        from image_uploader import upload_image
        
        # 使用 SM.MS 上传（免费，无需配置）
        result = upload_image(file_path, method="cos", cos_config={
            "secret_id": SECRET_ID,
            "secret_key": SECRET_KEY,
            "region": "ap-guangzhou",
            "bucket": "image-cache-1252557679"
          })  # 替换为你的COS桶)
        
        if not result.success or not result.url:
            raise Exception(f"图片上传失败: {result.error or '未获取到URL'}")
        
        # 缓存结果
        self._uploaded_urls[abs_path] = result.url
        return result.url

    def submit_job(
        self,
        prompt: str,
        resolution: str = "1024:1024",
        images: Optional[List[str]] = None,
        seed: Optional[int] = None,
        logo_add: int = 1,
        revise: int = 1
    ) -> str:
        """
        提交文生图任务

        Args:
            prompt: 文本描述，不能为空，推荐使用中文，最多 8192 个字符
            resolution: 生成图分辨率，默认 1024:1024
                       宽高维度均在 [512, 2048] 像素范围内
                       宽高乘积不超过 1024×1024 像素
            images: 垫图 URL 列表，最多 3 张图，支持以下格式：
                   - HTTP/HTTPS URL
                   - 本地文件路径（会自动上传到免费图床获取URL）
            seed: 随机种子，默认随机。不传则随机生成，正数则固定种子
            logo_add: 是否添加水印，1=添加(默认)，0=不添加
            revise: 是否开启 prompt 改写，1=开启(默认)，0=关闭

        Returns:
            任务 ID (JobId)

        Raises:
            Exception: 提交失败时抛出异常
        """
        body = {
            "Prompt": prompt,
            "Resolution": resolution,
            "LogoAdd": logo_add,
            "Revise": revise,
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
                    url = self._upload_local_image(img)
                    print(f"上传成功，URL: {url}")
                    processed_images.append(url)
            body["Images"] = processed_images
        if seed is not None:
            body["Seed"] = seed

        req = models.SubmitTextToImageJobRequest()
        req.from_json_string(json.dumps(body))
        
        try:
            resp = self.client.SubmitTextToImageJob(req)
            return resp.JobId or ""
        except TencentCloudSDKException as e:
            raise Exception(f"提交任务失败: {e.code} - {e.message}")

    def query_job(self, job_id: str) -> ImageGenerationResult:
        """
        查询文生图任务状态

        Args:
            job_id: 任务 ID

        Returns:
            ImageGenerationResult 对象

        Raises:
            Exception: 查询失败时抛出异常
        """
        body = {
            "JobId": job_id
        }

        req = models.QueryTextToImageJobRequest()
        req.from_json_string(json.dumps(body))
        
        try:
            resp = self.client.QueryTextToImageJob(req)
            return ImageGenerationResult(
                job_id=job_id,
                status_code=resp.JobStatusCode or "",
                status_msg=resp.JobStatusMsg or "",
                image_urls=resp.ResultImage or [],
                error_code=resp.JobErrorCode or None,
                error_msg=resp.JobErrorMsg or None,
                result_details=resp.ResultDetails,
                revised_prompt=resp.RevisedPrompt,
                request_id=resp.RequestId
            )
        except TencentCloudSDKException as e:
            raise Exception(f"查询任务失败: {e.code} - {e.message}")

    def generate_image_intern(
        self,
        prompt: str,
        resolution: str = "1024:1024",
        images: Optional[List[str]] = None,
        seed: Optional[int] = None,
        logo_add: int = 1,
        revise: int = 1,
        poll_interval: int = 2,
        max_retries: int = 60
    ) -> ImageGenerationResult:
        """
        生成图片（提交任务并轮询等待结果）

        Args:
            prompt: 文本描述
            resolution: 生成图分辨率
            images: 垫图 URL 列表
            seed: 随机种子
            logo_add: 是否添加水印
            revise: 是否开启 prompt 改写
            poll_interval: 轮询间隔（秒）
            max_retries: 最大轮询次数

        Returns:
            ImageGenerationResult 对象

        Raises:
            Exception: 生成失败或超时时抛出异常
        """
        # 提交任务
        job_id = self.submit_job(
            prompt=prompt,
            resolution=resolution,
            images=images,
            seed=seed,
            logo_add=logo_add,
            revise=revise
        )

        print(f"任务已提交，JobId: {job_id}")

        # 轮询等待结果
        for i in range(max_retries):
            result = self.query_job(job_id)

            if result.is_completed:
                print(f"任务处理完成")
                return result
            elif result.is_failed:
                raise Exception(f"任务处理失败: {result.error_code} - {result.error_msg}")

            print(f"[{i+1}/{max_retries}] 任务状态: {result.status_msg}，等待 {poll_interval} 秒...")
            time.sleep(poll_interval)

        raise Exception(f"等待任务完成超时，JobId: {job_id}")
    @staticmethod
    def generate_image(
        prompt: str,
        region: str = "ap-guangzhou",
        resolution: str = "1024:1024",
        images: Optional[List[str]] = None,
        seed: Optional[int] = None,
        logo_add: int = 0,
        revise: int = 1,
        poll_interval: int = 2,
        max_retries: int = 60
    ) -> ImageGenerationResult:
        """
        便捷的文生图函数（提交任务并轮询等待结果）

        Args:
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
            prompt: 文本描述
            region: 地域，默认 ap-guangzhou
            resolution: 生成图分辨率，默认 1024:1024
            images: 垫图 URL 列表
            seed: 随机种子
            logo_add: 是否添加水印，1=添加(默认)，0=不添加
            revise: 是否开启 prompt 改写，1=开启(默认)，0=关闭
            poll_interval: 轮询间隔（秒）
            max_retries: 最大轮询次数

        Returns:
            ImageGenerationResult 对象

        Example:
            >>> result = generate_image(
            ...     secret_id="your-secret-id",
            ...     secret_key="your-secret-key",
            ...     prompt="一只可爱的小猫在草地上玩耍",
            ...     resolution="1024:1024"
            ... )
            >>> print(result.image_urls)
        """
        client = HunyuanImageClient(region=region)
        return client.generate_image_intern(
            prompt=prompt,
            resolution=resolution,
            images=images,
            seed=seed,
            logo_add=logo_add,
            revise=revise,
            poll_interval=poll_interval,
            max_retries=max_retries
        )


if __name__ == "__main__":
    # ========== 测试代码 ==========
    # 注意：运行测试前需要填写你的腾讯云密钥

    # 测试配置
    TEST_PROMPT = "一只可爱的金毛犬在如图所示的豆袋上睡觉，背景是温馨的儿童房，光线柔和，风格卡通，分辨率1024x1024"
    TEST_RESOLUTION = "1024:1024"

    print("=" * 50)
    print("混元生图 API 测试")
    print("=" * 50)
    print(f"提示词: {TEST_PROMPT}")
    print(f"分辨率: {TEST_RESOLUTION}")
    print()

    try:
        # 方法 1: 使用便捷函数
        print("方法 1: 使用便捷函数 generate_image()")
        result = HunyuanImageClient.generate_image(
            prompt=TEST_PROMPT,
            resolution=TEST_RESOLUTION,
            revise=1,  # 开启改写
            logo_add=0,  # 添加水印
            poll_interval=2,
            max_retries=60,
            images=[r"D:\ps-workspace\temu\其它包\豆袋定制\爱心\simulate-1-253232249.jpg"]
        )
        print("\n生成成功!")
        print(f"任务 ID: {result.job_id}")
        print(f"RequestId: {result.request_id}")
        print(f"状态: {result.status_msg}")
        print(f"图片 URL 列表:")
        for i, url in enumerate(result.image_urls, 1):
            print(f"  [{i}] {url}")

        if result.revised_prompt:
            print(f"\n改写后的提示词:")
            for i, rp in enumerate(result.revised_prompt, 1):
                print(f"  [{i}] {rp}")

    except Exception as e:
        print(f"\n生成失败: {e}")

    print("\n" + "=" * 50)
    print("测试结束")
    print("=" * 50)

    # 方法 2: 使用客户端类（更灵活的控制）
    print("\n方法 2: 使用 HunyuanImageClient 客户端类")
    print("-" * 50)

    try:
        client = HunyuanImageClient()

        # 步骤 1: 提交任务
        print("步骤 1: 提交任务...")
        job_id = client.submit_job(
            prompt="一只橘猫趴在窗台上晒太阳",
            resolution="1024:1024",
            revise=0  # 关闭改写
        )
        print(f"任务已提交，JobId: {job_id}")

        # 步骤 2: 轮询查询任务状态
        print("\n步骤 2: 轮询查询任务状态...")
        max_retries = 60
        for i in range(max_retries):
            result = client.query_job(job_id)
            print(f"  [{i+1}/{max_retries}] 状态: {result.status_msg}")

            if result.is_completed:
                print("\n任务处理完成!")
                print(f"图片 URL: {result.image_urls}")
                break
            elif result.is_failed:
                print(f"\n任务处理失败: {result.error_msg}")
                break

            time.sleep(2)

    except Exception as e:
        print(f"测试失败: {e}")
