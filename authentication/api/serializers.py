from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from authentication.models import User,Companies
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from authentication.utils import Util
from django.core.validators import EmailValidator
from django.shortcuts import get_object_or_404
from django.utils import timezone
from messages import common
from django.template.loader import render_to_string
import os

class CreateUserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True, required=True)
    company_id = serializers.IntegerField(write_only=True, required=True)
    class Meta:
        model = User
        fields = ('password', 'password2', 'email', 'name','address','company_id')
        extra_kwargs = {
            'name': {'required': True},
        }

    # validate password and confirm passsword
    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        company_id = attrs.get('company_id')

        if password != password2:
            raise serializers.ValidationError({"password": common["messages"]["PASSWORDS_NOT_MATCH"]})
        
        if company_id and not Companies.objects.filter(id=company_id).exists():
            raise serializers.ValidationError({"company_id": common["messages"]["COMPANY_NOT_EXIST"]})
        
        return attrs

    def create(self, validated_data):
        company_id = validated_data.pop('company_id')
        password = validated_data.pop('password')
        validated_data.pop('password2', None)  # Remove password2 from validated_data
        return User.objects.create_user(password=password,company_id=company_id, **validated_data)
       
class LoginSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255)
    class Meta:
        model = User
        fields = ['email','password']

class ProfileSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()  # Define SerializerMethodField for company_name
    
    class Meta:
        model = User
        fields = ['id','name','email','address','company_id', 'company_name']

    def get_company_name(self, obj):
        company_id = obj.company_id
        if company_id:
            company = Companies.objects.filter(id=company_id).first()
            if company:
                return company.name
        return None  # Return None if company_id is not valid or company does not exist

class UpdateProfileSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(write_only=True, required=True)
    class Meta:
        model = User
        fields = ('email', 'name', 'address', 'id','company_id')
        extra_kwargs = {
            'id': {'required': True},
            'email': {'required': False},
        }

    def validate(self, attrs):
        email = attrs.get('email')
        company_id = attrs.get('company_id')
        # Extracting id from the request's data
        user_id = self.instance.id
        if email:
            try:
                # Use Django's EmailValidator to check if the email is valid
                EmailValidator()(email)
            except ValidationError:
                raise serializers.ValidationError(common["messages"]["INVALID_EMAIL_FORMAT"])
            
        if company_id:
            if not Companies.objects.filter(id=company_id).exists():
                raise serializers.ValidationError(common["messages"]["COMPANY_NOT_EXIST"])
            
        user = get_object_or_404(User, pk=user_id)
        if user:
            if 'name' in attrs:
                user.name = attrs['name']
            if 'email' in attrs:
                user.email = email
            if 'address' in attrs:
                user.address = attrs['address']
            if 'company_id' in attrs:
                user.company_id = attrs['company_id']
            user.updated_by_id = user_id
            user.save()
        else:
            raise serializers.ValidationError(common["messages"]["USER_NOT_EXIST"])
        
        return attrs

class UserDeleteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=True)

    def delete(self, request):
        user_id = self.validated_data['id']
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError(common["messages"]["USER_NOT_EXIST"])

        # Soft delete logic here
        user.deleted_at = timezone.now()
        user.deleted_by_id = request.user.id
        user.save()

class UserChangePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=16, style={'input_type':'password'}, write_only=True)
    password2 = serializers.CharField(max_length=16, style={'input_type':'password'}, write_only=True)
    

    def validate(self, attrs):
        password = attrs.get('password')
        password2 = attrs.get('password2')
        user = self.context.get('user')

        if password != password2:
            raise serializers.ValidationError(common["messages"]["PASSWORDS_NOT_MATCH"])
        user.set_password(password)
        user.save()
        return attrs
    
class SendPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    class Meta:
        fields = ['email']
    
    def validate(self,attrs):
        email = attrs.get('email')
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.id))
            token = PasswordResetTokenGenerator().make_token(user)
            link = os.environ.get('FRONTEND_URL') +'?token=' +uid +'/' + token
            url = os.environ.get('BACKEND_URL')
            #Send Email
            
            context = {
                    'link': link,
                    'name': user.name,
                    'url': url,
                }
            body = render_to_string('authentication/reset_password.html', context)

            data ={
                'subject': 'Reset Your Password',
                'body': body,
                'to_email': user.email
            }
            Util.send_email(data)
            return attrs
        else:
            raise serializers.ValidationError(common["messages"]["USER_NOT_REGISTERED"])
        
class UserPasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=16, style={'input_type':'password'}, write_only=True)
    password2 = serializers.CharField(max_length=16, style={'input_type':'password'}, write_only=True)
    class Meta:
        fields = ['password', 'password2']

    def validate(self, attrs):
        try:
            password = attrs.get('password')
            password2 = attrs.get('password2')
            uid = self.context.get('uid')
            token = self.context.get('token')

            if password != password2:
                raise serializers.ValidationError(common["messages"]["PASSWORDS_NOT_MATCH"])

            id = smart_str(urlsafe_base64_decode(uid))
            user = User.objects.get(id=id)
            
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise serializers.ValidationError(common["messages"]["INVALID_TOKEN"])
            
            user.set_password(password)
            user.save()
            return attrs
        
        except DjangoUnicodeDecodeError as identifier:
            PasswordResetTokenGenerator.check_token(user, token)
            raise serializers.ValidationError(common["messages"]["SESSION_EXPIRED"])
        
class UpdateUserProfileSerializer(serializers.ModelSerializer):
    company_id = serializers.IntegerField(write_only=True, required=True)
    class Meta:
        model = User
        fields = ('email', 'name', 'address', 'id','company_id')
        extra_kwargs = {
            'id': {'required': True},
            'email': {'required': False},
        }

    def validate(self, attrs):
        email = attrs.get('email') 
        company_id = attrs.get('company_id')
        # Extracting id from the request's data
        request_data = self.context['request'].data
        request_id = request_data.get('id')
        user_id = request_id if isinstance(request_id, int) else request_id[0] if request_id else None


        if email:
            try:
                # Use Django's EmailValidator to check if the email is valid
                EmailValidator()(email)
            except ValidationError:
                raise serializers.ValidationError(common["messages"]["INVALID_EMAIL_FORMAT"])
         
        if company_id:
            if not Companies.objects.filter(id=company_id).exists():
                raise serializers.ValidationError(common["messages"]["COMPANY_NOT_EXIST"])
            
        user = get_object_or_404(User, pk=user_id)
        if user:
            if 'name' in attrs:
                user.name = attrs['name']
            if 'email' in attrs:
                user.email = email
            if 'address' in attrs:
                user.address = attrs['address']
            if 'company_id' in attrs:
                user.company_id = attrs['company_id']
            user.updated_by_id = user_id
            user.save()
        else:
            raise serializers.ValidationError(common["messages"]["USER_NOT_EXIST"])
        
        return attrs

class UpdateProfileStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['is_active']

    def validate(self, attrs):
        user = self.instance  # Get the user instance
        is_active = attrs.get('is_active', user.is_active)  # Get the new status or use the existing one
        
        # Check if the status is already the same as the current one
        if is_active == user.is_active:
            raise serializers.ValidationError("Profile is already " + ("activated." if is_active else "deactivated."))

        return attrs

class UserListSerializer(serializers.ModelSerializer):
    company_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ['id','name','email','address','company_name','company_id','is_active']

    def get_company_name(self, obj):
        company_id = obj.company_id
        if company_id:
            company = Companies.objects.filter(id=company_id).first()
            if company:
                return company.name
        return None  # Return None if company_id is not valid or company does not exist