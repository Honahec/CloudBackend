from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from .models import File, Drop
from .serializers import FileSerializer, FileUploadSerializer, DropSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from .oss_utils import OSSTokenGenerator
import hashlib
from django.core.cache import cache
from django.utils import timezone

# Create your views here.
class FileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FileSerializer

    def get_queryset(self):
        """
        重写 get_queryset 方法，返回当前用户的未删除文件
        """
        user = self.request.user
        if not user.is_authenticated:
            return File.objects.none()
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
                'message': 'Success'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed'
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
                'message': f'Successfully created {len(created_files)} file record(s)'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed to create file records'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'], url_path='get-token')
    def get_upload_token(self, request):
        """
        获取阿里云OSS上传token
        """
        try:
            user = request.user
            file_name = request.data.get('file_name')
            file_size = request.data.get('file_size')
            content_type = request.data.get('content_type')

            if not all([file_name, file_size]):
                return Response({'error': 'Need file_name and file_size'}, status=status.HTTP_400_BAD_REQUEST)
            
            if user.used_space + file_size > user.quota:
                return Response({'error': 'Storage quota exceeded'}, status=status.HTTP_400_BAD_REQUEST)

            token_generator = OSSTokenGenerator()

            upload_id = hashlib.md5(f"{user.id}_{file_name}_{file_size}_{timezone.now().timestamp()}".encode()).hexdigest()

            file_info = {
                'user': user.id,
                'file_name': file_name,
                'file_size': file_size,
                'content_type': content_type,
                'upload_id': upload_id,
            }
            cache.set(f"upload_token_{upload_id}", file_info, timeout=3600)  # 缓存1小时

            # 生成上传token
            upload_token = token_generator.generate_upload_token(user.username, upload_id)
            
            return Response({
                'token': upload_token,
                'upload_id': upload_id,
                'message': 'Success'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed'
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
            return Response({'error': 'Need folder_name'}, status=status.HTTP_400_BAD_REQUEST)
        
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
            'message': 'Success',
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
                return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)
            
            # 逻辑删除
            file.is_deleted = True
            file.save()
            
            return Response({'message': 'Success'}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed'
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
                return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = FileUploadSerializer(file, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Success'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'errors': serializer.errors,
                    'message': 'Invalid data provided'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(
        detail=True,
        methods=['post'],
        url_path='download',
        permission_classes=[]
    )
    def download_file(self, request, pk=None):
        """
        获取文件下载链接
        """
        try:
            code = request.data.get('code', '')
            password = request.data.get('password', '')
            
            if code:
                # 通过code访问，直接查询文件而不依赖get_object()
                try:
                    drop = Drop.objects.get(code=code, is_deleted=False)
                except Drop.DoesNotExist:
                    return Response({'error': 'Invalid code'}, status=status.HTTP_404_NOT_FOUND)

                if drop.is_expired:
                    return Response({'error': 'Drop expired'}, status=status.HTTP_400_BAD_REQUEST)
                
                if drop.expire_time < timezone.now():
                    drop.is_expired = True
                    drop.save()
                    return Response({'error': 'Drop expired'}, status=status.HTTP_400_BAD_REQUEST)

                if drop.require_login and not request.user.is_authenticated:
                    return Response({'error': 'Please login'}, status=status.HTTP_401_UNAUTHORIZED)

                if drop.password and drop.password != password:
                    return Response({'error': 'Wrong password'}, status=status.HTTP_403_FORBIDDEN)
                
                # 直接从drop的files中获取指定的文件
                try:
                    file = drop.files.get(id=pk, is_deleted=False)
                except File.DoesNotExist:
                    return Response({'error': 'File not found in this drop'}, status=status.HTTP_404_NOT_FOUND)

            else:
                # 正常用户访问，使用get_object()
                if not request.user.is_authenticated:
                    return Response({'error': 'Please login'}, status=status.HTTP_401_UNAUTHORIZED)
                
                file = self.get_object()
                if file.user != request.user:
                    return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)
                
            if file.content_type == 'folder':
                return Response({'error': 'You cannot download a folder'}, status=status.HTTP_400_BAD_REQUEST)
            
            token_generator = OSSTokenGenerator()
            download_url = token_generator.generate_download_url(file.oss_url)
            
            return Response({
                'download_url': download_url,
                'message': 'Success'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class DropViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DropSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Drop.objects.none()
            
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
                return Response({'error': 'Need dropping list'}, status=status.HTTP_400_BAD_REQUEST)
            
            files = File.objects.filter(id__in=files_ids, user=user, is_deleted=False)
            if files.count() != len(files_ids):
                return Response({'error': 'No permission'}, status=status.HTTP_400_BAD_REQUEST)
            
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
                'message': 'Success'
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(
        detail=False,
        methods=['post'],
        url_path='get-drop',
        permission_classes=[] 
    )
    def get_drop(self, request):
        """
        获取分享详情
        """
        try:
            code = request.data.get('code', '')
            password = request.data.get('password', '')
            is_require_login = request.data.get('require_login', False)
            
            if is_require_login and not request.user.is_authenticated:
                return Response({'error': 'Please login'}, status=status.HTTP_401_UNAUTHORIZED)
            
            if not code:
                return Response({'error': 'Need sharing code'}, status=status.HTTP_400_BAD_REQUEST)
            
            # 直接查询Drop，不依赖get_queryset
            try:
                drop = Drop.objects.get(code=code, is_deleted=False)
            except Drop.DoesNotExist:
                return Response({'error': 'Invalid code'}, status=status.HTTP_404_NOT_FOUND)
            
            from django.utils import timezone

            if drop.expire_time < timezone.now():
                drop.is_expired = True
                drop.save()

            if drop.is_expired:
                return Response({'error': 'Drop expired'}, status=status.HTTP_400_BAD_REQUEST)
            
            if drop.require_login and not request.user.is_authenticated:
                return Response({'error': 'Please login'}, status=status.HTTP_401_UNAUTHORIZED)
            
            if drop.password and drop.password != password:
                return Response({'error': 'Wrong password'}, status=status.HTTP_403_FORBIDDEN)
            
            if drop.download_count >= drop.max_download_count:
                return Response({'error': 'Download limit exceeded'}, status=status.HTTP_400_BAD_REQUEST)
            
            files = drop.files.filter(is_deleted=False)
            drop.download_count += 1
            drop.save()
            
            return Response({
                'drop': DropSerializer(drop).data,
                'files': FileSerializer(files, many=True).data,
                'message': 'Success'
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed'
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
                return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)
            
            # 逻辑删除
            drop.is_deleted = True
            drop.save()
            
            return Response({'message': 'Success'}, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)