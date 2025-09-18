import json
import base64
import hmac
import hashlib
from datetime import datetime, timedelta
from django.conf import settings


class OSSTokenGenerator:
    """阿里云 OSS 上传Token生成器"""
    
    def __init__(self):
        self.access_key_id = settings.ALIYUN_ACCESS_KEY
        self.access_key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        self.bucket_name = settings.OSS_BUCKET_NAME
        self.endpoint = settings.OSS_ENDPOINT
    
    def generate_upload_token(self, username, duration_seconds=3600):
        """
        生成客户端直传OSS的临时访问令牌
        
        Args:
            username: 用户ID
            duration_seconds: 令牌有效期（秒），默认1小时
            
        Returns:
            dict: 包含上传信息的字典
        """
        try:
            # 计算过期时间
            expiration = datetime.now() + timedelta(seconds=duration_seconds)
            expiration_iso = expiration.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            # 文件路径前缀
            prefix = f"{username}/"
            
            # 构造上传策略
            policy_dict = {
                "expiration": expiration_iso,
                "conditions": [
                    {"bucket": self.bucket_name},
                    ["starts-with", "$key", prefix],
                    ["content-length-range", 0, 100 * 1024 * 1024]  # 限制文件大小最大100MB
                ]
            }
            
            # Base64编码策略
            policy_base64 = base64.b64encode(
                json.dumps(policy_dict).encode('utf-8')
            ).decode('utf-8')
            
            # 计算签名
            signature = base64.b64encode(
                hmac.new(
                    self.access_key_secret.encode('utf-8'),
                    policy_base64.encode('utf-8'),
                    hashlib.sha1
                ).digest()
            ).decode('utf-8')
            
            return {
                'access_key_id': self.access_key_id,
                'policy': policy_base64,
                'signature': signature,
                'expiration': expiration.isoformat(),
                'bucket': self.bucket_name,
                'endpoint': self.endpoint,
                'prefix': prefix,
                'host': f"https://{self.bucket_name}.{self.endpoint.replace('https://', '').replace('http://', '')}",
                'max_file_size': 100 * 1024 * 1024  # 100MB
            }
            
        except Exception as e:
            raise Exception(f"Error generating upload token: {str(e)}")
        
    def generate_download_url(self, object_key, expires_in=3600):
        """
        生成带签名的下载URL
        
        Args:
            object_key: 文件在OSS中的完整路径
            expires_in: URL有效期（秒），默认1小时
            
        Returns:
            str: 带签名的下载URL
        """
        try:
            expiration = int((datetime.now() + timedelta(seconds=expires_in)).timestamp())
            string_to_sign = f"GET\n\n\n{expiration}\n/{self.bucket_name}/{object_key}"
            signature = base64.b64encode(
                hmac.new(
                    self.access_key_secret.encode('utf-8'),
                    string_to_sign.encode('utf-8'),
                    hashlib.sha1
                ).digest()
            ).decode('utf-8')
            
            download_url = (
                f"https://{self.bucket_name}.{self.endpoint.replace('https://', '').replace('http://', '')}/"
                f"{object_key}?OSSAccessKeyId={self.access_key_id}&Expires={expiration}&Signature={signature}"
            )
            
            return download_url
            
        except Exception as e:
            raise Exception(f"Error generating download URL: {str(e)}")