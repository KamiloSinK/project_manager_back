from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer that includes user data."""
    
    @classmethod
    def get_token(cls, user):
        """Add custom claims to token."""
        token = super().get_token(user)
        
        # Add custom claims
        token['user_id'] = user.id
        token['email'] = user.email
        token['role'] = user.role
        token['full_name'] = user.full_name
        
        return token
    
    def validate(self, attrs):
        """Validate credentials and return tokens with user data."""
        data = super().validate(attrs)
        
        # Add user data to response
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'username': self.user.username,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'is_active': self.user.is_active,
            'created_at': self.user.created_at,
        }
        
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'password', 'password_confirm', 'role'
        )
        read_only_fields = ('id',)
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate_email(self, value):
        """Validate email uniqueness."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este email."
            )
        return value
    
    def validate_username(self, value):
        """Validate username uniqueness."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este nombre de usuario."
            )
        return value
    
    def validate(self, attrs):
        """Validate password confirmation and strength."""
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)
        
        if password != password_confirm:
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden.'
            })
        
        # Validate password strength
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({
                'password': list(e.messages)
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create user with encrypted password."""
        password = validated_data.pop('password')
        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""
    
    full_name = serializers.ReadOnlyField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'role', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username')
    
    def validate_username(self, value):
        """Validate username uniqueness excluding current user."""
        user = self.instance
        if User.objects.filter(username=value).exclude(id=user.id).exists():
            raise serializers.ValidationError(
                "Ya existe un usuario con este nombre de usuario."
            )
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password."""
    
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate_old_password(self, value):
        """Validate current password."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                "La contraseña actual es incorrecta."
            )
        return value
    
    def validate(self, attrs):
        """Validate new password confirmation and strength."""
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')
        
        if new_password != new_password_confirm:
            raise serializers.ValidationError({
                'new_password_confirm': 'Las contraseñas no coinciden.'
            })
        
        # Validate password strength
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })
        
        return attrs
    
    def save(self):
        """Update user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        """Validate email exists."""
        if not User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError(
                "No existe un usuario activo con este email."
            )
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""
    
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        """Validate new password confirmation and strength."""
        new_password = attrs.get('new_password')
        new_password_confirm = attrs.get('new_password_confirm')
        
        if new_password != new_password_confirm:
            raise serializers.ValidationError({
                'new_password_confirm': 'Las contraseñas no coinciden.'
            })
        
        # Validate password strength
        try:
            validate_password(new_password)
        except ValidationError as e:
            raise serializers.ValidationError({
                'new_password': list(e.messages)
            })
        
        return attrs