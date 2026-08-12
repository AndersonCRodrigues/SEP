import threading

_thread_local = threading.local()

def get_current_user():
    return getattr(_thread_local, "user", None)

def get_current_ip():
    return getattr(_thread_local, "ip", None)

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        
        if user and user.is_authenticated:
            _thread_local.user = request.user
        else:
            _thread_local.user = None
            
        _thread_local.ip = request.META.get("REMOTE_ADDR")

        try:
            response = self.get_response(request)
        finally:
            _thread_local.user = None
            _thread_local.ip = None

        return response
