# coding=utf-8

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import DepositoForm
from ctt.funciones import MiPaginador, url_back, log, bad_json, ok_json
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
                form = DepositoForm(request.POST, request.FILES)
                if form.is_valid():
                    deposito = DatoTransferenciaDeposito.objects.get(pk=request.POST['id'])
                    if DatoTransferenciaDeposito.objects.filter(deposito=True, referencia=form.cleaned_data['referencia'], cuentabanco=form.cleaned_data['cuentabanco']).exclude(id=deposito.id).exists():
                        return bad_json(mensaje=u'Ya existe un depósito con esos datos.')
                    deposito.fechabanco = form.cleaned_data['fechabanco']
                    deposito.referencia = form.cleaned_data['referencia']
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

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'edit':
                try:
                    data['title'] = u'Editar depósito o transferencia'
                    data['dep'] = dep = DatoTransferenciaDeposito.objects.get(pk=request.GET['id'])
                    data['form'] = DepositoForm(initial={'cuentabanco': dep.cuentabanco,
                                                         'valor': dep.valor,
                                                         'referencia': dep.referencia,
                                                         'fechabanco': dep.fechabanco})
                    return render(request, "adm_depositos/edit.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de depósitos'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    depositos = DatoTransferenciaDeposito.objects.filter(Q(cuentabanco__numero__icontains=search) |
                                                                         Q(cuentabanco__banco__nombre__icontains=search) |
                                                                         Q(pagotransferenciadeposito__pagos__rubro__inscripcion__persona__nombre1__icontains=search) |
                                                                         Q(pagotransferenciadeposito__pagos__rubro__inscripcion__persona__nombre2__icontains=search) |
                                                                         Q(pagotransferenciadeposito__pagos__rubro__inscripcion__persona__apellido1__icontains=search) |
                                                                         Q(pagotransferenciadeposito__pagos__rubro__inscripcion__persona__apellido2__icontains=search) |
                                                                         Q(cuentabanco__banco__nombre__icontains=search) |
                                                                         Q(referencia__icontains=search), deposito=True).distinct().order_by('-fecha')
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    depositos = DatoTransferenciaDeposito.objects.filter(id=ids, deposito=True)
                else:
                    depositos = DatoTransferenciaDeposito.objects.filter(deposito=True)
                paging = MiPaginador(depositos, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_depositos':
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
                request.session['paginador_url'] = 'adm_depositos'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['depositos'] = page.object_list
                return render(request, "adm_depositos/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
