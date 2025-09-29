# coding=utf-8
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import last_access, secure_module
from settings import CLASES_HORARIO_ESTRICTO, APERTURA_ATRASADAS_AUTOMATICAS, \
    SOLICITUD_APERTURACLASE_APROBADA_ID, TIPO_DOCENTE_TEORIA
from ctt.commonviews import adduserdata
from ctt.forms import SolicitudAperturaClaseForm
from ctt.funciones import log, generar_nombre, url_back, bad_json, ok_json, convertir_fecha
from ctt.models import SolicitudAperturaClase, Turno, LeccionGrupo


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
    if not CLASES_HORARIO_ESTRICTO:
        request.session['info'] = u'Su institución no utiliza horario estricto.'
        return HttpResponseRedirect('/')
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addsolicitud':
            try:
                form = SolicitudAperturaClaseForm(request.POST, request.FILES)
                if form.is_valid():
                    fecha = form.cleaned_data['fecha']
                    if fecha > datetime.now().date():
                        return bad_json(mensaje=u"La fecha no puede ser mayor que hoy.")
                    turno = form.cleaned_data['turno']
                    # if fecha <= (datetime.now().date()-timedelta(days=6)):
                    #     if not profesor.justificar:
                    #         return bad_json(mensaje=u"La fecha no puede ser mayor a 5 dias anteriores.")
                    turno = form.cleaned_data['turno']
                    if fecha == datetime.now().date() and datetime.now().time() <= turno.comienza:
                        return bad_json(mensaje=u"Este turno todavia no comienza.")
                    dia = fecha.isoweekday()
                    if LeccionGrupo.objects.filter(fecha=fecha, turno=turno, profesor=profesor).exists():
                        return bad_json(mensaje=u"Ya existe el registro de ese turno.")
                    solicitud = SolicitudAperturaClase(profesor=profesor,
                                                       fecha=form.cleaned_data['fecha'],
                                                       turno=form.cleaned_data['turno'],
                                                       motivonueva=form.cleaned_data['motivo'])
                    # if (solicitud.actualiza_coordinacion().id not in [18, 19]):
                    #     if not profesor.justificar:
                    #         if fecha <= (datetime.now().date()-timedelta(days=6)):
                    #             return bad_json(mensaje=u"La fecha no puede ser mayor a 5 dias anteriores.")
                    solicitud.save(request)
                    if APERTURA_ATRASADAS_AUTOMATICAS:
                        solicitud.estado = SOLICITUD_APERTURACLASE_APROBADA_ID
                        solicitud.save(request)
                    if 'documento' in request.FILES:
                        newfile = request.FILES['documento']
                        newfile._name = generar_nombre("aperturaclase_", newfile._name)
                        solicitud.documento = newfile
                        solicitud.save(request)
                    log(u'Adiciono solicitud apertura de clase: %s' % solicitud, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delsolicitud':
            try:
                solicitud = SolicitudAperturaClase.objects.get(pk=request.POST['id'])
                log(u'Elimino solicitud de apertura de clase: %s' % solicitud, request, "del")
                solicitud.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'turnos':
            try:
                fecha = convertir_fecha(request.POST['fecha'])
                nlista = {}
                for turno in Turno.objects.filter(clase__activo=True,
                                                  clase__materia__cerrado=False,
                                                  clase__materia__profesormateria__profesor=profesor,
                                                  clase__materia__profesormateria__tipoprofesor__id=TIPO_DOCENTE_TEORIA,
                                                  clase__materia__profesormateria__principal=True,
                                                  clase__inicio__lte=fecha,
                                                  clase__fin__gte=fecha,
                                                  clase__dia=fecha.isoweekday()).distinct().order_by('comienza'):
                    nlista.update({turno.id: {'id': turno.id, 'nombre': turno.flexbox_repr()}})
                return ok_json({'lista': nlista})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Nueva solicitud apertura de clase'
                    data['profesor'] = profesor
                    data['form'] = SolicitudAperturaClaseForm()
                    return render(request, "pro_aperturaclase/addsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud apertura de clase'
                    data['solicitud'] = SolicitudAperturaClase.objects.get(pk=request.GET['id'])
                    return render(request, "pro_aperturaclase/delsolicitud.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Solicitudes de apertura de clases'
                data['profesor'] = profesor
                data['solicitudes'] = profesor.solicitudaperturaclase_set.all().distinct()
                return render(request, "pro_aperturaclase/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
