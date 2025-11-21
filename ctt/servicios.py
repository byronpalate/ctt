# coding=utf-8
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.funciones import log, MiPaginador, ok_json, bad_json, url_back, remover_tildes
from ctt.models import (
    Cliente,
    RequerimientoServicio,Proforma,ProformaHistorial
)
from ctt.forms import RequerimientoServicioForm


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']

    # intentamos obtener el Cliente ligado a esta persona
    cliente = Cliente.objects.filter(persona=persona).first()

    # ------------------------ POST ------------------------
    if request.method == 'POST':
        action = request.POST.get('action')

        # ========= ADD REQUERIMIENTO =========
        if action == 'add':
            try:
                form = RequerimientoServicioForm(request.POST, request.FILES)
                if form.is_valid():
                    cd = form.cleaned_data
                    req = RequerimientoServicio(
                        espacio_fisico=cd['espacio_fisico'],
                        nombre_contacto=cd['nombre_contacto'],
                        email_contacto=cd['email_contacto'],
                        telefono_contacto=cd.get('telefono_contacto', ''),
                        descripcion=remover_tildes(cd.get('descripcion') or ""),
                        archivo=cd.get('archivo'),
                        cliente=cliente,
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

        # ========= EDIT REQUERIMIENTO =========
        if action == 'edit':
            try:
                req = get_object_or_404(
                    RequerimientoServicio,
                    pk=request.POST.get('id'),
                    cliente=cliente  # solo sus propios requerimientos
                )

                # solo permitir editar en estado RECIBIDO (antes de que el laboratorio arme proforma)
                if req.estado != RequerimientoServicio.Estado.RECIBIDO:
                    return bad_json(mensaje=u'El requerimiento ya está en gestión y no puede ser editado.')

                form = RequerimientoServicioForm(request.POST, request.FILES, instance=req)
                if form.is_valid():
                    req = form.save(commit=False)
                    req.descripcion = remover_tildes(req.descripcion or "")
                    req.save()

                    log(u'Cliente editó requerimiento: %s' % req, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        # ========= DELETE REQUERIMIENTO =========
        if action == 'delete':
            try:
                req = get_object_or_404(
                    RequerimientoServicio,
                    pk=request.POST.get('id'),
                    cliente=cliente
                )
                # solo permitir eliminar si sigue RECIBIDO
                if req.estado != RequerimientoServicio.Estado.RECIBIDO:
                    return bad_json(mensaje=u'Solo puede eliminar requerimientos en estado RECIBIDO.')

                log(u'Cliente eliminó requerimiento: %s' % req, request, "del")
                req.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        # ========= APPROVE (cliente aprueba) =========
        if action == 'approve':
            try:
                proforma = get_object_or_404(Proforma, pk=request.POST.get('id'))
                if proforma.estado != Proforma.Estado.ENVIADA:
                    return bad_json(mensaje=u'Solo se pueden aprobar proformas ENVIADAS.')

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
                    mensaje=u"Proforma aprobada por el cliente.",
                    actor_persona=None,
                    actor_externo=u"Cliente",
                    estado_anterior=estado_anterior,
                    estado_nuevo=proforma.estado,
                )

                log(u'Cliente aprobó proforma: %s' % proforma, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        # ========= REJECT (cliente rechaza) =========
        if action == 'reject':
            try:
                proforma = get_object_or_404(Proforma, pk=request.POST.get('id'))
                if proforma.estado != Proforma.Estado.ENVIADA:
                    return bad_json(mensaje=u'Solo se pueden rechazar proformas ENVIADAS.')

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
                    mensaje=u"Proforma rechazada por el cliente.",
                    actor_persona=None,
                    actor_externo=u"Cliente",
                    estado_anterior=estado_anterior,
                    estado_nuevo=proforma.estado,
                )

                log(u'Cliente rechazó proforma: %s' % proforma, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        return bad_json(error=0)

    # ------------------------ GET ------------------------
    else:
        if 'action' in request.GET:
            action = request.GET.get('action')

            # ========= ADD (pantalla nuevo requerimiento) =========
            if action == 'add':
                try:
                    data['title'] = u'Nuevo requerimiento de servicio'

                    initial = {}
                    # si tienes info en cliente, podrías precargar:
                    if cliente:
                        initial.update({
                            "nombre_contacto": cliente.razon_social,
                            "email_contacto": cliente.email,
                            "telefono_contacto": cliente.telefono,
                        })
                    data['form'] = RequerimientoServicioForm(initial=initial)
                    return render(request, "servicios/add.html", data)
                except Exception as ex:
                    pass

            # ========= EDIT =========
            if action == 'edit':
                try:
                    data['title'] = u'Editar requerimiento'
                    data['requerimiento'] = req = get_object_or_404(
                        RequerimientoServicio,
                        pk=request.GET.get('id'),
                        cliente=cliente
                    )
                    data['form'] = RequerimientoServicioForm(instance=req)
                    return render(request, "servicios/requerimiento_edit.html", data)
                except Exception as ex:
                    pass

            # ========= DETAIL =========
            # if action == 'detail':
            #     try:
            #         data['title'] = u'Detalle de requerimiento'
            #         data['requerimiento'] = req = get_object_or_404(
            #             RequerimientoServicio,
            #             pk=request.GET.get('id'),
            #             cliente=cliente
            #         )
            #         # si más adelante quieres mostrar proformas ligadas, podrías aquí:
            #         # data['proformas'] = req.proformas.all()
            #         return render(request, "servicios/requerimiento_detail.html", data)
            #     except Exception as ex:
            #         pass



            if action == 'detail':
                try:
                    data['title'] = u'Detalle de requerimiento'
                    req = get_object_or_404(
                        RequerimientoServicio,
                        pk=request.GET.get('id'),
                        # ajusta este filtro al dueño del requerimiento
                        # por ejemplo: cliente=persona.cliente  o creado_por=persona
                    )
                    data['requerimiento'] = req
                    data['proformas'] = req.proformas.all()
                    return render(request, "servicios/requerimiento_detail.html", data)
                except Exception as ex:
                    return url_back(request, ex=ex)

                # ========= DETALLE PROFORMA (cliente) =========
            if action == 'proforma_detail':
                try:
                    data['title'] = u'Detalle de proforma'
                    proforma = get_object_or_404(
                        Proforma,
                        pk=request.GET.get('id'),
                        # igual, filtra por el dueño (cliente) si aplica
                    )
                    data['proforma'] = proforma
                    return render(request, "servicios/proforma_detail.html", data)
                except Exception as ex:
                    return url_back(request, ex=ex)

            # ========= DELETE (confirmación) =========
            if action == 'delete':
                try:
                    data['title'] = u'Eliminar requerimiento'
                    data['requerimiento'] = get_object_or_404(
                        RequerimientoServicio,
                        pk=request.GET.get('id'),
                        cliente=cliente
                    )
                    return render(request, "servicios/requerimiento_delete.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)

        # ========= LISTADO (MIS REQUERIMIENTOS) =========
        try:
            data['title'] = u'Mis requerimientos de servicio'
            search = None
            ids = None

            qs = RequerimientoServicio.objects.all()
            # solo los del cliente actual (si existe)
            if cliente:
                qs = qs.filter(cliente=cliente)

            if 's' in request.GET:
                search = request.GET['s'].strip()
                qs = qs.filter(
                    Q(descripcion__icontains=search) |
                    Q(nombre_contacto__icontains=search) |
                    Q(email_contacto__icontains=search)
                ).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                qs = qs.filter(id=ids)

            paging = MiPaginador(qs.order_by('-fecha_recepcion'), 25)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session and 'paginador_url' in request.session:
                    if request.session['paginador_url'] == 'servicios':
                        paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                else:
                    p = paginasesion
                page = paging.page(p)
            except:
                p = 1
                page = paging.page(p)

            request.session['paginador'] = p
            request.session['paginador_url'] = 'servicios'
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['requerimientos'] = page.object_list
            data['sololectura'] = False  # el cliente puede crear/editar mientras esté RECIBIDO

            return render(request, "servicios/view.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')
