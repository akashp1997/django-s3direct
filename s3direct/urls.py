from django.urls import re_path
from s3direct import views


urlpatterns = [
    re_path('^get_upload_params/', views.get_upload_params, name='s3direct'),
    re_path('^get_aws_v4_signature/', views.generate_aws_v4_signature, name='s3direct-signing'),
]
