from datetime import date, datetime, time, timedelta

from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated

from .models import Pago
from .serializers import PagoSerializer, PagoDuenaSerializer

from io import BytesIO

from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill


class EsDuena(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.rol == "DUENA"
        )



class HistorialPagosView(generics.ListAPIView):
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user

        pagos = Pago.objects.select_related("socio")

        if usuario.rol == "SOCIO":
            pagos = pagos.filter(socio=usuario)
        elif usuario.rol != "DUENA":
            pagos = pagos.none()

        pagos = pagos.order_by("-fecha_pago")

        fecha_inicio = self.request.query_params.get("fecha_inicio")
        fecha_fin = self.request.query_params.get("fecha_fin")

        def convertir_fecha(valor):
            try:
                return date.fromisoformat(valor)
            except ValueError:
                raise ValidationError({
                    "fecha": "La fecha debe tener el formato AAAA-MM-DD."
                })

        if fecha_inicio:
            inicio = convertir_fecha(fecha_inicio)
        else:
            inicio = None

        if fecha_fin:
            fin = convertir_fecha(fecha_fin)
        else:
            fin = None

        if inicio and fin and inicio > fin:
            raise ValidationError({
                "fecha": "La fecha de inicio no puede ser posterior a la fecha de término."
            })

        if inicio:
            inicio_datetime = timezone.make_aware(
                datetime.combine(inicio, time.min),
                timezone.get_current_timezone()
            )
            pagos = pagos.filter(fecha_pago__gte=inicio_datetime)

        if fin:
            fin_exclusivo = timezone.make_aware(
                datetime.combine(fin + timedelta(days=1), time.min),
                timezone.get_current_timezone()
            )
            pagos = pagos.filter(fecha_pago__lt=fin_exclusivo)

        return pagos


class ExportarPagosExcelView(HistorialPagosView):
    permission_classes = [IsAuthenticated, EsDuena]

    def get(self, request, *args, **kwargs):
        pagos = self.get_queryset()

        libro = Workbook()
        hoja = libro.active
        hoja.title = "Historial de pagos"

        encabezados = [
            "ID",
            "Socio",
            "Tipo de pago",
            "Método de pago",
            "Monto (CLP)",
            "Estado",
            "Fecha de pago",
        ]

        hoja.append(encabezados)

        for celda in hoja[1]:
            celda.font = Font(color="FFFFFF", bold=True)
            celda.fill = PatternFill(
                start_color="198754",
                end_color="198754",
                fill_type="solid"
            )

        for pago in pagos:
            fecha_local = timezone.localtime(pago.fecha_pago)

            hoja.append([
                pago.id,
                pago.socio.get_full_name() or pago.socio.username,
                pago.get_tipo_pago_display(),
                pago.get_metodo_pago_display(),
                pago.monto,
                pago.get_estado_display(),
                fecha_local.strftime("%d-%m-%Y %H:%M"),
            ])

        anchos = {
            "A": 10,
            "B": 30,
            "C": 22,
            "D": 25,
            "E": 18,
            "F": 16,
            "G": 22,
        }

        for columna, ancho in anchos.items():
            hoja.column_dimensions[columna].width = ancho

        hoja.freeze_panes = "A2"
        hoja.auto_filter.ref = hoja.dimensions

        for fila in hoja.iter_rows(min_row=2):
            fila[4].number_format = '"$"#,##0'

        archivo = BytesIO()
        libro.save(archivo)
        archivo.seek(0)

        respuesta = HttpResponse(
            archivo.getvalue(),
            content_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

        respuesta["Content-Disposition"] = (
            'attachment; filename="historial_pagos_powerfit.xlsx"'
        )

        return respuesta 

class SoloDuena(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.rol == "DUENA"
        )


class PagosDuenaView(generics.ListAPIView):
    permission_classes = [SoloDuena]
    serializer_class = PagoDuenaSerializer

    def get_queryset(self):
        return (
            Pago.objects
            .select_related("socio")
            .order_by("-fecha_pago")
        )


class DocumentoPagoDuenaView(APIView):
    permission_classes = [IsAuthenticated, EsDuena]

    def get(self, request, pago_id):
        pago = get_object_or_404(Pago, id=pago_id)

        if pago.metodo_pago == Pago.MetodoPago.TRANSFERENCIA:
            documento = pago.comprobante
        else:
            documento = pago.boleta

        if not documento:
            return HttpResponse(
                "Este pago no tiene un documento adjunto.",
                status=404
            )

        try:
            archivo = documento.open("rb")
        except (FileNotFoundError, OSError):
            return HttpResponse(
                "No se encontró el archivo solicitado.",
                status=404
            )

        nombre_archivo = documento.name.rsplit("/", 1)[-1]

        return FileResponse(
            archivo,
            as_attachment=False,
            filename=nombre_archivo
        )


class BoletaPagoSocioView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pago_id):
        if request.user.rol != "SOCIO":
            return HttpResponse(
                "No tienes permiso para consultar esta boleta.",
                status=403
            )

        pago = get_object_or_404(
            Pago,
            id=pago_id,
            socio=request.user
        )

        if pago.estado != "APROBADO":
            return HttpResponse(
                "La boleta no está disponible para este pago.",
                status=404
            )

        if not pago.boleta:
            return HttpResponse(
                "Este pago no tiene una boleta adjunta.",
                status=404
            )

        try:
            archivo = pago.boleta.open("rb")
        except (FileNotFoundError, OSError):
            return HttpResponse(
                "No se encontró el archivo solicitado.",
                status=404
            )

        nombre_archivo = pago.boleta.name.rsplit("/", 1)[-1]

        return FileResponse(
            archivo,
            as_attachment=False,
            filename=nombre_archivo
        )
