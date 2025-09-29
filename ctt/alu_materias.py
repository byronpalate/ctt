# coding=utf-8

from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import RequestContext, Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from settings import MUESTRA_ESTADO_NIVELACION, SOLICITUD_NUMERO_AUTOMATICO, \
    PUEDE_ESPECIFICAR_CANTIDAD_SOLICITUD_SECRETARIA, TIPO_IVA_0_ID, \
    RUBRO_OTRO_SOLICITUD_ID, CALCULO_ASISTENCIA_CLASE
from ctt.commonviews import adduserdata, obtener_reporte
from ctt.forms import RubricaTallerPlanificacionForm
from ctt.funciones import url_back, bad_json, ok_json
from ctt.models import Matricula, Materia, TallerPlanificacionMateria, PlanificacionMateria, \
    ActividadesAprendizajeCondocenciaAsistida, ActividadesAprendizajeColaborativas, ClasesTallerPlanificacionMateria, \
    MateriaAsignada, AsistenciaLeccion, mi_institucion,DetalleModeloEvaluativo, RubroOtro, Rubro, null_to_numeric, Periodo


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
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':

        action = request.POST['action']

        if action == 'confirmartodos':
            try:
                asistencia = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                valor = True if request.POST['val'] == 'true' else False
                asistencia.confirmada = valor
                planificacion = asistencia.leccion.leccion_grupo().clasestallerplanificacionmateria
                if planificacion.horasdocente:
                    asistencia.confirmadaasistencia = valor
                if planificacion.horascolaborativas:
                    asistencia.confirmadacolaborativa = valor
                if planificacion.horasautonomas:
                    asistencia.confirmadaautonoma = valor
                if planificacion.horaspracticas:
                    asistencia.confirmadapractica = valor
                asistencia.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'confirmaasistencia':
            try:
                asistencia = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                asistencia.confirmada = True if request.POST['val'] == 'true' else False
                asistencia.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'confirmadocenciaasist':
            try:
                asistencia = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                asistencia.confirmadaasistencia = True if request.POST['val'] == 'true' else False
                asistencia.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'confirmadocenciacolab':
            try:
                asistencia = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                asistencia.confirmadacolaborativa = True if request.POST['val'] == 'true' else False
                asistencia.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'confirmadocenciaauto':
            try:
                asistencia = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                asistencia.confirmadaautonoma = True if request.POST['val'] == 'true' else False
                asistencia.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'confirmadocenciapract':
            try:
                asistencia = AsistenciaLeccion.objects.get(pk=request.POST['id'])
                asistencia.confirmadapractica = True if request.POST['val'] == 'true' else False
                asistencia.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'segmento':
            try:
                data = {}
                data['materiaasignada'] = MateriaAsignada.objects.get(id=request.POST['id'])
                template = get_template("alu_materias/segmentonotas.html")
                json_content = template.render(data)
                return ok_json({'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=3)

        if action == 'solicitar':
            try:
                materiaasignada = MateriaAsignada.objects.get(id=request.POST['id'])
                tipo = TipoSolicitudSecretariaDocente.objects.get(pk=18)
                if inscripcion.solicitudsecretariadocente_set.filter(materiaasignada=materiaasignada, tipo__id=18, matricula=materiaasignada.matricula).exists():
                    return bad_json(mensaje="Ya tiene una solicitud generada para esta materia.", error=4)
                solicitud = SolicitudSecretariaDocente(fecha=datetime.now().date(),
                                                       hora=datetime.now().time(),
                                                       inscripcion=inscripcion,
                                                       tipo=tipo,
                                                       descripcion="Solicitud de aprobacion de modulo posgrado",
                                                       cerrada=False,
                                                       materiaasignada=materiaasignada,
                                                       matricula=materiaasignada.matricula)
                solicitud.save(request)
                if SOLICITUD_NUMERO_AUTOMATICO:
                    if SolicitudSecretariaDocente.objects.filter(numero_tramite__gt=0).exists():
                        ultima = SolicitudSecretariaDocente.objects.filter(numero_tramite__gt=0).order_by('-id')[0]
                        solicitud.numero_tramite = ultima.numero_tramite + 1
                    else:
                        solicitud.numero_tramite = 1
                    solicitud.save(request)
                if solicitud.tipo.tiene_costo():
                    cantidad = 1
                    if PUEDE_ESPECIFICAR_CANTIDAD_SOLICITUD_SECRETARIA:
                        cantidad = form.cleaned_data['cantidad']
                    if solicitud.tipo.costo_unico:
                        valor = null_to_numeric(solicitud.tipo.valor + solicitud.tipo.costo_base, 2)
                    else:
                        valor = null_to_numeric((solicitud.tipo.valor * cantidad) + solicitud.tipo.costo_base, 2)
                    # for p in PeriodoSolicitud.objects.all():
                    #     if p.vigente():
                    #         periodosolicitud = p.id
                    periodosolicitud = Periodo.objects.filter(parasolicitudes=True)[0]
                    rubro = Rubro(inscripcion=inscripcion,
                                  valor=valor,
                                  iva_id=TIPO_IVA_0_ID,
                                  valortotal=valor,
                                  saldo=valor,
                                  periodo=periodosolicitud,
                                  fecha=datetime.now().date(),
                                  fechavence=datetime.now().date())
                    rubro.save(request)
                    rubrootro = RubroOtro(rubro=rubro,
                                          tipo_id=RUBRO_OTRO_SOLICITUD_ID,
                                          solicitud=solicitud)
                    rubrootro.save(request)
                    rubro.actulizar_nombre(nombre=solicitud.tipo.nombre)
                    solicitud.verificar_gratuidad()
                    solicitud.mail_subject_nuevo()
                    return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'solicitarsupletorio':
            try:
                materiaasignada = MateriaAsignada.objects.get(id=request.POST['id'])
                tipo = TipoSolicitudSecretariaDocente.objects.get(pk=25)
                if inscripcion.tiene_deuda():
                    if not inscripcion.mis_flag().puedetomarsupletorio :
                        return bad_json(mensaje=u"No se puede generar la solicitud. Existen valores pendientes. Regularice su deuda e intente nuevamente.", error=8)
                if inscripcion.solicitudsecretariadocente_set.filter(materiaasignada=materiaasignada, tipo__id=25, matricula=materiaasignada.matricula).exists():
                    return bad_json(mensaje="Ya tiene una solicitud generada para esta materia.", error=4)
                solicitud = SolicitudSecretariaDocente(fecha=datetime.now().date(),
                                                       hora=datetime.now().time(),
                                                       inscripcion=inscripcion,
                                                       tipo=tipo,
                                                       descripcion=tipo.descripcion,
                                                       cerrada=False,
                                                       materiaasignada=materiaasignada,
                                                       matricula=materiaasignada.matricula)
                solicitud.save(request)
                if SOLICITUD_NUMERO_AUTOMATICO:
                    if SolicitudSecretariaDocente.objects.filter(numero_tramite__gt=0).exists():
                        ultima = SolicitudSecretariaDocente.objects.filter(numero_tramite__gt=0).order_by('-id')[0]
                        solicitud.numero_tramite = ultima.numero_tramite + 1
                    else:
                        solicitud.numero_tramite = 1
                    solicitud.save(request)
                if solicitud.tipo.tiene_costo():
                    cantidad = 1
                    if PUEDE_ESPECIFICAR_CANTIDAD_SOLICITUD_SECRETARIA:
                        cantidad = form.cleaned_data['cantidad']
                    if solicitud.tipo.costo_unico:
                        valor = null_to_numeric(solicitud.tipo.valor + solicitud.tipo.costo_base, 2)
                    else:
                        valor = null_to_numeric((solicitud.tipo.valor * cantidad) + solicitud.tipo.costo_base, 2)
                    # for p in PeriodoSolicitud.objects.all():
                    #     if p.vigente():
                    #         periodosolicitud = p.id
                    periodosolicitud = Periodo.objects.filter(parasolicitudes=True)[0]
                    rubro = Rubro(inscripcion=inscripcion,
                                  valor=valor,
                                  iva_id=TIPO_IVA_0_ID,
                                  valortotal=valor,
                                  saldo=valor,
                                  periodo=periodosolicitud,
                                  fecha=datetime.now().date(),
                                  fechavence=datetime.now().date())
                    rubro.save(request)
                    rubrootro = RubroOtro(rubro=rubro,
                                          tipo_id=RUBRO_OTRO_SOLICITUD_ID,
                                          solicitud=solicitud)
                    rubrootro.save(request)
                    rubro.actulizar_nombre(nombre=solicitud.tipo.nombre +' - '+ materiaasignada.asignaturareal.nombre)
                    solicitud.verificar_gratuidad()
                    solicitud.mail_subject_nuevo()
                    return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'friends':
                try:
                    data['title'] = u'Alumnos de mi clase'
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['m'])
                    data['materiasasignadas'] = materia.materiaasignada_set.exclude(matricula=matricula)
                    return render(request, "alu_materias/friends.html", data)
                except Exception as ex:
                    pass

            if action == 'rubrica':
                try:
                    data['title'] = u'Rubrica Taller'
                    taller = None
                    planificacion = None
                    materia = None
                    if 'id' in request.GET:
                        data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                        rubrica = taller.mi_rubrica()
                        materia = taller.planificacionmateria.materia
                        form = RubricaTallerPlanificacionForm(initial={'resultadoaprendizaje': taller.resultadoaprendizaje,
                                                                       'evidencia': rubrica.evidencia,
                                                                       'criterio': rubrica.criterio,
                                                                       'logroexcelente': rubrica.logroexcelente,
                                                                       'logroavanzado': rubrica.logroavanzado,
                                                                       'logrobajo': rubrica.logrobajo,
                                                                       'logrodeficiente': rubrica.logrodeficiente,
                                                                       'logromedio': rubrica.logromedio},
                                                               )
                    else:
                        data['planificacionmateria'] = planificacion = PlanificacionMateria.objects.get(pk=request.GET['p'])
                        materia = planificacion.materia
                        rubrica = planificacion.mi_rubrica()
                        form = RubricaTallerPlanificacionForm(initial={'criterio': rubrica.criterio,
                                                                       'logroexcelente': rubrica.logroexcelente,
                                                                       'logroavanzado': rubrica.logroavanzado,
                                                                       'logrobajo': rubrica.logrobajo,
                                                                       'logrodeficiente': rubrica.logrodeficiente,
                                                                       'logromedio': rubrica.logromedio},
                                                               )
                    if planificacion:
                        form.planificacion()
                    data['form'] = form
                    data['materia'] = materia
                    data['permite_modificar'] = False
                    return render(request, "alu_materias/rubrica.html", data)
                except Exception as ex:
                    pass

            if action == 'detalletaller':
                try:
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['title'] = u'Detalle Taller'
                    data['planificacionmateria'] = taller.planificacionmateria
                    data['actividadesaprendizajecondocenciaasistida'] = ActividadesAprendizajeCondocenciaAsistida.objects.all()
                    data['actividadesaprendizajecolaborativas'] = ActividadesAprendizajeColaborativas.objects.all()
                    return render(request, "alu_materias/detalletaller.html", data)
                except Exception as ex:
                    pass

            if action == 'planificacion':
                try:
                    data['title'] = u'Planificación de la materia'
                    data['materiaasignada'] = materiaa = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['materia'] = materia = materiaa.materia
                    data['planificacionmateria'] = planificacionmateria = materia.mi_planificacion()
                    data['actividadesaprendizajecondocenciaasistida'] = ActividadesAprendizajeCondocenciaAsistida.objects.all()
                    data['actividadesaprendizajecolaborativas'] = ActividadesAprendizajeColaborativas.objects.all()
                    data['clases'] = ClasesTallerPlanificacionMateria.objects.filter(tallerplanificacionmateria__planificacionmateria__aprobado=True, tallerplanificacionmateria__planificacionmateria=planificacionmateria).order_by('-fecha').distinct()
                    return render(request, "alu_materias/planificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'guias':
                try:
                    materia = Materia.objects.get(pk=request.GET['id'])
                    data['title'] = u'Guías'
                    data['planificacionmateria'] = planificacionmateria = materia.planificacionmateria_set.all()[0]
                    data['guias'] = planificacionmateria.guiaspracticasmateria_set.all()
                    data['guiasnuevas'] = planificacionmateria.guiasnuevapracticasmateria_set.filter(aprobadocoordinacion=True)
                    data['reporte_0'] = obtener_reporte('reporte_guias_laboratorio')
                    data['reporte_1'] = obtener_reporte('reporte_guias_visita')
                    data['reporte_2'] = obtener_reporte('reporte_guias_bd')
                    data['reporte_3'] = obtener_reporte('reporte_guias_simulacion')
                    data['reporte_6'] = obtener_reporte('reporte_guias_laboratorio_tipo1')
                    data['reporte_7'] = obtener_reporte('reporte_guias_laboratorio_tipo2')
                    data['reporte_8'] = obtener_reporte('reporte_guias_laboratorio_tipo3')
                    return render(request, "alu_materias/guias.html", data)
                except Exception as ex:
                    pass

            if action == 'solicitar':
                try:
                    data['title'] = u'Certificado de aprobacion del modulo'
                    data['materia'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "alu_materias/solicitar.html", data)
                except Exception as ex:
                    pass

            if action == 'solicitarsupletorio':
                try:
                    data['title'] = u'Certificado de Solicitud de Supletorio'
                    data['materia'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "alu_materias/solicitarsupletorio.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Materias de alumno'
                if 'matriculaid' in request.GET:
                    data['matricula'] = matricula = Matricula.objects.get(pk=int(request.GET['matriculaid']))
                else:
                    data['matricula'] = matricula = inscripcion.ultima_matricula()
                data['matriculas'] = matriculas = inscripcion.matricula_set.all()
                if not matriculas:
                    request.session['info'] = u'Usted no tiene matrículas registradas.'
                    return HttpResponseRedirect('/')
                institucion = mi_institucion()
                if institucion.deudabloqueacronograma and inscripcion.persona.adeuda_a_la_fecha():
                    request.session['info'] = u'Usted tiene deuda vencida a la fecha de %s.' % inscripcion.persona.valor_deuda_vencida()
                    return HttpResponseRedirect('/')
                data['matriculaid'] = matricula.id
                for ma in matricula.materiaasignada_set.filter(cerrado=False, materia__actualizacionasistencia__isnull=False):
                    ma.save(actualiza=True)
                    ma.actualiza_estado()
                data['materiasasignadas'] = matricula.materiaasignada_set.all().order_by('materia__inicio')
                data['requiere_pago_materia'] = matricula.materiaasignada_set.filter(materia__modeloevaluativo__in=DetalleModeloEvaluativo.objects.filter(requierepago=True).values('modelo_id')).exists()
                data['matricula_nivelacion'] = matricula.es_nivelacion()
                data['muestra_estado_nivelacion'] = MUESTRA_ESTADO_NIVELACION
                data['reporte'] = obtener_reporte('certificado_aprobacion_materia')
                return render(request, "alu_materias/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
