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
    RequerimientoServicio, Proforma, ProformaHistorial, Trabajo
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


        return bad_json(error=0)

    # ------------------------ GET ------------------------
    else:
        if 'action' in request.GET:
            action = request.GET.get('action')

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
            data['title'] = u'Mis Ordenes de Trabajo'
            search = None
            ids = None

            qs = RequerimientoServicio.objects.filter(proformas__solicitud_trabajo__trabajo__responsable=persona)
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

            return render(request, "adm_ordenestrabajo/view.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')
