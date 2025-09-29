# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import NOTA_ESTADO_REPROBADO, PERM_DIRECTOR_SIS
from ctt.commonviews import adduserdata
from ctt.forms import PeriodoForm, CronogramaMatriculacionForm

from ctt.funciones import MiPaginador, log, bad_json, ok_json, url_back
from ctt.models import Periodo, Matricula, MateriaAsignada, \
    ModeloEvaluativo


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if persona.id in PERM_DIRECTOR_SIS:
        data['PERM_DIRECTOR_SIS'] = True
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                periodoactual = request.session['periodo']
                form = PeriodoForm(request.POST)

                if form.is_valid():
                    # if form.cleaned_data['parasolicitudes']:
                    #     if Periodo.objects.filter(parasolicitudes=True).exists():
                    #         return bad_json(mensaje=u"Solo puede existir un período activo para solicitudes.")
                    periodo = Periodo(nombre=form.cleaned_data['nombre'],
                                      inicio=form.cleaned_data['inicio'],
                                      fin=form.cleaned_data['fin'],
                                      activo=True,
                                      tipo=form.cleaned_data['tipo'],
                                      valida_asistencia=form.cleaned_data['valida_asistencia'],
                                      extendido=form.cleaned_data['extendido'],
                                      inicio_agregacion=form.cleaned_data['inicio_agregacion'],
                                      limite_agregacion=form.cleaned_data['limite_agregacion'],
                                      # parasolicitudes=form.cleaned_data['parasolicitudes'],
                                      # inicio_solicitudes=form.cleaned_data['inicio_solicitudes'],
                                      # limite_solicitudes=form.cleaned_data['limite_solicitudes']
                                      )
                    periodo.save(request)
                    periodo.distributivo_horas()
                    log(u'Adicionado periodo: %s' % periodo, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addperiodosolicitud':
            try:
                periodoactual = request.session['periodo']
                form = PeriodoSolicitudForm(request.POST)
                if form.is_valid():
                    periodo = PeriodoSolicitud(nombre=form.cleaned_data['nombre'],
                                               inicio=form.cleaned_data['inicio'],
                                               fin=form.cleaned_data['fin'],
                                               activo=True,
                                               cerrado=True)
                    periodo.save(request)
                    log(u'Adicionado periodo solicitud: %s' % periodo, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addcronograma':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                form = CronogramaMatriculacionForm(request.POST)
                if form.is_valid():
                    if PeriodoMatriculacion.objects.filter(periodo=periodo, nivelmalla=form.cleaned_data['nivelmalla'],
                                                           carrera=form.cleaned_data['carrera'],
                                                           modalidad=form.cleaned_data['modalidad']).exists():
                        return bad_json(mensaje=u"Ya existe un cronograma de matriculación con estos datos.")
                    periodo = PeriodoMatriculacion(periodo=periodo,
                                                   nivelmalla=form.cleaned_data['nivelmalla'],
                                                   carrera=form.cleaned_data['carrera'],
                                                   modalidad=form.cleaned_data['modalidad'],
                                                   fecha_inicio=form.cleaned_data['inicio'],
                                                   fecha_fin=form.cleaned_data['fin'])
                    periodo.save(request)
                    log(u'Adicionado periodo de matriculacion: %s' % periodo, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addcronogramapre':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                form = CronogramaMatriculacionForm(request.POST)
                if form.is_valid():
                    if PeriodoPreMatriculacion.objects.filter(periodo=periodo, nivelmalla=form.cleaned_data['nivelmalla'],
                                                              carrera=form.cleaned_data['carrera'],
                                                              modalidad=form.cleaned_data['modalidad']).exists():
                        return bad_json(mensaje=u"Ya existe un cronograma de pre matriculación con estos datos.")
                    periodo = PeriodoPreMatriculacion(periodo=periodo,
                                                      nivelmalla=form.cleaned_data['nivelmalla'],
                                                      carrera=form.cleaned_data['carrera'],
                                                      modalidad=form.cleaned_data['modalidad'],
                                                      fecha_inicio=form.cleaned_data['inicio'],
                                                      fecha_fin=form.cleaned_data['fin'])
                    periodo.save(request)
                    log(u'Adicionado periodo de prematriculacion: %s' % periodo, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editcronograma':
            try:
                cronograma = PeriodoMatriculacion.objects.get(pk=request.POST['id'])
                form = CronogramaMatriculacionForm(request.POST)
                if form.is_valid():
                    cronograma.fecha_inicio = form.cleaned_data['inicio']
                    cronograma.fecha_fin = form.cleaned_data['fin']
                    cronograma.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editcronogramapre':
            try:
                cronograma = PeriodoPreMatriculacion.objects.get(pk=request.POST['id'])
                form = CronogramaMatriculacionForm(request.POST)
                if form.is_valid():
                    cronograma.fecha_inicio = form.cleaned_data['inicio']
                    cronograma.fecha_fin = form.cleaned_data['fin']
                    cronograma.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edit':
            try:
                form = PeriodoForm(request.POST)
                if form.is_valid():
                    # if form.cleaned_data['parasolicitudes']:
                    #     if Periodo.objects.filter(parasolicitudes=True).exclude(pk=request.POST['id']).exists():
                    #         return bad_json(mensaje=u"Solo puede existir un período activo para solicitudes.")
                    periodo = Periodo.objects.get(pk=request.POST['id'])
                    if periodo.nivel_set.filter(fin__gt=form.cleaned_data['fin']).exists():
                        return bad_json(mensaje=u"La fecha fin no puede ser menor a un nivel existente.")
                    if periodo.nivel_set.filter(inicio__lt=form.cleaned_data['inicio']).exists():
                        return bad_json(mensaje=u"La fecha inicio no puede ser mayor a un nivel existente.")
                    if form.cleaned_data['fin'] <= form.cleaned_data['inicio']:
                        return bad_json(mensaje=u"Fechas incorrectas.")
                    if form.cleaned_data['fin'] < form.cleaned_data['limite_agregacion']:
                        return bad_json(mensaje=u"Fecha fin incorrecta.")
                    periodo.nombre = form.cleaned_data['nombre']
                    periodo.inicio = form.cleaned_data['inicio']
                    periodo.fin = form.cleaned_data['fin']
                    periodo.activo = True
                    periodo.tipo = form.cleaned_data['tipo']
                    periodo.valida_asistencia = form.cleaned_data['valida_asistencia']
                    periodo.extendido = form.cleaned_data['extendido']
                    periodo.inicio_agregacion = form.cleaned_data['inicio_agregacion']
                    periodo.limite_agregacion = form.cleaned_data['limite_agregacion']
                    # periodo.parasolicitudes = form.cleaned_data['parasolicitudes']
                    # periodo.inicio_solicitudes = form.cleaned_data['inicio_solicitudes']
                    # periodo.limite_solicitudes = form.cleaned_data['limite_solicitudes']
                    periodo.save(request)
                    log(u"Edito periodo: %s" % periodo, request, "del")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editperiodosolicitudperiodo':
            try:
                form = PeriodoSolicitudPeriodoForm(request.POST)
                if form.is_valid():
                    periodo = Periodo.objects.get(pk=request.POST['id'])
                    if form.cleaned_data['activo']:
                        if Periodo.objects.filter(parasolicitudes=True).exclude(pk=request.POST['id']).exists():
                            return bad_json(mensaje=u"Solo puede existir un período activo para solicitudes.")
                    periodo.inicio_solicitud = form.cleaned_data['inicio_solicitud']
                    periodo.fin_solicitud = form.cleaned_data['fin_solicitud']
                    periodo.save(request)
                    log(u"Edito periodo: %s" % periodo, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editperiodosolicitud':
            try:
                form = PeriodoSolicitudForm(request.POST)
                if form.is_valid():
                    periodo = PeriodoSolicitud.objects.get(pk=request.POST['id'])
                    if form.cleaned_data['fin'] <= form.cleaned_data['inicio']:
                        return bad_json(mensaje=u"Fechas incorrectas.")
                    periodo.nombre = form.cleaned_data['nombre']
                    periodo.inicio = form.cleaned_data['inicio']
                    periodo.fin = form.cleaned_data['fin']
                    periodo.activo = form.cleaned_data['activo']
                    periodo.activo = form.cleaned_data['activo']
                    periodo.cerrado = form.cleaned_data['cerrado']
                    periodo.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'actualizarcalificacion':
            try:
                for ma in MateriaAsignada.objects.filter(matricula__id=int(request.POST['maid']), estado__id=NOTA_ESTADO_REPROBADO):
                    ma.actualiza_estado()
                    if ma.materia.cerrado:
                        ma.cierre_materia_asignada()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'matriculasmora':
            try:
                lista = request.POST['lista']
                elementos = lista.split(';')
                matriculasseleccionadas = Matricula.objects.filter(id__in=[int(x) for x in elementos])
                for matricula in matriculasseleccionadas:
                    if matricula.tiene_rubros_pagados():
                        transaction.set_rollback(True)
                        return bad_json(mensaje=u"El estudiante %s tiene rubros pendientes de pago." % matricula.inscripcion.persona.nombre_completo())
                    log(u"Elimino matricula con mora: %s" % matricula, request, "del")
                    matricula.eliminar_rubros_matricula()
                    matricula.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delperiodo':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                log(u"Elimino periodo: %s" % periodo, request, "del")
                periodo.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delperiodosolicitud':
            try:
                periodo = PeriodoSolicitud.objects.get(pk=request.POST['id'])
                log(u"Elimino periodo solicitud: %s" % periodo, request, "del")
                periodo.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delcronograma':
            try:
                cronograma = PeriodoMatriculacion.objects.get(pk=request.POST['id'])
                log(u"Elimino cronograma de matriculacion: %s" % cronograma.periodo, request, "del")
                cronograma.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delcronogramapre':
            try:
                cronograma = PeriodoPreMatriculacion.objects.get(pk=request.POST['id'])
                log(u"Elimino cronograma de prematriculación: %s" % cronograma.periodo, request, "del")
                cronograma.delete()
                return ok_json({"id": cronograma.periodo.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'habprematricula':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                periodo.prematriculacionactiva = True
                periodo.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deshabprematricula':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                periodo.prematriculacionactiva = False
                periodo.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deshabmatricula':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                periodo.matriculacionactiva = False
                periodo.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'habmatricula':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                periodo.matriculacionactiva = True
                periodo.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'listaactualizacionmatriculas':
            try:
                periodo = Periodo.objects.get(pk=request.POST['pid'])
                matriculas = []
                cantidad = 0
                for modelo in ModeloEvaluativo.objects.filter(materia__nivel__periodo=periodo).distinct():
                    notaminima = modelo.notaaprobar
                    asistenciaminima = modelo.asistenciaaprobar
                    for ma in MateriaAsignada.objects.filter(estado__id=NOTA_ESTADO_REPROBADO, matricula__nivel__periodo=periodo, materia__modeloevaluativo=modelo, notafinal__gte=notaminima, asistenciafinal__gte=asistenciaminima).distinct():
                        if ma.matricula not in matriculas:
                            matriculas.append(ma.matricula)
                listafinal = []
                for m in matriculas:
                    listafinal.append({'nombre': u"%s" % m.inscripcion.persona.nombre_completo(), 'id': m.id})
                return ok_json({"cantidad": len(listafinal), "matriculas": listafinal})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'cerrarperiodo':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                periodo.cerrado = True
                periodo.save(request)
                log(u"Cerró el periodo académico: %s" % periodo.nombre, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'abrirperiodo':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                periodo.cerrado = False
                periodo.save(request)
                log(u"Abrio el periodo académico: %s" % periodo.nombre, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'habverperiodo':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                periodo.visualiza = True
                periodo.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'aprueboevaluacion':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                proceso = ProcesoEvaluativoAcreditacion.objects.get(periodo=periodo)
                if proceso.aprovadoevaluacion is False:
                    proceso.aprovadoevaluacion=True
                else:
                    proceso.aprovadoevaluacion = False
                proceso.save(request)
                log(u'Activo desactivo poder  anadir criterios al proceso %s' % proceso, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desverperiodo':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                periodo.visualiza = False
                periodo.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Nuevo periodo'
                    data['form'] = PeriodoForm()
                    return render(request, "adm_periodos/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar periodo'
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = PeriodoForm(initial={'nombre': periodo.nombre,
                                                        'inicio': periodo.inicio,
                                                        'fin': periodo.fin,
                                                        'tipo': periodo.tipo,
                                                        'inicio_agregacion': periodo.inicio_agregacion,
                                                        'limite_agregacion': periodo.limite_agregacion,
                                                        'valida_asistencia': periodo.valida_asistencia,
                                                        'extendido': periodo.extendido,
                                                        'parasolicitudes': periodo.parasolicitudes,
                                                        'inicio_solicitudes': periodo.inicio_solicitudes,
                                                        'limite_solicitudes': periodo.limite_solicitudes,})
                    return render(request, "adm_periodos/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'editperiodosolicitudperiodo':
                try:
                    data['title'] = u'Editar periodo'
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = PeriodoSolicitudPeriodoForm(initial={'inicio_solicitud': periodo.inicio_solicitudes,
                                                                        'fin_solicitud': periodo.limite_solicitudes})
                    return render(request, "adm_periodos/editperiodosolicitudperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'delperiodo':
                try:
                    data['title'] = u'Eliminar período'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/delperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'delperiodosolicitud':
                try:
                    data['title'] = u'Eliminar período'
                    data['periodo'] = PeriodoSolicitud.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/delperiodosolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'addperiodosolicitud':
                try:
                    data['title'] = u'Nuevo Período Solicitud'
                    data['form'] = PeriodoSolicitudForm()
                    return render(request, "adm_periodos/addperiodosol.html", data)
                except Exception as ex:
                    pass

            if action == 'editperiodosolicitud':
                try:
                    data['title'] = u'Editar Período Solicitud'
                    data['periodo'] = periodo = PeriodoSolicitud.objects.get(pk=request.GET['id'])
                    data['form'] = PeriodoSolicitudForm(initial={'nombre': periodo.nombre,
                                                                 'inicio': periodo.inicio,
                                                                 'fin': periodo.fin,
                                                                 'activo': periodo.activo,
                                                                 'cerrado': periodo.cerrado})
                    return render(request, "adm_periodos/editperiodosolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'cromatriculacion':
                try:
                    data['title'] = u'Cronograma de matriculación'
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['cronogramas'] = periodo.periodomatriculacion_set.all().order_by('carrera', 'nivelmalla')
                    return render(request, "adm_periodos/cromatriculacion.html", data)
                except Exception as ex:
                    pass

            if action == 'periodosolicitud':
                try:
                    data['title'] = u'Solicitudes  Período'
                    data['periodosol'] = periodosol = PeriodoSolicitud.objects.all()
                    return render(request, "adm_periodos/periodosolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'croprematriculacion':
                try:
                    data['title'] = u'Cronograma de prematriculación'
                    data['periodo'] = periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['cronogramas'] = periodo.periodoprematriculacion_set.all().order_by('carrera', 'nivelmalla')
                    return render(request, "adm_periodos/croprematriculacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addcronograma':
                try:
                    data['title'] = u'Adicionar cronograma de matriculación'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = CronogramaMatriculacionForm(initial={'inicio': datetime.now().date(),
                                                                        'fin': datetime.now().date()})
                    return render(request, "adm_periodos/addcronograma.html", data)
                except Exception as ex:
                    pass

            if action == 'addcronogramapre':
                try:
                    data['title'] = u'Adicionar cronograma de prematriculación'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    data['form'] = CronogramaMatriculacionForm(initial={'inicio': datetime.now().date(),
                                                                        'fin': datetime.now().date()})
                    return render(request, "adm_periodos/addcronogramapre.html", data)
                except Exception as ex:
                    pass

            if action == 'editcronograma':
                try:
                    data['title'] = u'Editar cronograma de matriculación'
                    cronograma = PeriodoMatriculacion.objects.get(pk=request.GET['id'])
                    data['cronograma'] = cronograma
                    form = CronogramaMatriculacionForm(initial={'inicio': cronograma.fecha_inicio,
                                                                'fin': cronograma.fecha_fin,
                                                                'carrera': cronograma.carrera,
                                                                'modalidad': cronograma.modalidad,
                                                                'nivelmalla': cronograma.nivelmalla})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_periodos/editcronograma.html", data)
                except Exception as ex:
                    pass

            if action == 'editcronogramapre':
                try:
                    data['title'] = u'Editar cronograma de prematriculación'
                    cronograma = PeriodoPreMatriculacion.objects.get(pk=request.GET['id'])
                    data['cronograma'] = cronograma
                    form = CronogramaMatriculacionForm(initial={'inicio': cronograma.fecha_inicio,
                                                                'fin': cronograma.fecha_fin,
                                                                'carrera': cronograma.carrera,
                                                                'modalidad': cronograma.modalidad,
                                                                'nivelmalla': cronograma.nivelmalla})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_periodos/editcronogramapre.html", data)
                except Exception as ex:
                    pass

            if action == 'delcronograma':
                try:
                    data['title'] = u'Eliminar cronograma de matriculación'
                    data['cronograma'] = PeriodoMatriculacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/delcronograma.html", data)
                except Exception as ex:
                    pass

            if action == 'delcronogramapre':
                try:
                    data['title'] = u'Eliminar cronograma de prematriculación'
                    data['cronograma'] = PeriodoPreMatriculacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/delcronogramapre.html", data)
                except Exception as ex:
                    pass

            if action == 'matriculasmora':
                try:
                    data['title'] = u'Matrículas en mora'
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodo'] = periodo
                    matriculas = Matricula.objects.filter(formalizada=False, nivel__periodo=periodo)
                    data['matriculas'] = matriculas
                    return render(request, "adm_periodos/matriculasmora.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabprematricula':
                try:
                    data['title'] = u'Deshabilitar pre-matricula'
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodo'] = periodo
                    return render(request, "adm_periodos/deshabprematricula.html", data)
                except Exception as ex:
                    pass

            if action == 'habprematricula':
                try:
                    data['title'] = u'Habilitar pre-matricula'
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodo'] = periodo
                    return render(request, "adm_periodos/habprematricula.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabmatricula':
                try:
                    data['title'] = u'Deshabilitar matricula'
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodo'] = periodo
                    return render(request, "adm_periodos/deshabmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'habmatricula':
                try:
                    data['title'] = u'Habilitar matricula'
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodo'] = periodo
                    return render(request, "adm_periodos/habmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrarperiodo':
                try:
                    data['title'] = u'Cerrar periodo'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/cerrarperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'abrirperiodo':
                try:
                    data['title'] = u'Abrir periodo'
                    data['periodo'] = Periodo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_periodos/abrirperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'habverperiodo':
                try:
                    data['title'] = u'Habilitar matricula'
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodo'] = periodo
                    return render(request, "adm_periodos/habverperiodo.html", data)
                except Exception as ex:
                    pass

            if action == 'aprueboevaluacion':
                try:
                    data['title'] = u'Habilitar evaluación docente'
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodo'] = periodo
                    return render(request, "adm_periodos/aprueboevaluacion.html", data)
                except Exception as ex:
                    pass

            if action == 'desverperiodo':
                try:
                    data['title'] = u'Habilitar matricula'
                    periodo = Periodo.objects.get(pk=request.GET['id'])
                    data['periodo'] = periodo
                    return render(request, "adm_periodos/desverperiodo.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Períodos lectivos'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    periodos = Periodo.objects.filter(Q(nombre__icontains=search) |
                                                      Q(tipo__nombre__icontains=search)).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    periodos = Periodo.objects.filter(id=ids)
                else:
                    periodos = Periodo.objects.all()
                paging = MiPaginador(periodos, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_periodos':
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
                request.session['paginador_url'] = 'adm_periodos'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['periodos'] = page.object_list
                return render(request, "adm_periodos/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
