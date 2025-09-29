# coding=utf-8
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from settings import PROFESOR_JUSTIFICA_ASISTENCIA, LIMITE_HORAS_JUSTIFICAR, CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS, \
    TIPO_DOCENTE_TEORIA, CALCULO_ASISTENCIA_CLASE
from ctt.commonviews import adduserdata, justificar_asistencia
from ctt.funciones import bad_json, ok_json
from ctt.models import Materia, AsistenciaLeccion, ActualizacionAsistencia


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'asistencia':
            try:
                asistencialeccion = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                if not request.user.is_superuser:
                    if LIMITE_HORAS_JUSTIFICAR:
                        if asistencialeccion.leccion.fecha < datetime.now().date() - timedelta(hours=CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS):
                            return bad_json(mensaje=u"Las faltas menores a %s hora(s) no pueden ser justificadas." % CANTIDAD_HORAS_JUSTIFICACION_ASISTENCIAS)
                resultado = justificar_asistencia(request)
                resultado['materiaasignada'] = asistencialeccion.materiaasignada.id
                resultado['dia'] = asistencialeccion.leccion.fecha.day
                resultado['mes'] = asistencialeccion.leccion.fecha.month
                resultado['anio'] = asistencialeccion.leccion.fecha.year
                return ok_json(resultado)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'segmento':
            try:
                materia = Materia.objects.filter(profesormateria__profesor=profesor).get(pk=request.POST['id'])
                if not CALCULO_ASISTENCIA_CLASE:
                    if ActualizacionAsistencia.objects.filter(materia=materia).exists():
                        for ma in materia.materiaasignada_set.filter(cerrado=False):
                            ma.save(actualiza=True)
                            ma.actualiza_estado()
                        registro = ActualizacionAsistencia.objects.filter(materia=materia)[0]
                        registro.delete()
                data = {'materia': materia}
                data['listadoestudiantes'] = materia.asignados_a_esta_materia()
                template = get_template("pro_asistencias/segmento.html")
                json_content = template.render(data)
                return ok_json({'data': json_content})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        return bad_json(error=0)
    else:
        try:
            data['title'] = u'Asistencias de alumnos'
            periodo = request.session['periodo']
            data['materias'] = Materia.objects.filter(nivel__periodo=periodo,
                                                      profesormateria__profesor=profesor,
                                                      profesormateria__tipoprofesor__id=TIPO_DOCENTE_TEORIA,
                                                      profesormateria__principal=True).distinct()
            data['profesor_justifica_asistencia'] = PROFESOR_JUSTIFICA_ASISTENCIA
            if 'id' in request.GET:
                data['id'] = request.GET['id']
            return render(request, "pro_asistencias/view.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')
