# coding=utf-8
import json
from datetime import *

import requests
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from settings import URL_NOTAS_CREDITO
from ctt.commonviews import adduserdata
from ctt.forms import NotaCreditoForm, ImportarNotaCreditoForm, NotaCreditoImportadaForm, LiquidarNotaCreditoForm
from ctt.funciones import MiPaginador, log, url_back, ok_json, bad_json
from ctt.models import NotaCredito, null_to_numeric, Pago, mi_institucion, NotaCreditoImportadas, Persona, \
    NotaCreditoaLiquidado


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'liquidar':
            try:
                notacredito = NotaCredito.objects.get(pk=request.POST['id'])
                form = LiquidarNotaCreditoForm(request.POST)
                if form.is_valid():
                    liquidado = NotaCreditoaLiquidado(notacredito=notacredito,
                                                      fecha=datetime.now().date(),
                                                      motivo=form.cleaned_data['motivo'],
                                                      valor=notacredito.saldo)
                    liquidado.save(request)
                    notacredito.save(request)
                    log(u"Liquido nota de credito: %s" % notacredito, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except:
                transaction.set_rollback(True)
                return bad_json(error=1)

        if action == 'eliminar':
            try:
                nc = NotaCredito.objects.get(pk=request.POST['id'])
                log(u"Elimino nota de credito: %s" % nc, request, "del")
                nc.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'addnotacredito':
            try:
                form = NotaCreditoForm(request.POST)
                if form.is_valid():
                    pe = form.cleaned_data['puntoemision']
                    numero = pe.numeracion() + "-" + form.cleaned_data['numero'].zfill(9)
                    if NotaCredito.objects.filter(numero=numero, electronica=pe.facturaelectronica).exists():
                        return bad_json(mensaje=u'Ya existe ese numero registrado.')
                    nc = NotaCredito(fecha=form.cleaned_data['fecha'],
                                     inscripcion_id=int(form.cleaned_data['inscripcion']),
                                     motivo=form.cleaned_data['motivo'],
                                     numero=numero,
                                     electronica=pe.facturaelectronica,
                                     valorinicial=form.cleaned_data['valorinicial'])
                    nc.save(request)
                    nc.actualiza_valor()
                else:
                    return bad_json(error=6)
                log(u'Adicionó nota de crédito: %s' % nc, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editnotacredito':
            try:
                form = NotaCreditoForm(request.POST)
                nc = NotaCredito.objects.get(pk=int(request.POST['id']))
                if form.is_valid():
                    if nc.tiene_pagos():
                        return bad_json(mensaje=u'Ya existe pagos registrados en esta nota de credito.')
                    nc.inscripcion_id = int(form.cleaned_data['inscripcion'])
                    nc.fecha = form.cleaned_data['fecha']
                    nc.valorinicial = form.cleaned_data['valorinicial']
                    nc.motivo = form.cleaned_data['motivo']
                    nc.save(request)
                    nc.actualiza_valor()
                else:
                    return bad_json(error=6)
                log(u'Modifico nota de crédito: %s' % nc, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editncimportada':
            try:
                form = NotaCreditoImportadaForm(request.POST)
                nc = NotaCreditoImportadas.objects.get(pk=int(request.POST['id']))
                if form.is_valid():
                    if form.cleaned_data['inscripcion']:
                        nc.inscripcion_id = int(form.cleaned_data['inscripcion'])
                    else:
                        nc.inscripcion = None
                    nc.save(request)
                else:
                    return bad_json(error=6)
                log(u'Modifico nota de crédito importada: %s' % nc, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'pagos':
            try:
                data = {}
                data['notacredito'] = notacredito = NotaCredito.objects.get(pk=int(request.POST['id']))
                data['pagos'] = Pago.objects.filter(pagonotacredito__notacredito=notacredito, valido=True).distinct()
                template = get_template("adm_notacredito/pagos.html")
                json_content = template.render(data)
                return ok_json({'html': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=3)

        if action == 'importar':
            try:
                form = ImportarNotaCreditoForm(request.POST)
                if form.is_valid():
                    fecha = form.cleaned_data['fecha']
                    NotaCreditoImportadas.objects.filter(fecha=fecha).delete()
                    institucion = mi_institucion()
                    r = requests.get(URL_NOTAS_CREDITO, params={'fecha': fecha.strftime("%d-%m-%Y"), 'ruc': institucion.ruc}, verify=False)
                    valores = json.loads(r._content)
                    for nota in valores['result']:
                        persona = None
                        inscripcion = None
                        if Persona.objects.filter(Q(cedula=nota['CLIENTE_ID']) | Q(pasaporte=nota['CLIENTE_ID'])).exists():
                            persona = Persona.objects.filter(Q(cedula=nota['CLIENTE_ID']) | Q(pasaporte=nota['CLIENTE_ID']))[0]
                            if persona.inscripcion_set.exists():
                                inscripcion = persona.inscripcion_set.all().order_by('-fecha')[0]
                        if not NotaCreditoImportadas.objects.filter(numero=nota['NUMERO'], electronica=nota['ESELECTRONICA']=="SI").exists() and not NotaCredito.objects.filter(numero=nota['NUMERO'], electronica=nota['ESELECTRONICA']=="SI").exists():
                            creditoimportar = NotaCreditoImportadas(fecha=fecha,
                                                                    persona=persona,
                                                                    inscripcion=inscripcion,
                                                                    numero=nota['NUMERO'],
                                                                    motivo=nota['MOTIVO'],
                                                                    consaldo=True,
                                                                    valor=null_to_numeric(nota['TOTAL'], 2),
                                                                    electronica=nota['ESELECTRONICA']=="SI",
                                                                    esbecaoayuda=True if nota['ESBECAOAYUDA']== 'SI' else False,
                                                                    periodo=nota['RUBROS'][0]['PERIODOACADEMICO'],
                                                                    motivootros=nota['MOTIVOOTROS'])
                            creditoimportar.save()
                    request.session['fechageneracionnotacredito'] = form.cleaned_data['fecha']
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=3)

        if action == 'generarnotacredito':
            try:
                fecha = request.session['fechageneracionnotacredito']
                lista = json.loads(request.POST['lista_items1'])
                for nota in NotaCreditoImportadas.objects.filter(id__in=[int(x) for x in lista]):
                    if not NotaCredito.objects.filter(numero=nota.numero, electronica=nota.electronica).exists():
                        notacredito = NotaCredito(fecha=fecha,
                                                  inscripcion=nota.inscripcion,
                                                  numero=nota.numero,
                                                  motivo=nota.motivo,
                                                  electronica=nota.electronica,
                                                  valorinicial=nota.valor,
                                                  saldo=nota.valor,
                                                  esbecaoayuda=nota.esbecaoayuda,
                                                  periodo=nota.periodo,
                                                  motivootros=nota.motivootros)
                        notacredito.save(request)
                        if not nota.consaldo:
                            liquidado = NotaCreditoaLiquidado(notacredito= notacredito,
                                                              fecha=fecha,
                                                              motivo='LIQUIDADO DESDE IMPORTACION',
                                                              valor=notacredito.valorinicial)
                            liquidado.save()
                            notacredito.save()
                        nota.procesada = True
                        nota.save(request)
                        log(u'Importo nota de crédito: %s' % notacredito, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'saldo':
            try:
                notacredito = NotaCreditoImportadas.objects.get(pk=request.POST['id'])
                notacredito.consaldo = request.POST['val'] == 'true'
                notacredito.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'liquidar':
                try:
                    data['title'] = u'Eliminar nota de crédito'
                    data['notacredito'] = NotaCredito.objects.get(pk=request.GET['id'])
                    data['form'] = LiquidarNotaCreditoForm()
                    return render(request, "adm_notacredito/liquidar.html", data)
                except Exception as ex:
                    pass

            if action == 'addnotacredito':
                try:
                    data['title'] = u'Nueva nota de crédito'
                    data['form'] = NotaCreditoForm()
                    return render(request, "adm_notacredito/addnotacredito.html", data)
                except Exception as ex:
                    pass

            if action == 'editncimportada':
                try:
                    data['title'] = u'Editar nota de credito importada'
                    data['notacredito'] = notacredito = NotaCreditoImportadas.objects.get(pk=int(request.GET['id']))
                    form = NotaCreditoImportadaForm(initial={'inscripcion': notacredito.inscripcion.id if notacredito.inscripcion else 0})
                    form.editar(notacredito)
                    data['form'] = form
                    return render(request, "adm_notacredito/editncimportada.html", data)
                except Exception as ex:
                    pass

            if action == 'editnotacredito':
                try:
                    data['title'] = u'Editar Nota Credito '
                    form = NotaCreditoForm()
                    data['notacredito'] = nc = NotaCredito.objects.get(pk=request.GET['id'])
                    form = NotaCreditoForm(initial={'inscripcion': nc.inscripcion.id,
                                                    'motivo': nc.motivo,
                                                    'fecha': nc.fecha,
                                                    'numero': nc.numero,
                                                    'valorinicial': nc.valorinicial})
                    form.editar(nc)
                    data['form'] = form
                    return render(request, "adm_notacredito/editnotacredito.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminar':
                try:
                    data['title'] = u'Eliminar nota de credito'
                    data['nc'] = NotaCredito.objects.get(pk=request.GET['id'])
                    return render(request, "adm_notacredito/eliminar.html", data)
                except Exception as ex:
                    pass

            if action == 'generarnotacredito':
                try:
                    data['title'] = u'Generar notas de créditos seleccionadas'
                    return render(request, "adm_notacredito/generarnotacredito.html", data)
                except Exception as ex:
                    pass

            if action == 'generar':
                try:
                    data['title'] = u'Generar notas de crédito'
                    data['fecha'] = fecha = request.session['fechageneracionnotacredito']
                    data['notasdecredito'] = NotaCreditoImportadas.objects.filter(fecha=fecha, procesada=False)
                    return render(request, "adm_notacredito/generar.html", data)
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar notas de créditos'
                    data['form'] = ImportarNotaCreditoForm()
                    return render(request, "adm_notacredito/importar.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de notas de crédito'
                search = None
                ids = None
                if 'id' in request.GET:
                    ids = int(request.GET['id'])
                    notascredito = NotaCredito.objects.filter(id=ids)
                elif 's' in request.GET:
                    search = request.GET['s'].strip()
                    notascredito = NotaCredito.objects.filter(Q(inscripcion__persona__nombre1__icontains=search) |
                                                              Q(inscripcion__persona__nombre2__icontains=search) |
                                                              Q(inscripcion__persona__apellido1__icontains=search) |
                                                              Q(inscripcion__persona__apellido2__icontains=search) |
                                                              Q(inscripcion__persona__cedula__icontains=search) |
                                                              Q(inscripcion__persona__pasaporte__icontains=search) |
                                                              Q(numero__icontains=search)).distinct()
                else:
                    notascredito = NotaCredito.objects.all()
                paging = MiPaginador(notascredito, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_notacredito':
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
                request.session['paginador_url'] = 'adm_notacredito'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['notascredito'] = page.object_list
                return render(request, "adm_notacredito/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
