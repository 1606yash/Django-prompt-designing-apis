from rest_framework import renderers
import json

class UserRenderer(renderers.JSONRenderer):
    charset = 'utf-8'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response_data = {}
        if 'ErrorDetail' in str(data):
            response_data['message'] = data['messages'][0]['message']
            response_data['data'] = ''
        else:
            response_data['message'] = ''
            response_data['data'] = data

        # Add status code to the response data
        response_data['success_code'] = renderer_context['response'].status_code
        response_data['success']= False
        return json.dumps(response_data)
