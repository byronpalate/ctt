# coding=utf-8
import json
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import get_template

from decorators import secure_module, last_access
from settings import GENERAR_RUBRO_DERECHO, NOTA_ESTADO_EN_CURSO, USA_RETIRO_MATERIA, \
    USA_RETIRO_MATRICULA, LISTA_FORMA_CALCULO, MATRICULAR_CON_CONFLICTO_HORARIO, CALCULO_ASISTENCIA_CLASE, \
    PERSONA_ADMINS_ACADEMICO_ID
from settings import NIVEL_MALLA_CERO
from ctt.adm_calculofinanzas import calculo_eliminacionmateria, costo_matricula
from ctt.commonviews import adduserdata, obtener_reporte, actualizar_nota, matricular, \
    conflicto_materias_seleccionadas, materias_abiertas
from ctt.forms import RetiradoMatriculaForm,\
    RetiradoMateriaForm, CambioFechaAsignacionMateriaForm, \
    FechaMatriculaForm
from ctt.funciones import convertir_fecha, generar_nombre, valores_asignados
from ctt.funciones import log, MiPaginador, bad_json, ok_json, url_back, empty_json
from ctt.models import Nivel, Carrera, Matricula, MateriaAsignada, RecordAcademico, Materia, Asignatura, Inscripcion, \
    AgregacionEliminacionMaterias, MateriaAsignadaRetiro, Clase, Turno, ParaleloMateria, \
    NivelMalla,  mi_institucion, Persona, CargoInstitucion, RetiroMatricula
