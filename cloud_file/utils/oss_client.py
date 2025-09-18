"""
阿里云OSS客户端工具模块
"""
import oss2
import logging
from django.conf import settings
from typing import Optional, Dict, Any
import io

logger = logging.getLogger(__name__)


class OSSClient:
    """阿里云OSS客户端封装类"""
    
    def __init__(self):
        self.access_key_id = settings.ALIYUN_ACCESS_KEY
        self.access_key_secret = settings.ALIYUN_ACCESS_KEY_SECRET
        self.endpoint = settings.OSS_ENDPOINT
        self.bucket_name = settings.OSS_BUCKET_NAME
        
        # 创建认证对象
        self.auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        
        # 创建Bucket对象
        self.bucket = oss2.Bucket(self.auth, self.endpoint, self.bucket_name)
    
    def upload_file(self, file_content: bytes, object_key: str, content_type: str = None) -> Dict[str, Any]:
        """
        上传文件到OSS
        
        Args:
            file_content: 文件内容(字节)
            object_key: OSS中的对象键(文件路径)
            content_type: 文件MIME类型
            
        Returns:
            Dict: 包含上传结果的字典
        """
        try:
            # 设置HTTP头
            headers = {}
            if content_type:
                headers['Content-Type'] = content_type
            
            # 上传文件
            result = self.bucket.put_object(
                object_key, 
                file_content,
                headers=headers
            )
            
            # 获取文件URL
            file_url = self.get_file_url(object_key)
            
            logger.info(f"文件上传成功: {object_key}")
            
            return {
                'success': True,
                'object_key': object_key,
                'url': file_url,
                'etag': result.etag,
                'request_id': result.request_id
            }
            
        except Exception as e:
            logger.error(f"文件上传失败: {object_key}, 错误: {str(e)}")
            return {
                'success': False,
                'object_key': object_key,
                'error': str(e)
            }
    
    def get_file_url(self, object_key: str, expires: int = 3600) -> str:
        """
        获取文件的访问URL
        
        Args:
            object_key: OSS中的对象键
            expires: URL过期时间(秒)，默认1小时
            
        Returns:
            str: 文件访问URL
        """
        try:
            # 生成签名URL
            url = self.bucket.sign_url('GET', object_key, expires)
            return url
        except Exception as e:
            logger.error(f"生成文件URL失败: {object_key}, 错误: {str(e)}")
            return ""
    
    def delete_file(self, object_key: str) -> Dict[str, Any]:
        """
        删除OSS中的文件
        
        Args:
            object_key: OSS中的对象键
            
        Returns:
            Dict: 删除结果
        """
        try:
            result = self.bucket.delete_object(object_key)
            logger.info(f"文件删除成功: {object_key}")
            
            return {
                'success': True,
                'object_key': object_key,
                'request_id': result.request_id
            }
            
        except Exception as e:
            logger.error(f"文件删除失败: {object_key}, 错误: {str(e)}")
            return {
                'success': False,
                'object_key': object_key,
                'error': str(e)
            }
    
    def file_exists(self, object_key: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            object_key: OSS中的对象键
            
        Returns:
            bool: 文件是否存在
        """
        try:
            return self.bucket.object_exists(object_key)
        except Exception as e:
            logger.error(f"检查文件存在性失败: {object_key}, 错误: {str(e)}")
            return False
    
    def get_file_info(self, object_key: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            object_key: OSS中的对象键
            
        Returns:
            Dict: 文件信息或None
        """
        try:
            result = self.bucket.head_object(object_key)
            
            return {
                'content_length': result.content_length,
                'content_type': result.content_type,
                'etag': result.etag,
                'last_modified': result.last_modified,
                'request_id': result.request_id
            }
            
        except Exception as e:
            logger.error(f"获取文件信息失败: {object_key}, 错误: {str(e)}")
            return None


# 创建全局OSS客户端实例
def get_oss_client() -> OSSClient:
    """获取OSS客户端实例"""
    return OSSClient()
