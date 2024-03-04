from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

UserModel = get_user_model()

class CustomUserModelBackend(ModelBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = UserModel.objects.get(email=email)
        except UserModel.DoesNotExist:
            # User not found, return None
            return None

        if user.check_password(password):
            # Password matches and user is active, return the user
            return user
        else:
            # Either password doesn't match return None
            return None

