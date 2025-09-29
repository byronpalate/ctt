# coding=utf-8
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module
from ctt.commonviews import adduserdata, fechas_semana, rango_fechas
from ctt.funciones import bad_json, convertir_fecha, ok_json
from ctt.models import mi_institucion, AsistenciaLeccion


@login_required(login_url='/login')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    data['matricula'] = inscripcion.matricula()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'confirmarasistencia':
            try:
                asistencia = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                asistencia.asistio = True
                asistencia.save(request)
                asistencia.materiaasignada.save(actualiza=True)
                lg = asistencia.leccion.leccion_grupo()
                lg.actualizarasistencias = True
                lg.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        try:

            data['title'] = u'Horario del estudiante'
            institucion = mi_institucion()
            if institucion.deudabloqueamishorarios and inscripcion.tiene_deuda_vencida():
                request.session['info'] = u'Para acceder al módulo, primero debe cancelar los valores pendientes'
                return HttpResponseRedirect('/')
            data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miércoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado'], [7, 'Domingo']]
            if 'anterior' not in request.GET and 'proximo' not in request.GET:
                if 'fecha' in request.GET:
                    fecha = convertir_fecha(request.GET['fecha'])
                    data['fechas'] = fechas = fechas_semana(fecha)
                else:
                    data['fechas'] = fechas = fechas_semana(datetime.now().date())
            else:
                if 'anterior' in request.GET:
                    data['fechas'] = fechas = fechas_semana(convertir_fecha(request.GET['fecha']) - timedelta(days=7))
                else:
                    data['fechas'] = fechas = fechas_semana(convertir_fecha(request.GET['fecha']) + timedelta(days=7))
            data['rangofechas'] = rango_fechas(fechas[0], fechas[1])
            data['fechahoy'] = datetime.now().date()
            data['habilitadosmodalidad'] = [3, 4]
            return render(request, "alu_horarios/view.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')
