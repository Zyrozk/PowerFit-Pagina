
from rest_framework.permissions import BasePermission


class EsDuenaParaEnrolamientoFacial(BasePermission):
    message = (
        "Solo la dueña de PowerFit Copiapó puede "
        "realizar el enrolamiento facial de los socios."
    )

    def has_permission(self, request, view):
        usuario = request.user

        return (
            usuario.is_authenticated
            and usuario.is_active
            and usuario.rol == "DUENA"
        )
