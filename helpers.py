from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse

# Send Success Response
def create_success_response(data = [], status_code = status.HTTP_200_OK, message = ''):
    return Response({'data': data,  'success': True, 'status': status_code, 'message': message})
 
# Send Error Response
def create_error_response(data = [], status_code = status.HTTP_422_UNPROCESSABLE_ENTITY, message = ''):
    return Response({'data': data, 'success': False, 'status': status_code, 'message': message})


def send_success_response(data=None, message='', code=status.HTTP_200_OK):
    response = {
        'success': True,
        'success_code': code,
        'message': message if message else None,
        'data': data,
    }

    return JsonResponse(response, status=code)

def send_failure_response(data=[], message='Something went wrong.', code=status.HTTP_422_UNPROCESSABLE_ENTITY):
    response = {
        'success': False,
        'success_code': code,
        'message': message,
        'data': data,
    }

    return JsonResponse(response, status=code)