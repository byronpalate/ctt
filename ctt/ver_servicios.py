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
from ctt.forms import (RevisionProformaForm, VincularFacturaForm, GenerarTrabajoForm, ProformaForm, ProformaDetalleForm,
                       RequerimientoServicioForm, SolicitarRequerimientoServicioForm)

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
                form = SolicitarRequerimientoServicioForm(request.POST, request.FILES)
                espacio = get_object_or_404(EspacioFisico, pk=request.POST.get('id'))
                if form.is_valid():
                    cd = form.cleaned_data
                    req = RequerimientoServicio(
                        tiposervicio=espacio.tipo_servicio,
                        descripcion=remover_tildes(cd.get('descripcion') or ""),
                        archivo=cd.get('archivo'),
                        cliente=get_object_or_404(Cliente, persona=persona),
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


        return bad_json(error=0)  # acción no reconocida

    # ====================== GET ======================
    if 'action' in request.GET:
        action = request.GET.get('action')

        if action == 'addrequerimiento':
            try:
                data['title'] = u'Nuevo requerimiento de servicio'
                data['espacio']= get_object_or_404(EspacioFisico, pk=request.GET.get('id'))
                initial = {}
                # si tienes info en cliente, podrías precargar:
                data['form'] = SolicitarRequerimientoServicioForm(initial=initial)
                return render(request, "ver_servicios/addrequerimiento.html", data)
            except Exception as ex:
                pass

        return url_back(request)


        return url_back(request)

    # ====== LISTADO PRINCIPAL: REQUERIMIENTOS ======
    try:
        data['title'] = u'Gestión de servicios (Requerimientos)'
        search = request.GET.get('s', '').strip()
        estado = request.GET.get('e')   # estado del requerimiento
        tipo = request.GET.get('t')     # tipo_servicio_id opcional

        qs = EspacioFisico.objects.all()

        if search:
            qs = qs.filter(
                Q(nombre__icontains=search) |
                Q(descripcion__icontains=search)
            )

        paging = MiPaginador(qs, 25)
        p = 1
        try:
            paginasesion = 1
            if 'paginador' in request.session and 'paginador_url' in request.session:
                if request.session['paginador_url'] == 'ver_servicios':
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
        request.session['paginador_url'] = 'ver_servicios'

        data['paging'] = paging
        data['rangospaging'] = paging.rangos_paginado(p)
        data['page'] = page
        data['search'] = search
        data['estado'] = estado or ""
        data['tipo'] = tipo or ""
        data['laboratorios'] = page.object_list

        return render(request, 'ver_servicios/view.html', data)
    except Exception as ex:
        return HttpResponseRedirect('/')
