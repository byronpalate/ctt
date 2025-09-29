# coding=utf-8
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import MUESTRA_ESTADO_NIVELACION, MODALIDAD_DISTANCIA
from ctt.commonviews import adduserdata
from ctt.funciones import url_back, bad_json
from ctt.models import mi_institucion


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'extracurricular':
                try:
                    data['title'] = u'Actividades extracurriculares'
                    data['pasantias'] = inscripcion.pasantias()
                    data['talleres'] = inscripcion.talleres()
                    data['practicas'] = inscripcion.practicas()
                    data['vccs'] = inscripcion.vcc()
                    return render(request, "alu_notas/extracurricular.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Registro académico'
                institucion = mi_institucion()
                if inscripcion.modalidad.id != MODALIDAD_DISTANCIA:
                    if institucion.deudabloqueanotas and inscripcion.adeuda_a_la_fecha():
                        flags = inscripcion.mis_flag()
                        if not flags.permitepagoparcial:
                            request.session['info'] = u'Usted tiene deuda vencida a la fecha de %s.' % inscripcion.valor_deuda_vencida()
                            return HttpResponseRedirect('/')
                data['records'] = inscripcion.recordacademico_set.all().order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                data['total_creditos'] = inscripcion.total_creditos()
                data['total_creditos_malla'] = inscripcion.total_creditos_malla()
                data['total_creditos_modulos'] = inscripcion.total_creditos_modulos()
                data['total_creditos_otros'] = inscripcion.total_creditos_otros()
                data['total_horas'] = inscripcion.total_horas()
                data['promedio'] = inscripcion.promedio_record()
                data['aprobadasmalla'] = inscripcion.recordacademico_set.filter(aprobada=True, asignaturamalla__isnull=False).count()
                data['aprobadasotras'] = inscripcion.recordacademico_set.filter(aprobada=True, asignaturamalla__isnull=True).count()
                data['reprobadasmalla'] = inscripcion.recordacademico_set.filter(aprobada=False, asignaturamalla__isnull=False).count()
                data['reprobadasotras'] = inscripcion.recordacademico_set.filter(aprobada=False, asignaturamalla__isnull=True).count()
                data['muestra_estado_nivelacion'] = MUESTRA_ESTADO_NIVELACION
                return render(request, "alu_notas/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
