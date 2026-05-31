"""
Custom exception handler for DRF.
Provides consistent error response format across all API endpoints.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns errors in a consistent format:
    {
        "error": "ERROR_CODE",
        "message": "Human-readable error message",
        "status_code": 400
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Customize the response data
        custom_response_data = {
            'error': exc.__class__.__name__.upper(),
            'message': str(exc),
            'status_code': response.status_code
        }
        
        # If there are field-specific errors, include them
        if isinstance(response.data, dict):
            if 'detail' in response.data:
                custom_response_data['message'] = response.data['detail']
            else:
                custom_response_data['details'] = response.data
        
        response.data = custom_response_data

    return response
