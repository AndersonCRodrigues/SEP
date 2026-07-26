from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

UserModel = get_user_model()

class EmailOUMatricula(ModelBackend):
    def authenticate(self, request, username = None, password = None, **kwargs):
        if username is None:
            return None
        
        try:
            user = UserModel.objects.get(
                Q(email__iexact=username) | Q(matricula__iexact=username)
                
            )  
        except UserModel.DoesNotExist:
            return None
        
        except UserModel.MultipleObjectsReturned:
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None