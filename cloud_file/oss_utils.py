import json
import base64
import hmac
import hashlib
from datetime import datetime, timedelta
from urllib.parse import quote
from django.conf import settings


class OSSTokenGenerator:
    """阿里云 OSS 上传Token生成器"""
    
    def __init__(self):
        self.access_key_id = settings.ALIYUN_ACCESS_KEY
        self.access_key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        self.bucket_name = settings.OSS_BUCKET_NAME
        self.endpoint = settings.OSS_ENDPOINT
    
    def _clean_object_key(self, object_key):
        """
        清理object_key，确保它是正确的文件路径格式
        
        Args:
            object_key: 原始的object_key，可能是完整URL或相对路径
            
        Returns:
            str: 清理后的object_key（相对路径，不以/开头）
        """
        # 如果传入的是完整URL，提取出文件路径部分
        if object_key.startswith('http'):
            from urllib.parse import urlparse
            parsed_url = urlparse(object_key)
            object_key = parsed_url.path.lstrip('/')
            
            # 如果路径中包含bucket名称，需要去除
            if object_key.startswith(f"{self.bucket_name}/"):
                object_key = object_key[len(f"{self.bucket_name}/"):]
        
        # 确保object_key不以/开头
        return object_key.lstrip('/')
    
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
            object_key: 文件在OSS中的完整路径（不包含域名，例如: user/file.pdf）
                       或完整的OSS URL（会自动提取路径部分）
            expires_in: URL有效期（秒），默认1小时
            
        Returns:
            str: 带签名的下载URL
        """
        try:
            # 清理object_key，确保它是正确的文件路径格式
            object_key = self._clean_object_key(object_key)
            
            expiration = int((datetime.now() + timedelta(seconds=expires_in)).timestamp())
            
            # 构造StringToSign（用于URL签名）
            # StringToSign = VERB + "\n" + CONTENT-MD5 + "\n" + CONTENT-TYPE + "\n" + EXPIRES + "\n" + CanonicalizedOSSHeaders + CanonicalizedResource
            verb = "GET"
            content_md5 = ""  # 下载时通常为空
            content_type = ""  # 下载时通常为空
            expires = str(expiration)
            canonicalized_oss_headers = ""  # 没有自定义OSS headers时为空
            canonicalized_resource = f"/{self.bucket_name}/{object_key}"
            
            string_to_sign = f"{verb}\n{content_md5}\n{content_type}\n{expires}\n{canonicalized_oss_headers}{canonicalized_resource}"
            
            # 计算签名
            signature = base64.b64encode(
                hmac.new(
                    self.access_key_secret.encode('utf-8'),
                    string_to_sign.encode('utf-8'),
                    hashlib.sha1
                ).digest()
            ).decode('utf-8')
            
            # URL编码签名（重要：URL中的签名需要进行URL编码）
            signature_encoded = quote(signature, safe='')
            
            # 构造下载URL
            host = self.endpoint.replace('https://', '').replace('http://', '')
            download_url = (
                f"https://{self.bucket_name}.{host}/"
                f"{object_key}?OSSAccessKeyId={self.access_key_id}&Expires={expiration}&Signature={signature_encoded}"
            )
            
            return download_url
            
        except Exception as e:
            raise Exception(f"Error generating download URL: {str(e)}")
    
    def generate_signed_url_with_headers(self, object_key, method='GET', expires_in=3600, headers=None):
        """
        生成带自定义headers的签名URL（用于Header中包含签名的场景）
        
        Args:
            object_key: 文件在OSS中的完整路径（不包含域名，例如: user/file.pdf）
                       或完整的OSS URL（会自动提取路径部分）
            method: HTTP方法，默认GET
            expires_in: URL有效期（秒），默认1小时
            headers: 自定义headers字典
            
        Returns:
            dict: 包含URL和需要的headers
        """
        try:
            if headers is None:
                headers = {}
            
            # 清理object_key，确保它是正确的文件路径格式
            object_key = self._clean_object_key(object_key)
            
            # 计算过期时间（RFC 2822格式）
            expiration = datetime.now() + timedelta(seconds=expires_in)
            date_str = expiration.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            # 获取Content-MD5和Content-Type
            content_md5 = headers.get('Content-MD5', '')
            content_type = headers.get('Content-Type', '')
            
            # 构造CanonicalizedOSSHeaders
            canonicalized_oss_headers = ""
            oss_headers = {}
            for key, value in headers.items():
                if key.lower().startswith('x-oss-'):
                    oss_headers[key.lower()] = value
            
            if oss_headers:
                sorted_headers = sorted(oss_headers.items())
                canonicalized_oss_headers = ''.join([f"{k}:{v}\n" for k, v in sorted_headers])
            
            # 构造CanonicalizedResource
            canonicalized_resource = f"/{self.bucket_name}/{object_key}"
            
            # 构造StringToSign（用于Header签名）
            string_to_sign = f"{method}\n{content_md5}\n{content_type}\n{date_str}\n{canonicalized_oss_headers}{canonicalized_resource}"
            
            # 计算签名
            signature = base64.b64encode(
                hmac.new(
                    self.access_key_secret.encode('utf-8'),
                    string_to_sign.encode('utf-8'),
                    hashlib.sha1
                ).digest()
            ).decode('utf-8')
            
            # 构造URL和headers
            host = self.endpoint.replace('https://', '').replace('http://', '')
            url = f"https://{self.bucket_name}.{host}/{object_key}"
            
            request_headers = headers.copy()
            request_headers['Date'] = date_str
            request_headers['Authorization'] = f"OSS {self.access_key_id}:{signature}"
            
            return {
                'url': url,
                'headers': request_headers,
                'string_to_sign': string_to_sign  # 调试用
            }
            
        except Exception as e:
            raise Exception(f"Error generating signed URL with headers: {str(e)}")