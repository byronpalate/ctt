# coding=utf-8
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.funciones import bad_json, ok_json
from ctt.models import EjeFormativo, AsignaturaMalla, mi_institucion


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'predecesora':
                try:
                    asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['id'])
                    lista = []
                    for predecesora in asignaturamalla.asignaturamallapredecesora_set.all():
                        lista.append([predecesora.predecesora.asignatura.nombre, predecesora.predecesora.nivelmalla.nombre])
                    return ok_json({"lista": lista})
                except Exception as ex:
                    return bad_json(error=3)

        return bad_json(error=0)
    else:
        try:
            data['title'] = u'Malla del alumno'
            institucion = mi_institucion()
            if institucion.deudabloqueamimalla and inscripcion.persona.adeuda_a_la_fecha():
                request.session['info'] = u'Usted tiene deuda vencida a la fecha de %s.' % inscripcion.persona.valor_deuda_vencida()
                return HttpResponseRedirect('/')
            data['malla'] = malla = inscripcion.mi_malla()
            data['ejesformativos'] = EjeFormativo.objects.all().order_by('nombre')
            data['modulos'] = malla.modulomalla_set.all()
            data['itinerarios'] = malla.asignaturamalla_set.filter(itinerario=inscripcion.mi_itinerario()).order_by('itinerario', 'nivelmalla', 'asignatura')
            return render(request, "alu_malla/view.html", data)
        except Exception as ex:
            return HttpResponseRedirect('/')
