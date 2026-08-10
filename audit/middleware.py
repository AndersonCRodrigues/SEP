import threading

_state = threading.local()


def get_current_user():
    return getattr(_state, "user", None)


def get_current_ip():
    return getattr(_state, "ip", None)


def client_ip(request):
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        _state.user = user if user is not None and user.is_authenticated else None
        _state.ip = client_ip(request)
        try:
            return self.get_response(request)
        finally:
            _state.user = None
            _state.ip = None
