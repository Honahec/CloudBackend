from rest_framework import viewsets
from rest_framework.response import Response
from .models import User
from .serializers import UserSerializer, UserAuthSerializer
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.viewsets import GenericViewSet

# Create your views here.

class UserAuthViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ['username', 'email']

    def get_serializer_class(self):
        return UserAuthSerializer
    
    def get_queryset(self):
        return User.objects.order_by('id')

    @action(
        detail=False,
        methods=['post'],
        url_path='login',
        permission_classes=[]
    )
    def login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        try:
            user = User.objects.get(username=username)
            if user.check_password(password) and user.is_active:
                # 生成JWT token
                refresh = RefreshToken.for_user(user)
                serializer = self.get_serializer(user)
                return Response({
                    'user': serializer.data,
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                })
            else:
                raise AuthenticationFailed('Username or Password error')
        except User.DoesNotExist:
            raise AuthenticationFailed('Username or Password error')

    @action(
        detail=False,   
        methods=['post'],
        url_path='register',
        permission_classes=[]
    )
    def register(self, request):
        serializer = UserAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 检查用户名是否已存在
        if User.objects.filter(username=request.data.get('username')).exists():
            return Response({'error': 'Username already exists'}, status=400)
        
        # 检查邮箱是否已存在
        if User.objects.filter(email=request.data.get('email')).exists():
            return Response({'error': 'Email already exists'}, status=400)
        
        # 先创建权限对象
        from .models import Permission
        user_permission = Permission.objects.create()
        
        # 创建用户
        user = User.objects.create_user(
            username=serializer.validated_data['username'],
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        user.display_name = serializer.validated_data.get('display_name', serializer.validated_data['username'])
        user.permission = user_permission
        user.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            'user': UserAuthSerializer(user).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })
    
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
    
    @action(
        detail=False,
        methods=['post'],
        url_path='logout',
        permission_classes=[IsAuthenticated]
    )
    def logout(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'status': 'Success'})
        except Exception as e:
            return Response({'status': 'Success'})

    @action(
        detail=False,
        methods=['post'],
        url_path='refresh-token',
        permission_classes=[]
    )
    def refresh_token(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Require refresh token'}, status=400)
        
        try:
            refresh = RefreshToken(refresh_token)
            access_token = refresh.access_token
            return Response({
                'access': str(access_token),
                'refresh': str(refresh),
            })
        except TokenError as e:
            return Response({'error': 'Uneffective token'}, status=401)

class UserSettingsViewSet(GenericViewSet):
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
            return Response({'error': 'old_password error'}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({'status': 'Success'})
    
    @action(
        detail=False,
        methods=['post'],
        url_path='update-display-name',
        permission_classes=[IsAuthenticated]
    )
    def update_display_name(self, request, pk=None):
        user = request.user
        display_name = request.data.get('display_name')

        if display_name:
            user.display_name = display_name
        else:   
            user.display_name = user.username

        user.save()
        return Response('status', 'Success')
    
    @action(
        detail=False,
        methods=['post'],
        url_path='update-email',
        permission_classes=[IsAuthenticated]
    )
    def update_email(self, request, pk=None):
        user = request.user
        email = request.data.get('email')

        if email:
            # 检查邮箱是否已存在
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                return Response({'error': 'email already exists'}, status=400)
            user.email = email
            user.save()
            return Response('status', 'Success')
        else:
            return Response({'error': 'Email is neccessary'}, status=400)