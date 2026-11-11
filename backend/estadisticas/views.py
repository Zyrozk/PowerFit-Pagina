
from calendar import monthrange
from datetime import date, datetime, time, timedelta

from django.db.models import Count
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from clases.models import Clase
from membresias.models import Membresia, Reserva


def restar_meses(fecha, cantidad):
    total = fecha.year * 12 + fecha.month - 1 - cantidad
    anio, mes_cero = divmod(total, 12)
    mes = mes_cero + 1
    dia = min(fecha.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def obtener_inicio_periodo(periodo, hoy):
    if periodo == "semana":
        return hoy - timedelta(days=hoy.weekday())

    if periodo == "mes":
        return hoy.replace(day=1)

    if periodo == "3_meses":
        return restar_meses(hoy, 3)

    if periodo == "6_meses":
        return restar_meses(hoy, 6)

    if periodo == "anio":
        return restar_meses(hoy, 12)

    return None


def construir_grafico(inicio, hoy, periodo, asistencias):
    fechas = [item["clase__fecha"] for item in asistencias]

    if periodo == "semana":
        puntos = []
        for desplazamiento in range((hoy - inicio).days + 1):
            dia = inicio + timedelta(days=desplazamiento)
            puntos.append({
                "etiqueta": dia.strftime("%d/%m"),
                "valor": fechas.count(dia),
            })
        return puntos

    if periodo == "mes":
        puntos = []
        comienzo = inicio
        numero = 1

        while comienzo <= hoy:
            fin = min(comienzo + timedelta(days=6), hoy)
            puntos.append({
                "etiqueta": f"Sem {numero}",
                "valor": sum(comienzo <= fecha <= fin for fecha in fechas),
            })
            comienzo = fin + timedelta(days=1)
            numero += 1

        return puntos

    puntos = []
    cursor = inicio.replace(day=1)

    while cursor <= hoy:
        ultimo_dia = monthrange(cursor.year, cursor.month)[1]
        fin_mes = cursor.replace(day=ultimo_dia)
        desde = max(cursor, inicio)
        hasta = min(fin_mes, hoy)

        puntos.append({
            "etiqueta": cursor.strftime("%m/%Y"),
            "valor": sum(desde <= fecha <= hasta for fecha in fechas),
        })

        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    return puntos


class EstadisticasDuenaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, "rol", None) != "DUENA":
            return Response(
                {"detail": "No tienes permiso para consultar estas estadísticas."},
                status=403,
            )

        periodo = request.query_params.get("periodo", "mes")
        hoy = timezone.localdate()
        inicio = obtener_inicio_periodo(periodo, hoy)

        if inicio is None:
            return Response(
                {"detail": "El período seleccionado no es válido."},
                status=400,
            )

        ahora = timezone.localtime()
        hora_actual = ahora.time().replace(tzinfo=None)

        reservas_asistidas = Reserva.objects.filter(
            estado=Reserva.Estado.CONFIRMADA,
            asistencia=Reserva.Asistencia.ASISTIO,
            clase__fecha__range=(inicio, hoy),
        )

        asistencias_por_fecha = list(
            reservas_asistidas.values("clase__fecha")
        )

        socios_activos = (
            Membresia.objects.filter(
                estado=Membresia.Estado.ACTIVA,
                fecha_vencimiento__gt=hoy,
            )
            .values("socio_id")
            .distinct()
            .count()
        )

        clases_realizadas = (
            Clase.objects.filter(
                fecha__range=(inicio, hoy),
                activa=True,
            )
            .filter(
                fecha__lt=hoy
            )
            .count()
        )

        clases_realizadas += Clase.objects.filter(
            fecha=hoy,
            hora_fin__lte=hora_actual,
            activa=True,
        ).count()

        membresias_nuevas = Membresia.objects.filter(
            fecha_aprobacion__date__range=(inicio, hoy),
            estado=Membresia.Estado.ACTIVA,
        ).count()

        ranking = (
            reservas_asistidas
            .values("clase__tipo")
            .annotate(asistencias=Count("id"))
            .order_by("-asistencias", "clase__tipo")
        )

        nombres_clases = dict(Clase.Tipo.choices)

        clases_mayor_asistencia = [
            {
                "nombre": nombres_clases.get(
                    item["clase__tipo"],
                    item["clase__tipo"],
                ),
                "asistencias": item["asistencias"],
            }
            for item in ranking
        ]

        return Response({
            "periodo": periodo,
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": hoy.isoformat(),
            "asistencias": reservas_asistidas.count(),
            "socios_activos": socios_activos,
            "clases_realizadas": clases_realizadas,
            "membresias_nuevas": membresias_nuevas,
            "grafico_asistencias": construir_grafico(
                inicio,
                hoy,
                periodo,
                asistencias_por_fecha,
            ),
            "clases_mayor_asistencia": clases_mayor_asistencia,
        })
