# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import FechaPeriodoEvaluacionesForm, CronoramaCalificacionesForm
from ctt.funciones import log, url_back, bad_json, ok_json, convertir_fecha
from ctt.models import ModeloEvaluativo, FechaEvaluacionCampoModelo, CronogramaEvaluacionModelo, Nivel, Materia


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

        if action == 'edit':
            try:
                periodoevaluaciones = FechaEvaluacionCampoModelo.objects.get(pk=request.POST['id'])
                form = FechaPeriodoEvaluacionesForm(request.POST)
                if form.is_valid():
                    if form.cleaned_data['califdesde'] > form.cleaned_data['califhasta']:
                        return bad_json(mensaje=u"La fecha inicio debe ser menor que la fecha fin.")
                    periodoevaluaciones.inicio = form.cleaned_data['califdesde']
                    periodoevaluaciones.fin = form.cleaned_data['califhasta']
                    periodoevaluaciones.save(request)
                    log(u'Modifico campo de cronorama de calificaciones: %s' % periodoevaluaciones, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'actualizafechainicio':
            try:
                periodoevaluaciones = FechaEvaluacionCampoModelo.objects.get(pk=request.POST['id'])
                fecha_str = request.POST['valor']
                # Convertir la cadena de fecha a un objeto datetime.date
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                if fecha > periodoevaluaciones.fin:
                    return bad_json(mensaje=u"La fecha inicio debe ser menor que la fecha fin.")
                periodoevaluaciones.inicio = fecha
                periodoevaluaciones.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'actualizafechafin':
            try:
                periodoevaluaciones = FechaEvaluacionCampoModelo.objects.get(pk=request.POST['id'])
                fecha_str = request.POST['valor']

                # Convertir la cadena de fecha a un objeto datetime.date
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                if fecha < periodoevaluaciones.inicio:
                    return bad_json(mensaje=u"La fecha fin debe ser mayor que la fecha inicio.")
                periodoevaluaciones.fin = fecha
                periodoevaluaciones.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delcronograma':
            try:
                cronograma = CronogramaEvaluacionModelo.objects.get(pk=request.POST['id'])
                log(u'Elimino cronorama de calificaciones: %s' % cronograma, request, "del")
                cronograma.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'addcronograma':
            try:
                modeloevaluativo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                nivel = Nivel.objects.get(pk=request.POST['idn'])
                form = CronoramaCalificacionesForm(request.POST)
                periodo = request.session['periodo']
                if form.is_valid():
                    cronograma = CronogramaEvaluacionModelo(nivel=nivel,
                                                            modelo=modeloevaluativo,
                                                            nombre=form.cleaned_data['nombre'])
                    cronograma.save(request)
                    for campo in modeloevaluativo.campos():
                        fechaevaluacion = FechaEvaluacionCampoModelo(cronograma=cronograma,
                                                                     campo=campo,
                                                                     inicio=periodo.inicio,
                                                                     fin=periodo.fin)
                        fechaevaluacion.save(request)
                    log(u'Adiciono cronograma de calificaciones: %s' % cronograma, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'materias':
            try:
                cronograma = CronogramaEvaluacionModelo.objects.get(pk=request.POST['id'])
                log(u'Elimino materias del cronograma de calificaciones: %s' % cronograma, request, "del")
                cronograma.materias.clear()
                if request.POST['listamaterias']:
                    for materia in Materia.objects.filter(id__in=[int(x) for x in request.POST['listamaterias'].split(',')]):
                        if materia.cronogramaevaluacionmodelo_set.filter(periodo=cronograma.periodo).exists():
                            for c in materia.cronogramaevaluacionmodelo_set.filter(periodo=cronograma.periodo):
                                c.materias.remove(materia)
                        cronograma.materias.add(materia)
                        if not materia.nivel.cerrado:
                            materia.cerrado = False
                            materia.save(request)
                            materia.materiaasignada_set.update(cerrado=False)
                        log(u'Adiciono materias al cronograma de calificaciones: %s - %s' % (cronograma, materia.nombre_completo()), request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'edit':
                try:
                    periodoevaluaciones = FechaEvaluacionCampoModelo.objects.get(pk=request.GET['id'])
                    data['title'] = u'Editar fecha del campo: ' + periodoevaluaciones.campo.nombre
                    data['periodoevaluaciones'] = periodoevaluaciones
                    data['form'] = FechaPeriodoEvaluacionesForm(initial={'califdesde': periodoevaluaciones.inicio,
                                                                         'califhasta': periodoevaluaciones.fin})
                    return render(request, "fecha_evaluaciones/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'materias':
                try:
                    data['title'] = u'Selección de materias del cronograma'
                    data['cronograma'] = cronograma = CronogramaEvaluacionModelo.objects.get(pk=request.GET['id'])
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['idn'])
                    data['materias'] = Materia.objects.filter(nivel=nivel,  modeloevaluativo=cronograma.modelo)
                    return render(request, "fecha_evaluaciones/materias.html", data)
                except Exception as ex:
                    pass

            if action == 'delcronograma':
                try:
                    data['title'] = u'Eliminar cronograma'
                    data['cronograma'] = CronogramaEvaluacionModelo.objects.get(pk=request.GET['id'])
                    return render(request, "fecha_evaluaciones/delcronograma.html", data)
                except Exception as ex:
                    pass

            if action == 'addcronograma':
                try:
                    data['title'] = u'Nuevo cronograma de calificaciones'
                    data['modeloevaluativo'] = ModeloEvaluativo.objects.get(pk=request.GET['id'])
                    data['nivel'] = Nivel.objects.get(pk=request.GET['idn'])
                    data['form'] = CronoramaCalificacionesForm()
                    return render(request, "fecha_evaluaciones/addcronograma.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Cronograma de evaluaciones - modelos evaluativos'
                data['periodo'] = periodo = request.session['periodo']
                data['coordinacion'] = request.session['coordinacionseleccionada']
                data['modelo_evaluativo'] = ModeloEvaluativo.objects.filter(materia__nivel__periodo=periodo, materia__nivel__nivellibrecoordinacion__coordinacion=request.session['coordinacionseleccionada']).distinct()
                return render(request, "fecha_evaluaciones/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
