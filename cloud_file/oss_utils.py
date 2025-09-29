import json
import base64
import hmac
import hashlib
from datetime import datetime, timedelta
from urllib.parse import quote
from django.conf import settings
import requests


class OSSTokenGenerator:
    """阿里云 OSS 上传Token生成器"""
    
    def __init__(self):
        self.access_key_id = settings.ALIYUN_ACCESS_KEY
        self.access_key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        self.bucket_name = settings.OSS_BUCKET_NAME
        self.endpoint = settings.OSS_ENDPOINT
    

    
    def generate_upload_token(self, username, file_size, duration_seconds=3600):
        """
        生成客户端直传OSS的临时访问令牌
        
        Args:
            username: 用户名
            upload_id: 上传会话ID
            file_size: 预期文件大小（字节）
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
            
            # 动态计算文件大小限制（允许10%的缓冲区，最小1MB缓冲）
            size_buffer = max(1024 * 1024, int(file_size * 0.1))  # 最小1MB或10%缓冲
            max_allowed_size = file_size + size_buffer
            
            # 构造上传策略
            policy_dict = {
                "expiration": expiration_iso,
                "conditions": [
                    {"bucket": self.bucket_name},
                    ["starts-with", "$key", prefix],
                    ["content-length-range", 0, max_allowed_size]  # 动态限制文件大小
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
                'declared_file_size': file_size,
                'max_file_size': max_allowed_size
            }
            
        except Exception as e:
            raise Exception(f"Error generating upload token: {str(e)}")
        
    def generate_download_url(self, object_key, expires_in=3600):
        """
        生成带签名的下载URL
        
        Args:
            object_key: 完整的OSS URL（例如: https://bucket.oss-region.aliyuncs.com/username/file1.jpg）
            expires_in: URL有效期（秒），默认1小时
            
        Returns:
            str: 带签名的下载URL
        """
        try:
            # 从完整URL中提取文件路径
            from urllib.parse import urlparse
            parsed_url = urlparse(object_key)
            file_path = parsed_url.path.lstrip('/')
            
            expiration = int((datetime.now() + timedelta(seconds=expires_in)).timestamp())
            
            # 构造StringToSign（用于URL签名）
            # StringToSign = VERB + "\n" + CONTENT-MD5 + "\n" + CONTENT-TYPE + "\n" + EXPIRES + "\n" + CanonicalizedOSSHeaders + CanonicalizedResource
            verb = "GET"
            content_md5 = ""  # 下载时通常为空
            content_type = ""  # 下载时通常为空
            expires = str(expiration)
            canonicalized_oss_headers = ""  # 没有自定义OSS headers时为空
            canonicalized_resource = f"/{self.bucket_name}/{file_path}"
            
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
                f"{file_path}?OSSAccessKeyId={self.access_key_id}&Expires={expiration}&Signature={signature_encoded}"
            )
            
            return download_url
            
        except Exception as e:
            raise Exception(f"Error generating download URL: {str(e)}")
    
    def get_file_size(self, object_key):
        """
        从OSS获取文件大小
        
        Args:
            object_key: 文件在OSS中的路径（不包含bucket名）
            
        Returns:
            int: 文件大小（字节）
        """
        try:
            # 构造HEAD请求URL
            host = self.endpoint.replace('https://', '').replace('http://', '')
            url = f"https://{self.bucket_name}.{host}/{object_key}"
            
            # 生成认证头
            expiration = int((datetime.now() + timedelta(seconds=60)).timestamp())
            
            # 构造StringToSign
            verb = "HEAD"
            content_md5 = ""
            content_type = ""
            expires = str(expiration)
            canonicalized_oss_headers = ""
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
            
            # 构建请求参数
            params = {
                'OSSAccessKeyId': self.access_key_id,
                'Expires': expires,
                'Signature': signature
            }
            
            response = requests.head(url, params=params, timeout=10)
            
            if response.status_code == 200:
                content_length = response.headers.get('Content-Length')
                if content_length:
                    return int(content_length)
                else:
                    raise Exception("Content-Length header not found")
            elif response.status_code == 404:
                raise Exception(f"File not found: {object_key}")
            else:
                raise Exception(f"OSS request failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f"Error getting file size from OSS: {str(e)}")
    
    def delete_file(self, object_key):
        """
        从OSS删除文件
        
        Args:
            object_key: 文件在OSS中的路径（不包含bucket名）
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 构造DELETE请求URL
            host = self.endpoint.replace('https://', '').replace('http://', '')
            url = f"https://{self.bucket_name}.{host}/{object_key}"
            
            # 生成认证头
            expiration = int((datetime.now() + timedelta(seconds=60)).timestamp())
            
            # 构造StringToSign
            verb = "DELETE"
            content_md5 = ""
            content_type = ""
            expires = str(expiration)
            canonicalized_oss_headers = ""
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
            
            # 构建请求参数
            params = {
                'OSSAccessKeyId': self.access_key_id,
                'Expires': expires,
                'Signature': signature
            }
            
            response = requests.delete(url, params=params, timeout=10)
            
            if response.status_code in [204, 404]:  # 204表示删除成功，404表示文件不存在（也算删除成功）
                return True
            else:
                raise Exception(f"OSS delete failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            raise Exception(f"Error deleting file from OSS: {str(e)}")