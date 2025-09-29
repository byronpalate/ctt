# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render, HttpResponseRedirect

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata, obtener_reporte
from ctt.forms import SesionCajaForm, CierreSesionCajaForm
from ctt.funciones import MiPaginador, log, ok_json, bad_json, url_back
from ctt.models import SesionCaja, CierreSesionCaja, Pago, null_to_numeric, ValeCaja, PapeletaDeposito


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
    data['cajas'] = miscajas = persona.mis_cajas()
    if miscajas:
        sesion_caja = persona.caja_abierta()
        if sesion_caja:
            caja = sesion_caja.caja
            puedepagar = sesion_caja.puede_pagar()
    data['sesion_caja'] = sesion_caja
    data['caja'] = caja
    data['puede_pagar'] = puedepagar
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsesion':
            try:
                form = SesionCajaForm(request.POST)
                if form.is_valid():
                    if sesion_caja:
                        return bad_json(mensaje=u"No puede abrir varias cajas al mismo tiempo.")
                    sesioncaja = SesionCaja(caja=form.cleaned_data['caja'],
                                            fecha=datetime.now().date(),
                                            hora=datetime.now().time(),
                                            fondo=form.cleaned_data['fondo'])
                    sesioncaja.save(request)
                    log(u'Adiciono sesion de caja: %s' % sesioncaja, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addpapeleta':
            try:
                form = PapeletaForm(request.POST)
                if form.is_valid():
                    cierre = CierreSesionCaja.objects.get(id=int(request.POST['id']))
                    papeleta = PapeletaDeposito(cierresesioncaja=cierre,
                                                referencia=form.cleaned_data['referencia'],
                                                cuentabanco=form.cleaned_data['cuentabanco'],
                                                valor=form.cleaned_data['valor'])
                    papeleta.save(request)
                    log(u'Adiciono papeleta de caja: %s' % papeleta, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editpapeleta':
            try:
                form = PapeletaForm(request.POST)
                if form.is_valid():
                    papeleta = PapeletaDeposito.objects.get(id=int(request.POST['id']))
                    papeleta.referencia = form.cleaned_data['referencia']
                    papeleta.cuentabanco = form.cleaned_data['cuentabanco']
                    papeleta.valor = form.cleaned_data['valor']
                    papeleta.save(request)
                    log(u'Edito papeleta de caja: %s' % papeleta, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delpapeleta':
            try:
                papeleta = PapeletaDeposito.objects.get(pk=request.POST['id'])
                log(u"Elimino papeleta de deposito: %s" % papeleta, request, "del")
                papeleta.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'cerrarsesion':
            try:
                form = CierreSesionCajaForm(request.POST)
                if form.is_valid():
                    sesion_caja = SesionCaja.objects.get(pk=request.POST['id'])
                    deposito = null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__datotransferenciadeposito__deposito=True, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    transferencia = null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__datotransferenciadeposito__deposito=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    cheques = null_to_numeric(Pago.objects.filter(pagocheque__isnull=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    tarjetas = null_to_numeric(Pago.objects.filter(pagotarjeta__isnull=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    valorcajaentregado = null_to_numeric(ValeCaja.objects.filter(sesion=sesion_caja, tipooperacion=1).distinct().aggregate(valor=Sum('valor'))['valor'], 2)
                    valorcajadevuelto = null_to_numeric(ValeCaja.objects.filter(sesion=sesion_caja, tipooperacion=2).distinct().aggregate(valor=Sum('valor'))['valor'], 2)
                    reciboscaja = null_to_numeric(Pago.objects.filter(pagorecibocajainstitucion__isnull=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    notacreditointerna = null_to_numeric(Pago.objects.filter(pagonotacredito__isnull=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    cs = CierreSesionCaja(sesion=sesion_caja,
                                          bill100=form.cleaned_data['bill100'],
                                          bill50=form.cleaned_data['bill50'],
                                          bill20=form.cleaned_data['bill20'],
                                          bill10=form.cleaned_data['bill10'],
                                          bill5=form.cleaned_data['bill5'],
                                          bill2=form.cleaned_data['bill2'],
                                          bill1=form.cleaned_data['bill1'],
                                          enmonedas=form.cleaned_data['enmonedas'],
                                          deposito=deposito,
                                          transferencia=transferencia,
                                          cheque=cheques,
                                          tarjeta=tarjetas,
                                          recibocaja=reciboscaja,
                                          total=float(request.POST['totalcaja']),
                                          notacreditointerna=notacreditointerna,
                                          valecajaingreso=valorcajadevuelto,
                                          valecajaegreso=valorcajaentregado,
                                          fecha=datetime.now(),
                                          hora=datetime.now().time())
                    cs.save(request)
                    sesion_caja.abierta = False
                    sesion_caja.save(request)
                    log(u'Cierra sesion: %s - %s - %s' % (cs.fecha,cs.sesion,cs.total), request, "add")
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

            if action == 'addsesion':
                try:
                    data['title'] = u'Abrir sesión de cobranzas en caja'
                    form = SesionCajaForm()
                    form.adicionar(miscajas)
                    data['form'] = form
                    return render(request, "adm_caja/addsesion.html", data)
                except Exception as ex:
                    pass

            if action == 'addpapeleta':
                try:
                    data['title'] = u'Agregar papeleta'
                    data['cierre'] = cierre = CierreSesionCaja.objects.get(id=int(request.GET['id']))
                    data['form'] = PapeletaForm()
                    return render(request, "adm_caja/addpapeleta.html", data)
                except Exception as ex:
                    pass

            if action == 'editpapeleta':
                try:
                    data['title'] = u'Agregar papeleta'
                    data['papeleta'] = papeleta = PapeletaDeposito.objects.get(id=int(request.GET['id']))
                    data['form'] = PapeletaForm(initial={'cuentabanco': papeleta.cuentabanco,
                                                         'referencia': papeleta.referencia,
                                                         'valor': papeleta.valor})
                    return render(request, "adm_caja/editpapeleta.html", data)
                except Exception as ex:
                    pass

            if action == 'papeletas':
                try:
                    data['title'] = u'Papeletas'
                    data['cierre'] = cierre = CierreSesionCaja.objects.get(id=int(request.GET['id']))
                    data['papeletas'] = cierre.papeletas()
                    return render(request, "adm_caja/papeletas.html", data)
                except Exception as ex:
                    pass

            if action == 'delpapeleta':
                try:
                    data['title'] = u'Eliminar papeleta de depósito'
                    data['papeleta'] = PapeletaDeposito.objects.get(pk=request.GET['id'])
                    return render(request, "adm_caja/delpapeleta.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrarsesion':
                try:
                    data['title'] = u"Cierre de sesión de cobranzas en caja"
                    data['sesion_caja'] = sesion_caja = SesionCaja.objects.get(pk=request.GET['id'])
                    deposito = null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__datotransferenciadeposito__deposito=True, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    transferencia = null_to_numeric(Pago.objects.filter(pagotransferenciadeposito__datotransferenciadeposito__deposito=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    cheques = null_to_numeric(Pago.objects.filter(pagocheque__isnull=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    tarjetas = null_to_numeric(Pago.objects.filter(pagotarjeta__isnull=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    valorcajaentregado = null_to_numeric(ValeCaja.objects.filter(sesion=sesion_caja, tipooperacion=1).distinct().aggregate(valor=Sum('valor'))['valor'], 2)
                    valorcajadevuelto = null_to_numeric(ValeCaja.objects.filter(sesion=sesion_caja, tipooperacion=2).distinct().aggregate(valor=Sum('valor'))['valor'], 2)
                    reciboscaja = null_to_numeric(Pago.objects.filter(pagorecibocajainstitucion__isnull=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    notacreditointerna = null_to_numeric(Pago.objects.filter(pagonotacredito__isnull=False, sesion=sesion_caja, valido=True).aggregate(valor=Sum('valor'))['valor'], 2)
                    data['form'] = CierreSesionCajaForm(initial={'deposito': deposito,
                                                                 'transferencia': transferencia,
                                                                 'fondoinicial': sesion_caja.fondo,
                                                                 'cheque': cheques,
                                                                 'reciboscaja': reciboscaja,
                                                                 'notacreditointerna': notacreditointerna,
                                                                 'valecajadevuelto': valorcajadevuelto,
                                                                 'valecajaentregado': valorcajaentregado,
                                                                 'totalrecaudado': sesion_caja.total_sesion() - notacreditointerna,
                                                                 'tarjeta': tarjetas})
                    return render(request, "adm_caja/cerrarsesion.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Registro de sesiones de cobranza en caja'
                ids = None
                data['miscajas'] = miscajas
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    sesiones = SesionCaja.objects.filter(id=ids, caja__in=miscajas)
                else:
                    sesiones = SesionCaja.objects.filter(caja__in=miscajas)
                paging = MiPaginador(sesiones, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_caja':
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
                request.session['paginador_url'] = 'adm_caja'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['ids'] = ids if ids else ''
                data['page'] = page
                data['sesiones'] = page.object_list
                data['reporte_0'] = obtener_reporte('cierre_sesion_caja')
                data['reporte_1'] = obtener_reporte('listado_ingresos_caja')
                data['reporte_2'] = obtener_reporte('listado_ingresos_facturas')
                return render(request, "adm_caja/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
