# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import ReciboCajaForm, EliminarRubroForm, ActividadInscripcionForm
from ctt.funciones import log, MiPaginador, url_back, bad_json, ok_json
from ctt.models import ReciboCajaInstitucion, ReciboCajaLiquidado


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
                recibo = ReciboCajaInstitucion.objects.get(pk=request.POST['id'])
                form = EliminarRubroForm(request.POST)
                if form.is_valid():
                    liquidado = ReciboCajaLiquidado(recibocaja=recibo,
                                                    fecha=datetime.now().date(),
                                                    motivo=form.cleaned_data['motivo'],
                                                    valor=recibo.saldo)
                    liquidado.save(request)
                    recibo.save(request)
                    log(u"Liquido recibo de caja: %s" % recibo, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except:
                transaction.set_rollback(True)
                return bad_json(error=1)

        if action == 'transferir':
            try:
                form = ActividadInscripcionForm(request.POST)
                if form.is_valid():
                    recibo = ReciboCajaInstitucion.objects.get(pk=request.POST['id'])
                    recibo.inscripcion_id = int(form.cleaned_data['inscripcion'])
                    recibo.save(request)
                    log(u"Transfirio recibo de caja: %s" % recibo, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'add':
            try:
                form = ReciboCajaForm(request.POST)
                if form.is_valid():
                    recibo = ReciboCajaInstitucion(inscripcion_id=int(form.cleaned_data['inscripcion']),
                                                   motivo=form.cleaned_data['motivo'],
                                                   valorinicial=form.cleaned_data['valorinicial'],
                                                   hora=datetime.now().time(),
                                                   fecha=form.cleaned_data['fecha'])
                    recibo.save(request)
                    log(u"Agrego recibo de caja: %s" % recibo, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edit':
            try:
                form = ReciboCajaForm(request.POST)
                if form.is_valid():
                    recibo = ReciboCajaInstitucion.objects.get(pk=request.POST['id'])
                    recibo.inscripcion_id = int(form.cleaned_data['inscripcion'])
                    recibo.motivo = form.cleaned_data['motivo']
                    recibo.valorinicial = form.cleaned_data['valorinicial']
                    recibo.hora = datetime.now().time()
                    recibo.fecha = form.cleaned_data['fecha']
                    recibo.save(request)
                    log(u"Modifico recibo de caja: %s" % recibo, request, "edit")
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

            if action == 'transferir':
                try:
                    data['title'] = u'Transferir recibo de caja'
                    data['recibo'] = recibo = ReciboCajaInstitucion.objects.get(pk=request.GET['id'])
                    form = ActividadInscripcionForm(initial={"inscripcion": recibo.inscripcion.id if recibo.inscripcion else None})
                    form.transferir(recibo)
                    data['form'] = form
                    return render(request, "adm_recibo_caja/transferir.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Agregar recibo de caja'
                    data['form'] = ReciboCajaForm()
                    return render(request, "adm_recibo_caja/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar recibo de caja'
                    data['recibo'] = recibo = ReciboCajaInstitucion.objects.get(pk=request.GET['id'])
                    form = ReciboCajaForm(initial={'fecha': recibo.fecha,
                                                   'inscripcion': recibo.inscripcion.id if recibo.inscripcion else None,
                                                   'motivo': recibo.motivo,
                                                   'valorinicial': recibo.valorinicial})
                    form.transferir(recibo)
                    data['form'] = form
                    return render(request, "adm_recibo_caja/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'liquidar':
                try:
                    data['title'] = u'Liquidar recibo de caja'
                    data['recibo'] = recibo = ReciboCajaInstitucion.objects.get(pk=request.GET['id'])
                    data['form'] = EliminarRubroForm()
                    return render(request, "adm_recibo_caja/liquidar.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de recibos de caja'
                persona = request.session['persona']
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    recibos = ReciboCajaInstitucion.objects.filter(Q(motivo__icontains=search) |
                                                                   Q(inscripcion__persona__pasaporte__icontains=search) |
                                                                   Q(inscripcion__persona__pasaporte__icontains=search) |
                                                                   Q(inscripcion__persona__nombre1__icontains=search) |
                                                                   Q(inscripcion__persona__nombre2__icontains=search) |
                                                                   Q(inscripcion__persona__apellido1__icontains=search) |
                                                                   Q(inscripcion__persona__apellido2__icontains=search)).distinct().order_by('-fecha')
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    recibos = ReciboCajaInstitucion.objects.filter(id=ids).order_by('-fecha')
                else:
                    recibos = ReciboCajaInstitucion.objects.all().order_by('-fecha')
                paging = MiPaginador(recibos, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_recibo_caja':
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
                request.session['paginador_url'] = 'adm_recibo_caja'
                data['paging'] = paging
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['recibos'] = page.object_list
                return render(request, "adm_recibo_caja/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
