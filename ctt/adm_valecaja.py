# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import ValeCajaForm
from ctt.funciones import MiPaginador, log, url_back, bad_json, ok_json
from ctt.models import ValeCaja


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

        if action == 'add':
            try:
                if not puedepagar:
                    return bad_json(mensaje=u"No existe una sessión de caja abierta.")
                form = ValeCajaForm(request.POST)
                if form.is_valid():
                    vale = ValeCaja(tipooperacion=form.cleaned_data['tipo'],
                                    valor=form.cleaned_data['valor'],
                                    recibe_id=form.cleaned_data['recibe'],
                                    responsable_id=form.cleaned_data['responsable'],
                                    concepto=form.cleaned_data['concepto'],
                                    referencia=form.cleaned_data['referencia'],
                                    sesion=sesion_caja,
                                    fecha=datetime.now().date(),
                                    hora=datetime.now().time())
                    vale.save(request)
                    log(u'Adiciono vale de caja: %s' % vale, request, "add")
                    return ok_json({"id": vale.id})
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edit':
            try:
                vale = ValeCaja.objects.get(pk=request.POST['id'])
                form = ValeCajaForm(request.POST)
                if form.is_valid():
                    vale.valorentregado = form.cleaned_data['valor']
                    vale.concepto = form.cleaned_data['concepto']
                    vale.referencia = form.cleaned_data['referencia']
                    if vale.tipooperacion == 1:
                        vale.recibe_id = form.cleaned_data['recibe']
                        vale.responsable_id = form.cleaned_data['responsable']
                    vale.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'del':
            try:
                vale = ValeCaja.objects.get(pk=request.POST['id'])
                log(u'Elimino vale de caja: %s' % vale, request, "del")
                vale.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar vale de caja'
                    data['form'] = ValeCajaForm()
                    return render(request, "adm_valecaja/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar vale de caja'
                    data['vale'] = vale = ValeCaja.objects.get(pk=request.GET['id'])
                    form = ValeCajaForm(initial={'valor': vale.valor,
                                                 'tipo': vale.tipooperacion,
                                                 'recibe': vale.recibe.id if vale.recibe else 0,
                                                 'responsable': vale.responsable.id if vale.responsable else 0,
                                                 'referencia': vale.referencia,
                                                 'concepto': vale.concepto})
                    form.editar(vale)
                    data['form'] = form
                    return render(request, "adm_valecaja/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'del':
                try:
                    data['title'] = u'Elimnar vale de caja'
                    vale = ValeCaja.objects.get(pk=request.GET['id'])
                    data['vale'] = vale
                    return render(request, "adm_valecaja/del.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de vales de caja'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    vales = ValeCaja.objects.filter(Q(referencia__icontains=search) |
                                                    Q(valor__icontains=search) |
                                                    Q(recibe__icontains=search) |
                                                    Q(responsable__icontains=search) |
                                                    Q(sesion__caja__persona__nombre1__icontains=search) |
                                                    Q(sesion__caja__persona__nombre2__icontains=search) |
                                                    Q(sesion__caja__persona__apellido1__icontains=search) |
                                                    Q(sesion__caja__persona__apellido2__icontains=search)).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    vales = ValeCaja.objects.filter(id=ids)
                else:
                    vales = ValeCaja.objects.all()
                paging = MiPaginador(vales, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_valecaja':
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
                request.session['paginador_url'] = 'adm_valecaja'
                data['paging'] = paging
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['vales'] = page.object_list
                return render(request, "adm_valecaja/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
