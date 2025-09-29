# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import ReciboPagoCanceladoForm
from ctt.funciones import MiPaginador, log, ok_json, bad_json, url_back
from ctt.models import ReciboPago


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    sesion_caja = None
    caja = None
    puedepagar = False
    if persona.puede_recibir_pagos():
        sesion_caja = persona.caja_abierta()
        if sesion_caja:
            caja = sesion_caja.caja
            puedepagar = sesion_caja.puede_pagar()
    data['sesion_caja'] = sesion_caja
    data['caja'] = caja
    data['puede_pagar'] = puedepagar
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'anular':
            try:
                recibo = ReciboPago.objects.get(pk=request.POST['id'])
                form = ReciboPagoCanceladoForm(request.POST)
                if form.is_valid():
                    hoy = datetime.now().date()
                    mesactual = hoy.month
                    anioactual = hoy.year
                    if not request.user.is_superuser:
                        if recibo.fecha.year != anioactual or recibo.fecha.month != mesactual:
                            return bad_json(mensaje=u'No puede eliminar el recibo porque no es del mes actual.')
                    for pagoexedente in recibo.recibopagoexedente_set.all():
                        if pagoexedente.recibocajainstitucion.pagorecibocajainstitucion_set.filter(pagos__valido=True).exists():
                            return bad_json(mensaje=u'No puede eliminar el recibo de pago porque el exedente ya fue utilizado.')
                    recibo.cancelar(form.cleaned_data['motivo'])
                    log(u'Anulo recibo de pago: %s' % recibo, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'rubros':
                try:
                    data['title'] = u'Listado de rubros del recibo de pago'
                    data['recibo'] = recibo = ReciboPago.objects.get(pk=request.GET['id'])
                    data['pagos'] = recibo.pagos.all()
                    return render(request, "adm_recibopago/rubros.html", data)
                except Exception as ex:
                    pass

            if action == 'anular':
                try:
                    data['title'] = u'Anular Recibo de pago'
                    data['recibo'] = recibo = ReciboPago.objects.get(pk=request.GET['id'])
                    data['form'] = ReciboPagoCanceladoForm()
                    return render(request, "adm_recibopago/anular.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de recibos de pago'
                search = None
                ids = None
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    recibos = ReciboPago.objects.filter(id=ids)
                elif 's' in request.GET:
                    search = request.GET['s'].strip()
                    recibos = ReciboPago.objects.filter(Q(numero__icontains=search) |
                                                        Q(total__icontains=search) |
                                                        Q(inscripcion__persona__nombre1__icontains=search) |
                                                        Q(inscripcion__persona__nombre2__icontains=search) |
                                                        Q(inscripcion__persona__apellido1__icontains=search) |
                                                        Q(inscripcion__persona__apellido2__icontains=search) |
                                                        Q(sesion__caja__nombre__icontains=search)).distinct().order_by('-fecha', '-numero')
                else:
                    recibos = ReciboPago.objects.all().order_by('-fecha', '-numero')
                paging = MiPaginador(recibos, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_recibopago':
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
                request.session['paginador_url'] = 'adm_recibopago'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['recibos'] = page.object_list
                persona = request.session['persona']
                data['puede_pagar'] = persona.puede_recibir_pagos()
                data['hoy'] = datetime.now().date()
                return render(request, "adm_recibopago/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
