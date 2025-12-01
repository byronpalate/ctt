# coding=utf-8
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.funciones import log, MiPaginador, ok_json, bad_json, url_back, remover_tildes
from ctt.models import (Proforma, RevisionProforma, SolicitudTrabajo, Trabajo, Factura, Cliente, Persona, Group,
                        RequerimientoServicio, ProformaHistorial, ServicioCatalogo, ProformaDetalle, RubroServicio,
                        Rubro, EspacioFisico)
from ctt.forms import (RevisionProformaForm, VincularFacturaForm, GenerarTrabajoForm, ProformaForm,ProformaDetalleForm,RequerimientoServicioForm)
from datetime import datetime, timedelta, time
from django.utils import timezone
from settings import  TIPO_IVA_0_ID
@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']

    # ====================== POST ======================
    if request.method == 'POST':
        action = request.POST.get('action')

        # ========= ADD REQUERIMIENTO =========
        if action == 'addrequerimiento':
            try:
                form = RequerimientoServicioForm(request.POST, request.FILES)
                if form.is_valid():
                    cd = form.cleaned_data
                    req = RequerimientoServicio(
                        espacio_fisico=cd['espacio_fisico'],
                        descripcion=remover_tildes(cd.get('descripcion') or ""),
                        archivo=cd.get('archivo'),
                        cliente=cd['cliente'],
                        estado=RequerimientoServicio.Estado.RECIBIDO,
                        fecha_recepcion=timezone.now(),
                    )
                    req.save()
                    log(u'Cliente editó requerimiento: %s' % req, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        # ======= CREAR PROFORMA DESDE REQUERIMIENTO =======
        if action == 'add_proforma':
            try:
                requerimiento_id = request.POST.get('id')
                requerimiento = get_object_or_404(RequerimientoServicio, pk=requerimiento_id)

                form = ProformaForm(request.POST)
                if not form.is_valid():
                    return bad_json(error=6)

                # Si el requerimiento ya tiene cliente, usamos ese por defecto
                cliente = form.cleaned_data.get('cliente') or requerimiento.cliente

                proforma = Proforma(
                    cliente=cliente,
                    requerimiento=requerimiento,
                    observaciones=remover_tildes(form.cleaned_data.get('observaciones') or ""),
                    descuento=form.cleaned_data.get('descuento') or Decimal('0.00'),
                    iva=form.cleaned_data.get('iva'),
                    creado_por=persona,
                    numero="PF-%s" % timezone.now().strftime("%Y%m%d%H%M%S"),
                    estado=Proforma.Estado.BORRADOR,
                )
                proforma.save(request)

                # Cambiamos estado del requerimiento si recién estaba RECIBIDO
                if requerimiento.estado == RequerimientoServicio.Estado.RECIBIDO:
                    requerimiento.estado = RequerimientoServicio.Estado.EN_PROFORMA
                    requerimiento.save()

                # Historial de proforma
                ProformaHistorial.objects.create(
                    proforma=proforma,
                    tipo=ProformaHistorial.TipoEvento.CREACION,
                    mensaje=u"Proforma creada desde el requerimiento #%s." % requerimiento.id,
                    actor_persona=persona,
                    estado_anterior=None,
                    estado_nuevo=proforma.estado,
                )

                log(u'Creó proforma %s desde requerimiento %s' % (proforma.numero, requerimiento.id), request, "add")
                return ok_json({"id": proforma.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        # ======= REVISAR (aprobar / rechazar) PROFORMA =======
        if action == 'revisar':
            try:
                proforma = get_object_or_404(Proforma, pk=request.POST.get('id'))
                form = RevisionProformaForm(request.POST)
                if not form.is_valid():
                    return bad_json(error=6)

                cumple = form.cleaned_data['cumple']
                comentarios = remover_tildes(form.cleaned_data.get('comentarios') or "")

                # guarda/actualiza la revisión
                RevisionProforma.objects.update_or_create(
                    proforma=proforma,
                    defaults={
                        'revisado_por': persona,
                        'cumple': cumple,
                        'comentarios': comentarios
                    }
                )

                estado_anterior = proforma.estado
                proforma.estado = Proforma.Estado.APROBADA if cumple else Proforma.Estado.RECHAZADA
                proforma.fecha_respuesta = timezone.now()
                proforma.save(request)

                # Si aprueba, crea/asegura la Solicitud de Trabajo
                if cumple:
                    SolicitudTrabajo.objects.get_or_create(
                        proforma=proforma,
                        defaults={'cliente': proforma.cliente}
                    )
                    # si está asociada a un requerimiento, lo podemos cerrar
                    if proforma.requerimiento_id:
                        req = proforma.requerimiento
                        req.estado = RequerimientoServicio.Estado.CERRADO
                        req.save()

                ProformaHistorial.objects.create(
                    proforma=proforma,
                    tipo=ProformaHistorial.TipoEvento.APROBACION if cumple else ProformaHistorial.TipoEvento.RECHAZO,
                    mensaje=u"Revisión de proforma. %s" % comentarios,
                    actor_persona=persona,
                    estado_anterior=estado_anterior,
                    estado_nuevo=proforma.estado,
                )

                log(u'Revisión de proforma %s (cumple=%s)' % (proforma, cumple), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        # ======= VINCULAR FACTURA EXISTENTE A LA SOLICITUD =======
        if action == 'vincular_factura':
            try:
                solicitud = get_object_or_404(SolicitudTrabajo, pk=request.POST.get('id'))
                form = VincularFacturaForm(request.POST)
                if not form.is_valid():
                    return bad_json(error=6)

                factura = form.cleaned_data['factura']  # ModelChoice a Factura existente
                factura.solicitud = solicitud
                factura.save()

                log(u'Vinculó factura %s a solicitud %s' % (factura, solicitud.id), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        # ======= AGREGAR DETALLE (SERVICIO) A UNA PROFORMA =======
        if action == 'agregar_detalle':
            try:
                proforma = get_object_or_404(Proforma, pk=request.POST.get('id'))
                form = ProformaDetalleForm(request.POST)
                if not form.is_valid():
                    return bad_json(error=6)

                servicio = form.cleaned_data['servicio']
                descripcion = remover_tildes(form.cleaned_data['descripcion'] or "")
                fecha = form.cleaned_data['fecha']
                horainicio = form.cleaned_data['horainicio']
                horafin = form.cleaned_data['horafin']
                cantidad = form.cleaned_data['cantidad']
                precio_unitario = form.cleaned_data['precio_unitario'] or servicio.precio_base

                # Crear el detalle
                ProformaDetalle.objects.create(
                    proforma=proforma,
                    servicio=servicio,
                    descripcion=descripcion,
                    cantidad=cantidad,
                    precio_unitario=precio_unitario,
                    fecha=fecha,
                    horainicio=datetime.strptime(horainicio, '%H:%M').time(),
                    horafin=datetime.strptime(horafin, '%H:%M').time(),
                )

                # Recalcular totales de la proforma (incluye IVA si lo definiste en el modelo)
                if hasattr(proforma, "recomputar_totales"):
                    proforma.recomputar_totales()
                    # si tu ModeloBase usa save(request) para auditoría, lo dejamos igual
                    proforma.save(request)

                log(u'Agregó servicio %s a la proforma %s' % (servicio, proforma), request, "add")
                return ok_json()

            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'generar_rubro':
            try:
                proforma = get_object_or_404(Proforma, pk=request.POST.get('id'))

                # Solo permitimos rubro si la proforma está aprobada
                if proforma.estado != Proforma.Estado.APROBADA:
                    return bad_json(mensaje=u'La proforma debe estar APROBADA para generar el rubro.')

                # Evitar duplicados: usamos el vínculo RubroServicio
                if RubroServicio.objects.filter(proforma=proforma).exists():
                    return bad_json(mensaje=u'Ya existe un rubro generado para esta proforma.')

                hoy = timezone.now().date()
                valor = float(proforma.total or 0)

                # ============================================================
                # 1) DEFINIR INSCRIPCION / PERIODO PARA EL RUBRO
                # ============================================================
                # Si tu Proforma tiene FK a Inscripcion:
                #   inscripcion = proforma.inscripcion
                #
                # Si no, deberías decidir aquí cómo obtienes una inscripcion:
                #   - cliente → persona → inscripcion
                #   - una inscripcion genérica especial para servicios, etc.
                #
                # Por ahora dejo este ejemplo suponiendo que existe:
                cliente = proforma.cliente  # <-- AJUSTA ESTO
                periodo = None # <-- AJUSTA ESTO SI TU INSCRIPCION TIENE OTRO PATH

                # ============================================================
                # 2) CREAR RUBRO
                # ============================================================
                rubro = Rubro.objects.create(
                    cliente=cliente,
                    periodo=None,
                    nombre=f"SERVICIO - PROFORMA {proforma.numero}",
                    fecha=hoy,
                    fechavence=hoy,
                    valor=valor,
                    iva_id=TIPO_IVA_0_ID,
                    valoriva=0,
                    valortotal=valor,
                    saldo=valor,
                    cancelado=False,
                    pasivo=False,
                    valornivelactual=0,
                    observacion=f"Generado desde proforma {proforma.numero}",
                    validoprontopago=False,
                    valorajuste=0,
                    motivoajuste=""
                )

                # Si tienes este método definido en Rubro, lo puedes usar:
                try:
                    rubro.actulizar_nombre(f"SERVICIO - PROFORMA {proforma.numero}")
                except:
                    pass

                # ============================================================
                # 3) VINCULAR RUBRO <-> PROFORMA
                # ============================================================
                RubroServicio.objects.create(
                    rubro=rubro,
                    proforma=proforma,
                    descripcion=f"Rubro por servicios de la proforma {proforma.numero}"
                )

                # 🔹 Crear la solicitud de trabajo si no existe aún
                if not hasattr(proforma, 'solicitud_trabajo'):
                    solicitud = SolicitudTrabajo.objects.create(
                        proforma=proforma,
                        cliente=proforma.cliente,
                        # requerimiento=proforma.requerimiento,
                        estado=SolicitudTrabajo.Estado.PEND_PAGO
                    )

                # Opcional: cerrar requerimiento cuando ya tiene rubro
                if proforma.requerimiento and proforma.requerimiento.estado != 4:
                    proforma.requerimiento.estado = 4  # CERRADO
                    proforma.requerimiento.save(request)

                log(u'Generó rubro %s para proforma %s' % (rubro.id, proforma.numero), request, "add")
                return ok_json()

            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        # ======= GENERAR TRABAJO =======
        if action == 'generar_trabajo':
            try:
                solicitud = get_object_or_404(SolicitudTrabajo, pk=request.POST.get('id'))
                form = GenerarTrabajoForm(request.POST)
                if not form.is_valid():
                    return bad_json(error=6)

                # -----------------------------------------
                # VALIDAR QUE LA PROFORMA TENGA RUBRO PAGADO
                # -----------------------------------------
                proforma = solicitud.proforma

                try:
                    rubro_servicio = proforma.rubro_servicio  # OneToOne
                except RubroServicio.DoesNotExist:
                    return bad_json(
                        mensaje=u'La proforma no tiene rubro generado. No se puede crear la orden de trabajo.'
                    )

                if not rubro_servicio.rubro.cancelado:
                    return bad_json(
                        mensaje=u'El rubro de esta proforma aún NO está pagado. '
                                u'Solo se puede generar la orden de trabajo cuando el rubro esté cancelado.'
                    )

                responsable = form.cleaned_data['responsable']  # Persona
                descripcion = remover_tildes(form.cleaned_data.get('descripcion') or "")

                # si ya existe, no duplicar
                if hasattr(solicitud, 'trabajo'):
                    return bad_json(mensaje=u'Ya existe un trabajo generado para esta solicitud.')

                trabajo = Trabajo.objects.create(
                    solicitud=solicitud,
                    responsable=responsable,
                    descripcion=descripcion
                )

                log(u'Generó trabajo %s para solicitud %s' % (trabajo.id, solicitud.id), request, "add")
                return ok_json({"id": trabajo.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'send':
            try:
                proforma = get_object_or_404(Proforma, pk=request.POST.get('id'))
                # Solo permitir enviar si está en BORRADOR
                if proforma.estado != Proforma.Estado.BORRADOR:
                    return bad_json(mensaje=u'La proforma no está en estado BORRADOR.')

                # usamos el helper del modelo
                proforma.enviar_al_cliente(actor_persona=persona)

                # si tiene requerimiento, actualizamos su estado
                if proforma.requerimiento:
                    req = proforma.requerimiento
                    # asumiendo que tienes un estado PROFORMA_ENVIADA = 3
                    if req.estado < RequerimientoServicio.Estado.PROFORMA_ENVIADA:
                        req.estado = RequerimientoServicio.Estado.PROFORMA_ENVIADA
                        req.save()

                log(u'Proforma enviada al cliente: %s' % proforma, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delrequerimiento':
            try:
                req = RequerimientoServicio.objects.get(pk=request.POST['id'])
                log(u'Elimino curso: %s' % req, request, "del")
                req.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        # ========= APPROVE (cliente aprueba) =========
        if action == 'approve':
            try:
                proforma = get_object_or_404(Proforma, pk=request.POST.get('id'))

                estado_anterior = proforma.estado
                proforma.estado = Proforma.Estado.APROBADA
                proforma.fecha_respuesta = timezone.now()
                proforma.save()

                # si hay requerimiento, lo cierras o lo pasas a "CERRADO"
                if proforma.requerimiento:
                    req = proforma.requerimiento
                    # asumiendo que tienes un estado CERRADO = 4
                    req.estado = RequerimientoServicio.Estado.CERRADO
                    req.save()

                proforma.registrar_evento(
                    tipo=ProformaHistorial.TipoEvento.EDICION,
                    mensaje=u"Proforma aprobada por el administrador.",
                    actor_persona=None,
                    actor_externo=u"Cliente",
                    estado_anterior=estado_anterior,
                    estado_nuevo=proforma.estado,
                )

                log(u'Administrador aprobó proforma: %s' % proforma, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        # ========= REJECT (cliente rechaza) =========
        if action == 'reject':
            try:
                proforma = get_object_or_404(Proforma, pk=request.POST.get('id'))

                estado_anterior = proforma.estado
                proforma.estado = Proforma.Estado.RECHAZADA
                proforma.fecha_respuesta = timezone.now()
                proforma.save()

                if proforma.requerimiento:
                    req = proforma.requerimiento
                    # puedes devolverlo a EN_PROFORMA o dejarlo como PROFORMA_ENVIADA_RECHAZADA
                    # depende de tu modelo de estados
                    # ejemplo: lo dejamos como CERRADO también o un estado de "Rechazada"
                    req.estado = RequerimientoServicio.Estado.CERRADO
                    req.save()

                proforma.registrar_evento(
                    tipo=ProformaHistorial.TipoEvento.EDICION,
                    mensaje=u"Proforma rechazada por el administrador.",
                    actor_persona=None,
                    actor_externo=u"Cliente",
                    estado_anterior=estado_anterior,
                    estado_nuevo=proforma.estado,
                )

                log(u'Administrador rechazó proforma: %s' % proforma, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        return bad_json(error=0)

        return bad_json(error=0)  # acción no reconocida

    # ====================== GET ======================
    if 'action' in request.GET:
        action = request.GET.get('action')


        # ======= MODAL: AGREGAR DETALLE A PROFORMA =======
        if action == 'agregar_detalle':
            try:
                proforma = get_object_or_404(Proforma, pk=request.GET.get('id'))
                data['title'] = u'Agregar servicio a proforma %s' % proforma.numero
                form = ProformaDetalleForm()

                # Filtrar lista de servicios según el tipo del requerimiento (si aplica)
                if proforma.requerimiento and proforma.requerimiento.espacio_fisico.tipo_servicio_id:
                    form.fields['servicio'].queryset = ServicioCatalogo.objects.filter(
                        espacio_fisico__tipo_servicio_id=proforma.requerimiento.espacio_fisico.tipo_servicio.id
                    )

                data['form'] = form
                data['proforma'] = proforma

                return render(request, 'gestion_servicios/agregar_detalle.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)


        # ======= MODAL: revisar proforma =======
        if action == 'revisar':
            try:
                data['title'] = u'Revisar proforma'
                data['proforma'] = proforma = get_object_or_404(Proforma, pk=request.GET.get('id'))
                inicial = {}
                if hasattr(proforma, 'revision'):
                    inicial = {
                        'cumple': proforma.revision.cumple,
                        'comentarios': proforma.revision.comentarios
                    }
                data['form'] = RevisionProformaForm(initial=inicial)
                return render(request, 'gestion_servicios/revisar.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)

        # ======= MODAL: vincular factura =======
        if action == 'vincular_factura':
            try:
                data['title'] = u'Vincular factura existente'
                data['solicitud'] = get_object_or_404(SolicitudTrabajo, pk=request.GET.get('id'))
                data['form'] = VincularFacturaForm()
                return render(request, 'gestion_servicios/vincular_factura.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)

        # ======= MODAL: generar trabajo =======
        if action == 'generar_trabajo':
            try:
                data['title'] = u'Generar trabajo'
                data['solicitud'] = get_object_or_404(SolicitudTrabajo, pk=request.GET.get('id'))
                data['form'] = GenerarTrabajoForm()
                return render(request, 'gestion_servicios/generar_trabajo.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)


        # ======= DETALLE DE UNA PROFORMA =======
        if action == 'detalle_proforma':
            try:
                proforma = get_object_or_404(Proforma, pk=request.GET.get('id'))
                data['title'] = u'Detalle de proforma'
                data['proforma'] = proforma
                # usamos el related_name='detalles'
                data['detalles'] = proforma.detalles.select_related('servicio').all()
                espacio = proforma.requerimiento.espacio_fisico
                hoy = timezone.now().date()
                dias = [hoy + timedelta(days=i) for i in range(7)]
                horas = [time(h, 0) for h in range(7, 18)]
                data['detallesproformas'] = ProformaDetalle.objects.filter(fecha__range=(hoy, hoy + timedelta(days=6)),servicio__espacio_fisico=espacio,)
                data['misdetalles'] = ProformaDetalle.objects.filter(servicio__espacio_fisico=espacio,fecha__range=(hoy, hoy + timedelta(days=6)))
                data['horas'] = horas
                data['dias'] = dias
                data['title'] = u'Espacio'
                data['espacio'] = espacio
                # data['bloqueos'] = DesactivarCancha.objects.filter(cancha=cancha)
                return render(request, 'gestion_servicios/detalle_proforma.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)

        # ======= DETALLE de REQUERIMIENTO (incluye proformas asociadas) =======
        if action == 'detalle_requerimiento':
            try:
                data['title'] = u'Detalle de requerimiento'
                req = get_object_or_404(RequerimientoServicio, pk=request.GET.get('id'))
                data['requerimiento'] = req
                data['proformas'] = req.proformas.select_related('cliente').all()
                return render(request, 'gestion_servicios/detalle_requerimiento.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)

        # ======= MODAL: crear proforma desde requerimiento =======
        if action == 'add_proforma':
            try:
                data['title'] = u'Nueva proforma desde requerimiento'
                req = get_object_or_404(RequerimientoServicio, pk=request.GET.get('requerimiento_id'))
                data['requerimiento'] = req

                initial = {
                    "observaciones": remover_tildes(req.descripcion or ""),
                }
                data['form'] = ProformaForm(initial=initial)
                return render(request, 'gestion_servicios/add_proforma.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)

            # ========= ADD (pantalla nuevo requerimiento) =========
        if action == 'addrequerimiento':
            try:
                data['title'] = u'Nuevo requerimiento de servicio'

                initial = {}
                # si tienes info en cliente, podrías precargar:
                data['form'] = RequerimientoServicioForm(initial=initial)
                return render(request, "gestion_servicios/addrequerimiento.html", data)
            except Exception as ex:
                pass

        if action == 'delrequerimiento':
            try:
                data['title'] = u'Borrar requerimiento de servicio'
                data['req'] = curso = RequerimientoServicio.objects.get(pk=request.GET['id'])
                return render(request, "gestion_servicios/delcurso.html", data)
            except Exception as ex:
                pass

        return url_back(request)

    # ====== LISTADO PRINCIPAL: REQUERIMIENTOS ======
    try:
        data['title'] = u'Gestión de servicios (Requerimientos)'
        search = request.GET.get('s', '').strip()
        estado = request.GET.get('e')   # estado del requerimiento
        tipo = request.GET.get('t')     # tipo_servicio_id opcional

        qs = RequerimientoServicio.objects.select_related('cliente', 'espacio_fisico').all()

        if search:
            qs = qs.filter(
                Q(nombre_contacto__icontains=search) |
                Q(email_contacto__icontains=search) |
                Q(descripcion__icontains=search)
            )

        if estado and estado.isdigit():
            qs = qs.filter(estado=int(estado))

        if tipo and tipo.isdigit():
            qs = qs.filter(espacio_fisico_id=int(tipo))

        qs = qs.order_by('-fecha_recepcion', '-id')

        paging = MiPaginador(qs, 25)
        p = 1
        try:
            paginasesion = 1
            if 'paginador' in request.session and 'paginador_url' in request.session:
                if request.session['paginador_url'] == 'gestion_servicios':
                    paginasesion = int(request.session['paginador'])
            if 'page' in request.GET:
                p = int(request.GET.get('page'))
            else:
                p = paginasesion
            page = paging.page(p)
        except:
            p = 1
            page = paging.page(p)

        request.session['paginador'] = p
        request.session['paginador_url'] = 'gestion_servicios'

        data['paging'] = paging
        data['rangospaging'] = paging.rangos_paginado(p)
        data['page'] = page
        data['search'] = search
        data['estado'] = estado or ""
        data['tipo'] = tipo or ""
        data['requerimientos'] = page.object_list

        # control de solo lectura por grupos
        data['sololectura'] = True
        ids_grupos = [11, 28]  # ajusta a tus grupos que pueden gestionar
        listagrupo = Group.objects.filter(id__in=ids_grupos)
        if persona.en_grupos(listagrupo):
            data['sololectura'] = False

        return render(request, 'gestion_servicios/view.html', data)
    except Exception as ex:
        return HttpResponseRedirect('/')
