from rest_framework import viewsets
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed

# Create your views here.

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ['username', 'email']

    def get_serializer_class(self):
        return UserSerializer
    
    def get_queryset(self):
        return User.objects.order_by('id')

    @action(
        detail=False,
        methods=['post'],
        url_path='login'
    )
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                serializer = self.get_serializer(user)
                return Response(serializer.data)
            else:
                raise AuthenticationFailed('用户名或密码错误')
        except User.DoesNotExist:
            raise AuthenticationFailed('用户名或密码错误')

    @action(
        detail=False,   
        methods=['post'],
        url_path='register',
        permission_classes=[]  # 注册不需要认证
    )
    def register(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 检查用户名是否已存在
        if User.objects.filter(username=request.data.get('username')).exists():
            return Response({'error': '用户名已存在'}, status=400)
        
        # 检查邮箱是否已存在
        if User.objects.filter(email=request.data.get('email')).exists():
            return Response({'error': '邮箱已存在'}, status=400)
        
        # 创建用户
        user = User.objects.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            display_name=serializer.validated_data.get('display_name', serializer.validated_data['username'])
        )

        return Response(UserSerializer(user).data, status=201)
    
    @action(
        detail=False,
        methods=['get'],
        url_path='profile',
        permission_classes=[IsAuthenticated]
    )
    def profile(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data)

class UserSettingsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['post'],
        url_path='change-password',
        permission_classes=[IsAuthenticated]
    )
    def change_password(self, request, pk=None):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({'error': '旧密码错误'}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({'status': '密码更新成功'})