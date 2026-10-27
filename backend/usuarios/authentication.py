
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model


class EmailBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):
        Usuario = get_user_model()

        email = kwargs.get("email") or username

        if not email or not password:
            return None

        try:
            usuario = Usuario.objects.get(email__iexact=email.strip())
        except (Usuario.DoesNotExist, Usuario.MultipleObjectsReturned):
            Usuario().set_password(password)
            return None

        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario

        return None
