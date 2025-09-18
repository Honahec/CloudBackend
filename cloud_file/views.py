from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import File
from .serializers import FileSerializer, FileUploadSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from .tasks import upload_file_to_oss, batch_upload_files_to_oss
import logging

logger = logging.getLogger(__name__)


# Create your views here.
class FileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FileSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = File.objects.filter(user=user)
        return queryset.order_by('-id')

    def create(self, request):
        if type(request.data) == dict:
            _data = [request.data]
        else:
            _data = request.data

        user = request.user
        data = []

        for item in _data:
            serializer = FileUploadSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            data.append(serializer)

        response_data = []
        file_items = []
        for serializer in data:
            serializer.save(user=user)
            _data = serializer.data
            response_data.append(_data)
            file_items.append(serializer.instance)

        # 触发异步任务上传文件到对象存储
        self._trigger_upload_tasks(file_items, request.data if type(request.data) == dict else _data)
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    def _trigger_upload_tasks(self, file_items, request_data_list):
        """
        触发异步上传任务
        
        Args:
            file_items: 文件模型实例列表
            request_data_list: 请求数据列表，包含文件内容
        """
        try:
            # 如果是单个文件
            if len(file_items) == 1:
                file_obj = file_items[0]
                file_content_base64 = None
                
                # 从请求数据中获取文件内容
                if isinstance(request_data_list, dict):
                    file_content_base64 = request_data_list.get('file_content')
                elif isinstance(request_data_list, list) and len(request_data_list) > 0:
                    file_content_base64 = request_data_list[0].get('file_content')
                
                # 启动异步上传任务
                task = upload_file_to_oss.delay(file_obj.id, file_content_base64)
                logger.info(f"启动文件上传任务: {file_obj.name}, 任务ID: {task.id}")
                
            # 如果是多个文件，使用批量上传
            else:
                file_ids = [file_obj.id for file_obj in file_items]
                
                # 为每个文件启动单独的上传任务
                for i, file_obj in enumerate(file_items):
                    file_content_base64 = None
                    if i < len(request_data_list):
                        file_content_base64 = request_data_list[i].get('file_content')
                    
                    task = upload_file_to_oss.delay(file_obj.id, file_content_base64)
                    logger.info(f"启动文件上传任务: {file_obj.name}, 任务ID: {task.id}")
                
        except Exception as e:
            logger.error(f"启动异步上传任务失败: {str(e)}")
            # 更新文件状态为失败
            for file_obj in file_items:
                file_obj.upload_status = 'failed'
                file_obj.upload_error = f"启动上传任务失败: {str(e)}"
                file_obj.save(update_fields=['upload_status', 'upload_error'])
    
    @action(detail=True, methods=['post'])
    def retry_upload(self, request, pk=None):
        """
        重新上传文件
        """
        file_obj = self.get_object()
        
        # 检查文件状态
        if file_obj.upload_status == 'completed':
            return Response(
                {'error': '文件已经上传成功，无需重试'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 获取文件内容
        file_content_base64 = request.data.get('file_content')
        if not file_content_base64:
            return Response(
                {'error': '请提供文件内容'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 重置状态为待上传
            file_obj.upload_status = 'pending'
            file_obj.upload_error = None
            file_obj.save(update_fields=['upload_status', 'upload_error'])
            
            # 启动异步上传任务
            task = upload_file_to_oss.delay(file_obj.id, file_content_base64)
            logger.info(f"重新启动文件上传任务: {file_obj.name}, 任务ID: {task.id}")
            
            return Response({
                'message': '重新上传任务已启动',
                'task_id': task.id,
                'file_id': file_obj.id
            })
            
        except Exception as e:
            logger.error(f"重新启动上传任务失败: {str(e)}")
            return Response(
                {'error': f'启动上传任务失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def upload_status(self, request):
        """
        批量查询文件上传状态
        """
        file_ids = request.query_params.get('file_ids', '').split(',')
        file_ids = [int(fid) for fid in file_ids if fid.isdigit()]
        
        if not file_ids:
            return Response(
                {'error': '请提供有效的文件ID列表'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        files = self.get_queryset().filter(id__in=file_ids)
        
        status_data = []
        for file_obj in files:
            status_data.append({
                'id': file_obj.id,
                'name': file_obj.name,
                'upload_status': file_obj.upload_status,
                'upload_error': file_obj.upload_error,
                'oss_url': file_obj.oss_url,
                'created_at': file_obj.created_at,
                'updated_at': file_obj.updated_at
            })
        
        return Response(status_data)