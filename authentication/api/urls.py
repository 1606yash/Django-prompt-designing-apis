from django.urls import path
from .views import CreateUserView, UserLoginView, ProfileView, UserChangePasswordView, SendPasswordResetEmailView,UserPasswordResetView, UpdateUserProfileView,DeleteUserView,UserProfileView,UpdateProfileView,UpdateUserStatusView,UserListView,CommonListView, ChangeUserPasswordView,LogoutView
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView,TokenBlacklistView


urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('update-profile/', UpdateProfileView.as_view(), name='update-profile'),

    path('add-user/', CreateUserView.as_view(), name='add-user'),
    path('get-user-profile/', UserProfileView.as_view(), name='user-profile'),
    path('update-user-profile/', UpdateUserProfileView.as_view(), name='update-user-profile'),
    path('delete-user/', DeleteUserView.as_view(), name='delete-user'),
    path('update-user-profile-status/', UpdateUserStatusView.as_view(), name='update-user-profile-status'),
    path('get-users-list/', UserListView.as_view(), name='get-users-list'),

    path('change-password/', UserChangePasswordView.as_view(), name='change-password'),
    path('send-reset-password-email/', SendPasswordResetEmailView.as_view(), name='send_reset_password_email'),
    path('reset-password/<uid>/<token>/', UserPasswordResetView.as_view(), name='reset-password'),

    path('get-app-config/', CommonListView.as_view(), name='get-app-config'),
    path('logout/', LogoutView.as_view(), name='logout'),
        
    path('change-user-password/', ChangeUserPasswordView.as_view(), name='change-user-password'),
    
]
