# coding=utf-8
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata, obtener_reporte
from ctt.funciones import bad_json
from ctt.models import Matricula, mi_institucion


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':

        return bad_json(error=0)
    else:
        try:
            data['title'] = u'Consulta de asistencias'
            institucion = mi_institucion()
            if institucion.deudabloqueaasistencia and inscripcion.persona.adeuda_a_la_fecha():
                request.session['info'] = u'Usted tiene deuda vencida a la fecha de %s.' % inscripcion.persona.valor_deuda_vencida()
                return HttpResponseRedirect('/')
            if 'matriculaid' in request.GET:
                data['matricula'] = matricula = Matricula.objects.get(pk=int(request.GET['matriculaid']))
            else:
                data['matricula'] = matricula = inscripcion.ultima_matricula()
            if not matricula:
                request.session['info'] = u'Usted no tiene una matrícula activa.'
                return HttpResponseRedirect('/')
            data['matriculaid'] = matricula.id
            data['matriculas'] = inscripcion.matricula_set.all()
            cantidadmaxima = 0
            for materia in matricula.materiaasignada_set.all():
                if materia.cantidad_asistencias_lecciones() > cantidadmaxima:
                    cantidadmaxima = materia.cantidad_asistencias_lecciones()
            materiaasignadas = []
            for materia in matricula.materiaasignada_set.all().order_by('materia__asignatura'):
                materiaasignadas.append([materia, materia.asistencias_lecciones(), cantidadmaxima, materia.cantidad_asistencias_lecciones(), cantidadmaxima - materia.cantidad_asistencias_lecciones()])
            data['materiasasiganadas'] = materiaasignadas
            data['cantidad'] = cantidadmaxima
            data['reporte_0'] = obtener_reporte('clases_consolidado_alumno')
            return render(request, "alu_asistencias/view.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')
