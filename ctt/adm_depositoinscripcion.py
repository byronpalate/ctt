# coding=utf-8

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import RequestContext

from decorators import secure_module, last_access
from settings import URL_APP_DATAFAST
from ctt.commonviews import adduserdata
from ctt.forms import DepositoInscripcionForm, ReasignarDepositosResponsableForm, ObservacionesPlanoficacionForm
from ctt.funciones import MiPaginador, url_back, ok_json, bad_json, log
from ctt.models import DepositoInscripcion, Sede, \
    Carrera, Modalidad, null_to_text
from ctt.tasks import send_mail


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

        if action == 'autorizar':
            try:
                deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                deposito.autorizado = True
                deposito.save(request)
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'desautorizar':
            try:
                deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                deposito.autorizado = False
                deposito.save(request)
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'edit':
            try:
                form = DepositoInscripcionForm(request.POST, request.FILES)
                if form.is_valid():
                    persona = request.session['persona']
                    deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                    if DepositoInscripcion.objects.filter(cuentabanco=form.cleaned_data['cuentabanco'], fecha=form.cleaned_data['fecha'], referencia=form.cleaned_data['referencia'], ventanilla=True if form.cleaned_data['ventanilla'] else False).exclude(id=deposito.id).exists():
                        return bad_json(mensaje=u'Ya existe ese numero de referencia ingresado')
                    deposito.fecha = form.cleaned_data['fecha']
                    deposito.ventanilla = True if form.cleaned_data['ventanilla'] else False
                    deposito.movilweb = True if form.cleaned_data['movilweb'] else False
                    deposito.deposito = True if form.cleaned_data['ventanilla'] else False
                    deposito.referencia = form.cleaned_data['referencia']
                    deposito.cuentabanco = form.cleaned_data['cuentabanco']
                    deposito.valor = form.cleaned_data['valor']
                    deposito.motivo = form.cleaned_data['motivo']
                    deposito.procesado = False
                    deposito.estadoprocesado = 3
                    deposito.save(request)
                    from ocr.deposito_ocr import procesar_deposito_imagen
                    try:
                        procesar_deposito_imagen(deposito)
                    except Exception as e:
                        transaction.set_rollback(True)
                        return bad_json(mensaje=f"OCR error: {e}")
                    log(u'Edito deposito de inscripcion: %s' % deposito, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'reasignar':
            try:
                form = ReasignarDepositosResponsableForm(request.POST)
                if form.is_valid():
                    deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                    deposito.responsable = form.cleaned_data['responsable']
                    deposito.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'marcarprocesado':
            try:
                deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                deposito.liquidar()
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'observaciones':
            try:
                deposito = DepositoInscripcion.objects.get(pk=request.POST['id'])
                form = ObservacionesPlanoficacionForm(request.POST)
                if form.is_valid():
                    if len(null_to_text(form.cleaned_data['observaciones'])) > 0:
                        deposito.observacion = True
                        send_mail(subject='Notificación de error en el deposito.',
                                  html_template='emails/notificaciondeposito.html',
                                  data={'deposito': deposito,'observaciones': form.cleaned_data['observaciones']},
                                  recipient_list=[deposito.inscripcion.persona])
                    else:
                        deposito.observacion = False
                    deposito.observaciones = form.cleaned_data['observaciones']
                    deposito.save(request)
                    log(u'Desaprobo deposito: %s' % deposito, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'autorizar':
                try:
                    data['title'] = u'Autorizar depósito'
                    data['deposito'] = deposito = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_depositoinscripcion/autorizar.html", data)
                except Exception as ex:
                    pass

            if action == 'desautorizar':
                try:
                    data['title'] = u'Desutorizar depósito'
                    data['deposito'] = deposito = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_depositoinscripcion/desautorizar.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar deposito'
                    data['deposito'] = deposito = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    form = DepositoInscripcionForm(initial={'cuentabanco': deposito.cuentabanco,
                                                            'motivo': deposito.motivo,
                                                            'transferencia': False if deposito.deposito else True,
                                                            'valor': deposito.valor,
                                                            'referencia': deposito.referencia,
                                                            'fecha': deposito.fecha,
                                                            'ventanilla': deposito.ventanilla,
                                                            'movilweb': deposito.movilweb})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_depositoinscripcion/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'marcarprocesado':
                try:
                    data['title'] = u'Liquidar depósito'
                    data['deposito'] = deposito = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = deposito.inscripcion
                    return render(request, "adm_depositoinscripcion/marcarprocesado.html", data)
                except Exception as ex:
                    pass

            if action == 'reasignar':
                try:
                    data['title'] = u'Asignación de responsable'
                    data['deposito'] = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = ReasignarDepositosResponsableForm()
                    return render(request, "adm_depositoinscripcion/reasignar.html", data)
                except Exception as ex:
                    pass

            if action == 'observaciones':
                try:
                    data['title'] = u' Observaciones en el depósito'
                    data['deposito'] = deposito = DepositoInscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = ObservacionesPlanoficacionForm(initial={'observaciones': deposito.observaciones})
                    return render(request, "adm_depositoinscripcion/observaciones.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de depósitos'
                search = None
                ids = None
                depositos = DepositoInscripcion.objects.filter(valor__gt=0).order_by('-fecha_creacion')
                depositos_sel = 0
                if not 'adm_depositoinscripcion_estado_sel' in request.session:
                    request.session['adm_depositoinscripcion_estado_sel'] = 0
                if not 'adm_depositoinscripcion_sede_sel' in request.session:
                    request.session['adm_depositoinscripcion_sede_sel'] = 0
                if not 'adm_depositoinscripcion_carrera_sel' in request.session:
                    request.session['adm_depositoinscripcion_carrera_sel'] = 0
                if not 'adm_depositoinscripcion_modalidad_sel' in request.session:
                    request.session['adm_depositoinscripcion_modalidad_sel'] = 0
                if 'id_e' in request.GET:
                    request.session['adm_depositoinscripcion_estado_sel'] = int(request.GET['id_e'])
                if int(request.session['adm_depositoinscripcion_estado_sel']) > 0:
                    if int(request.session['adm_depositoinscripcion_estado_sel']) == 1:
                        depositos = depositos.filter(estadoprocesado=1)
                    elif int(request.session['adm_depositoinscripcion_estado_sel']) == 2:
                        depositos = depositos.filter(estadoprocesado=2)
                    elif int(request.session['adm_depositoinscripcion_estado_sel']) == 3:
                        depositos = depositos.filter(estadoprocesado=3)
                data['estado_sel'] = request.session['adm_depositoinscripcion_estado_sel']
                if 'id_s' in request.GET:
                    request.session['adm_depositoinscripcion_sede_sel'] = int(request.GET['id_s'])
                if  int(request.session['adm_depositoinscripcion_sede_sel']) > 0:
                    depositos = depositos.filter(inscripcion__sede__id=int(request.session['adm_depositoinscripcion_sede_sel']))
                data['sede_sel'] = request.session['adm_depositoinscripcion_sede_sel']
                if 'id_c' in request.GET:
                    request.session['adm_depositoinscripcion_carrera_sel'] = int(request.GET['id_c'])
                if int(request.session['adm_depositoinscripcion_carrera_sel']) > 0:
                    depositos = depositos.filter(inscripcion__carrera__id=int(request.session['adm_depositoinscripcion_carrera_sel']))
                data['carrera_sel'] = request.session['adm_depositoinscripcion_carrera_sel']
                if 'id_m' in request.GET:
                    request.session['adm_depositoinscripcion_modalidad_sel'] = int(request.GET['id_m'])
                if int(request.session['adm_depositoinscripcion_modalidad_sel']) > 0:
                    depositos = depositos.filter(inscripcion__modalidad__id=int(request.session['adm_depositoinscripcion_modalidad_sel']))
                data['modalidad_sel'] = request.session['adm_depositoinscripcion_modalidad_sel']
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    if len(search.split(' ')) >= 2:
                        ss = search.split(' ')
                        depositos = depositos.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                     Q(inscripcion__persona__apellido2__icontains=ss[1])).distinct()
                    else:
                        depositos = depositos.filter(Q(inscripcion__persona__apellido1__icontains=search) |
                                                     Q(inscripcion__persona__apellido2__icontains=search) |
                                                     Q(inscripcion__persona__nombre1__icontains=search) |
                                                     Q(inscripcion__persona__nombre2__icontains=search) |
                                                     Q(cuentabanco__banco__nombre__icontains=search) |
                                                     Q(referencia__icontains=search)).distinct().order_by('-fecha_creacion')
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    depositos = depositos.filter(id=ids).order_by('-fecha_creacion')
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
                request.session['paginador_url'] = 'adm_depositoinscripcion'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['depositos'] = page.object_list
                data['sedes'] = Sede.objects.all()
                data['carreras'] = Carrera.objects.all()
                data['modalidades'] = Modalidad.objects.all()
                data['path'] = URL_APP_DATAFAST
                return render(request, "adm_depositoinscripcion/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
