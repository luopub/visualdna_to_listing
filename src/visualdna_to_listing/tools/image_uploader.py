"""
图片上传工具
支持多种免费图床服务，将本地图片上传并获取公开URL

支持的服务:
1. SM.MS - 免费图床，无需配置，5GB免费空间
2. ImgBB - 免费图床，需要API Key
3. 腾讯云COS - 需要配置，有免费额度
"""

import os
import base64
import requests
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class UploadResult:
    """上传结果"""
    success: bool
    url: Optional[str] = None
    delete_url: Optional[str] = None
    error: Optional[str] = None


class SmMsUploader:
    """
    SM.MS 免费图床上传器
    
    特点:
    - 免费5GB存储空间
    - 单张图片最大5MB
    - 支持格式: jpg, jpeg, png, gif, bmp, webp
    - 无需注册，无需API Key
    - 图片保留时间: 永久
    
    API文档: https://sm.ms/doc/
    """
    
    API_URL = "https://sm.ms/api/v2/upload"
    
    @classmethod
    def upload(cls, file_path: str, timeout: int = 30) -> UploadResult:
        """
        上传图片到 SM.MS
        
        Args:
            file_path: 本地图片路径
            timeout: 超时时间（秒）
            
        Returns:
            UploadResult 对象
        """
        path = Path(file_path)
        if not path.exists():
            return UploadResult(success=False, error=f"文件不存在: {file_path}")
        
        # 检查文件大小 (5MB限制)
        file_size = path.stat().st_size
        if file_size > 5 * 1024 * 1024:
            return UploadResult(success=False, error=f"文件大小超过5MB限制: {file_size / 1024 / 1024:.2f}MB")
        
        try:
            with open(file_path, "rb") as f:
                files = {"smfile": (path.name, f)}
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                response = requests.post(
                    cls.API_URL,
                    files=files,
                    headers=headers,
                    timeout=timeout
                )
            
            data = response.json()
            
            if data.get("success"):
                return UploadResult(
                    success=True,
                    url=data["data"]["url"],
                    delete_url=data["data"].get("delete")
                )
            elif data.get("code") == "image_repeated":
                # 图片已存在，返回已有URL
                return UploadResult(
                    success=True,
                    url=data["images"],
                    error="图片已存在，返回已有URL"
                )
            else:
                return UploadResult(
                    success=False,
                    error=data.get("message", "上传失败，未知错误")
                )
                
        except requests.exceptions.Timeout:
            return UploadResult(success=False, error="上传超时")
        except requests.exceptions.RequestException as e:
            return UploadResult(success=False, error=f"网络请求失败: {e}")
        except Exception as e:
            return UploadResult(success=False, error=f"上传失败: {e}")


class ImgBBUploader:
    """
    ImgBB 免费图床上传器
    
    特点:
    - 免费无限存储空间
    - 单张图片最大32MB
    - 支持格式: jpg, jpeg, png, gif, bmp, webp, tiff
    - 需要免费注册获取API Key: https://imgbb.com/
    
    API文档: https://api.imgbb.com/
    """
    
    API_URL = "https://api.imgbb.com/1/upload"
    
    def __init__(self, api_key: str):
        """
        初始化上传器
        
        Args:
            api_key: ImgBB API Key，从 https://imgbb.com/ 获取
        """
        self.api_key = api_key
    
    def upload(self, file_path: str, expiration: int = 0, timeout: int = 30) -> UploadResult:
        """
        上传图片到 ImgBB
        
        Args:
            file_path: 本地图片路径
            expiration: 过期时间（秒），0表示永不过期
            timeout: 超时时间（秒）
            
        Returns:
            UploadResult 对象
        """
        path = Path(file_path)
        if not path.exists():
            return UploadResult(success=False, error=f"文件不存在: {file_path}")
        
        try:
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            payload = {
                "key": self.api_key,
                "image": image_data,
            }
            if expiration > 0:
                payload["expiration"] = expiration
            
            response = requests.post(
                self.API_URL,
                data=payload,
                timeout=timeout
            )
            
            data = response.json()
            
            if data.get("success"):
                return UploadResult(
                    success=True,
                    url=data["data"]["url"],
                    delete_url=data["data"].get("delete_url")
                )
            else:
                return UploadResult(
                    success=False,
                    error=data.get("error", {}).get("message", "上传失败")
                )
                
        except requests.exceptions.Timeout:
            return UploadResult(success=False, error="上传超时")
        except requests.exceptions.RequestException as e:
            return UploadResult(success=False, error=f"网络请求失败: {e}")
        except Exception as e:
            return UploadResult(success=False, error=f"上传失败: {e}")


