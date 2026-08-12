from functools import wraps
from django.http import HttpResponseForbidden


def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden("Vc precisa estar logado")
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("Vc ñ tem permissão pra essa página")

        return _wrapped_view

    return decorator
