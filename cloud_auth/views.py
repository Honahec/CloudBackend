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


    def create(self, request):
        Serializer = UserSerializer(data=request.data)
        Serializer.is_valid(raise_exception=True)

        if User.objects.filter(username=request.data.get('username')).exists():
            return Response({'error': '用户名已存在'}, status=400)
        
        user = User.objects.create_user(
            username=Serializer.validated_data['username'],
            email=Serializer.validated_data['email'],
            password=Serializer.validated_data['password']
        )

        return Response(UserSerializer(user).data, status=201)
    
    @action(
        detail=False,
        methods=['get'],
        url_path='profile',
        permission_classes = [IsAuthenticated]
    )
    def profile(self, request):
        user: User = self.get_object()
        serializer = self.get_serializer(user)
        return Response(serializer.data)

class UserSettingsViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    @action(
        detail=False,
        methods=['post'],
        url_path='change-password',
        permission_classes = [IsAuthenticated]
    )
    def change_password(self, request, pk=None):
        user: User = self.get_object()
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not user.check_password(old_password):
            return Response({'error': '旧密码错误'}, status=400)

        user.set_password(new_password)
        user.save()
        return Response({'status': '密码更新成功'})