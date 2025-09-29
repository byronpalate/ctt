# coding=utf-8

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import TransferenciaForm
from ctt.funciones import MiPaginador, url_back, bad_json, log, ok_json
from ctt.models import DatoTransferenciaDeposito


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'edit':
            try:
                form = TransferenciaForm(request.POST, request.FILES)
                if form.is_valid():
                    deposito = DatoTransferenciaDeposito.objects.get(pk=request.POST['id'])
                    if DatoTransferenciaDeposito.objects.filter(deposito=False, referencia=form.cleaned_data['referencia'], cuentabanco=form.cleaned_data['cuentabanco']).exclude(id=deposito.id).exists():
                        return bad_json(mensaje=u'Ya existe un depósito con esos datos.')
                    deposito.fechabanco = form.cleaned_data['fechabanco']
                    deposito.referencia = form.cleaned_data['referencia']
                    deposito.tipotransferencia = form.cleaned_data['tipotransferencia']
                    deposito.cuentabanco = form.cleaned_data['cuentabanco']
                    deposito.valor = form.cleaned_data['valor']
                    deposito.save()
                    log(u'Modifico deposito de inscripcion: %s' % deposito, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'edit':
                try:
                    data['title'] = u'Editar depósito o transferencia'
                    data['dep'] = dep = DatoTransferenciaDeposito.objects.get(pk=request.GET['id'])
                    data['form'] = TransferenciaForm(initial={'cuentabanco': dep.cuentabanco,
                                                              'valor': dep.valor,
                                                              'tipotransferencia': dep.tipotransferencia,
                                                              'referencia': dep.referencia,
                                                              'fechabanco': dep.fechabanco})
                    return render(request, "adm_transferencias/edit.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de transferencias'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    transferencias = DatoTransferenciaDeposito.objects.filter(Q(cuentabanco__numero__icontains=search) |
                                                                              Q(cuentabanco__banco__nombre__icontains=search) |
                                                                              Q(referencia__icontains=search), pagotransferenciadeposito__pagos__valido=True, deposito=False).order_by('-fecha').distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    transferencias = DatoTransferenciaDeposito.objects.filter(id=ids, pagotransferenciadeposito__pagos__valido=True, deposito=False).distinct().order_by('-fecha').distinct()
                else:
                    transferencias = DatoTransferenciaDeposito.objects.filter(deposito=False, pagotransferenciadeposito__pagos__valido=True).distinct().order_by('-fecha').distinct()
                paging = MiPaginador(transferencias, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_transferencias':
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
                request.session['paginador_url'] = 'adm_transferencias'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['transferencias'] = page.object_list
                return render(request, "adm_transferencias/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
