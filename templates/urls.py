# templates/urls.py
from django.urls import path
from .views import template_list, template_update, template_detail, template_list_user, user_favourite_template, template_delete, template_update_status, generate_chatgpt_output, generate_chatgpt_output_helper
# from channels.routing import ProtocolTypeRouter, URLRouter


urlpatterns = [
    path('templates/', template_list, name='template-list'),
    path('templates-update/', template_update, name='template-update'),
    path('templates-delete/<int:template_id>', template_delete, name='template-delete'),
    path('templates-detail/<int:template_id>/', template_detail, name='template-detail'),
    path('user-templates/', template_list_user, name='user-template'),
    path('mark-template/', user_favourite_template, name='mark-template'),
    path('use-template/<int:template_id>/', template_detail, name='use-template'),
    path('change-template-status/', template_update_status, name='update-status-template'),
    path('generate-output/', generate_chatgpt_output, name='generate-chatgpt-output'),
    path('generate-output-helper/', generate_chatgpt_output_helper, name='generate-chatgpt-output-helper'),
]
