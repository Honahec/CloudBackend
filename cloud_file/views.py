from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import File, Drop
from .serializers import FileSerializer, FileUploadSerializer, DropSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from .oss_utils import OSSTokenGenerator

# Create your views here.
class FileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FileSerializer

    def get_queryset(self):
        """
        重写 get_queryset 方法，返回当前用户的未删除文件
        """
        user = self.request.user
        return File.objects.filter(user=user, is_deleted=False)

    @action(
        detail=False,
        methods=['post'], 
        url_path='list'
    )
    def list_files(self, request):
        """
        根据路径获取文件列表
        """
        try:
            user = request.user
            path = request.data.get('path', '/')
            
            queryset = File.objects.filter(
                user=user,
                path=path,
                is_deleted=False
            )
            
            return Response({
                'files': FileSerializer(queryset, many=True).data,
                'message': '文件列表获取成功'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': '获取文件列表失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
        
    @action(
        detail=True,
        methods=['post'],
        url_path='update',
    )
    def update_file(self, request, pk=None):
        try:
            user = request.user
            file = self.get_object()
            if file.user != user:
                return Response({'error': '没有权限更新此文件'}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = FileUploadSerializer(file, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'file': FileSerializer(file).data,
                    'message': '文件信息更新成功'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'errors': serializer.errors,
                    'message': 'Invalid data provided'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': '更新文件信息失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(
        detail=True,
        methods=['post'],
        url_path='download',
    )
    def download_file(self, request, pk=None):
        """
        获取文件下载链接
        """
        try:
            user = request.user
            file = self.get_object()
            if file.user != user:
                return Response({'error': '没有权限下载此文件'}, status=status.HTTP_403_FORBIDDEN)
            
            if file.content_type == 'folder':
                return Response({'error': '文件夹无法下载'}, status=status.HTTP_400_BAD_REQUEST)
            
            token_generator = OSSTokenGenerator()
            download_url = token_generator.generate_download_url(file.oss_url)
            
            return Response({
                'download_url': download_url,
                'message': '下载链接已生成'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': '生成下载链接失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class DropViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DropSerializer

    def get_queryset(self):
        user = self.request.user
        drops = Drop.objects.filter(user=user, is_deleted=False)

        from django.utils import timezone

        for drop in drops:
            if drop.expire_time < timezone.now():
                drop.is_expired = True
                drop.save()

        return drops
    
    @action(
        detail=False,
        methods=['post'],
        url_path='create'
    )
    def create_drop(self, request):
        """
        创建文件分享
        """
        try:
            user = request.user
            files_ids = request.data.get('files', [])
            expire_days = request.data.get('expire_days', 1)
            code = request.data.get('code', '')
            require_login = request.data.get('require_login', False)
            max_download_count = request.data.get('max_download_count', 1)
            password = request.data.get('password', '')

            if not files_ids:
                return Response({'error': '需要提供文件列表'}, status=status.HTTP_400_BAD_REQUEST)
            
            files = File.objects.filter(id__in=files_ids, user=user, is_deleted=False)
            if files.count() != len(files_ids):
                return Response({'error': '部分文件不存在或无权限'}, status=status.HTTP_400_BAD_REQUEST)
            
            from django.utils import timezone
            from datetime import timedelta
            expire_time = timezone.now() + timedelta(days=expire_days)
            
            drop = Drop.objects.create(
                user=user,
                expire_days=expire_days,
                expire_time=expire_time,
                code=code,
                require_login=require_login,
                max_download_count=max_download_count,
                password=password
            )
            drop.files.set(files)
            drop.save()
            
            return Response({
                'drop': DropSerializer(drop).data,
                'message': '分享创建成功'
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': '创建分享失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(
        detail=False,
        methods=['post'],
        url_path='get-drop'
    )
    def get_drop(self, request):
        """
        获取分享详情
        """
        try:
            code = request.data.get('code', '')
            password = request.data.get('password', '')
            if not code:
                return Response({'error': '需要提供分享code'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                drop = Drop.objects.get(code=code, is_deleted=False)
            except Drop.DoesNotExist:
                return Response({'error': '分享不存在'}, status=status.HTTP_404_NOT_FOUND)
            
            from django.utils import timezone

            if drop.expire_time < timezone.now():
                drop.is_expired = True

            if drop.is_expired:
                return Response({'error': '分享已过期'}, status=status.HTTP_400_BAD_REQUEST)
            
            if drop.password and drop.password != password:
                return Response({'error': '密码错误'}, status=status.HTTP_403_FORBIDDEN)
            
            if drop.require_login and not request.user.is_authenticated:
                return Response({'error': '需要登录后访问'}, status=status.HTTP_401_UNAUTHORIZED)
            
            if drop.download_count >= drop.max_download_count:
                return Response({'error': '下载次数已达上限'}, status=status.HTTP_400_BAD_REQUEST)
            
            files = drop.files.filter(is_deleted=False)
            drop.download_count += 1
            drop.save()
            
            return Response({
                'drop': DropSerializer(drop).data,
                'files': FileSerializer(files, many=True).data,
                'message': '获取分享详情成功'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': '获取分享详情失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(
        detail=True,
        methods=['post'],
        url_path='delete',
    )
    def delete_drop(self, request, pk=None):
        """
        删除分享（逻辑删除）
        """
        try:
            user = request.user
            drop = self.get_object()
            if drop.user != user:
                return Response({'error': '没有权限删除此分享'}, status=status.HTTP_403_FORBIDDEN)
            
            # 逻辑删除
            drop.is_deleted = True
            drop.save()
            
            return Response({'message': '分享已删除'}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': '删除分享失败'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)