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
from django.db import models

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
            
            # 确保file_size是整数类型
            try:
                file_size = int(file_size)
            except (ValueError, TypeError):
                return Response({'error': 'file_size must be a valid integer'}, status=status.HTTP_400_BAD_REQUEST)
            
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
            upload_token = token_generator.generate_upload_token(user.username, file_size)
            
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

    # 完成客户端上传后调用此接口创建文件记录
    @action(detail=False, methods=['post'], url_path='uploaded')
    def uploaded(self, request):
        try:
            user = request.user
            upload_id = request.data.get('upload_id')
            
            if not upload_id:
                return Response({
                    'error': 'upload_id is required',
                    'message': 'Missing upload_id'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 从缓存中获取上传信息
            cached_info = cache.get(f"upload_token_{upload_id}")
            if not cached_info:
                return Response({
                    'error': 'Invalid or expired upload_id',
                    'message': 'Upload session not found'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 验证用户身份
            if cached_info['user'] != user.id:
                return Response({
                    'error': 'Permission denied',
                    'message': 'Upload session belongs to different user'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # 从 OSS 校验文件实际大小
            token_generator = OSSTokenGenerator()
            # OSS文件路径应该与客户端上传时使用的路径一致
            
            oss_url = request.data.get('oss_url')
            if not oss_url:
                return Response({
                    'error': 'oss_url is required',
                    'message': 'Missing oss_url'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 从 OSS URL 中提取文件的实际路径
            # URL 格式: https://bucket.oss-region.aliyuncs.com/username/actual_filename
            try:
                oss_key = f"{user.username}/{oss_url.split(f'/{user.username}/')[-1]}"
            except Exception as e:
                return Response({
                    'error': f'Failed to parse OSS URL: {str(e)}',
                    'message': 'OSS URL parsing failed'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                actual_file_size = token_generator.get_file_size(oss_key)
            except Exception as e:
                return Response({
                    'error': f'Failed to verify file on OSS: {str(e)}',
                    'message': 'OSS file verification failed'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 校验文件大小是否与声明的一致（允许小幅偏差）
            declared_size = cached_info['file_size']
            if abs(actual_file_size - declared_size) > 1024:  # 允许1KB的偏差
                return Response({
                    'error': f'File size mismatch. Declared: {declared_size}, Actual: {actual_file_size}',
                    'message': 'File size verification failed'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 重新检查用户配额（使用实际文件大小）
            if user.used_space + actual_file_size > user.quota:
                # 文件已上传到OSS，但配额不足，需要删除OSS文件
                try:
                    token_generator.delete_file(oss_key)
                except:
                    pass  # 删除失败不影响返回错误
                
                return Response({
                    'error': 'Storage quota exceeded after upload',
                    'message': 'Insufficient storage space'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取其他上传信息
            path = request.data.get('path', '/')
            
            # 创建文件记录（使用客户端传入的实际 OSS URL）
            File.objects.create(
                user=user,
                name=cached_info['file_name'],
                content_type=cached_info.get('content_type', 'application/octet-stream'),
                size=actual_file_size,
                oss_url=oss_url,
                path=path,
                is_deleted=False
            )
            
            # 更新用户已使用空间
            user.used_space += actual_file_size
            user.save()
            
            # 清除缓存
            cache.delete(f"upload_token_{upload_id}")
            
            return Response({
                'message': 'File uploaded successfully'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed to create file record'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'], url_path='storage-info')
    def get_storage_info(self, request):
        """
        获取用户存储使用情况
        """
        try:
            user = request.user
            return Response({
                'quota': user.quota,
                'used_space': user.used_space,
                'available_space': user.quota - user.used_space,
                'usage_percentage': round((user.used_space / user.quota * 100), 2) if user.quota > 0 else 0,
                'message': 'Success'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed to get storage info'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='recalculate-storage')
    def recalculate_storage(self, request):
        """
        重新计算用户存储使用情况（管理员功能或修复数据不一致时使用）
        """
        try:
            user = request.user
            
            # 计算用户所有未删除文件的总大小（排除文件夹）
            total_size = File.objects.filter(
                user=user, 
                is_deleted=False,
                content_type__isnull=False
            ).exclude(content_type='folder').aggregate(
                total=models.Sum('size')
            )['total'] or 0
            
            # 更新用户已使用空间
            old_used_space = user.used_space
            user.used_space = total_size
            user.save()
            
            return Response({
                'old_used_space': old_used_space,
                'new_used_space': total_size,
                'difference': total_size - old_used_space,
                'message': 'Storage recalculated successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e),
                'message': 'Failed to recalculate storage'
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
        删除文件
        """
        try:
            user = request.user
            file = self.get_object()
            if file.user != user:
                return Response({'error': 'No permission'}, status=status.HTTP_403_FORBIDDEN)
            
            token_generator = OSSTokenGenerator()
            oss_key = f"{user.username}/{file.oss_url.split(f'/{user.username}/')[-1]}"
            token_generator.delete_file(oss_key)

            # 逻辑删除
            file.is_deleted = True
            file.save()
            
            # 更新用户已使用空间（释放空间）
            if file.content_type != 'folder':
                user.used_space = max(0, user.used_space - file.size)
                user.save()
            
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