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

    def get_queryset(self):
        user = self.request.user
        queryset = File.objects.filter(user=user)
        return queryset.order_by('-id')

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