class TencentCOSUploader:
    """
    腾讯云COS上传器
    
    特点:
    - 6个月免费额度（50GB存储 + 10GB流量）
    - 与腾讯云混元生图同生态，访问稳定
    - 需要配置存储桶
    
    使用前需要安装: pip install cos-python-sdk-v5
    """
    
    def __init__(
        self,
        secret_id: str,
        secret_key: str,
        region: str,
        bucket: str,
    ):
        """
        初始化COS上传器
        
        Args:
            secret_id: 腾讯云 SecretId
            secret_key: 腾讯云 SecretKey
            region: 地域，如 ap-guangzhou
            bucket: 存储桶名称，格式: bucketname-appid
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.region = region
        self.bucket = bucket
    
    def upload(
        self,
        file_path: str,
        key: Optional[str] = None,
        timeout: int = 30
    ) -> UploadResult:
        """
        上传图片到腾讯云COS
        
        Args:
            file_path: 本地图片路径
            key: COS对象键，不传则自动生成
            timeout: 超时时间（秒）
            
        Returns:
            UploadResult 对象
        """
        try:
            from qcloud_cos import CosConfig
            from qcloud_cos import CosS3Client
            import uuid
            from datetime import datetime
        except ImportError:
            return UploadResult(
                success=False,
                error="未安装COS SDK，请运行: pip install cos-python-sdk-v5"
            )
        
        path = Path(file_path)
        if not path.exists():
            return UploadResult(success=False, error=f"文件不存在: {file_path}")
        
        try:
            config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
            )
            client = CosS3Client(config)
            
            # 生成唯一文件名
            if key is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                unique_id = uuid.uuid4().hex[:8]
                key = f"hunyuan_images/{timestamp}_{unique_id}{path.suffix}"
            
            with open(file_path, "rb") as f:
                client.put_object(
                    Bucket=self.bucket,
                    Body=f,
                    Key=key,
                )
            
            # 构建访问URL
            url = f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"
            
            return UploadResult(success=True, url=url)
            
        except Exception as e:
            return UploadResult(success=False, error=f"上传失败: {e}")


def upload_image(
    file_path: str,
    method: str = "smms",
    api_key: Optional[str] = None,
    cos_config: Optional[dict] = None,
) -> UploadResult:
    """
    便捷的图片上传函数
    
    Args:
        file_path: 本地图片路径
        method: 上传方式，可选: "smms", "imgbb", "cos"
        api_key: ImgBB的API Key（method="imgbb"时需要）
        cos_config: COS配置字典（method="cos"时需要）
            {
                "secret_id": "xxx",
                "secret_key": "xxx",
                "region": "ap-guangzhou",
                "bucket": "bucketname-appid"
            }
    
    Returns:
        UploadResult 对象
    
    Example:
        # 使用 SM.MS（推荐，无需配置）
        result = upload_image("test.jpg", method="smms")
        
        # 使用 ImgBB
        result = upload_image("test.jpg", method="imgbb", api_key="your-api-key")
        
        # 使用 腾讯云COS
        result = upload_image("test.jpg", method="cos", cos_config={
            "secret_id": "xxx",
            "secret_key": "xxx",
            "region": "ap-guangzhou",
            "bucket": "mybucket-123456"
        })
    """
    if method == "smms":
        return SmMsUploader.upload(file_path)
    elif method == "imgbb":
        if not api_key:
            return UploadResult(success=False, error="ImgBB需要提供api_key参数")
        return ImgBBUploader(api_key).upload(file_path)
    elif method == "cos":
        if not cos_config:
            return UploadResult(success=False, error="COS需要提供cos_config参数")
        return TencentCOSUploader(
            secret_id=cos_config["secret_id"],
            secret_key=cos_config["secret_key"],
            region=cos_config["region"],
            bucket=cos_config["bucket"],
        ).upload(file_path)
    else:
        return UploadResult(success=False, error=f"不支持的上传方式: {method}")


if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python image_uploader.py <图片路径>")
        print("\n推荐使用 SM.MS，无需任何配置")
        sys.exit(1)
    
    file_path = sys.argv[1]
    print(f"上传图片: {file_path}")
    print("使用 SM.MS 图床...")
    
    result = upload_image(file_path, method="smms")
    
    if result.success:
        print(f"\n上传成功!")
        print(f"图片URL: {result.url}")
        if result.delete_url:
            print(f"删除URL: {result.delete_url}")
    else:
        print(f"\n上传失败: {result.error}")
