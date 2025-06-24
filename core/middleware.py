from django.utils import timezone
from .models import AuditLog, DataAccessLog

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request
        response = self.get_response(request)

        # Log user activity if user is authenticated
        if request.user.is_authenticated:
            # Determine action type based on the request path
            action_type = self._get_action_type(request)
            if action_type:
                AuditLog.objects.create(
                    user=request.user,
                    action_type=action_type,
                    action_detail=f"{request.method} {request.path}",
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    status='success' if 200 <= response.status_code < 400 else 'failed'
                )

        return response

    def _get_action_type(self, request):
        """Map request paths to audit log action types"""
        path = request.path.lower()
        method = request.method

        if 'login' in path:
            return 'login'
        elif 'logout' in path:
            return 'logout'
        elif 'profile/update' in path:
            return 'profile_update'
        elif 'change-password' in path:
            return 'password_change'
        elif 'notifications' in path:
            return 'settings_change'
        elif 'export-data' in path:
            return 'data_export'
        elif 'request-deletion' in path:
            return 'deletion_request'
        return None

    def _get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

class DataAccessLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Log data access for authenticated users
        if request.user.is_authenticated and hasattr(request, 'data_access'):
            DataAccessLog.objects.create(
                user=request.user,
                operation_type=request.data_access.get('operation_type'),
                data_model=request.data_access.get('data_model'),
                record_id=request.data_access.get('record_id'),
                ip_address=self._get_client_ip(request),
                accessed_fields=request.data_access.get('accessed_fields', {})
            )

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR') 