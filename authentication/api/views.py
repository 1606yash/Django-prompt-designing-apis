from rest_framework import status
from rest_framework.views import APIView
from authentication.backends.backends import CustomUserModelBackend
from django.contrib.auth.hashers import check_password
from authentication.models import User,Companies,BlackListedToken,IsTokenValid
from .serializers import CreateUserSerializer,UserChangePasswordSerializer, SendPasswordResetEmailSerializer,UserPasswordResetSerializer,UpdateProfileSerializer, UserDeleteSerializer,ProfileSerializer,UpdateUserProfileSerializer,UpdateProfileStatusSerializer,UserListSerializer
from authentication.api.renderers import UserRenderer
from rest_framework_simplejwt.tokens import RefreshToken
from messages import common
from django.utils import timezone
from helpers import send_success_response, send_failure_response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q


#generate token manually
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email  # Add custom claims
        # Add more custom claims if needed
        return token

# user registration 
class CreateUserView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    permission_classes = [IsTokenValid]
    allowed_methods = ['POST'] # allowed method post only

    def post(self, request, format=None):
        try:
            if not request.user.is_authenticated:  # Check if user is not authenticated
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
            
            if not request.user.is_staff:  # Check if user is not admin
                return send_failure_response(message=common["messages"]["USER_NOT_ADMIN"], code=status.HTTP_403_FORBIDDEN)
            
            if request.data.get('name') is None:
                return send_failure_response(message=common["messages"]["USER_NAME_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if len(request.data.get('name')) > 100:
                return send_failure_response(message=common["messages"]["USER_NAME_FIELD_LEN"], code=status.HTTP_400_BAD_REQUEST)
            
            if request.data.get('password') is None:
                return send_failure_response(message=common["messages"]["PASSWORD_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if request.data.get('password2') is None:
                return send_failure_response(message=common["messages"]["PASSWORD2_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if (len(request.data.get('password2'))>50) or  (len(request.data.get('password'))>50):
                return send_failure_response(message=common["messages"]["PWD_FIELD_LEN"], code=status.HTTP_400_BAD_REQUEST)
            
            if request.data.get('email') is None:
                return send_failure_response(message=common["messages"]["EMAIL_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if len(request.data.get('email')) > 100:
                return send_failure_response(message=common["messages"]["EMAIL_FIELD_LEN"], code=status.HTTP_400_BAD_REQUEST)
            
            if request.data.get('company_id') is None:
                return send_failure_response(message=common["messages"]["COMPANY_ID_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if request.data.get('address') is None:
                return send_failure_response(message=common["messages"]["ADDRESS_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if len(request.data.get('address')) > 250:
                return send_failure_response(message=common["messages"]["ADDR_FIELD_LEN"], code=status.HTTP_400_BAD_REQUEST)
            
            serializer = CreateUserSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                user = serializer.save()
                updated_user_data = {
                    'id': serializer.instance.id,
                    'name': serializer.instance.name,
                    'email': serializer.instance.email,
                    'address': serializer.instance.address,
                    'company_id': serializer.instance.company_id
                }
                # success response
                return send_success_response(data=updated_user_data,message=common["messages"]["USER_REGISTERED_SUCCESSFULLY"], code=status.HTTP_201_CREATED)
            else:
                error_messages = ""
                for field, errors in serializer.errors.items():
                    error_messages += f"{errors[0]}"  # Concatenate field name with error message
                    break  # Stop after processing the first error
                return send_failure_response(message=error_messages.strip(), code=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# user login 
class UserLoginView(APIView):
    renderer_classes = [UserRenderer]
    allowed_methods = ['POST'] # allowed method post only
    
    def post(self, request, *args, **kwargs):
        try:
            email = request.data.get('email')
            password = request.data.get('password')

            if not email:
                return send_failure_response(message=common["messages"]["EMAIL_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if not password:
                return send_failure_response(message=common["messages"]["PASSWORD_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            backend = CustomUserModelBackend()
            user = backend.authenticate(request, email=email, password=password)
            print('view user info',user)
            if user is not None:

                if not user.is_active:
                    return send_failure_response(message=common["messages"]["USER_ACC_INACTIVE"], code=status.HTTP_403_FORBIDDEN)
                
                if user.deleted_at is not None:
                    return send_failure_response(message=common["messages"]["USER_ALREADY_DELETED"], code=status.HTTP_403_FORBIDDEN)
            
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])

                company_name = None
                if user.company_id:
                    company = Companies.objects.filter(id=user.company_id).first()
                    company_name = company.name if company else None

                serializer = MyTokenObtainPairSerializer()
                token = serializer.get_token(user)
                refresh = RefreshToken.for_user(user)
                userData = {
                    'refresh_token': str(refresh),
                    'access_token': str(refresh.access_token),
                    'user': {
                        'email': user.email, 
                        'name': user.name,
                        'address': user.address, 
                        'is_admin': user.is_admin,
                        'company_id': user.company_id,
                        'company_name': company_name
                    }
                }
                return send_success_response(data=userData,message=common["messages"]["USER_LOGIN_SUCCESSFULLY"], code=status.HTTP_200_OK)
            else:
                return send_failure_response(message=common["messages"]["INVALID_EMAIL_PASSWORD"], code=status.HTTP_401_UNAUTHORIZED)
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LogoutView(APIView):
    renderer_classes = [UserRenderer]
    allowed_methods = ['POST'] # allowed method post only
    
    def post(self, request):
        if not request.user.is_authenticated:  # Check if user is not authenticated
            return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
        try:
            # Get the token from the authorization header
            authorization_header = request.META.get('HTTP_AUTHORIZATION', '')
            if not authorization_header.startswith('Bearer '):
                return send_failure_response(message=common["messages"]["INVALID_TOKEN"], code=status.HTTP_401_UNAUTHORIZED)
            
            token = authorization_header.split('Bearer ')[1]

            # Invalidate token only if it's valid
            if token:
                user_id = request.user.id

                # Check if token is already blacklisted
                if BlackListedToken.objects.filter(user_id=user_id, token=token).exists():
                    return send_failure_response(message=common["messages"]["TOKEN_EXPIRED"], code=status.HTTP_400_BAD_REQUEST)

                # Add token to blacklist
                BlackListedToken.objects.create(user_id=user_id, token=token)

            return send_success_response(data={}, message=common["messages"]["USER_LOGOUT_SUCCESSFULLY"], code=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return send_failure_response(message=common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# get profile details   
class ProfileView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    permission_classes = [IsTokenValid]
    allowed_methods = ['GET'] # allowed method get only

    def get(self,request, format=None):
        try:
            if not request.user.is_authenticated:  # Check if user is not authenticated
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
            serializer = ProfileSerializer(request.user)
            return send_success_response(data=serializer.data, message=common["messages"]["PROFILE_FETCHED_SUCCESSFULLY"], code=status.HTTP_200_OK) # success response
        
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# update user profile   
class UpdateUserProfileView(APIView):
    renderer_classes = [UserRenderer]
    permission_classes = [IsTokenValid]
    allowed_methods = ['PATCH']

    def patch(self, request, format=None):
        try:
            if not request.user.is_authenticated:  # Check if user is not authenticated
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
            
            if not request.user.is_staff:  # Check if user is not admin
                return send_failure_response(message=common["messages"]["USER_NOT_ADMIN"], code=status.HTTP_403_FORBIDDEN)
            
            user_id = request.data.get('id')
            company_id = request.data.get('company_id')
            
            if user_id is None:
                return send_failure_response(message=common["messages"]["USER_ID_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if company_id is None:
                return send_failure_response(message=common["messages"]["COMPANY_ID_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            try:
                user_instance = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return send_failure_response(message=common["messages"]["USER_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)
            
            # Check if user is not deleted before allowing update
            if user_instance.deleted_at is not None:
                return send_failure_response(message=common["messages"]["USER_NOT_UPDATED"], code=status.HTTP_403_FORBIDDEN)
            
            serializer = UpdateUserProfileSerializer(instance=user_instance, data=request.data, context={'request': request})
            
            if serializer.is_valid():
                serializer.save()
                company_name = None
                if serializer.instance.company_id:
                    company = Companies.objects.filter(id=serializer.instance.company_id).first()
                    company_name = company.name if company else None

                updated_user_data = {
                    'id': serializer.instance.id,
                    'name': serializer.instance.name,
                    'email': serializer.instance.email,
                    'address': serializer.instance.address,
                    'company_id': serializer.instance.company_id,
                    'company_name': company_name
                }
                return send_success_response(data=updated_user_data, message=common["messages"]["USER_UPDATED_SUCCESSFULLY"], code=status.HTTP_200_OK)
            else:
                error_messages = ""
                for field, errors in serializer.errors.items():
                    error_messages += f"{errors[0]}"  # Concatenate field name with error message
                    break  # Stop after processing the first error
                return send_failure_response(message=error_messages.strip(), code=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# delete user     
class DeleteUserView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    permission_classes = [IsTokenValid]
    allowed_methods = ['DELETE'] # allowed method delete only

    def delete(self, request, format=None):
        try:
            if not request.user.is_authenticated:  # Check if user is not authenticated
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
            
            if not request.user.is_staff:  # Check if user is not admin
                return send_failure_response(message=common["messages"]["USER_NOT_ADMIN"], code=status.HTTP_403_FORBIDDEN)
            
            user_id = request.data.get('id')
            # user_instance = get_object_or_404(User, pk=user_id)
            if user_id is None:
                return send_failure_response(message=common["messages"]["USER_ID_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            try:
                user_instance = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return send_failure_response(message=common["messages"]["USER_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)

            if user_instance.deleted_at is not None:
                return send_failure_response(message=common["messages"]["USER_ALREADY_DELETED"], code=status.HTTP_400_BAD_REQUEST)

            serializer = UserDeleteSerializer(data=request.data)
            if serializer.is_valid():   # if it doesn't go in if condition it raise an exception
                serializer.delete(request)
                # success response
                return send_success_response(data={}, message=common["messages"]["USER_DELETED_SUCCESSFULLY"], code=status.HTTP_200_OK)
            else:
                error_messages = ""
                for field, errors in serializer.errors.items():
                    error_messages += f"{errors[0]}"  # Concatenate field name with error message
                    break  # Stop after processing the first error
                return send_failure_response(message=error_messages.strip(), code=status.HTTP_400_BAD_REQUEST) # If serializer is not valid, return 400 Bad Request response
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# change password
class UserChangePasswordView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    permission_classes = [IsTokenValid]
    allowed_methods = ['POST'] # allowed method post only

    def post(self,request, format=None):
        try:
            if not request.user.is_authenticated:  # Check if user is not authenticated
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
            
            old_password = request.data.get('old_password')
            new_password = request.data.get('password')
            user = request.user
            if old_password is None or old_password == "":
                return send_failure_response(message=common["messages"]["OLD_PASSWORD_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if new_password is None or old_password == "":
                return send_failure_response(message=common["messages"]["PASSWORD_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if request.data.get('password2') is None or old_password == "":
                return send_failure_response(message=common["messages"]["PASSWORD2_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if not check_password(old_password, user.password):
                return send_failure_response(message=common["messages"]["INCORRECT_OLD_PASSWORD"], code=status.HTTP_400_BAD_REQUEST)
            
            if old_password == new_password:
                return send_failure_response(message=common["messages"]["NEW_PASSWORD_SAME_AS_OLD"], code=status.HTTP_400_BAD_REQUEST)
            
            serializer = UserChangePasswordSerializer(data=request.data, context={'user':user})
            if serializer.is_valid():   # if it doesn't go in if condition it raise an exception
                return send_success_response(data={}, message=common["messages"]["PASSWORD_CHANGED_SUCCESSFULLY"], code=status.HTTP_200_OK) # success response
            else:
                error_messages = ""
                for field, errors in serializer.errors.items():
                    error_messages += f"{errors[0]}"  # Concatenate field name with error message
                    break  # Stop after processing the first error
                return send_failure_response(message=error_messages.strip(), code=status.HTTP_400_BAD_REQUEST) # If serializer is not valid, return 400 Bad Request response
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# send password reset email
class SendPasswordResetEmailView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    allowed_methods = ['POST'] # allowed method post only
    
    def post(self, request, format=None):
        try:
            if request.data.get('email') is None:
                return send_failure_response(message=common["messages"]["EMAIL_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            serializer = SendPasswordResetEmailSerializer(data=request.data)
            if serializer.is_valid():   # if it doesn't go in if condition it raise an exception
                # success response
                return send_success_response(data={}, message=common["messages"]["PASSWORD_RESET_LINK_SUCCESSFULLY"], code=status.HTTP_200_OK)
            else:
                error_messages = ""
                for field, errors in serializer.errors.items():
                    error_messages += f"{errors[0]}"  # Concatenate field name with error message
                    break  # Stop after processing the first error
                return send_failure_response(message=error_messages.strip(), code=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# password reset
class UserPasswordResetView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    allowed_methods = ['POST'] # allowed method post only
    def post(self, request, uid, token, format=None):
        try:
            if request.data.get('password') is None:
                return send_failure_response(message=common["messages"]["PASSWORD_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if request.data.get('password2') is None:
                return send_failure_response(message=common["messages"]["PASSWORD2_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            serializer = UserPasswordResetSerializer(data=request.data, context={'uid':uid,'token': token})
            if serializer.is_valid():   # if it doesn't go in if condition it raise an exception
                return send_success_response(data={}, message=common["messages"]["PASSWORD_RESET_SUCCESSFULLY"], code=status.HTTP_200_OK)
            else:
                error_messages = ""
                for field, errors in serializer.errors.items():
                    error_messages += f"{errors[0]}"  # Concatenate field name with error message
                    break  # Stop after processing the first error
                return send_failure_response(message=error_messages.strip(), code=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# get user profile by id
class UserProfileView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    permission_classes = [IsTokenValid]
    allowed_methods = ['GET'] # allowed method get only

    def get(self,request, format=None):
        try:
            if not request.user.is_authenticated:  # Check if user is not authenticated
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
            
            if not request.user.is_staff:  # Check if user is not admin
                return send_failure_response(message=common["messages"]["USER_NOT_ADMIN"], code=status.HTTP_403_FORBIDDEN)
            
            user_id = request.data.get('id')
            if not user_id:
                return send_failure_response(message=common["messages"]["USER_ID_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            try:
                user_instance = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return send_failure_response(message=common["messages"]["USER_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)
            serializer = ProfileSerializer(user_instance)
            return send_success_response(data=serializer.data, message=common["messages"]["PROFILE_FETCHED_SUCCESSFULLY"], code=status.HTTP_200_OK) # success response
        
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# update profile for user role
class UpdateProfileView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    permission_classes = [IsTokenValid]
    allowed_methods = ['PATCH'] # allowed method patch only

    def patch(self, request, format=None):
        try:
            if not request.user.is_authenticated:  # Check if user is not authenticated
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
            serializer = UpdateProfileSerializer(instance=request.user, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():   # if it doesn't go in if condition it raise an exception
                serializer.save()

                company_name = None
                if serializer.instance.company_id:
                    company = Companies.objects.filter(id=serializer.instance.company_id).first()
                    company_name = company.name if company else None

                updated_user_data = {
                    'id': serializer.instance.id,
                    'name': serializer.instance.name,
                    'email': serializer.instance.email,
                    'address': serializer.instance.address,
                    'company_id': serializer.instance.company_id,
                    'company_name': company_name
                }
                # success response
                return send_success_response(data=updated_user_data, message=common["messages"]["PROFILE_UPDATED_SUCCESSFULLY"], code=status.HTTP_200_OK) # success response
            else:
                error_messages = ""
                for field, errors in serializer.errors.items():
                    error_messages += f"{errors[0]}"  # Concatenate field name with error message
                    break  # Stop after processing the first error
                return send_failure_response(message=error_messages.strip(), code=status.HTTP_400_BAD_REQUEST) # If serializer is not valid, return 400 Bad Request response
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# update user status       
class UpdateUserStatusView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    permission_classes = [IsTokenValid]
    allowed_methods = ['POST'] # allowed method post only
        
    def post(self, request, format=None):
        try:
            if not request.user.is_authenticated:  # Check if user is not authenticated
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
            
            if not request.user.is_staff:  # Check if user is not admin
                return send_failure_response(message=common["messages"]["USER_NOT_ADMIN"], code=status.HTTP_403_FORBIDDEN)
            
            user_id = request.data.get('id')
            is_active = request.data.get('is_active')

            if user_id is None:
                return send_failure_response(message=common["messages"]["USER_ID_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)

            if is_active is None:
                return send_failure_response(message=common["messages"]["STATUS_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            try:
                user_instance = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return send_failure_response(message=common["messages"]["USER_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)

            if user_instance.deleted_at is not None:
                return send_failure_response(message=common["messages"]["USER_ALREADY_DELETED"], code=status.HTTP_400_BAD_REQUEST)

            serializer = UpdateProfileStatusSerializer(user_instance, data=request.data)  # Pass instance here
            if serializer.is_valid():   # if it doesn't go in if condition it raise an exception
                serializer.save()
                # success response
                if serializer.instance.is_active:
                    return send_success_response(data={}, message=common["messages"]["USER_PROFILE_ACTIVATED_SUCCESSFULLY"], code=status.HTTP_200_OK)
                else:
                    return send_success_response(data={}, message=common["messages"]["USER_PROFILE_DEACTIVATED_SUCCESSFULLY"], code=status.HTTP_200_OK)
            else:
                error_messages = ""
                for field, errors in serializer.errors.items():
                    error_messages += f"{errors[0]}"  # Concatenate field name with error message
                    break  # Stop after processing the first error
                return send_failure_response(message=error_messages.strip(), code=status.HTTP_400_BAD_REQUEST) # If serializer is not valid, return 400 Bad Request response
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)

# user listing
class UserListView(APIView):
    renderer_classes = [UserRenderer]  # Assuming UserRenderer is defined somewhere
    permission_classes = [IsTokenValid]
    allowed_methods = ['GET']  # Allowed method get only

    def get(self, request, format=None):
        try:
            if not request.user.is_authenticated:
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)

            if not request.user.is_staff:
                return send_failure_response(message=common["messages"]["USER_NOT_ADMIN"], code=status.HTTP_403_FORBIDDEN)

            users = User.objects.filter(is_admin=False)

            # Check if company_id is provided in the query parameters
            page_number = request.GET.get('page', 1)
            per_page = request.GET.get('per_page', 10)
            search_query = request.GET.get('search', '')
            company_id = request.GET.get('company_id')  # Corrected to request.GET.get
            sortField = request.GET.get('column', 'created_at')  
            sortOrder = request.GET.get('direction', '-') 
            sortOrder = ""  if (sortOrder == "asc" or sortOrder == "ASC") else "-"
 
            if company_id:
                users = users.filter(company_id=company_id)  # Assuming company_id is a field in your User model

            if search_query:
                # users = users.filter(name__icontains=search_query)  # Assuming you want to search by name
                users = users.filter(Q(name__icontains=search_query) | Q(email__icontains=search_query))

            sort_by = sortOrder+sortField
            users = users.order_by(sort_by)
            paginator = Paginator(users, per_page)
            
            try:
                users_paginated = paginator.page(int(page_number))
            except PageNotAnInteger:
                users_paginated = paginator.page(1)
            except EmptyPage:
                users_paginated = paginator.page(paginator.num_pages)

            serializer = UserListSerializer(users_paginated, many=True)
            
            context = {
                'user_data': serializer.data,
                'page': users_paginated.number,
                'pages': paginator.num_pages,
                'per_page': per_page,
                'total': paginator.count,
            }

            return send_success_response(context, message="User data fetched successfully.")
        
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CommonListView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    permission_classes = [IsTokenValid]
    allowed_methods = ['GET'] # allowed method get only

    def get(self, request, format=None):
        try:
            companies = Companies.objects.all().order_by('name')
            serialized_companies = [{'company_id': company.id,
                                    'company_name': company.name,
                                    } for company in companies]
            return send_success_response(data={'companies':serialized_companies}, message=common["messages"]["COMMON_LIST_FETCHED_SUCCESSFULLY"], code=status.HTTP_200_OK)
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
class ChangeUserPasswordView(APIView):
    renderer_classes = [UserRenderer]  # it will give errors in error dictionary
    permission_classes = [IsTokenValid]
    allowed_methods = ['POST'] # allowed method post only

    def post(self,request, format=None):
        try:
            if not request.user.is_authenticated:  # Check if user is not authenticated
                return send_failure_response(message=common["messages"]["AUTHENTICATION_ERROR"], code=status.HTTP_401_UNAUTHORIZED)
            
            request_data = request.data
            user_id = request_data.get('user_id')
            if request_data.get('user_id') is None:
                return send_failure_response(message=common["messages"]["UID_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if request_data.get('password') is None:
                return send_failure_response(message=common["messages"]["PASSWORD_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            if request_data.get('password2') is None:
                return send_failure_response(message=common["messages"]["PASSWORD2_REQUIRED"], code=status.HTTP_400_BAD_REQUEST)
            
            try:
                user_instance = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return send_failure_response(message=common["messages"]["USER_NOT_FOUND"], code=status.HTTP_404_NOT_FOUND)
            
            serializer = UserChangePasswordSerializer(data=request_data, context={'user':user_instance})
            if serializer.is_valid():   # if it doesn't go in if condition it raise an exception
                return send_success_response(data={}, message=common["messages"]["PASSWORD_CHANGED_SUCCESSFULLY"], code=status.HTTP_200_OK) # success response
            else:
                error_messages = ""
                for field, errors in serializer.errors.items():
                    error_messages += f"{errors[0]}"  # Concatenate field name with error message
                    break  # Stop after processing the first error
                return send_failure_response(message=error_messages.strip(), code=status.HTTP_400_BAD_REQUEST) # If serializer is not valid, return 400 Bad Request response
            
        except Exception as e:
            # Handle the exception here
            # You can log the exception for debugging purposes
            print("An exception occurred:", str(e))
            # You can also return a custom error response
            return send_failure_response(message= common["messages"]["SOMETHING_WENT_WRONG"], code=status.HTTP_500_INTERNAL_SERVER_ERROR)

