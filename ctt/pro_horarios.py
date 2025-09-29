# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import CLASES_HORARIO_ESTRICTO, TIPO_DOCENTE_TEORIA
from ctt.commonviews import adduserdata
from ctt.funciones import bad_json
from ctt.models import Clase, Sesion, LeccionGrupo, ProfesorMateria, Profesor, MateriaAsignada


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = data['periodo']
    perfilprincipal = request.session['perfilprincipal']
    data['profesor'] = profesor = Profesor.objects.get(pk=perfilprincipal.profesor.id)
    if request.method == 'POST':
        return bad_json(error=0)
    else:
        try:
            data['title'] = u'Horario de profesor'
            hoy = datetime.now()
            estudianteasignado = MateriaAsignada.objects.filter(matricula__inscripcion__neebienestar__isnull=False,
                                                                materia__profesormateria__principal=True,
                                                                materia__profesormateria__profesor=profesor,
                                                                matricula__nivel__periodo=periodo,
                                                                matricula__inscripcion__neebienestar__periodo=periodo,
                                                                matricula__inscripcion__neebienestar__aprobado=True)
            for plan in estudianteasignado:
                if NeeBienestarPlanIncial.objects.filter(materiaasignada=plan).exists():
                    True
                else:
                    data['notificacion'] = NeeBienestarNotificaciones.objects.filter(planinicial=True, periodo=periodo, hasta__gte=hoy)
                    break
            for plan in estudianteasignado:
                if ObservacionesNeeBienestar.objects.filter(materiaasignada=plan).exists():
                    True
                else:
                    data['notificacionobs'] = NeeBienestarNotificaciones.objects.filter(observaciones=True, periodo=periodo, hasta__gte=hoy)
                    break
            clasesabiertas = LeccionGrupo.objects.filter(profesor=profesor, abierta=True).order_by('-fecha', '-horaentrada')
            hoy = datetime.now().date()
            data['disponible'] = clasesabiertas.count() == 0
            if clasesabiertas:
                data['claseabierta'] = clasesabiertas[0]
            if not data['disponible']:
                if clasesabiertas.count() > 1:
                    for clase in clasesabiertas[1:]:
                        clase.abierta = False
                        clase.save(request)
                data['lecciongrupo'] = LeccionGrupo.objects.filter(profesor=profesor, abierta=True)[0]
            data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miércoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sábado'], [7, 'Domingo']]
            if CLASES_HORARIO_ESTRICTO:
                materiasnoprogramadaspos = ProfesorMateria.objects.filter(materia__cerrado=False,
                                                                          profesor=profesor,
                                                                          hasta__gt=hoy,
                                                                          tipoprofesor__id=TIPO_DOCENTE_TEORIA,
                                                                          principal=True,
                                                                          materia__nivel__nivellibrecoordinacion__coordinacion__id__in=[18, 19]).exclude(materia__clase__id__isnull=False)
                clasespos = Clase.objects.filter(activo=True, fin__gte=hoy, materia__profesormateria__profesor=profesor, materia__nivel__nivellibrecoordinacion__coordinacion__id__in=[18, 19]).order_by('inicio')
                materiasnoprogramadaspre = ProfesorMateria.objects.filter(materia__cerrado=False,
                                                                          materia__nivel__distributivoaprobado=True,
                                                                          profesor=profesor, hasta__gt=hoy,
                                                                          tipoprofesor__id=TIPO_DOCENTE_TEORIA,
                                                                          principal=True).exclude(materia__clase__id__isnull=False)
                clasespre = Clase.objects.filter(activo=True, fin__gte=hoy, materia__profesormateria__profesor=profesor).order_by('inicio')
                data['materiasnoprogramadas'] = materiasnoprogramadas = (materiasnoprogramadaspre | materiasnoprogramadaspos).distinct()
                data['misclases'] = clases = (clasespre | clasespos).distinct()
            else:
                data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(materia__cerrado=False, profesor=profesor, tipoprofesor__id=TIPO_DOCENTE_TEORIA, principal=True).exclude(materia__clase__id__isnull=False)
                data['misclases'] = clases = Clase.objects.filter(activo=True, materia__profesormateria__profesor=profesor).order_by('inicio')
            data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
            data['fecha'] = datetime.now().date()
            data['clases_horario_estricto'] = CLASES_HORARIO_ESTRICTO
            return render(request, "pro_horarios/view.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')
