"""
文件上传异步任务模块
"""
from celery import shared_task
from django.apps import apps
import logging
import os
import tempfile
from uuid import uuid4
from .utils.oss_client import get_oss_client

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def upload_file_to_oss(self, file_id: int, file_content_base64: str = None):
    """
    异步上传文件到阿里云OSS
    
    Args:
        file_id: 文件记录ID
        file_content_base64: base64编码的文件内容(可选)
    """
    try:
        # 动态导入模型以避免循环导入
        File = apps.get_model('cloud_file', 'File')
        
        # 获取文件记录
        try:
            file_obj = File.objects.get(id=file_id)
        except File.DoesNotExist:
            logger.error(f"文件记录不存在: {file_id}")
            return {
                'success': False,
                'error': f'文件记录不存在: {file_id}'
            }
        
        # 更新上传状态为处理中
        file_obj.upload_status = 'uploading'
        file_obj.save(update_fields=['upload_status'])
        
        # 生成唯一的OSS对象键
        file_extension = os.path.splitext(file_obj.name)[1]
        object_key = f"files/{file_obj.user.id}/{uuid4().hex}{file_extension}"
        
        # 获取OSS客户端
        oss_client = get_oss_client()
        
        # 如果提供了base64内容，直接使用
        if file_content_base64:
            import base64
            file_content = base64.b64decode(file_content_base64)
        else:
            # 这里可以根据实际情况从临时文件或其他地方获取文件内容
            # 示例：假设文件内容存储在某个临时位置
            logger.warning(f"未提供文件内容，文件ID: {file_id}")
            file_obj.upload_status = 'failed'
            file_obj.upload_error = "未提供文件内容"
            file_obj.save(update_fields=['upload_status', 'upload_error'])
            return {
                'success': False,
                'error': '未提供文件内容'
            }
        
        # 上传文件到OSS
        upload_result = oss_client.upload_file(
            file_content=file_content,
            object_key=object_key,
            content_type=file_obj.content_type
        )
        
        if upload_result['success']:
            # 更新文件记录
            file_obj.oss_key = object_key
            file_obj.oss_url = upload_result['url']
            file_obj.upload_status = 'completed'
            file_obj.upload_error = None
            file_obj.save(update_fields=[
                'oss_key', 'oss_url', 'upload_status', 'upload_error'
            ])
            
            logger.info(f"文件上传成功: {file_obj.name}, OSS Key: {object_key}")
            
            return {
                'success': True,
                'file_id': file_id,
                'oss_key': object_key,
                'oss_url': upload_result['url']
            }
        else:
            # 上传失败，更新状态
            file_obj.upload_status = 'failed'
            file_obj.upload_error = upload_result.get('error', '上传失败')
            file_obj.save(update_fields=['upload_status', 'upload_error'])
            
            logger.error(f"文件上传失败: {file_obj.name}, 错误: {upload_result.get('error')}")
            
            return {
                'success': False,
                'file_id': file_id,
                'error': upload_result.get('error', '上传失败')
            }
            
    except Exception as exc:
        logger.error(f"异步任务执行异常: {str(exc)}")
        
        # 更新文件状态为失败
        try:
            File = apps.get_model('cloud_file', 'File')
            file_obj = File.objects.get(id=file_id)
            file_obj.upload_status = 'failed'
            file_obj.upload_error = str(exc)
            file_obj.save(update_fields=['upload_status', 'upload_error'])
        except Exception:
            pass
        
        # 重试机制
        if self.request.retries < self.max_retries:
            # 延迟重试（指数退避）
            countdown = 60 * (2 ** self.request.retries)
            logger.info(f"任务重试，第{self.request.retries + 1}次，延迟{countdown}秒")
            raise self.retry(countdown=countdown, exc=exc)
        else:
            logger.error(f"任务重试次数已达上限，最终失败: {str(exc)}")
            return {
                'success': False,
                'file_id': file_id,
                'error': str(exc)
            }


@shared_task
def delete_file_from_oss(oss_key: str):
    """
    异步删除OSS中的文件
    
    Args:
        oss_key: OSS对象键
    """
    try:
        oss_client = get_oss_client()
        result = oss_client.delete_file(oss_key)
        
        if result['success']:
            logger.info(f"OSS文件删除成功: {oss_key}")
        else:
            logger.error(f"OSS文件删除失败: {oss_key}, 错误: {result.get('error')}")
        
        return result
        
    except Exception as exc:
        logger.error(f"删除OSS文件异常: {oss_key}, 错误: {str(exc)}")
        return {
            'success': False,
            'oss_key': oss_key,
            'error': str(exc)
        }


@shared_task
def batch_upload_files_to_oss(file_ids: list):
    """
    批量上传文件到OSS
    
    Args:
        file_ids: 文件ID列表
    """
    results = []
    
    for file_id in file_ids:
        try:
            result = upload_file_to_oss.delay(file_id)
            results.append({
                'file_id': file_id,
                'task_id': result.id,
                'status': 'queued'
            })
        except Exception as exc:
            logger.error(f"启动批量上传任务失败: {file_id}, 错误: {str(exc)}")
            results.append({
                'file_id': file_id,
                'task_id': None,
                'status': 'failed',
                'error': str(exc)
            })
    
    logger.info(f"批量上传任务已启动，文件数量: {len(file_ids)}")
    return results
