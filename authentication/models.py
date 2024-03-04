from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
from django.utils import timezone
from django.conf import settings

class SoftDelete(models.Model):
    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='%(class)s_deleted_by', null=True, blank=True)

    def soft_delete(self, user):
        self.deleted_at = timezone.now()  # Set the deleted_at timestamp
        self.deleted_by = user  # Set the user who performed the deletion
        self.save()

    def restore(self):
        self.deleted_at = None  # Reset the deleted_at timestamp
        self.deleted_by = None  # Reset the deleted_by user
        self.save()

    class Meta:
        abstract = True

class Companies(SoftDelete,models.Model):
    name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Company'  # Singular name for the model in the admin interface
        verbose_name_plural = 'Companies'  # Plural name for the model in the admin interface
        db_table = 'companies'

    def __str__(self):
        return self.name

        
class UserManager(BaseUserManager):
    def create_user(self, email, name,address=None, password=None,company_id=None,created_by=None):
        """
        Creates and saves a User with the given email, name and password.
        """
        if not email:
            raise ValueError("Users must have an email address")

        user = self.model(
            email=self.normalize_email(email),
            name=name,
            address=address,
            company_id=company_id,
            created_by=created_by
        )

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None):
        """
        Creates and saves a superuser with the given email, name and password.
        """
        user = self.create_user(
            email,
            password=password,
            name=name,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser,SoftDelete):
    company = models.ForeignKey(Companies,on_delete=models.CASCADE,related_name='company', null=True, blank=True)
    email = models.EmailField(max_length=255,unique=True,verbose_name='Email')
    name = models.CharField(max_length=255, blank=True)
    address = models.TextField(blank=True, null=True)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    created_by = models.ForeignKey('self', on_delete=models.CASCADE, related_name='created_by_user', null=True, blank=True)
    updated_by = models.ForeignKey('self', on_delete=models.CASCADE, related_name='updated_by_user', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'  # Specify the desired table name

    def __str__(self):
        return self.email
    
    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        return self.is_admin
    
    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        return True
    
    @property
    def is_staff(self):
        "Is the user a member of staff?"
        return self.is_admin
    

# Create your models here.
class Template(SoftDelete, models.Model):
    label = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)  
    system_promt_acron_analytic_service = models.TextField(null=True, default=None)
    system_promt_acron_safety_service = models.TextField(null=True, default=None)
    system_promt_acron_srs = models.TextField(null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_templates', null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_templates', null=True, blank=True)

    def __str__(self):
        return self.label
    
    class Meta:
        db_table = "templates"

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()
                
        # Delete associated questions

    def get_company(self):
        return self.company    

class Question(SoftDelete, models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    question_text = models.TextField()
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_questions', null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_questions', null=True, blank=True)
    

    def __str__(self):
        return self.question_text
    
    class Meta:
        db_table = "questions"

class UserFavTemplates(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fav_templates')
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_user_fav_templates', null=True, blank=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='updated_user_fav_templates', null=True, blank=True)
    
    class Meta:
        db_table = 'user_fav_templates'




