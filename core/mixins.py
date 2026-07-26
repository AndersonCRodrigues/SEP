from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import AccessMixin

class RoleRequiredMixin(AccessMixin):
    allowed_roles = []
    
    def dispatch(self,request,*args,**kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role in self.allowed_roles:
            return super().dispatch(request,*args,**kwargs)
        raise PermissionDenied("Vc ñ tem permissão pra acessar essa pag")