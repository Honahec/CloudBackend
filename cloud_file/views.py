from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import File
from .serializers import FileSerializer, FileUploadSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from .oss_utils import OSSTokenGenerator

# Create your views here.
class FileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FileSerializer

    @action(detail=False, methods=['post'], url_path='list')
    def get_queryset(self, request):
        user = self.request.user
        queryset = File.objects.filter(
            user=user,
            path=request.data.get('path', '/'),
            is_deleted=False
        )
        return Response({
            'files': FileSerializer(queryset, many=True).data,
            'message': '文件列表获取成功'
        }, status=status.HTTP_200_OK)

    # 完成客户端上传后调用此接口创建文件记录
    @action(detail=False, methods=['post'], url_path='uploaded')
    def uploaded(self, request):
        try:
            user = request.user
            
            # 支持单个文件或批量文件
            if isinstance(request.data, dict):
                files_data = [request.data]
            else:
                files_data = request.data
            
            created_files = []
            
            for file_data in files_data:
                # 验证数据
                serializer = FileUploadSerializer(data=file_data)
                if serializer.is_valid():
                    # 直接创建已完成状态的文件记录
                    file_instance = serializer.save(user=user)
                    created_files.append(FileSerializer(file_instance).data)
                else:
                    return Response({
                        'errors': serializer.errors,
                        'message': 'Invalid file data provided'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'files': created_files,
                'message': f'Successfully created {len(created_files)} file record(s)'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed to create file records'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='get-token')
    def get_upload_token(self, request):
        """
        获取阿里云OSS上传token
        """
        try:
            user = request.user
            token_generator = OSSTokenGenerator()
            
            # 生成上传token
            upload_token = token_generator.generate_upload_token(user.username)
            
            return Response({
                'token': upload_token,
                'message': '已生成token'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e),
                'message': '生成token失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(
        detail=False,
        methods=['post'],
        url_path='new-folder',
    )
    def new_folder(self, request):
        """
        创建新文件夹（逻辑文件夹）
        """
        folder_name = request.data.get('folder_name')
        path = request.data.get('path', '/')
        if not folder_name:
            return Response({'error': '需要提供folder_name'}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        # 创建一个逻辑文件夹记录，实际不占用OSS存储
        folder = File.objects.create(
            user=user,
            name=folder_name,
            content_type='folder',
            size=0,
            oss_url='',
            path=path,
            is_deleted=False
        )
        
        return Response({
            'folder': FileSerializer(folder).data,
            'message': '文件夹创建成功'
        }, status=status.HTTP_201_CREATED)
    
    @action(
        detail=True,
        methods=['post'],
        url_path='delete',
    )
    def delete_file(self, request, pk=None):
        """
        删除文件（逻辑删除）
        """
        try:
            user = request.user
            file = self.get_object()
            if file.user != user:
                return Response({'error': '没有权限删除此文件'}, status=status.HTTP_403_FORBIDDEN)
            
            # 逻辑删除
            file.is_deleted = True
            file.save()
            
            return Response({'message': '文件已删除'}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': '删除文件失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)