# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import last_access, secure_module
from ctt.utils.etools.certificacionb1ingles import (VALOR_EXAMEN_CERTIFICACION_B1, carrera_obligatoria_certificacion_b1,
                                                    convocatorias_b1, crear_registro_b1, datos_niveles_ingles, detalle_calculo_b1,
                                                    get_convocatoria_b1, tipo_convocatoria_b1, validar_postulacion_b1)
from ctt.commonviews import adduserdata
from ctt.funciones import bad_json, log, ok_json, url_back
from ctt.models import ProcesoAplicanteExamenSuficiencia


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    inscripcion = perfilprincipal.inscripcion
    data['costob1'] = VALOR_EXAMEN_CERTIFICACION_B1
    data['inscripcion'] = inscripcion

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'registrarse':
            try:
                proceso = get_convocatoria_b1(request.POST['id'])
                hoy = datetime.now().date()
                if proceso.cerrado or not proceso.activo or proceso.fechainicio > hoy or proceso.fechafin < hoy:
                    return bad_json(mensaje=u'La convocatoria no se encuentra habilitada para registro.')
                mensaje = validar_postulacion_b1(inscripcion, proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)
                if not proceso.registro(inscripcion):
                    registro = crear_registro_b1(proceso, inscripcion, request)
                    log(u'Registro de estudiante a certificacion B1 Ingles: %s' % registro, request, 'add')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)

    if 'action' in request.GET:
        action = request.GET['action']

        if action == 'registrarse':
            try:
                data['title'] = u'Registrarse en certificacion institucional B1'
                data['proceso'] = proceso = get_convocatoria_b1(request.GET['id'])
                if proceso.cerrado or datetime.today().date() > proceso.fechafin:
                    return HttpResponseRedirect('/alu_certificacionb1ingles')
                data['datosniveles'] = datos_niveles_ingles(inscripcion)
                data['obligatorio_b1'] = carrera_obligatoria_certificacion_b1(inscripcion)
                return render(request, 'alu_certificacionb1ingles/aplicar.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)

        if action == 'registro':
            try:
                data['title'] = u'Registro certificacion institucional B1'
                data['proceso'] = proceso = get_convocatoria_b1(request.GET['id'])
                registro = proceso.registro(inscripcion)
                if not registro:
                    return HttpResponseRedirect('/alu_certificacionb1ingles')
                data['registro'] = registro
                data['datosniveles'] = datos_niveles_ingles(inscripcion)
                data['calculo'] = detalle_calculo_b1(registro)
                data['obligatorio_b1'] = carrera_obligatoria_certificacion_b1(inscripcion)
                return render(request, 'alu_certificacionb1ingles/registro.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)

        return url_back(request)

    try:
        data['title'] = u'Postulacion certificacion institucional B1 Ingles'
        hoy = datetime.now().date()
        registrados_ids = ProcesoAplicanteExamenSuficiencia.objects.filter(
            inscripcion=inscripcion,
            convocatoria__tipoconvocatoria=tipo_convocatoria_b1()).values_list('convocatoria_id', flat=True)
        procesos = convocatorias_b1().filter(
            Q(id__in=registrados_ids) |
            Q(fechainicio__lte=hoy, fechafin__gte=hoy, activo=True,
              cerrado=False,
              modalidad=inscripcion.modalidad,
              coordinacion=inscripcion.coordinacion)
        ).distinct().order_by('-fechainicio')
        data['procesos'] = procesos
        data['datosniveles'] = datos_niveles_ingles(inscripcion)
        data['obligatorio_b1'] = carrera_obligatoria_certificacion_b1(inscripcion)
        return render(request, 'alu_certificacionb1ingles/view.html', data)
    except Exception:
        return HttpResponseRedirect('/')
