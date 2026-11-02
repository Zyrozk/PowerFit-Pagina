from datetime import datetime
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from clases.models import Clase
from pagos.models import Pago
from .models import Membresia, Reserva, sumar_mes
from .serializers import MembresiaSerializer, ReservaSerializer
from django.core.files.images import get_image_dimensions
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from pathlib import Path
from PIL import Image, UnidentifiedImageError


class SoloDuena(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol == 'DUENA'


def verificar_socio(user):
    if user.rol != 'SOCIO':
        raise PermissionDenied('Esta acción está disponible solo para socios.')


def validar_resolucion_pago(pago, decision, datos, archivos):
    if decision == "RECHAZAR":
        motivo = str(datos.get("motivo_rechazo", "")).strip()

        if not motivo:
            raise ValidationError({
                "motivo_rechazo": "Debes indicar el motivo del rechazo."
            })

        if len(motivo) > 1000:
            raise ValidationError({
                "motivo_rechazo": "El motivo no puede superar los 1000 caracteres."
            })

        return None, motivo

    if decision != "APROBAR":
        raise ValidationError({
            "decision": "Usa APROBAR o RECHAZAR."
        })

    if pago.metodo_pago == Pago.MetodoPago.TRANSFERENCIA:
        if not pago.comprobante:
            raise ValidationError({
                "comprobante": "El pago no tiene comprobante de transferencia."
            })

        return None, ""

    boleta = archivos.get("boleta")

    if boleta is None:
        raise ValidationError({
            "boleta": "Debes adjuntar la boleta antes de aprobar."
        })

    if boleta.size > 10 * 1024 * 1024:
        raise ValidationError({
            "boleta": "La boleta no puede superar los 10 MB."
        })

    extension = Path(boleta.name).suffix.lower()

    if extension not in (".jpg", ".jpeg", ".png", ".webp", ".pdf"):
        raise ValidationError({
            "boleta": "Solo se permiten archivos JPG, PNG, WEBP o PDF."
        })

    boleta.seek(0)

    if extension == ".pdf":
        if boleta.read(5) != b"%PDF-":
            raise ValidationError({
                "boleta": "El archivo no parece ser un PDF válido."
            })
    else:
        try:
            with Image.open(boleta) as imagen:
                formato = imagen.format
                imagen.verify()

            if formato not in ("JPEG", "PNG", "WEBP"):
                raise ValidationError({
                    "boleta": "El formato de imagen no es válido."
                })

        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError({
                "boleta": "La imagen no es válida."
            })

    boleta.seek(0)

    return boleta, ""


def validar_clase(clase):
    inicio = timezone.make_aware(datetime.combine(clase.fecha, clase.hora_inicio), timezone.get_current_timezone())
    if not clase.activa or inicio <= timezone.now():
        raise ValidationError('La clase ya comenzó o no está disponible.')
    if Reserva.objects.filter(clase=clase, estado__in=[Reserva.Estado.CONFIRMADA, Reserva.Estado.PENDIENTE]).count() >= clase.cupos:
        raise ValidationError('No quedan cupos disponibles.')


class PlanesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response([{'codigo': p, 'nombre': nombre, 'clases': Membresia.CUPOS[p], 'precio_clp': Membresia.PRECIOS[p]} for p, nombre in Membresia.Plan.choices] + [{'codigo': 'CLASE_PARTICULAR', 'nombre': 'Clase particular', 'clases': 1, 'precio_clp': 3500}])


class MembresiasView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MembresiaSerializer

    def get_queryset(self):
        qs = Membresia.objects.select_related('socio', 'pago').order_by('-fecha_solicitud')
        if self.request.user.rol == 'DUENA':
            return qs
        if self.request.user.rol == 'SOCIO':
            return qs.filter(socio=self.request.user)
        return qs.none()



class ComprarPlanView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        verificar_socio(request.user)

        plan = request.data.get("plan")
        metodo = request.data.get("metodo_pago")
        comprobante = request.FILES.get("comprobante")

        if plan not in Membresia.PRECIOS:
            raise ValidationError({
                "plan": "Plan inválido."
            })

        if metodo not in Pago.MetodoPago.values:
            raise ValidationError({
                "metodo_pago": "Método de pago inválido."
            })

        if metodo == Pago.MetodoPago.TRANSFERENCIA:
            if comprobante is None:
                raise ValidationError({
                    "comprobante": "Debes adjuntar una imagen del comprobante de transferencia."
                })

            if comprobante.size > 10 * 1024 * 1024:
                raise ValidationError({
                    "comprobante": "La imagen no puede superar los 10 MB."
                })

            from PIL import Image, UnidentifiedImageError

            try:
                comprobante.seek(0)

                with Image.open(comprobante) as imagen:
                    formato = imagen.format
                    imagen.verify()

                if formato not in ("JPEG", "PNG", "WEBP"):
                    raise ValidationError({
                        "comprobante": "Solo se permiten imágenes JPG, PNG o WEBP."
                    })

                comprobante.seek(0)

            except (UnidentifiedImageError, OSError, ValueError):
                raise ValidationError({
                    "comprobante": "El archivo no es una imagen válida."
                })

        elif comprobante is not None:
            raise ValidationError({
                "comprobante": "Solo debes adjuntar comprobante si pagas por transferencia."
            })

        if Membresia.objects.filter(
            socio=request.user,
            estado=Membresia.Estado.PENDIENTE
        ).exists():
            raise ValidationError({
                "membresia": "Ya tienes una solicitud de membresía pendiente."
            })

        with transaction.atomic():
            pago = Pago.objects.create(
                socio=request.user,
                tipo_pago=Pago.TipoPago.MEMBRESIA,
                metodo_pago=metodo,
                monto=Membresia.PRECIOS[plan],
                estado=Pago.EstadoPago.PENDIENTE,
                comprobante=comprobante
            )

            membresia = Membresia.objects.create(
                socio=request.user,
                pago=pago,
                plan=plan,
                clases_totales=Membresia.CUPOS[plan],
                clases_restantes=Membresia.CUPOS[plan]
            )

        return Response(
            MembresiaSerializer(membresia).data,
            status=status.HTTP_201_CREATED
        )




class ResolverMembresiaView(APIView):
    permission_classes = [SoloDuena]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        decision = request.data.get("decision")

        if decision not in ("APROBAR", "RECHAZAR"):
            raise ValidationError({
                "decision": "Usa APROBAR o RECHAZAR."
            })

        with transaction.atomic():
            try:
                membresia = (
                    Membresia.objects
                    .select_for_update()
                    .select_related("pago")
                    .get(pk=pk)
                )
            except Membresia.DoesNotExist:
                raise NotFound("Membresía no encontrada.")

            if membresia.estado != Membresia.Estado.PENDIENTE:
                raise ValidationError(
                    "La membresía ya fue resuelta."
                )

            pago = (
                Pago.objects
                .select_for_update()
                .get(pk=membresia.pago_id)
            )

            if pago.estado != Pago.EstadoPago.PENDIENTE:
                raise ValidationError(
                    "El pago ya fue resuelto."
                )

            boleta, motivo = validar_resolucion_pago(
                pago,
                decision,
                request.data,
                request.FILES
            )

            if decision == "APROBAR":
                ahora = timezone.now()

                membresia.estado = Membresia.Estado.ACTIVA
                membresia.fecha_aprobacion = ahora
                membresia.fecha_vencimiento = sumar_mes(
                    timezone.localdate(ahora)
                )

                pago.estado = Pago.EstadoPago.APROBADO
                pago.motivo_rechazo = ""

                if boleta is not None:
                    pago.boleta = boleta

            else:
                membresia.estado = Membresia.Estado.RECHAZADA
                pago.estado = Pago.EstadoPago.RECHAZADO
                pago.motivo_rechazo = motivo

            pago.save(
                update_fields=[
                    "estado",
                    "boleta",
                    "motivo_rechazo"
                ]
            )

            membresia.save(
                update_fields=[
                    "estado",
                    "fecha_aprobacion",
                    "fecha_vencimiento"
                ]
            )

        return Response(
            MembresiaSerializer(membresia).data
        )


class ReservasView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReservaSerializer

    def get_queryset(self):
        qs = Reserva.objects.select_related('clase', 'socio', 'membresia').order_by('-fecha_creacion')
        if self.request.user.rol == 'DUENA':
            return qs
        if self.request.user.rol == 'SOCIO':
            return qs.filter(socio=self.request.user)
        if self.request.user.rol == 'COACH':
            return qs.filter(clase__coach=self.request.user)
        return qs.none()


class ReservarClaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        verificar_socio(request.user)
        try:
            clase_id = int(request.data.get('clase_id'))
        except (ValueError, TypeError):
            raise ValidationError({'clase_id': 'Debes indicar una clase válida.'})
        modalidad = request.data.get('modalidad')
        if modalidad not in ('MEMBRESIA', 'PARTICULAR'):
            raise ValidationError({'modalidad': 'Usa MEMBRESIA o PARTICULAR.'})
        try:
            with transaction.atomic():
                try:
                    clase = Clase.objects.select_for_update().get(pk=clase_id)
                except Clase.DoesNotExist:
                    raise NotFound('Clase no encontrada.')
                validar_clase(clase)
                if Reserva.objects.filter(socio=request.user, clase=clase, estado__in=['CONFIRMADA', 'PENDIENTE']).exists():
                    raise ValidationError('Ya tienes una reserva para esta clase.')
                if modalidad == 'MEMBRESIA':
                    try:
                        membresia_id = int(request.data.get('membresia_id'))
                    except (ValueError, TypeError):
                        raise ValidationError({'membresia_id': 'Debes indicar tu membresía.'})
                    try:
                        membresia = Membresia.objects.select_for_update().get(pk=membresia_id, socio=request.user)
                    except Membresia.DoesNotExist:
                        raise NotFound('Membresía no encontrada.')
                    if not membresia.vigente or membresia.clases_restantes == 0:
                        raise ValidationError('La membresía está vencida, pendiente o sin clases disponibles.')
                    membresia.clases_restantes -= 1
                    membresia.save(update_fields=['clases_restantes'])
                    reserva = Reserva.objects.create(socio=request.user, clase=clase, membresia=membresia)
                else:
                    metodo = request.data.get('metodo_pago')
                    if metodo not in Pago.MetodoPago.values:
                        raise ValidationError({'metodo_pago': 'Método de pago inválido.'})
                    pago = Pago.objects.create(socio=request.user, tipo_pago=Pago.TipoPago.CLASE_PARTICULAR, metodo_pago=metodo, monto=3500)
                    reserva = Reserva.objects.create(socio=request.user, clase=clase, pago=pago, estado=Reserva.Estado.PENDIENTE)
        except IntegrityError:
            raise ValidationError('Ya tienes una reserva para esta clase.')
        return Response(ReservaSerializer(reserva).data, status=status.HTTP_201_CREATED)



class ResolverReservaParticularView(APIView):
    permission_classes = [SoloDuena]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        decision = request.data.get("decision")

        if decision not in ("APROBAR", "RECHAZAR"):
            raise ValidationError({
                "decision": "Usa APROBAR o RECHAZAR."
            })

        with transaction.atomic():
            try:
                reserva = (
                    Reserva.objects
                    .select_for_update()
                    .select_related("pago")
                    .get(pk=pk, pago__isnull=False)
                )
            except Reserva.DoesNotExist:
                raise NotFound(
                    "Reserva particular no encontrada."
                )

            if reserva.estado != Reserva.Estado.PENDIENTE:
                raise ValidationError(
                    "La reserva ya fue resuelta."
                )

            pago = (
                Pago.objects
                .select_for_update()
                .get(pk=reserva.pago_id)
            )

            if pago.estado != Pago.EstadoPago.PENDIENTE:
                raise ValidationError(
                    "El pago ya fue resuelto."
                )

            boleta, motivo = validar_resolucion_pago(
                pago,
                decision,
                request.data,
                request.FILES
            )

            if decision == "APROBAR":
                pago.estado = Pago.EstadoPago.APROBADO
                pago.motivo_rechazo = ""
                reserva.estado = Reserva.Estado.CONFIRMADA

                if boleta is not None:
                    pago.boleta = boleta

            else:
                pago.estado = Pago.EstadoPago.RECHAZADO
                pago.motivo_rechazo = motivo
                reserva.estado = Reserva.Estado.CANCELADA

            pago.save(
                update_fields=[
                    "estado",
                    "boleta",
                    "motivo_rechazo"
                ]
            )

            reserva.save(
                update_fields=["estado"]
            )

        return Response(
            ReservaSerializer(reserva).data
        )



class RegistrarAsistenciaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if request.user.rol not in ('DUENA', 'COACH'):
            raise PermissionDenied('Solo la dueña o el coach asignado pueden registrar asistencia.')

        asistencia = request.data.get('asistencia')
        if asistencia not in (Reserva.Asistencia.ASISTIO, Reserva.Asistencia.NO_ASISTIO):
            raise ValidationError({'asistencia': 'Usa ASISTIO o NO_ASISTIO.'})

        with transaction.atomic():
            try:
                reserva = (
                    Reserva.objects.select_for_update()
                    .select_related('clase', 'membresia')
                    .get(pk=pk)
                )
            except Reserva.DoesNotExist:
                raise NotFound('Reserva no encontrada.')

            if request.user.rol == 'COACH' and reserva.clase.coach_id != request.user.pk:
                raise PermissionDenied('Solo puedes registrar asistencia en tus propias clases.')

            if reserva.estado != Reserva.Estado.CONFIRMADA:
                raise ValidationError('Solo se registra asistencia en reservas confirmadas.')

            if reserva.asistencia != Reserva.Asistencia.PENDIENTE:
                raise ValidationError('La asistencia ya fue registrada. No se puede aplicar dos veces.')

            fin_clase = timezone.make_aware(
                datetime.combine(reserva.clase.fecha, reserva.clase.hora_fin),
                timezone.get_current_timezone()
            )
            if timezone.now() < fin_clase:
                raise ValidationError('La asistencia se registra una vez finalizada la clase.')

            if asistencia == Reserva.Asistencia.NO_ASISTIO and reserva.membresia_id:
                membresia = Membresia.objects.select_for_update().get(pk=reserva.membresia_id)
                if membresia.vigente and membresia.clases_restantes < membresia.clases_totales:
                    membresia.clases_restantes += 1
                    membresia.save(update_fields=['clases_restantes'])
                    reserva.clase_devuelta = True

            reserva.asistencia = asistencia
            reserva.fecha_registro_asistencia = timezone.now()
            reserva.registrado_por = request.user
            reserva.save(update_fields=[
                'asistencia', 'fecha_registro_asistencia', 'registrado_por', 'clase_devuelta'
            ])

        return Response(ReservaSerializer(reserva).data)
