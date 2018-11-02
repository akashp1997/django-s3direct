import boto3

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from .utils import get_s3direct_destinations, get_key


@csrf_protect
@require_POST
def get_upload_params(request):
    """Authorises user and validates given file properties."""
    file_name = request.POST['name']
    file_type = request.POST['type']
    file_size = int(request.POST['size'])
    dest = get_s3direct_destinations().get(request.POST['dest'])
    if not dest:
        return JsonResponse({'error': 'File destination does not exist.'},
                                    status=404)

    # Validate request and destination config:
    allowed = dest.get('allowed')
    auth = dest.get('auth')
    key = dest.get('key')
    content_length_range = dest.get('content_length_range')

    if auth and not auth(request.user):
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    if (allowed and file_type not in allowed) and allowed != '*':
        return JsonResponse({'error': 'Invalid file type (%s).' % file_type},
                                      status=400)

    if content_length_range and not content_length_range[0] <= file_size <= content_length_range[1]:
        return JsonResponse(
            {'error': 'Invalid file size (must be between %s and %s bytes).' % content_length_range},
            status=400)

    # Generate object key
    if not key:
        return JsonResponse({'error': 'Missing destination path.'},
                                       status=500)
    else:
        object_key = get_key(key, file_name, dest)

    bucket = dest.get('bucket') or settings.AWS_STORAGE_BUCKET_NAME

    region = dest.get('region') or getattr(settings, 'S3DIRECT_REGION', None) or 'us-east-1'

    secret_access_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)
    access_key_id = getattr(settings, 'AWS_ACCESS_KEY_ID', None)


    s3 = boto3.client('s3',
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region
        )

    # AWS credentials are not required for publicly-writable buckets
    fields = {
        'cache_control': dest.get('cache_control'),
        'content_disposition': dest.get('content_disposition'),
        'server_side_encryption': dest.get('server_side_encryption'),
        'acl': dest.get('acl') or 'public-read',
    }
    upload_data = s3.generate_presigned_post(
        Bucket=bucket,
        Key=object_key,
        Fields=fields,
        )
    return JsonResponse(upload_data)


"""@csrf_protect
@require_POST
def generate_aws_v4_signature(request):
    message = unquote(request.POST['to_sign'])
    signing_date = datetime.strptime(request.POST['datetime'], '%Y%m%dT%H%M%SZ')
    signing_key = get_aws_v4_signing_key(settings.AWS_SECRET_ACCESS_KEY, signing_date, settings.S3DIRECT_REGION, 's3')
    signature = get_aws_v4_signature(signing_key, message)
    return HttpResponse(signature)
"""