from ctt.tasks import send_mail


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    institucion = mi_institucion()
    miscarreras = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'precierretodos':
                try:
                    matriculas = []
                    cantidad = 0
                    for matricula in Matricula.objects.filter(cerrada=False, nivel__id=request.POST['id']):
                        mo = {'nombre': u"%s" % matricula.inscripcion.persona.nombre_completo(), 'id': matricula.id}
                        cantidad += 1
                        matriculas.append(mo)
                    return ok_json({"cantidad": cantidad, "matriculas 2": matriculas})
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'cierremag':
                try:
                    from ctt.adm_calculofinanzas import post_cierre_matricula
                    matricula = Matricula.objects.get(pk=request.POST['maid'])
                    if matricula.retirado():
                        matricula.estadomatricula = 3
                        matricula.save()
                    else:
                        matricula.calcular_estado_matricula()
                    if matricula.materiaasignada_set.filter(materia__cerrado=False).exists():
                        pass
                    else:
                        matricula.cerrada = True
                        matricula.save(request)
                        post_cierre_matricula(matricula)
                        datospromocion = matricula.mi_promocion()
                        datospromocion.nivelmalla = matricula.inscripcion.mi_nivel().nivel
                        datospromocion.save()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'promote':
                try:
                    matricula = Matricula.objects.get(pk=int(request.POST['id']))
                    materia = Materia.objects.get(pk=int(request.POST['idm']))
                    representa = Asignatura.objects.get(pk=request.POST['asignaturareal'])
                    verificahorario = int(request.POST['seleccionadoasis']) == 0
                    mallaalumno = matricula.inscripcion.mi_malla()
                    tiponominacion = request.POST['tiponominacion']
                    valoresingresados = valores_asignados(periodo, matricula.nivel.sede, matricula.inscripcion.carrera, matricula.nivel.modalidad, mallaalumno)
                    if valoresingresados:
                        if tiponominacion == 'moduloadelanto' and valoresingresados.precioadelantoidiomas <= 0:
                            return bad_json(mensaje=u"No existen valores para ADELANTO DE IDIOMAS en el idmalla: %s, favor comunicarse con el Depto Financiero." % mallaalumno.id)
                    else:
                        return bad_json(mensaje=u"No existen valores ingresados en el idmalla: %s, favor comunicarse con el Depto Financiero." % mallaalumno.id)
                    if verificahorario:
                        listamateria = list(matricula.materiaasignada_set.filter(verificahorario=True).values_list('materia_id', flat=True))
                        listamateria.append(materia.id)
                        materias = Materia.objects.filter(id__in=listamateria)
                        conflicto = conflicto_materias_seleccionadas(materias)
                        if conflicto:
                            return bad_json(mensaje=conflicto)
                    if matricula.inscripcion.existe_en_malla(representa) and not matricula.inscripcion.puede_tomar_materia(representa):
                        return bad_json(mensaje=u"No puede tomar esta materia por tener precedencias.")
                    # if matricula.inscripcion.existe_en_modulos(representa) and not matricula.inscripcion.puede_tomar_materia_modulo(representa):
                    #     return bad_json(mensaje=u"No puede tomar esta materia por tener precedencias.")
                    if not materia.tiene_capacidad():
                        return bad_json(mensaje=u"No existe cupo para esta materia.")
                    if materia.cerrado:
                        return bad_json(mensaje=u"La materia se encuentra cerrada.")
                    if matricula.materiaasignada_set.filter(materia=materia).exists():
                        return bad_json(mensaje=u"Ya se encuentra matriculado en esta materia.")
                    if not matricula.permite_agregaciones() and tiponominacion == 'moduloasignar':
                        return bad_json(mensaje=u"No puede agregar materias fuera de las fechas permitidas.")
                    malla = matricula.inscripcion.mi_malla()

                    am = None
                    mm = None
                    horas = materia.horas
                    creditos = materia.creditos
                    if malla.asignaturamalla_set.filter( asignatura=representa).exists():
                        am = malla.asignaturamalla_set.filter(asignatura=representa)[0]
                        horas = am.horas
                        creditos = am.creditos
                    matriculas = matricula.inscripcion.historicorecordacademico_set.filter(noaplica=False, convalidacion=False, homologada=False, asignatura=representa, fecha__lt=materia.nivel.fin).count() + 1
                    materiaasignada = MateriaAsignada(matricula=matricula,
                                                      materia=materia,
                                                      asignaturamalla=am,
                                                      asignaturareal=representa,
                                                      horas=horas,
                                                      creditos=creditos,
                                                      notafinal=0,
                                                      asistenciafinal=0,
                                                      verificahorario=verificahorario,
                                                      sinasistencia=True if matricula.inscripcion.modalidad.id == 3 else False,
                                                      cerrado=False,
                                                      matriculas=matriculas,
                                                      observaciones='',
                                                      fechaasignacion=materia.inicio,
                                                      estado_id=NOTA_ESTADO_EN_CURSO)
                    materiaasignada.save(request)
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.save(request)
                    matricula.save(request)
                    registro = AgregacionEliminacionMaterias(matricula=matricula,
                                                             agregacion=True,
                                                             asignatura=materiaasignada.materia.asignatura,
                                                             responsable=request.session['persona'],
                                                             fecha=datetime.now().date(),
                                                             creditos=materiaasignada.materia.creditos,
                                                             nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
                                                             matriculas=materiaasignada.matriculas,
                                                             adelanto=True if tiponominacion == 'moduloadelanto' else False)
                    registro.save(request)
                    log(u'Adiciono materia: %s' % materiaasignada, request, "add")
                    matricula.actualiza_tipo_inscripcion()
                    matricula.inscripcion.actualiza_tipo_inscripcion()
                    matricula.agregacion(materiaasignada, tiponominacion)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'conflictohorario':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                    mismaterias = json.loads(request.POST['mismaterias'])
                    materias = Materia.objects.filter(id__in=[int(x) for x in mismaterias])
                    conflicto = conflicto_materias_seleccionadas(materias)
                    if conflicto:
                        return bad_json(mensaje=conflicto)
                    return ok_json()
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'delmateria':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    matricula = materiaasignada.matricula
                    materia = materiaasignada.materia
                    if not matricula.nivel.periodo.fecha_agregaciones():
                        return bad_json(mensaje=u"No puede eliminar materias fuera de las fechas de agregaciones.")
                    if materiaasignada.rubromateria_set.exists():
                        return bad_json(mensaje=u"Debe revisar las finanzas del estudiante.")
                    log(u'Elimino materia asignada: %s' % materiaasignada, request, "del")
                    matricula.eliminar_materia(materiaasignada, persona)
                    matricula.save(request)
                    matricula.actualiza_tipo_inscripcion()
                    matricula.inscripcion.actualiza_tipo_inscripcion()
                    matricula.inscripcion.actualiza_gratuidad()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'sinasistencia':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.sinasistencia = True
                    materiaasignada.actualiza_estado()
                    log(u'Modifico estado asistencia: %s' % materiaasignada, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'conasistencia':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.sinasistencia = False
                    materiaasignada.actualiza_estado()
                    log(u'Modifico estado asistencia: %s' % materiaasignada, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'sinmovilidad':
                try:
                    materia = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materia.sinasistencia = False
                    materia.verificahorario = True
                    materia.movilidad = False
                    materia.save(request)
                    materia.actualiza_notafinal()
                    if materia.materia.cerrado:
                        materia.cierre_materia_asignada()
                    log(u'Modifio estado movilidad: %s' % materia, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'conamovilidad':
                try:
                    materia = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materia.sinasistencia = True
                    materia.verificahorario = False
                    materia.movilidad = True
                    materia.save(request)
                    materia.actualiza_notafinal()
                    if materia.materia.cerrado:
                        materia.cierre_materia_asignada()
                    log(u'Modifico estado movilidad: %s' % materia, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'cambiarfechamatricula':
                try:
                    form = FechaMatriculaForm(request.POST)
                    if form.is_valid():
                        nuevafecha = form.cleaned_data['fecha']
                        matricula = Matricula.objects.get(pk=request.POST['id'])
                        if nuevafecha < (datetime(matricula.nivel.inicio.year, matricula.nivel.inicio.month, matricula.nivel.inicio.day, 0, 0, 0) - timedelta(days=30)).date():
                            return bad_json(mensaje=u"La fecha no puede ser menor a 30 dias antes del nivel.")
                        if nuevafecha > matricula.nivel.fechatopematriculaes:
                            return bad_json(mensaje=u"La fecha no puede ser mayor a la fecha de matricula especial.")
                        matricula.fecha = nuevafecha
                        matricula.save(request)
                        log(u'Modifico fecha de matricula: %s' % matricula, request, "del")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delmatricula':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    if matricula.tiene_rubros_pagados():
                        return bad_json(mensaje=u'Existen pagos relacionados a esta matrícula')
                    matricula.formalizada = False
                    matricula.save()
                    matricula.eliminar_rubros_matricula()
                    for materiaasignada in matricula.materiaasignada_set.all():
                        materiaasignada.delete()
                    log(u'Elimino matricula: %s' % matricula, request, "del")
                    matricula.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'anularmatricula':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    matricula.formalizada = False
                    matricula.save()
                    matricula.eliminar_rubros_matricula()
                    for materiaasignada in matricula.materiaasignada_set.all():
                        materiaasignada.delete()
                    log(u'Anulo matricula de carrera: %s-%s' % (matricula.inscripcion.persona.cedula, matricula), request, "del")
                    for recipiente in Persona.objects.filter(id__in=[20454]):
                        send_mail(subject='Notificación de anulación de matricula.',
                                  html_template='emails/notificacionanulacionmatricula.html',
                                  data={'matricula': matricula},
                                  recipient_list=[recipiente])
                    matricula.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'activaranular':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    matricula.permiteanular = True
                    matricula.save(request)
                    log(u'Activo Anulación de matricula: %s' % matricula, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'desactivaranular':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    matricula.permiteanular = False
                    matricula.save(request)
                    log(u'Desactivo Anulación de matricula: %s' % matricula, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'recalcular':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    tipo = int(request.POST['idf'])
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'formalizar':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    matricula.formalizada = True
                    matricula.save(request)
                    Matricula.objects.filter(pk=matricula.id).update(tienepagominimo=True)
                    log(u'Formalizo matricula: %s' % matricula, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'generarrubros':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    matricula.calcular_rubros_matricula()
                    log(u'Genero rubros de matricula: %s' % matricula, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'noformalizar':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    matricula.formalizada = False
                    matricula.save(request)
                    Matricula.objects.filter(pk=matricula.id).update(tienepagominimo=False)
                    log(u'Quito formalizo matricula: %s' % matricula, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'retirar':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    form = RetiradoMatriculaForm(request.POST, request.FILES)
                    if form.is_valid():
                        newfile = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("retiro_", newfile._name)
                        if not matricula.retirado():
                            retiro = RetiroMatricula(matricula=matricula,
                                                     fecha=datetime.now(),
                                                     subtipo=form.cleaned_data['tipo'],
                                                     motivo=form.cleaned_data['motivo'],
                                                     archivo=newfile)
                            retiro.save()
                            Matricula.objects.filter(pk=request.POST['id']).update(cerrada=True)
                            log(u'Retiro la matricula: %s' % matricula, request, "edit")
                            return ok_json()
                        else:
                            return bad_json(mensaje=u"Ya se encuentra retirado de la matricula.")
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'retirarmateria':
                try:
                    materia = MateriaAsignada.objects.get(pk=request.POST['id'])
                    form = RetiradoMateriaForm(request.POST)
                    if form.is_valid():
                        if not materia.retirado():
                            retiro = MateriaAsignadaRetiro(materiaasignada=materia,
                                                           motivo=form.cleaned_data['motivo'],
                                                           valida=False,
                                                           fecha=datetime.now().date())
                            retiro.save(request)
                            materia.cerrado = True
                            materia.save(request)
                            calculo_eliminacionmateria(materia, persona, retiro.motivo)
                            materia.actualiza_estado()
                            log(u'Retiro de materia: %s' % retiro, request, "edit")
                            return ok_json()
                        else:
                            return bad_json(mensaje=u"Ya se encuentra retirado de la materia.")
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'materiasabiertas':
                try:
                    asignatura = Asignatura.objects.get(pk=request.POST['ida'])
                    inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                    nivel = Nivel.objects.get(pk=request.POST['nivel'])
                    return ok_json(data=materias_abiertas(asignatura, inscripcion, nivel))
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'matricular':
                return matricular(request, False, True)

            if action == 'movermateriasession':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])

                    if not materia.tiene_capacidad():
                        return bad_json(mensaje=u"No existe cupo para esta materia")
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['maid'])
                    materiaanterior = materiaasignada.materia
                    asistencias = materiaasignada.asistencialeccion_set.all()
                    asistencias.delete()
                    evaluaciones = materiaasignada.evaluacion()
                    evaluaciones.delete()
                    materiaasignada.materia = materia
                    materiaasignada.save(request)
                    materiaasignada.notafinal = 0
                    materiaasignada.fechaasignacion = materia.inicio
                    materiaasignada.asistenciafinal = 0
                    materiaasignada.save(request)
                    conflicto = conflicto_materias_seleccionadas(Materia.objects.filter(id__in=[x.materia.id for x in materiaasignada.matricula.materiaasignada_set.filter(verificahorario=True)]))
                    if conflicto:
                        transaction.set_rollback(True)
                        return bad_json(mensaje=conflicto)
                    materiaasignada.asistencias()
                    materiaasignada.evaluacion()
                    materiaasignada.matricula.save(request)
                    if materia.intensivo != materiaanterior.intensivo:
                        if materia.intensivo:
                            materiaasignada.matricula.agregacion(materiaasignada)
                    log(u'Cambio seccion materia: %s' % materiaasignada, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'nota':
                try:
                    result = actualizar_nota(request)
                    return empty_json(result)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'homologar':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    form = HomologacionInscripcionForm(request.POST)
                    if form.is_valid():
                        if materiaasignada.materiaasignadahomologacion_set.exists():
                            materiaasignadahomologacion = materiaasignada.materiaasignadahomologacion_set.all()[0]
                            homologacion = materiaasignadahomologacion.homologacion
                            homologacion.carrera = form.cleaned_data['carrera']
                            homologacion.asignatura = form.cleaned_data['asignatura']
                            homologacion.fecha = form.cleaned_data['fecha']
                            homologacion.nota_ant = form.cleaned_data['nota_ant']
                            homologacion.observaciones = form.cleaned_data['observaciones']
                            homologacion.creditos = form.cleaned_data['creditos']
                            homologacion.save(request)
                        else:
                            homologacion = HomologacionInscripcion(carrera=form.cleaned_data['carrera'],
                                                                   asignatura=form.cleaned_data['asignatura'],
                                                                   fecha=form.cleaned_data['fecha'],
                                                                   nota_ant=form.cleaned_data['nota_ant'],
                                                                   observaciones=form.cleaned_data['observaciones'],
                                                                   creditos=form.cleaned_data['creditos'])
                            homologacion.save(request)
                            materiaasignadahomologacion = MateriaAsignadaHomologacion(materiaasignada=materiaasignada,
                                                                                      homologacion=homologacion)
                            materiaasignadahomologacion.save(request)
                        log(u'Adicionada homologacion: %s' % homologacion, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'convalidar':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    form = ConvalidacionInscripcionForm(request.POST)
                    if form.is_valid():
                        if materiaasignada.materiaasignadaconvalidacion_set.exists():
                            materiaasignadaconvalidacion = materiaasignada.materiaasignadaconvalidacion_set.all()[0]
                            convalidacion = materiaasignadaconvalidacion.convalidacion
                            convalidacion.centro = form.cleaned_data['centro']
                            convalidacion.carrera = form.cleaned_data['carrera']
                            convalidacion.asignatura = form.cleaned_data['asignatura']
                            convalidacion.anno = form.cleaned_data['anno']
                            convalidacion.nota_ant = form.cleaned_data['nota_ant']
                            convalidacion.nota_act = form.cleaned_data['nota_act']
                            convalidacion.observaciones = form.cleaned_data['observaciones']
                            convalidacion.creditos = form.cleaned_data['creditos']
                            convalidacion.save(request)
                        else:
                            convalidacion = ConvalidacionInscripcion(centro=form.cleaned_data['centro'],
                                                                     carrera=form.cleaned_data['carrera'],
                                                                     asignatura=form.cleaned_data['asignatura'],
                                                                     anno=form.cleaned_data['anno'],
                                                                     nota_ant=form.cleaned_data['nota_ant'],
                                                                     nota_act=form.cleaned_data['nota_act'],
                                                                     observaciones=form.cleaned_data['observaciones'],
                                                                     creditos=form.cleaned_data['creditos'])
                            convalidacion.save(request)
                            materiaasignadaconvalidacion = MateriaAsignadaConvalidacion(materiaasignada=materiaasignada, convalidacion=convalidacion)
                            materiaasignadaconvalidacion.save(request)
                        log(u'Adicionada convalidacion: %s' % convalidacion, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'fechaasignacion':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    form = CambioFechaAsignacionMateriaForm(request.POST)
                    if form.is_valid():
                        materiaasignada.fechaasignacion = form.cleaned_data['fecha']
                        materiaasignada.save(request)
                        log(u'Modifico la fecha de asignacion de la materia: %s' % materiaasignada, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'segmento':
                try:
                    data = {}
                    data['materiaasignada'] = MateriaAsignada.objects.filter(id=request.POST['idma'])
                    data['materia'] = Materia.objects.get(pk=request.POST['id'])
                    data['validardeuda'] = False
                    data['incluyepago'] = False
                    data['incluyedatos'] = False
                    data['auditor'] = persona.tiene_permiso('ctt.puede_modificar_calificacion_tardia')
                    data['cronograma'] = None
                    data['permitecambiarcodigo'] = False
                    template = get_template("matriculas/segmento.html")
                    json_content = template.render(data)
                    return ok_json({'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == 'infohorario':
                try:
                    data = {}
                    periodo = None
                    lista = json.loads(request.POST['lista'])
                    data['materiasregulares'] = materiasregulares = Materia.objects.filter(id__in=lista).distinct()
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    data['clases'] = clases = Clase.objects.filter(materia__in=materiasregulares, activo=True).distinct()
                    data['turnos'] = Turno.objects.filter(clase__in=clases).distinct().order_by('comienza')
                    if materiasregulares:
                        periodo = materiasregulares.all()[0].nivel.periodo
                    data['periodo'] = periodo
                    template = get_template("matriculas/aluhorario.html")
                    json_content = template.render(data)
                    return ok_json({'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == 'verificariece':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['id'])
                    matricula.iece = (request.POST['valor'] == 'true')
                    matricula.save(request)
                    log(u"Agrego matricula iece: %s" % matricula, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'costomatricula':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                    nivel = Nivel.objects.get(pk=request.POST['nivel'])
                    fecha = convertir_fecha(request.POST['fecha'])
                    asignaturas = json.loads(request.POST['asignaturas'])
                    materias = json.loads(request.POST['materias'])
                    if inscripcion.carrera.posgrado:
                        if not materias:
                            return bad_json(mensaje=u"No puede matricular sin nignuna materia, escoja todas las materias respectivas del nivel para poder continuar.")
                    costo = costo_matricula(inscripcion=inscripcion, asignaturas=asignaturas, materias=materias, nivel=nivel, fecha=fecha)
                    return ok_json(data={'costos': costo})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == 'sidebeasistir':
                try:
                    materia = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materia.sinasistencia = False
                    materia.verificahorario = True
                    materia.save(request)
                    materia.actualiza_notafinal()
                    if materia.materia.cerrado:
                        materia.cierre_materia_asignada()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'nodebeasistir':
                try:
                    materia = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materia.sinasistencia = True
                    materia.verificahorario = False
                    materia.save(request)
                    materia.actualiza_notafinal()
                    if materia.materia.cerrado:
                        materia.cierre_materia_asignada()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'observaciones_tardia':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.observaciones = request.POST['observacion']
                    materiaasignada.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delevidencia':
                try:
                    evidencia = EvidenciaMateria.objects.get(pk=request.POST['id'])
                    log(u'Elimino evidencia de materia: %s' % evidencia, request, "del")
                    evidencia.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addevidencia':
                try:
                    ma = MateriaAsignada.objects.get(pk=request.POST['id'])
                    form = EvidenciaMateriaForm(request.POST, request.FILES)
                    if form.is_valid():
                        newfile = None
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("materia_", newfile._name)
                        evidencia = EvidenciaMateria(materia=ma.materia,
                                                     descripcion=form.cleaned_data['descripcion'],
                                                     fecha=form.cleaned_data['fecha'],
                                                     archivo=newfile)
                        evidencia.save(request)
                        log(u'Adiciono evidencia de materia: %s' % ma.materia, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editevidencia':
                try:
                    evidencia = EvidenciaMateria.objects.get(pk=request.POST['id'])
                    form = EvidenciaMateriaForm(request.POST, request.FILES)
                    if form.is_valid():
                        newfile = evidencia.archivo
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("tutoria_", newfile._name)
                        evidencia.descripcion = form.cleaned_data['descripcion']
                        evidencia.fecha = form.cleaned_data['fecha']
                        evidencia.archivo = newfile
                        evidencia.save(request)
                        log(u'Modificó evidencia de materia: %s' % evidencia, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addarchivoevidencia':
                try:
                    evidencia = EvidenciaMateria.objects.get(pk=request.POST['id'])
                    form = EvidenciaMateriaForm(request.POST, request.FILES)
                    if form.is_valid():
                        newfile = evidencia.archivo
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("tutoria_", newfile._name)
                        evidencia.archivo = newfile
                        evidencia.save(request)
                        log(u'Modificó evidencia de materia: %s' % evidencia, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'matricula':
                try:
                    data['title'] = u'Matricula de nivel académico'
                    nivel = Nivel.objects.get(pk=request.GET['id'])
                    idm = None
                    periodo = request.session['periodo']
                    search = ""
                    data['paralelosmaterias'] = ParaleloMateria.objects.all()
                    data['nivelesmalla'] = NivelMalla.objects.all()
                    data['carreras'] = carreras = request.session['carreras']
                    if 'materiaid' in request.session:
                        del request.session['materiaid']
                    carreraid = None
                    nivelmallaid = None
                    paralelomateriaid = None
                    # CARRERAS
                    if 'carreraid' in request.session:
                        carreraid = request.session['carreraid']
                    else:
                        request.session['carreraid'] = carreraid = carreras[0].id
                    if 'carreraid' in request.GET:
                        request.session['carreraid'] = carreraid = int(request.GET['carreraid'])
                    # NIVEL MALLA
                    if 'nivelmallaid' in request.session:
                        nivelmallaid = request.session['nivelmallaid']
                    else:
                        request.session['nivelmallaid'] = nivelmallaid = -1
                    if 'nivelmallaid' in request.GET:
                        request.session['nivelmallaid'] = nivelmallaid = int(request.GET['nivelmallaid'])
                    # PARALELO MATERIA
                    if 'paralelomateriaid' in request.session:
                        paralelomateriaid = request.session['paralelomateriaid']
                    else:
                        request.session['paralelomateriaid'] = paralelomateriaid = -1
                    if 'paralelomateriaid' in request.GET:
                        request.session['paralelomateriaid'] = paralelomateriaid = int(request.GET['paralelomateriaid'])
                    matriculas = Matricula.objects.filter(nivel=nivel)
                    if carreraid >= 0:
                        matriculas = matriculas.filter(inscripcion__carrera__id=carreraid)
                    if nivelmallaid >= 0:
                        matriculas = matriculas.filter(nivelmalla__id=nivelmallaid)
                    if paralelomateriaid > 0:
                        matriculas = matriculas.filter(paraleloprincipal__id=paralelomateriaid)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            matriculas = matriculas.filter(Q(inscripcion__persona__nombre1__icontains=search) |
                                                           Q(inscripcion__persona__nombre2__icontains=search) |
                                                           Q(inscripcion__persona__apellido1__icontains=search) |
                                                           Q(inscripcion__persona__apellido2__icontains=search) |
                                                           Q(inscripcion__persona__cedula__icontains=search) |
                                                           Q(inscripcion__persona__pasaporte__icontains=search) |
                                                           Q(inscripcion__identificador__icontains=search) |
                                                           Q(inscripcion__carrera__nombre__icontains=search) |
                                                           Q(inscripcion__persona__usuario__username__icontains=search), nivel=nivel).order_by('inscripcion__persona').distinct()
                        else:
                            matriculas = matriculas.filter(Q(inscripcion__persona__apellido1__icontains=ss[0]) &
                                                           Q(inscripcion__persona__apellido2__icontains=ss[1]), nivel=nivel).order_by('inscripcion__persona').distinct()
                    elif 'idm' in request.GET:
                        matriculas = matriculas.filter(nivel=nivel, id=request.GET['idm']).order_by('inscripcion__persona').distinct()
                    else:
                        matriculas = matriculas.filter(nivel=nivel).order_by('inscripcion__persona').distinct()
                    paging = MiPaginador(matriculas, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session and 'paginador_url' in request.session:
                            if request.session['paginador_url'] == 'matriculas':
                                paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        page = paging.page(p)
                    except:
                        p = 1
                        page = paging.page(p)
                    request.session['paginador'] = p
                    request.session['paginador_url'] = 'matriculas'
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['matriculas'] = page.object_list
                    data['search'] = search if search else ""
                    data['idm'] = idm if idm else ""
                    data['carreraid'] = carreraid
                    data['nivelmallaid'] = nivelmallaid
                    data['paralelomateriaid'] = paralelomateriaid
                    data['nivel'] = nivel
                    data['periodo'] = periodo
                    data['matriculados_total'] = matriculas.count()
                    data['reporte_0'] = obtener_reporte('lista_alumnos_matriculados')
                    data['reporte_1'] = obtener_reporte('certificado_matricula')
                    data['reporte_2'] = obtener_reporte('reporte_compromiso_pago')
                    data['reporte_3'] = obtener_reporte('certificado_de_promocion')
                    data['reporte_4'] = obtener_reporte('certificado_de_promocion_ingles')
                    data['usa_retiro_matricula'] = USA_RETIRO_MATRICULA
                    data['lista_forma_calculo'] = LISTA_FORMA_CALCULO
                    data['periodoseleccionado'] = periodo
                    data['formaliza'] = persona.tiene_permiso('ctt.puede_formalizar_matricula')
                    return render(request, "matriculas/matricula.html", data)
                except Exception as ex:
                    pass

            if action == 'addmatriculalibre':
                try:
                    data['title'] = u'Matricular estudiante'
                    data['periodo'] = periodo = request.session['periodo']
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    data['coordinacion'] = nivel.coordinacion()
                    data['errmsj'] = None
                    data['iid'] = None
                    data['inscripcion'] = None
                    if 'iid' in request.GET:
                        data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['iid'])
                        malla = inscripcion.mi_malla()
                        if inscripcion.sede != nivel.sede:
                            data['errmsj'] = u'EL ESTUDIANTE PERTENECE A OTRA SEDE'
                        elif inscripcion.carrera not in nivel.coordinacion().carrera.all():
                            data['errmsj'] = u'EL ESTUDIANTE NO ES DE LAS CARRERAS DE SU COORDINACION O FACULTAD'
                        elif inscripcion.modalidad != nivel.modalidad:
                            data['errmsj'] = u'EL ESTUDIANTE PERTENECE A OTRA MODALIDAD'
                        elif inscripcion.sesion != nivel.sesion:
                            data['errmsj'] = u'EL ESTUDIANTE PERTENECE A OTRA SESION'
                        elif not inscripcion.habilitadomatricula:
                            data['errmsj'] = u'EL ESTUDIANTE NO TIENE PERMISO DE MATRICULA'
                        elif inscripcion.retiro_carrera():
                            data['errmsj'] = u'EL ESTUDIANTE SE ENCUENTRA RETIRADO DE LA CARRERA'
                        elif inscripcion.matriculado():
                            data['errmsj'] = u'EL ESTUDIANTE ESTA MATRICULADO'
                        elif inscripcion.persona.documentos_sin_entregar():
                            data['errmsj'] = u'EL ESTUDIANTE TIENE LIBROS PENDIENTE DE ENTREGA'
                        elif not institucion.matricularcondeuda:
                            if inscripcion.persona.tiene_deuda_vencida():
                                if not inscripcion.permitematriculacondeuda:
                                    data['errmsj'] = u'EL ESTUDIANTE TIENE DEUDA VIGENTE'

                        if inscripcion.mi_nivel().nivel.id == NIVEL_MALLA_CERO:
                            data['materiasmalla'] = malla.asignaturamalla_set.filter(nivelmalla_id=NIVEL_MALLA_CERO).filter(matriculacion=True).order_by('nivelmalla', 'ejeformativo')
                        else:
                            data['materiasmalla'] = malla.asignaturamalla_set.filter().filter(matriculacion=True).order_by('nivelmalla', 'ejeformativo')
                        data['datosincripcion'] = inscripcion.documentosdeinscripcion_set.all()[0]
                        data['maximo_materia_online'] = malla.maximomateriasonline
                        data['secretarias'] = CargoInstitucion.objects.filter(cargo_id=50).distinct()
                    else:
                        data['matriculado'] = False
                        data['materiasmalla'] = None
                        data['materiasmodulos'] = None
                        data['maximo_materia_online'] = 0
                    data['matricular_con_conflicto_horario'] = MATRICULAR_CON_CONFLICTO_HORARIO
                    data['hoy'] = datetime.now().date()
                    data['nombreerroneo'] = Inscripcion.objects.get(pk=request.GET['ide']).persona.nombre_completo() if 'err' in request.GET else ''
                    return render(request, "matriculas/addmatriculalibre.html", data)
                except Exception as ex:
                    pass

            if action == 'delmatricula':
                try:
                    data['title'] = u'Borrar matricula de estudiante'
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['tiene_evaluacion'] = matricula.tiene_evaluacion()
                    return render(request, "matriculas/delmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'anularmatricula':
                try:
                    data['title'] = u'Anular matricula de estudiante'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/anularmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'activaranular':
                try:
                    data['title'] = u'Permitir anulación matricula de estudiante'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/activaranularmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivaranular':
                try:
                    data['title'] = u'Desactivar anulación matricula de estudiante'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/desactivaranularmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'recalcular':
                try:
                    data['title'] = u'Recalcular Rubros'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    data['tipo'] = request.GET['idf']
                    return render(request, "matriculas/recalcular.html", data)
                except Exception as ex:
                    pass

            if action == 'formalizar':
                try:
                    data['title'] = u'Formalizar Matrícula'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/formalizar.html", data)
                except Exception as ex:
                    pass

            if action == 'generarrubros':
                try:
                    data['title'] = u'Generar Rubros'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/generarrubros.html", data)
                except Exception as ex:
                    pass

            if action == 'noformalizar':
                try:
                    data['title'] = u'Formalizar Matrícula'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/noformalizar.html", data)
                except Exception as ex:
                    pass

            if action == 'continua':
                try:
                    matricula = Matricula.objects.get(pk=request.GET['id'])
                    if not matricula.nivel.cerrado:
                        retiro = matricula.retiromatricula_set.all()
                        retiro.delete()
                        for materia in matricula.materiaasignada_set.all():
                            retiro = materia.retiro()
                            retiro.delete()
                            if not materia.materia.cerrado:
                                materia.cerrado = False
                                materia.save(request)
                            materia.actualiza_estado()
                        log(u'Elimino retiro de matricula: %s' % retiro, request, "del")
                    return HttpResponseRedirect("/matriculas?action=matricula&id=" + str(matricula.nivel.id))
                except Exception as ex:
                    pass

            if action == 'retirar':
                try:
                    data['title'] = u'Retirar matricula de estudiante'
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    data['form'] = RetiradoMatriculaForm()
                    return render(request, "matriculas/retirar.html", data)
                except Exception as ex:
                    pass

            if action == 'retirarmateria':
                try:
                    data['title'] = u'Retirar de la materia al estudiante'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['form'] = RetiradoMateriaForm()
                    return render(request, "matriculas/retirarmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'continuarmateria':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    retiro = materiaasignada.materiaasignadaretiro_set.all()
                    materiaasignada.cerrado = False
                    materiaasignada.save(actualiza=True)
                    log(u"Elimino retiro de materia: %s" % materiaasignada, request, "del")
                    retiro.delete()
                    return HttpResponseRedirect("/matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    pass

            if action == 'calificaciontardia':
                try:
                    data['title'] = u'Calificación tardía'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['validardeuda'] = False
                    data['incluyepago'] = False
                    data['incluyedatos'] = False
                    return render(request, "matriculas/calificaciontardia.html", data)
                except Exception as ex:
                    pass

            if action == 'evidenciasmateria':
                try:
                    data['title'] = u'Evidencias de pasantía'
                    data['materiaasignada'] = ma = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['evidencias'] = ma.materia.evidenciamateria_set.all().order_by('-fecha')
                    return render(request, "matriculas/evidencias.html", data)
                except Exception as ex:
                    pass

            if action == 'addevidenciamateria':
                try:
                    data['title'] = u'Adicionar evidencia'
                    data['materiaasignada'] = ma = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['form'] = EvidenciaMateriaForm()
                    return render(request, "matriculas/addevidencia.html", data)
                except Exception as ex:
                    pass

            if action == 'addarchivoevidencia':
                try:
                    data['title'] = u'Adicionar evidencia'
                    data['materiaasignada'] = ma = MateriaAsignada.objects.get(pk=request.GET['ma'])
                    data['evidencia'] = evidencia = EvidenciaMateria.objects.get(pk=request.GET['id'])
                    form = EvidenciaMateriaForm()
                    form.archivo_e()
                    data['form'] = form
                    return render(request, "matriculas/addarchivoevidencia.html", data)
                except Exception as ex:
                    pass

            if action == 'editevidenciamateria':
                try:
                    data['title'] = u'Editar evidencia'
                    data['materiaasignada'] = ma = MateriaAsignada.objects.get(pk=request.GET['ma'])
                    data['evidencia'] = evidencia = EvidenciaMateria.objects.get(pk=request.GET['id'])
                    data['form'] = EvidenciaMateriaForm(initial={'fecha': evidencia.fecha,
                                                                 'descripcion': evidencia.descripcion})
                    return render(request, "matriculas/editevidencia.html", data)
                except Exception as ex:
                    pass

            if action == 'delevidenciamateria':
                try:
                    data['title'] = u'Borrar evidencia'
                    data['materiaasignada'] = ma = MateriaAsignada.objects.get(pk=request.GET['ma'])
                    data['evidencia'] = evidencia = EvidenciaMateria.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/delevidencia.html", data)
                except Exception as ex:
                    pass

            if action == 'materias':
                try:
                    data['title'] = u'Materias asignadas'
                    data['periodo'] = periodo
                    data['hoy'] = datetime.now().date()
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['materias'] = materias = matricula.materiaasignada_set.all()
                    data['records'] = records = RecordAcademico.objects.filter(inscripcion=matricula.inscripcion, aprobada=True).order_by('asignatura')
                    aprobadasids = [x.asignatura.id for x in records]
                    malla = matricula.inscripcion.mi_malla()

                    if not CALCULO_ASISTENCIA_CLASE:
                        for ma in matricula.materiaasignada_set.filter(cerrado=False):
                            ma.save(actualiza=True)
                            ma.actualiza_estado()
                    data['esposgrado'] = True if matricula.inscripcion.carrera.posgrado else False
                    data['pendientes_malla'] = malla.asignaturamalla_set.filter().exclude(asignatura_id__in=aprobadasids).order_by('nivelmalla')
                    data['genera_rubro_derecho'] = GENERAR_RUBRO_DERECHO
                    data['usa_retiro_materia'] = USA_RETIRO_MATERIA
                    data['permiteagregaciones'] = matricula.nivel.periodo.fecha_agregaciones()
                    data['reporte_0'] = obtener_reporte('seguimiento_silabus_estudiante')
                    data['reporte_1'] = obtener_reporte('certificado_de_promocion_materia')
                    data['reporte_2'] = obtener_reporte('certificado_de_promocion_ingles_materia')
                    return render(request, "matriculas/materias.html", data)
                except Exception as ex:
                    pass

            if action == 'delmateria':
                try:
                    data['title'] = u'Eliminar materia de asignadas'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/delmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'sinasistencia':
                try:
                    data['title'] = u'No tomar en cuenta asistencia'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/sinasistencia.html", data)
                except Exception as ex:
                    pass

            if action == 'conasistencia':
                try:
                    data['title'] = u'Tomar en cuenta asistencia'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/conasistencia.html", data)
                except Exception as ex:
                    pass

            if action == 'sinmovilidad':
                try:
                    data['title'] = u'No tomar en cuenta la movilidad'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/sinmovilidad.html", data)
                except Exception as ex:
                    pass

            if action == 'conmovilidad':
                try:
                    data['title'] = u'Tomar en cuenta movilidad'
                    data['materiaasignada'] = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/conmovilidad.html", data)
                except Exception as ex:
                    pass

            if action == 'promote':
                try:
                    data['title'] = u'Seleccionar materia para alumno'
                    data['tiponominacion'] = request.GET['tiponominacion'] if 'tiponominacion' in request.GET else None
                    data['asignatura'] = asignatura = Asignatura.objects.get(pk=request.GET['id'])
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['matricula'])
                    hoy = datetime.now().date()
                    data['materias'] = materias_abiertas(asignatura, matricula.inscripcion, matricula.nivel)
                    data['matricular_con_conflicto_horario'] = MATRICULAR_CON_CONFLICTO_HORARIO
                    return render(request, "matriculas/promote.html", data)
                except Exception as ex:
                    pass

            if action == 'movermateriasession':
                try:
                    data['title'] = u'Mover materia de session'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    hoy = datetime.now().date()
                    data['materias'] = materias_abiertas(materiaasignada.asignaturareal, materiaasignada.matricula.inscripcion, materiaasignada.matricula.nivel)
                    data['matricula'] = materiaasignada.matricula
                    return render(request, "matriculas/movermateriasession.html", data)
                except Exception as ex:
                    pass

            if action == 'validapararecord':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    retiro = materiaasignada.retiro()
                    retiro.valida = True
                    retiro.save(request)
                    return HttpResponseRedirect("/matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'novalidapararecord':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    retiro = materiaasignada.retiro()
                    retiro.valida = False
                    retiro.save(request)
                    return HttpResponseRedirect("/matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'convalidar':
                try:
                    data['title'] = u'Homologación de materia'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadaconvalidacion_set.exists():
                        materiaasignadaconvalidacion = materiaasignada.materiaasignadaconvalidacion_set.all()[0]
                        data['form'] = ConvalidacionInscripcionForm(initial={'asignatura': materiaasignadaconvalidacion.convalidacion.asignatura,
                                                                             'centro': materiaasignadaconvalidacion.convalidacion.centro,
                                                                             'carrera': materiaasignadaconvalidacion.convalidacion.carrera,
                                                                             'creditos': materiaasignadaconvalidacion.convalidacion.creditos,
                                                                             'observaciones': materiaasignadaconvalidacion.convalidacion.observaciones,
                                                                             'nota_ant': materiaasignadaconvalidacion.convalidacion.nota_ant,
                                                                             'nota_act': materiaasignadaconvalidacion.convalidacion.nota_act,
                                                                             'anno': materiaasignadaconvalidacion.convalidacion.anno})
                    else:
                        data['form'] = ConvalidacionInscripcionForm(initial={'asignatura': materiaasignada.materia.asignatura.nombre,
                                                                             'creditos': materiaasignada.materia.creditos})
                    return render(request, "matriculas/convalidar.html", data)
                except Exception as ex:
                    pass

            if action == 'fechaasignacion':
                try:
                    data['title'] = u'Cambiar fecha asignacion de la materia'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    data['form'] = CambioFechaAsignacionMateriaForm(initial={'fecha': materiaasignada.matricula.fecha})
                    return render(request, "matriculas/fechaasignacion.html", data)
                except Exception as ex:
                    pass

            if action == 'delconvalidacion':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadaconvalidacion_set.exists():
                        materiaasignadaconvalidacion = materiaasignada.materiaasignadaconvalidacion_set.all()[0]
                        log(u'Elimino convalidacion de materia: %s' % materiaasignadaconvalidacion, request, "del")
                        materiaasignadaconvalidacion.delete()
                    return HttpResponseRedirect("matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'delhomologacion':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadahomologacion_set.exists():
                        materiaasignadahomologacion = materiaasignada.materiaasignadahomologacion_set.all()[0]
                        log(u'Elimino homologacion de materia: %s' % materiaasignada, request, "del")
                        materiaasignadahomologacion.delete()
                    return HttpResponseRedirect("matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'homologar':
                try:
                    data['title'] = u'Homologacion de materia'
                    data['materiaasignada'] = materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    if materiaasignada.materiaasignadahomologacion_set.exists():
                        materiaasignadahomologacion = materiaasignada.materiaasignadahomologacion_set.all()[0]
                        data['form'] = HomologacionInscripcionForm(initial={'carrera': materiaasignadahomologacion.homologacion.carrera,
                                                                            'asignatura': materiaasignadahomologacion.homologacion.asignatura,
                                                                            'fecha': materiaasignadahomologacion.homologacion.fecha,
                                                                            'nota_ant': materiaasignadahomologacion.homologacion.nota_ant,
                                                                            'creditos': materiaasignadahomologacion.homologacion.creditos,
                                                                            'observaciones': materiaasignadahomologacion.homologacion.observaciones})
                    else:
                        data['form'] = HomologacionInscripcionForm(initial={'creditos': materiaasignada.materia.creditos})
                    return render(request, "matriculas/homologar.html", data)
                except Exception as ex:
                    pass

            if action == 'actualizarrecord':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.GET['id'])
                    materiaasignada.cierre_materia_asignada()
                    log(u'Actualizar record: %s' % materiaasignada, request, "edit")
                    return HttpResponseRedirect("matriculas?action=materias&id=" + str(materiaasignada.matricula.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cambiarfechamatricula':
                try:
                    data['title'] = u'Cambiar fecha de matricula de estudiante'
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['form'] = FechaMatriculaForm(initial={'fecha': matricula.fecha})
                    return render(request, "matriculas/cambiarfechamatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'sidebeasistir':
                try:
                    data['title'] = u'Confirmar que debe asistir'
                    data['materia'] = materia = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/sidebeasistir.html", data)
                except Exception as ex:
                    pass

            if action == 'nodebeasistir':
                try:
                    data['title'] = u'Confirmar que no debe asistir'
                    data['materia'] = materia = MateriaAsignada.objects.get(pk=request.GET['id'])
                    return render(request, "matriculas/nodebeasistir.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            data['title'] = u'Matrículas de alumnos'
            data['periodo'] = periodo = request.session['periodo']
            data['coordinacion'] = request.session['coordinacionseleccionada']
            data['reporte_0'] = obtener_reporte('matriculados_maestrias_con_materiasasignadas')
            return render(request, "matriculas/view.html", data)
