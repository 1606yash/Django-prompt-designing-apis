from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from authentication.models import User, Companies

class UserModelAdminForm(forms.ModelForm):
    company = forms.ModelChoiceField(queryset=Companies.objects.all(), empty_label='-- Select Company --',required=False)

    class Meta:
        model = User
        fields = '__all__'

class UserModelAdmin(BaseUserAdmin):
    form = UserModelAdminForm  # Use the custom form
    list_display = ('id', 'name', 'email', 'address', 'is_active', 'is_staff', 'company_name')
    list_filter = ('is_admin',)
    fieldsets = (
        ('Personal info', {'fields': ('name','email', 'address', 'company')}),  # Include 'company' in the fieldsets
        ('Permissions', {'fields': ('is_admin', 'is_active')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'name', 'password1', 'password2', 'company'),
            },
        ),
    )
    search_fields = ('email',)
    ordering = ('email', 'id',)
    filter_horizontal = ()

    def company_name(self, obj):
        return obj.company.name if obj.company else None

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('company')  # Ensure company is fetched in a single query
        return queryset

# Now register the new UserModelAdmin...
admin.site.register(User, UserModelAdmin)

class CompanyModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')  # Specify fields to display in the list view
    list_filter = ('id',)  # Specify fields for filtering
    fieldsets = (
        ('Organization Name', {'fields': ('name',)}),
    )
    search_fields = ('name',)
    ordering = ('name', 'id',)
    filter_horizontal = ()

    def custom_name(self, obj):
        return obj.name  # Return the desired custom name for the 'name' field

    custom_name.short_description = 'Companies'  # Set the display name for the custom field

admin.site.register(Companies, CompanyModelAdmin)  # Register your model with the model admin class
