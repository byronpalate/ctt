# coding=utf-8
import json
from datetime import datetime

import xlrd
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.encoding import smart_str

from decorators import secure_module, last_access
from settings import NOTA_ESTADO_EN_CURSO, HORARIO_RESUMIDO, ALUMNOS_GROUP_ID, \
    CARRERA_FORMACION_CONTINUA_ID, ARCHIVO_TIPO_GENERAL, PERSONA_ADMINS_ACADEMICO_ID
from ctt.commonviews import adduserdata, obtener_reporte, actualizar_nota_curso
from ctt.forms import CursoEscuelaForm, MateriasCursoEscuelaForm, PagoCursoEscuelaForm, ClaseCursoForm, \
    CambiarAulaCursoComplemetarioForm, ActividadInscripcionForm, RetiradoMatriculaForm, DividirCursoEscuelaForm, \
    MoverCursoEscuelaForm, CostoCursoEscuelaForm, CambiarTipoRegistroForm, LocacionCursoEscuelaForm, LocacionForm, \
    LocacionCursoForm, ListaModeloEvaluativoForm, NuevaInscripcionExternaForm, \
    CambiarFichaInscripcionForm, ImportarArchivoXLSForm, PorcentajeDescuentoCursoForm, PreguntaAprobacionesForm, \
    AddDocumentoCursosComplementariosForm, ProfesorMateriaCursoForm
from ctt.funciones import MiPaginador, log, ok_json, bad_json, url_back, generar_usuario, generar_nombre, \
    fechatope_cursos, remover_tildes
from ctt.models import CursoEscuelaComplementaria, MatriculaCursoEscuelaComplementaria, Inscripcion, \
    MateriaCursoEscuelaComplementaria, \
    PagosCursoEscuelaComplementaria, MateriaAsignadaCurso, Clase, null_to_numeric, \
    RetiroMatriculaCursoEscuelaComplementaria, TipoCostoCurso, \
    LocacionesCurso, Locacion, EvaluacionGenericaCurso, \
    Persona, Coordinacion, Malla, Rubro, HistoricoRecordAcademico, RecordAcademico, Archivo, TipoEstudianteCurso, \
    Carrera, PorcentajeDescuentoCursos, null_to_text, Profesor


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    coordinacion = request.session['coordinacionseleccionada']

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'editar':
                try:
                    form = CursoEscuelaForm(request.POST)
                    if form.is_valid():
                        actividad = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        if CursoEscuelaComplementaria.objects.filter(codigo=form.cleaned_data['codigo']).exclude(id=actividad.id).exists():
                            return bad_json(mensaje=u"El código de identificacion del curso ya esta en uso.")
                        actividad.nombre = remover_tildes(form.cleaned_data['nombre'])
                        actividad.tema = form.cleaned_data['tema']
                        if actividad.materiacursoescuelacomplementaria_set.exists():
                            actividad.materiacursoescuelacomplementaria_set.update(fecha_inicio=form.cleaned_data['fechainicio'], fecha_fin=form.cleaned_data['fechafin'])
                        if not form.cleaned_data['sincupo']:
                            if form.cleaned_data['cupo'] < actividad.registrados():
                                return bad_json(mensaje=u"El numero de registrados es mayor al cupo solicitado.")
                        actividad.cupo = form.cleaned_data['cupo']
                        actividad.permiteregistrootramodalidad = form.cleaned_data['permiteregistrootramodalidad']
                        actividad.prerequisitos = form.cleaned_data['prerequisitos']
                        actividad.penalizar = form.cleaned_data['penalizar']
                        actividad.sincupo = form.cleaned_data['sincupo']
                        actividad.depositorequerido = True if actividad.costomatricula or actividad.costocuota else False
                        actividad.registroonline = form.cleaned_data['registroonline']
                        actividad.registrointerno = form.cleaned_data['registrointerno']
                        actividad.record = form.cleaned_data['record']
                        if not actividad.matriculacursoescuelacomplementaria_set.exists():
                            actividad.registrootrasede = form.cleaned_data['registrootrasede']
                            actividad.examencomplexivo = form.cleaned_data['examencomplexivo']
                            actividad.libreconfiguracion = form.cleaned_data['libreconfiguracion']
                            actividad.optativa = form.cleaned_data['optativa']
                            actividad.nivelacion = form.cleaned_data['nivelacion']
                        actividad.fecha_inicio = form.cleaned_data['fechainicio']
                        actividad.fecha_fin = form.cleaned_data['fechafin']
                        periodo = request.session['periodo']
                        sede = request.session['coordinacionseleccionada'].sede
                        tipocurso = form.cleaned_data['tipocurso']
                        costo = tipocurso.mis_costos_periodo(periodo, sede)
                        diferenciado = tipocurso.costodiferenciado
                        costomatricula = costo.costomatricula
                        costocuota = costo.costocuota
                        cuotas = costo.cuotas
                        diferenciado = tipocurso.costodiferenciado
                        if tipocurso.costolibre:
                            costomatricula = form.cleaned_data['costomatricula']
                            costocuota = form.cleaned_data['costocuota']
                            cuotas = form.cleaned_data['cuotas']
                        actividad.costomatricula = costomatricula
                        actividad.tipocurso = tipocurso
                        actividad.cuotas = cuotas
                        actividad.costocuota = costocuota
                        if not Clase.objects.filter(materiacurso__curso=actividad).exists():
                            actividad.modalidad = form.cleaned_data['modalidad']
                            actividad.sesion = form.cleaned_data['sesion']
                        actividad.carrera = form.cleaned_data['carrera']
                        actividad.paralelo = form.cleaned_data['paralelo']
                        actividad.codigo = form.cleaned_data['codigo']
                        actividad.departamento = remover_tildes(form.cleaned_data['departamento'])
                        actividad.solicitante_id = form.cleaned_data['solicitante'] if form.cleaned_data['solicitante'] > 0 else None
                        actividad.sincupo = form.cleaned_data['sincupo']
                        actividad.save(request)
                        log(u"Modifico curso: %s" % actividad, request, "edit")
                        try:
                            return ok_json()
                        except Exception as ex:
                            pass
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'add':
                try:
                    form = CursoEscuelaForm(request.POST)
                    if form.is_valid():
                        if form.cleaned_data['fechafin'] < form.cleaned_data['fechainicio']:
                            return bad_json(mensaje=u"Fechas incorrectas.")
                        if CursoEscuelaComplementaria.objects.filter(codigo=null_to_text(form.cleaned_data['codigo'])).exists():
                            return bad_json(mensaje=u"El código de identificacion del curso ya esta en uso.")
                        periodo = request.session['periodo']
                        sede = request.session['coordinacionseleccionada'].sede
                        tipocurso = form.cleaned_data['tipocurso']
                        costo = tipocurso.mis_costos_periodo(periodo, sede)
                        costomatricula = costo.costomatricula
                        costocuota = costo.costocuota
                        cuotas = costo.cuotas
                        diferenciado = tipocurso.costodiferenciado
                        aprobacion = costocuota + costomatricula
                        if tipocurso.costolibre:
                            costomatricula = form.cleaned_data['costomatricula']
                            costocuota = form.cleaned_data['costocuota']
                            cuotas = form.cleaned_data['cuotas']
                            aprobacion = costocuota + costomatricula
                        actividad = CursoEscuelaComplementaria(nombre=remover_tildes(form.cleaned_data['nombre']),
                                                               usamodeloevaluativo=form.cleaned_data['usamodeloevaluativo'],
                                                               penalizar=form.cleaned_data['penalizar'],
                                                               prerequisitos=form.cleaned_data['prerequisitos'],
                                                               permiteregistrootramodalidad=form.cleaned_data['permiteregistrootramodalidad'],
                                                               modeloevaluativo=form.cleaned_data['modeloevaluativo'],
                                                               tema=form.cleaned_data['tema'],
                                                               fecha_inicio=form.cleaned_data['fechainicio'],
                                                               fecha_fin=form.cleaned_data['fechafin'],
                                                               sesion=form.cleaned_data['sesion'],
                                                               codigo=form.cleaned_data['codigo'],
                                                               departamento=remover_tildes(form.cleaned_data['departamento']),
                                                               tipocurso=form.cleaned_data['tipocurso'],
                                                               periodo=request.session['periodo'],
                                                               solicitante_id=form.cleaned_data['solicitante'] if form.cleaned_data['solicitante'] > 0 else None,
                                                               carrera=form.cleaned_data['carrera'],
                                                               modalidad=form.cleaned_data['modalidad'],
                                                               paralelo=form.cleaned_data['paralelo'],
                                                               record=form.cleaned_data['record'],
                                                               sincupo=form.cleaned_data['sincupo'],
                                                               registrootrasede=form.cleaned_data['registrootrasede'],
                                                               registroonline=form.cleaned_data['registroonline'],
                                                               registrointerno=form.cleaned_data['registrointerno'],
                                                               costomatricula=null_to_numeric(costomatricula, 2),
                                                               costocuota=null_to_numeric(costocuota, 2),
                                                               cuotas=null_to_numeric(cuotas, 0),
                                                               cupo=form.cleaned_data['cupo'],
                                                               aprobacionfinanciero=False,
                                                               costodiferenciado=diferenciado,
                                                               coordinacion=request.session['coordinacionseleccionada'])
                        actividad.save(request)
                        actividad.actualiza_deposito_requerido()
                        validapromedio = tipocurso.validapromedio
                        log(u"Adiciono curso corto: %s" % actividad, request, "add")
                        return ok_json({"id": actividad.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addespecialidad':
                try:
                    form = CursoEscuelaForm(request.POST)
                    if form.is_valid():
                        if form.cleaned_data['fechafin'] < form.cleaned_data['fechainicio']:
                            return bad_json(mensaje=u"Fechas incorrectas.")
                        if CursoEscuelaComplementaria.objects.filter(codigo=form.cleaned_data['codigo']).exists():
                            return bad_json(mensaje=u"El código de identificacion del curso ya esta en uso.")
                        periodo = request.session['periodo']
                        sede = request.session['coordinacionseleccionada'].sede
                        costo = None
                        if form.cleaned_data['tipocurso']:
                            tipocurso = form.cleaned_data['tipocurso']
                            costo = tipocurso.mis_costos_periodo(periodo, sede)
                            costomatricula = costo.costomatricula
                            costocuota = costo.costocuota
                            cuotas = costo.cuotas
                            diferenciado = tipocurso.costodiferenciado
                        else:
                            costomatricula = form.cleaned_data['costomatricula']
                            costocuota = form.cleaned_data['costocuota']
                            cuotas = form.cleaned_data['cuotas']
                            diferenciado = form.cleaned_data['costodiferenciado']
                        actividad = CursoEscuelaComplementaria(mallacurso=form.cleaned_data['mallacurso'],
                                                               nombre=form.cleaned_data['nombre'],
                                                               fecha_inicio=form.cleaned_data['fechainicio'],
                                                               fecha_fin=form.cleaned_data['fechafin'],
                                                               sesion=form.cleaned_data['sesion'],
                                                               modalidad=form.cleaned_data['modalidad'],
                                                               codigo=form.cleaned_data['codigo'],
                                                               departamento=form.cleaned_data['departamento'],
                                                               periodo=request.session['periodo'],
                                                               solicitante_id=form.cleaned_data['solicitante'] if form.cleaned_data['solicitante'] > 0 else None,
                                                               paralelo=form.cleaned_data['paralelo'],
                                                               sincupo=form.cleaned_data['sincupo'],
                                                               record=form.cleaned_data['record'],
                                                               cupo=form.cleaned_data['cupo'],
                                                               registroonline=form.cleaned_data['registroonline'],
                                                               registrointerno=form.cleaned_data['registrointerno'],
                                                               costomatricula=null_to_numeric(costomatricula, 2),
                                                               costocuota=null_to_numeric(costocuota, 2),
                                                               cuotas=null_to_numeric(cuotas, 0),
                                                               aprobacionfinanciero=True,
                                                               costodiferenciado=diferenciado,
                                                               coordinacion=request.session['coordinacionseleccionada'],
                                                               depositoobligatorio=request.session['depositoobligatorio'])
                        actividad.save(request)
                        # if diferenciado and form.cleaned_data['tipocurso']:
                        #     for cd in costo.costodiferenciadocursoperiodo_set.all():
                        #         costod = CostodiferenciadoCurso(curso=actividad,
                        #                                         tipo=cd.tipo,
                        #                                         costomatricula=cd.costomatricula,
                        #                                         costocuota=cd.costocuota,
                        #                                         cuotas=cd.cuotas)
                        #         costod.save(request)
                        for asignatura in actividad.mallacurso.asignaturacurso_set.all():
                            materia = MateriaCursoEscuelaComplementaria(curso=actividad,
                                                                        asignaturamallacurso=asignatura,
                                                                        asignatura=asignatura.asignatura,
                                                                        fecha_inicio=actividad.fecha_inicio,
                                                                        fecha_fin=actividad.fecha_fin,
                                                                        requiereaprobar=asignatura.requiereaprobar,
                                                                        calificar=asignatura.calificar,
                                                                        calfmaxima=asignatura.notamaxima,
                                                                        calfminima=asignatura.notaaprobar,
                                                                        asistminima=asignatura.asistenciaaprobar,
                                                                        horas=asignatura.horas,
                                                                        creditos=asignatura.creditos)
                            materia.save(request)
                        log(u"Adiciono curso especialidad: %s" % actividad, request, "add")
                        return ok_json({"id": actividad.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addmateria':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    if LocacionesCurso.objects.filter(matriculacursoescuelacomplementaria__curso=curso).distinct().count() > 1:
                        return bad_json(mensaje=u'Existen matriculados en locaciones diferentes, debe de separar los estudiantes')
                    form = MateriasCursoEscuelaForm(request.POST)
                    if form.is_valid():
                        if not curso.usamodeloevaluativo:
                            calfmaxima = null_to_numeric(form.cleaned_data['califmaxima'], 0)
                            calfminima = null_to_numeric(form.cleaned_data['califminima'], 0)
                            asistminima = form.cleaned_data['asistminima']
                        else:
                            calfmaxima = curso.modeloevaluativo.notamaxima
                            calfminima = curso.modeloevaluativo.notaaprobar
                            asistminima = curso.modeloevaluativo.asistenciaaprobar
                        lms = None
                        plantillalms = None
                        if form.cleaned_data['usalms']:
                            lms = form.cleaned_data['lms']
                            plantillalms = form.cleaned_data['plantillalms']
                        profesor = None
                        if form.cleaned_data['profesor']:
                            profesor = Profesor.objects.get(pk=int(form.cleaned_data['profesor']))
                        validapromedio = False
                        if curso.tipocurso.id == 52:
                            validapromedio = True
                        materias = MateriaCursoEscuelaComplementaria(asignatura=form.cleaned_data['asignatura'],
                                                                     profesor=profesor,
                                                                     fecha_inicio=form.cleaned_data['fechainicio'],
                                                                     fecha_fin=form.cleaned_data['fechafin'],
                                                                     requiereaprobar=form.cleaned_data['requiereaprobar'],
                                                                     calificar=form.cleaned_data['calificar'],
                                                                     horas=form.cleaned_data['horas'],
                                                                     creditos=form.cleaned_data['creditos'],
                                                                     validacreditos=form.cleaned_data['validacreditos'],
                                                                     validapromedio=validapromedio,
                                                                     calfmaxima=calfmaxima,
                                                                     calfminima=calfminima,
                                                                     asistminima=asistminima,
                                                                     curso=curso)
                        materias.save()
                        for participante in curso.matriculacursoescuelacomplementaria_set.all():
                            materiaasignada = MateriaAsignadaCurso(matricula=participante,
                                                                   materia=materias,
                                                                   estado_id=NOTA_ESTADO_EN_CURSO)
                            materiaasignada.save()
                        log(u'Adiciono materia de curso: %s' % materias, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'adddescuento':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    form = PorcentajeDescuentoCursoForm(request.POST)
                    if form.is_valid():
                        if curso.existe_descuento(form.cleaned_data['descuento']):
                            return bad_json(mensaje="Ese descuento ya existe", error=6)
                        descuento = PorcentajeDescuentoCursos(curso=curso,
                                                              porcentaje=form.cleaned_data['porcentaje'],
                                                              descuento=form.cleaned_data['descuento'])
                        descuento.save()
                        log(u'Adiciono descuento de curso: %s %f' % (descuento.curso, descuento.porcentaje), request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addlocacion':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    form = LocacionCursoEscuelaForm(request.POST)
                    if form.is_valid():
                        if curso.materiacursoescuelacomplementaria_set.exists():
                            return bad_json(mensaje=u'Este curso ya tiene materias')
                        if LocacionesCurso.objects.filter(curso=curso, locacion=form.cleaned_data['locacion']).exists():
                            return bad_json(mensaje=u'Ya fue registrada esta locación para este curso')
                        locacion = LocacionesCurso(curso=curso,
                                                   locacion=form.cleaned_data['locacion'])
                        locacion.save(request)
                        log(u'Adiciono locacion de curso: %s' % locacion, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'nuevalocacion':
                try:
                    form = LocacionForm(request.POST)
                    if form.is_valid():
                        curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        sede = request.session['coordinacionseleccionada'].sede
                        if Locacion.objects.filter(nombre=form.cleaned_data['nombre'], sede=sede).exists():
                            return bad_json(mensaje=u'Ya existe una locación con ese nombre')
                        locacion = Locacion(nombre=form.cleaned_data['nombre'], sede=sede)
                        locacion.save(request)
                        locacioncurso = LocacionesCurso(curso=curso, locacion=locacion)
                        locacioncurso.save(request)
                        log(u'Adiciono locacion: %s' % locacion, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editlocacion':
                try:
                    locacion = LocacionesCurso.objects.get(pk=request.POST['id'])
                    form = LocacionCursoEscuelaForm(request.POST)
                    if form.is_valid():
                        locacion.locacion = form.cleaned_data['locacion']
                        locacion.save(request)
                        log(u'Adiciono locacion de curso: %s' % locacion, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'dellocacion':
                try:
                    locacion = LocacionesCurso.objects.get(pk=request.POST['id'])
                    log(u'Elimino locacion curso: %s' % locacion, request, "del")
                    locacion.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'eliminar':
                try:
                    actividad = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    log(u'Elimino curso: %s' % actividad, request, "del")
                    actividad.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'registrar':
                try:
                    form = ActividadInscripcionForm(request.POST)
                    fechamatricula = datetime.now().date()
                    if form.is_valid():
                        curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        if not curso.aprobacionfinanciero:
                            return bad_json(mensaje=u'El curso no ha sido aprobado por financiero')
                        inscripcion = Inscripcion.objects.get(id=int(form.cleaned_data['inscripcion']))
                        if curso.cerrado:
                            return bad_json(mensaje=u'El curso ya esta cerrado')
                        if MatriculaCursoEscuelaComplementaria.objects.filter(curso_id=request.POST['id'],inscripcion_id=form.cleaned_data['inscripcion']).exists():
                            return bad_json(mensaje=u'El alumno ya esta matriculado en este curso')
                        if not (curso.id == 2523 or inscripcion.id == 88456):
                            if inscripcion.tiene_deuda_fuera_periodo(curso.periodo) and not inscripcion.permitematriculacondeuda:
                                return bad_json(mensaje=u'El alumno no puede tomar este curso porque mantiene una deuda con la institución.')
                        matricula = MatriculaCursoEscuelaComplementaria(curso=curso,
                                                                        tipoestudiantecurso=form.cleaned_data['tipo'] if form.cleaned_data['tipo'] else None,
                                                                        inscripcion=inscripcion,
                                                                        locacion=form.cleaned_data['locacion'] if form.cleaned_data['locacion'] else None,
                                                                        estado_id=NOTA_ESTADO_EN_CURSO,
                                                                        fecha=fechamatricula,
                                                                        hora=datetime.now().time(),
                                                                        formalizada=True if (curso.costomatricula == 0 and curso.costocuota == 0) else False,
                                                                        fechatope=fechatope_cursos(fechamatricula, inscripcion))
                        matricula.save()
                        for materia in curso.materiacursoescuelacomplementaria_set.all():
                            asignatura = MateriaAsignadaCurso(matricula=matricula,
                                                              materia=materia,
                                                              estado_id=NOTA_ESTADO_EN_CURSO)
                            asignatura.save()
                        matricula.generar_rubro()
                        log(u"Adiciono registro de curso: %s" % matricula, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'registrarn':
                try:
                    form = NuevaInscripcionExternaForm(request.POST)
                    fechamatricula = datetime.now().date()
                    if form.is_valid():
                        curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        sede = curso.coordinacion.sede
                        persona = None
                        cedula = form.cleaned_data['cedula'].strip()
                        pasaporte = form.cleaned_data['pasaporte'].strip()
                        if not cedula and not pasaporte:
                            return bad_json(mensaje=u"Debe ingresar una identificación.")
                        if cedula:
                            if Persona.objects.filter(cedula=cedula).exists():
                                return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                        if pasaporte:
                            if Persona.objects.filter(pasaporte=pasaporte).exists():
                                return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                        if not Coordinacion.objects.filter(sede=sede, carrera__id=CARRERA_FORMACION_CONTINUA_ID).exists():
                            return bad_json(mensaje=u'No existe una Coordinación que maneje formación continua para esta sede.')
                        coordinacion = coordinacion = request.session['coordinacionseleccionada']
                        if not Malla.objects.filter(carrera__id=CARRERA_FORMACION_CONTINUA_ID).exists():
                            return bad_json(mensaje=u'No existe una Malla para Formacion continua.')
                        malla = Malla.objects.filter(carrera__id=CARRERA_FORMACION_CONTINUA_ID)[0]
                        persona = Persona(nombre1=remover_tildes(form.cleaned_data['nombre1']),
                                          nombre2=remover_tildes(form.cleaned_data['nombre2']),
                                          apellido1=remover_tildes(form.cleaned_data['apellido1']),
                                          apellido2=remover_tildes(form.cleaned_data['apellido2']),
                                          nacimiento=form.cleaned_data['nacimiento'],
                                          cedula=form.cleaned_data['cedula'],
                                          pasaporte=form.cleaned_data['pasaporte'],
                                          pais=form.cleaned_data['pais'],
                                          provincia=form.cleaned_data['provincia'],
                                          canton=form.cleaned_data['canton'],
                                          parroquia=form.cleaned_data['parroquia'],
                                          paisnac=form.cleaned_data['pais'],
                                          provincianac=form.cleaned_data['provincia'],
                                          cantonnac=form.cleaned_data['canton'],
                                          parroquianac=form.cleaned_data['parroquia'],
                                          sexo=form.cleaned_data['sexo'],
                                          telefono=form.cleaned_data['telefono'],
                                          telefono_conv=form.cleaned_data['telefono_conv'],
                                          email=form.cleaned_data['email'],
                                          direccion=remover_tildes(form.cleaned_data['direccion']))
                        persona.save()
                        persona.cambiar_clave()
                        generar_usuario(persona=persona, group_id=ALUMNOS_GROUP_ID)
                        inscripcion = Inscripcion(persona=persona,
                                                  fecha=datetime.now().date(),
                                                  hora=datetime.now().time(),
                                                  carrera_id=55,
                                                  sede=sede,
                                                  modalidad=malla.modalidad,
                                                  sesion=curso.sesion,
                                                  coordinacion=coordinacion,
                                                  observaciones='INGRESADO POR CURSOS Y ESCUELAS COMO EXTERNO')
                        inscripcion.save()
                        persona.crear_perfil(inscripcion=inscripcion)
                        matricula = MatriculaCursoEscuelaComplementaria(curso=curso,
                                                                        inscripcion=inscripcion,
                                                                        tipoestudiantecurso=form.cleaned_data['tipo'],
                                                                        estado_id=NOTA_ESTADO_EN_CURSO,
                                                                        fecha=fechamatricula,
                                                                        hora=datetime.now().time(),
                                                                        fechatope=fechatope_cursos(fechamatricula, inscripcion))
                        matricula.save()
                        for materia in curso.materiacursoescuelacomplementaria_set.all():
                            asignatura = MateriaAsignadaCurso(matricula=matricula,
                                                              materia=materia,
                                                              estado_id=NOTA_ESTADO_EN_CURSO)
                            asignatura.save()
                        matricula.generar_rubro()
                        inscripcion.preguntas_inscripcion()
                        inscripcion.persona.mi_perfil()
                        inscripcion.documentos_entregados()
                        inscripcion.mi_malla()
                        inscripcion.actualizar_nivel()
                        log(u'Ingreso alumno EXTERNO por cursos y escuelas: %s' % persona.nombre_completo(), request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'registromasivo':
                try:
                    fechamatricula = datetime.now().date()
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['idcurso'])
                    if not curso.aprobacionfinanciero:
                        return bad_json(mensaje=u'El curso no ha sido aprobado por financiero')
                    if curso.cerrado:
                        return bad_json(mensaje=u'El curso ya esta cerrado')
                    form = ImportarArchivoXLSForm(request.POST, request.FILES)
                    if form.is_valid():
                        hoy = datetime.now().date()
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("registromasivo_", nfile._name)
                        archivo = Archivo(nombre='REGISTRO MASIVO',
                                          fecha=datetime.now(),
                                          archivo=nfile,
                                          tipo_id=ARCHIVO_TIPO_GENERAL)
                        archivo.save(request)
                        workbook = xlrd.open_workbook(archivo.archivo.file.name)
                        sheet = workbook.sheet_by_index(0)
                        linea = 1
                        for rowx in range(sheet.nrows):
                            if linea > 1:
                                puntosalva = transaction.savepoint()
                                try:
                                    cols = sheet.row_values(rowx)
                                    cedula = smart_str(cols[0]).strip()
                                    pasaporte = smart_str(cols[1]).strip()
                                    persona = Persona.objects.get(cedula=cols[0])
                                    coordinacion = Coordinacion.objects.get(pk=int(cols[13]))
                                    carrera = Carrera.objects.get(pk=int(cols[14]))
                                    if not carrera.posgrado:
                                        inscripcion = Inscripcion.objects.filter(persona_id=persona.id, coordinacion_id=coordinacion.id, carrera_id=carrera.id)[0]
                                    else:
                                        inscripcion = Inscripcion.objects.filter(persona_id=persona.id,
                                                                                 carrera_id=carrera.id,
                                                                                 carrera__posgrado=True)[0]
                                    if inscripcion.tiene_deuda_fuera_periodo(curso.periodo):
                                        return bad_json(mensaje=u'El alumno no puede tomar este curso porque mantiene una deuda con la institución.')
                                    if not MatriculaCursoEscuelaComplementaria.objects.filter(curso_id=curso.id, inscripcion_id=inscripcion.id).exists():
                                        tipoestudiantecurso = TipoEstudianteCurso.objects.get(pk=7)
                                        matricula = MatriculaCursoEscuelaComplementaria(curso=curso,
                                                                                        tipoestudiantecurso=tipoestudiantecurso,
                                                                                        inscripcion=inscripcion,
                                                                                        locacion=None,
                                                                                        estado_id=NOTA_ESTADO_EN_CURSO,
                                                                                        fechatope=fechatope_cursos(fechamatricula, inscripcion))
                                        matricula.save()
                                        for materia in curso.materiacursoescuelacomplementaria_set.all():
                                            asignatura = MateriaAsignadaCurso(matricula=matricula,
                                                                              materia=materia,
                                                                              estado_id=NOTA_ESTADO_EN_CURSO)
                                            asignatura.save()
                                        matricula.generar_rubro()
                                        log(u"Adiciono registro de curso: %s" % matricula, request, "add")
                                    transaction.savepoint_commit(puntosalva)
                                except Exception as ex:
                                    transaction.savepoint_rollback(puntosalva)
                                    return bad_json(mensaje=u'Error al ingresar la línea: %s' % linea)
                            linea += 1
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delmatricula':
                try:
                    matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    if matricula.tiene_rubros_pagados():
                        return bad_json(mensaje=u'Existen pagos relacionados a esta matrícula')
                    matricula.eliminar_rubros_matricula()
                    for materiaasignada in matricula.materiaasignadacurso_set.all():
                        materiaasignada.delete()
                    log(u'Elimino matricula de curso: %s' % matricula, request, "del")
                    matricula.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'cambiartiporegistro':
                try:
                    form = CambiarTipoRegistroForm(request.POST)
                    if form.is_valid():
                        matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        if matricula.tiene_rubros_pagados():
                            return bad_json(mensaje=u'No se puede cambiar el Tipo. Existen pagos relacionados a esta matrícula')
                        matricula.tipoestudiantecurso = form.cleaned_data['tipo']
                        matricula.eliminar_rubros_matricula()
                        matricula.generar_rubro()
                        matricula.save(request)
                        log(u'Modifico matricula de curso: %s' % matricula, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'cambiarinscripcion':
                try:
                    form = CambiarFichaInscripcionForm(request.POST)
                    matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    inscripcion = matricula.inscripcion
                    if form.is_valid():
                        nuevainscripcion = Inscripcion.objects.filter(inscripcionmalla__malla=form.cleaned_data['malla'], persona=inscripcion.persona)[0]
                        if nuevainscripcion.egresado():
                            return bad_json(mensaje=u'No puede elegir una malla en la cual e encuentre egresado.')
                        for materia in matricula.materiaasignadacurso_set.all():
                            if nuevainscripcion.historicorecordacademico_set.filter(asignatura=materia.materia.asignatura).exists():
                                transaction.set_rollback(True)
                                return bad_json(mensaje=u'No se puede mover este registro.')
                            HistoricoRecordAcademico.objects.filter(inscripcion=inscripcion, asignatura=materia.materia.asignatura).update(inscripcion=nuevainscripcion)
                            if nuevainscripcion.recordacademico_set.filter(asignatura=materia.materia.asignatura).exists():
                                transaction.set_rollback(True)
                                return bad_json(mensaje=u'No se puede mover este registro.')
                            RecordAcademico.objects.filter(inscripcion=inscripcion, asignatura=materia.materia.asignatura).update(inscripcion=nuevainscripcion)
                        for rubro in Rubro.objects.filter(inscripcion=inscripcion, rubrocursoescuelacomplementaria__participante=matricula):
                            rubro.inscripcion = nuevainscripcion
                            rubro.save()
                        matricula.inscripcion = nuevainscripcion
                        matricula.save(request)
                        inscripcion.save()
                        nuevainscripcion.save()
                        log(u'Modifico matricula de curso: %s' % matricula, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'editclase':
                try:
                    form = ClaseCursoForm(request.POST)
                    if form.is_valid():
                        clase = Clase.objects.get(pk=request.POST['id'])
                        clase.aula = form.cleaned_data['aula']
                        clase.inicio = form.cleaned_data['inicio']
                        clase.fin = form.cleaned_data['fin']
                        clase.save()
                        log(u'Modifico horario de curso: %s' % clase, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editmateria':
                try:
                    form = MateriasCursoEscuelaForm(request.POST)
                    if form.is_valid():
                        materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        if materia.clase_set.filter(inicio__lt=form.cleaned_data['fechainicio']).exists():
                            return bad_json(mensaje=u'La fecha de inicio no coincide con el horario.')
                        if materia.clase_set.filter(fin__gt=form.cleaned_data['fechafin']).exists():
                            return bad_json(mensaje=u'La fecha fin no coincide con el horario.')
                        if form.cleaned_data['asignatura']:
                            materia.asignatura = form.cleaned_data['asignatura']
                        materia.profesor_id = form.cleaned_data['profesor']
                        materia.fecha_inicio = form.cleaned_data['fechainicio']
                        materia.fecha_fin = form.cleaned_data['fechafin']
                        materia.calificar = form.cleaned_data['calificar']
                        materia.asistminima = form.cleaned_data['asistminima']
                        materia.horas = form.cleaned_data['horas']
                        materia.creditos = form.cleaned_data['creditos']
                        materia.validacreditos = form.cleaned_data['validacreditos']
                        validapromedio = False
                        if materia.curso.tipocurso.id == 52:
                            validapromedio = True
                        materia.validapromedio = validapromedio
                        if form.cleaned_data['calificar']:
                            materia.calfmaxima = form.cleaned_data['califmaxima']
                            materia.calfminima = form.cleaned_data['califminima']
                        else:
                            materia.calfmaxima = 0
                            materia.calfminima = 0
                        materia.save()
                        for participante in materia.materiaasignadacurso_set.all():
                            participante.actualiza_estado()
                            participante.save()
                        log(u'Modifico materia de curso: %s' % materia, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editdescuento':
                try:
                    form = PorcentajeDescuentoCursoForm(request.POST)
                    if form.is_valid():
                        descuento = PorcentajeDescuentoCursos.objects.get(pk=request.POST['id'])
                        if descuento.curso.existe_descuento(form.cleaned_data['descuento']):
                            return bad_json(mensaje="Ese descuento ya existe", error=6)
                        descuento.porcentaje = form.cleaned_data['porcentaje']
                        descuento.descuento = form.cleaned_data['descuento']
                        descuento.save()
                        log(u'Modifico descuento de curso: %s' % descuento, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delmateria':
                try:
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    log(u'Elimino materia de curso: %s' % materia, request, "del")
                    materia.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'deldescuento':
                try:
                    descuento = PorcentajeDescuentoCursos.objects.get(pk=request.POST['id'])
                    log(u'Elimino descuento de curso: %s' % descuento, request, "del")
                    descuento.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'continuar':
                try:
                    matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    matricula.retiromatriculacursoescuelacomplementaria_set.all().delete()
                    log(u'Continuo curso: %s' % matricula, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'activar':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    curso.activo = True
                    curso.save(request)
                    log(u'Activo curso complementario: %s' % curso, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'desactivar':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    curso.activo = False
                    curso.save(request)
                    log(u'Desactivo curso complementario: %s' % curso, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'activarlocacion':
                try:
                    locacion = LocacionesCurso.objects.get(pk=request.POST['id'])
                    locacion.activo = True
                    locacion.save(request)
                    log(u'Activo locacion: %s' % locacion, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'desactivarlocacion':
                try:
                    locacion = LocacionesCurso.objects.get(pk=request.POST['id'])
                    locacion.activo = False
                    locacion.save(request)
                    log(u'Desactivo locacion: %s' % locacion, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'aprobarfin':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    curso.aprobacionfinanciero = True
                    curso.apruebafinanciero = persona
                    curso.save(request)
                    log(u'Aprobo financiero curso: %s' % curso, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'desaprobarfin':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    curso.aprobacionfinanciero = False
                    curso.apruebafinanciero = None
                    curso.activo = False
                    curso.save(request)
                    log(u'Desaprobo financiero curso: %s' % curso, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addpagos':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    form = PagoCursoEscuelaForm(request.POST)
                    if form.is_valid():
                        pagocurso = PagosCursoEscuelaComplementaria(curso=curso,
                                                                    tipo=form.cleaned_data['tipo'],
                                                                    fecha=form.cleaned_data['fecha'],
                                                                    valor=form.cleaned_data['valor'])
                        pagocurso.save()
                        log(u"Adiciono pago de curso: %s" % pagocurso, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editpagos':
                try:
                    pagocurso = PagosCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    form = PagoCursoEscuelaForm(request.POST)
                    if form.is_valid():
                        pagocurso.fecha = form.cleaned_data['fecha']
                        pagocurso.valor = form.cleaned_data['valor']
                        pagocurso.save()
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addclase':
                try:
                    form = ClaseCursoForm(request.POST)
                    if form.is_valid():
                        materia = MateriaCursoEscuelaComplementaria.objects.get(pk=int(request.POST['id']))
                        if Clase.objects.filter(materiacurso=materia, turno=form.cleaned_data['turno'], inicio=form.cleaned_data['inicio'], fin=form.cleaned_data['fin'], aula=form.cleaned_data['aula'], dia=form.cleaned_data['dia']).exists():
                            return bad_json(mensaje=u'Ya exise ese horario registrado.')
                        clase = Clase(materiacurso=materia,
                                      turno=form.cleaned_data['turno'],
                                      aula=form.cleaned_data['aula'],
                                      dia=form.cleaned_data['dia'],
                                      inicio=form.cleaned_data['inicio'],
                                      fin=form.cleaned_data['fin'],
                                      activo=True)
                        clase.save()
                        log(u'Adicionado horario de curso complementario: %s' % clase, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delclase':
                try:
                    clase = Clase.objects.get(pk=request.POST['id'])
                    if not clase.tiene_lecciones():
                        clase.delete()
                    else:
                        clase.activo = False
                        clase.save(request)
                    log(u'Elimino horario de materia de curso: %s' % clase, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'cambiaraulaclase':
                try:
                    form = CambiarAulaCursoComplemetarioForm(request.POST)
                    if form.is_valid():
                        materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        materia.clase_set.update(aula=form.cleaned_data['aula'])
                        log(u'Modifico horario: %s' % materia, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'retirar':
                try:
                    form = RetiradoMatriculaForm(request.POST)
                    if form.is_valid():
                        matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        retiro = RetiroMatriculaCursoEscuelaComplementaria(fecha=datetime.now().date(),
                                                                           matricula=matricula,
                                                                           observacion=form.cleaned_data['motivo'])
                        retiro.save(request)
                        log(u'Retiro de matricula de curso: %s' % matricula, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'cambiarlocacion':
                try:
                    form = LocacionCursoForm(request.POST)
                    if form.is_valid():
                        matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        matricula.locacion = form.cleaned_data['locacion']
                        matricula.save(request)
                        log(u'Cambio locacion de matricula de curso: %s' % matricula, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'anularmatricula':
                try:
                    matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    matricula.eliminar_rubros_matricula()
                    for materiaasignada in matricula.materiaasignadacurso_set.all():
                        materiaasignada.delete()
                    log(u'Anulo matricula cursos complementarios: %s' % matricula, request, "del")
                    matricula.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'mover':
                try:
                    form = MoverCursoEscuelaForm(request.POST)
                    if form.is_valid():
                        cursoproviene = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        cursodestino = form.cleaned_data['curso']
                        if cursodestino.cerrado or cursodestino.materiacursoescuelacomplementaria_set.filter(cerrada=True).exists():
                            return bad_json(mensaje=u'No puede mover alumnos a este curso ya que existen materias cerradas o el curso ya esta cerrado.')
                        datos = json.loads(request.POST['lista_items1'])
                        if cursodestino.cupo:
                            if (cursodestino.registrados() + len(datos)) > cursodestino.cupo:
                                return bad_json(mensaje=u'Sobrepasa el cupo del curso.')
                        for dato in datos:
                            matriculaanterior = MatriculaCursoEscuelaComplementaria.objects.get(pk=int(dato['id']))
                            materiaasignadas = matriculaanterior.materiaasignadacurso_set.all()
                            materiaasignadas.delete()
                            matriculaanterior.curso = cursodestino
                            matriculaanterior.save(request)
                            for materia in cursodestino.materiacursoescuelacomplementaria_set.all():
                                asignatura = MateriaAsignadaCurso(matricula=matriculaanterior,
                                                                  materia=materia,
                                                                  estado_id=NOTA_ESTADO_EN_CURSO)
                                asignatura.save(request)
                            log(u"Movio a curso: %s" % matriculaanterior, request, "add")
                        return ok_json({"id": cursodestino.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'dividir':
                try:
                    form = DividirCursoEscuelaForm(request.POST, request.FILES)
                    if form.is_valid():
                        curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                        if CursoEscuelaComplementaria.objects.filter(codigo=form.cleaned_data['codigo']).exists():
                            return bad_json(mensaje=u"El código de identificacion del curso ya esta en uso.")
                        actividad = CursoEscuelaComplementaria(nombre=curso.nombre,
                                                               usamodeloevaluativo=curso.usamodeloevaluativo,
                                                               modeloevaluativo=curso.modeloevaluativo,
                                                               mallacurso=curso.mallacurso if curso.mallacurso else None,
                                                               coordinacion=curso.coordinacion,
                                                               codigo=form.cleaned_data['codigo'],
                                                               solicitante_id=curso.solicitante_id if curso.solicitante_id > 0 else None,
                                                               departamento=curso.departamento,
                                                               fecha_inicio=curso.fecha_inicio,
                                                               fecha_fin=curso.fecha_fin,
                                                               tema=curso.tema,
                                                               periodo=curso.periodo,
                                                               sesion=curso.sesion,
                                                               modalidad=curso.modalidad,
                                                               tipocurso=curso.tipocurso,
                                                               sincupo=curso.sincupo,
                                                               cupo=curso.cupo,
                                                               paralelo=form.cleaned_data['paralelo'],
                                                               depositorequerido=curso.depositorequerido,
                                                               cerrado=curso.cerrado,
                                                               costodiferenciado=curso.costodiferenciado,
                                                               costomatricula=curso.costomatricula,
                                                               costocuota=curso.costocuota,
                                                               cuotas=curso.cuotas,
                                                               activo=curso.activo,
                                                               registroonline=curso.registroonline,
                                                               registrootrasede=curso.registrootrasede,
                                                               registrointerno=curso.registrointerno,
                                                               record=curso.record,
                                                               examencomplexivo=curso.examencomplexivo,
                                                               libreconfiguracion=curso.libreconfiguracion,
                                                               optativa=curso.optativa,
                                                               nivelacion=curso.nivelacion,
                                                               aprobacionfinanciero=curso.nivelacion,
                                                               apruebafinanciero=curso.apruebafinanciero,
                                                               actualizacionconocimiento=curso.actualizacionconocimiento,
                                                               permiteregistrootramodalidad=curso.permiteregistrootramodalidad,
                                                               penalizar=curso.penalizar,
                                                               prerequisitos=curso.prerequisitos,
                                                               depositoobligatorio=curso.depositoobligatorio)
                        actividad.save()
                        datos = json.loads(request.POST['lista_items1'])
                        for mat in curso.materiacursoescuelacomplementaria_set.all():
                            matn = MateriaCursoEscuelaComplementaria(curso=actividad,
                                                                     asignaturamallacurso=mat.asignaturamallacurso,
                                                                     asignatura=mat.asignatura,
                                                                     profesor=mat.profesor,
                                                                     fecha_inicio=mat.fecha_inicio,
                                                                     fecha_fin=mat.fecha_fin,
                                                                     calificar=mat.calificar,
                                                                     calfmaxima=mat.calfmaxima,
                                                                     calfminima=mat.calfminima,
                                                                     horas=mat.horas,
                                                                     creditos=mat.creditos,
                                                                     asistminima=mat.asistminima,
                                                                     cerrada=mat.cerrada,
                                                                     validacreditos=mat.validacreditos,
                                                                     validapromedio=mat.validapromedio,
                                                                     requiereaprobar=mat.requiereaprobar)
                            matn.save(request)
                            for dato in datos:
                                m = MatriculaCursoEscuelaComplementaria.objects.get(pk=int(dato['id']))
                                ma = m.materiaasignadacurso_set.filter(materia=mat)[0]
                                ma.materia = matn
                                ma.save()
                        for dato in datos:
                            m = MatriculaCursoEscuelaComplementaria.objects.get(pk=int(dato['id']))
                            m.curso = actividad
                            m.save()
                        log(u"Dividio curso: %s" % actividad, request, "add")
                        return ok_json({"id": actividad.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'adddoc':
                try:
                    registrado = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    form = AddDocumentoCursosComplementariosForm(request.POST, request.FILES)
                    if form.is_valid():
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("pregunta_", newfile._name)
                        archivo = DocumentosPersona(persona=registrado.inscripcion.persona,
                                                    nombre=form.cleaned_data['nombre'],
                                                    archivo=newfile)
                        archivo.save(request)
                        log(u'Adiciono archivo con nombre: %s para %s'  % (archivo.nombre,registrado.inscripcion.persona),request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'deldoc':
                try:
                    doc = DocumentosPersona.objects.get(pk=request.POST['id'])
                    log(u'Elimino el documento : %s de la persona %s' % (doc.nombre,doc.persona), request, "del")
                    doc.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'set_tiporegistro':
                try:
                    registro = MatriculaCursoEscuelaComplementaria.objects.get(pk=int(request.POST['id']))
                    registro.tiporegistro = int(request.POST['valor'])
                    registro.notateoria = 0
                    registro.notaexamen = 0
                    registro.notapractica = 0
                    registro.save(request)
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'set_nota_pract':
                try:
                    registro = MatriculaCursoEscuelaComplementaria.objects.get(pk=int(request.POST['id']))
                    registro.notapractica = float(request.POST['valor'])
                    registro.save(request)
                    registro.notaexamen = registro.nota_final()
                    registro.save(request)
                    return ok_json(data={'final': str(registro.notaexamen)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'set_nota_teo':
                try:
                    registro = MatriculaCursoEscuelaComplementaria.objects.get(pk=int(request.POST['id']))
                    registro.notateoria = float(request.POST['valor'])
                    registro.save(request)
                    registro.notaexamen = registro.nota_final()
                    registro.save(request)
                    return ok_json(data={'final': str(registro.notaexamen)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'datos_tipo_curso':
                try:
                    tipocurso = TipoCostoCurso.objects.get(pk=request.POST['id'])
                    periodo = request.session['periodo']
                    sede = request.session['coordinacionseleccionada'].sede
                    costo = tipocurso.mis_costos_periodo(periodo, sede)
                    return ok_json(data={'libre': tipocurso.costolibre, 'diferenciado': tipocurso.costodiferenciado, 'costo_mat': str(costo.costomatricula), 'costo_cuota': costo.costocuota, 'cuotas': costo.cuotas, 'validapromedio': tipocurso.validapromedio})
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cerrarmateria':
                try:
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    materia.cerrada = True
                    materia.validapromedio=materia.curso.tipocurso.validapromedio
                    materia.save()
                    for materiaasignada in materia.materiaasignadacurso_set.all():
                        materiaasignada.cierre_materia_asignada()
                        materiaasignada.matricula.actualiza_estado()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'abrirmateria':
                try:
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    materia.cerrada = False
                    materia.save()
                    for materiaasignada in materia.materiaasignadacurso_set.all():
                        materiaasignada.actualiza_estado()
                        materiaasignada.matricula.actualiza_estado()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'updatenotas':
                try:
                    materia = MateriaAsignadaCurso.objects.get(pk=request.POST['mid'])
                    valor = int(request.POST['valor'])
                    materia.calificacion = valor
                    materia.save(request)
                    materia.actualiza_estado()
                    log(u'Modifico calificacion de curso: %s' % materia, request, "edit")
                    return ok_json({'valor': materia.calificacion})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'updateasistencias':
                try:
                    materia = MateriaAsignadaCurso.objects.get(pk=request.POST['mid'])
                    valor = int(request.POST['valor'])
                    materia.asistencia = valor
                    materia.save(request)
                    materia.actualiza_estado()
                    log(u'Modifico asistencia de actualizacion de conocimientos: %s' % materia, request, "edit")
                    return ok_json({'valor': materia.asistencia})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'nota_curso':
                try:
                    result = actualizar_nota_curso(request)
                    return ok_json(result)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'asistcurso':
                try:
                    participante = MateriaAsignadaCurso.objects.get(pk=request.POST['id'])
                    participante.asistenciafinal = float(request.POST['valor'])
                    participante.save(request)
                    participante.actualiza_estado()
                    return ok_json({"valor": participante.asistenciafinal, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'notacurso':
                try:
                    participante = MateriaAsignadaCurso.objects.get(pk=request.POST['id'])
                    participante.notafinal = float(request.POST['valor'])
                    participante.save(request)
                    return ok_json({"valor": participante.notafinal, "estado": participante.estado.nombre, 'aprobada': participante.estado.aprobada(), 'curso': participante.estado.encurso()})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'cambiarmodelo':
                try:
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    form = ListaModeloEvaluativoForm(request.POST)
                    if form.is_valid():
                        materia = curso.materiacursoescuelacomplementaria_set.all()[0]
                        for m in materia.materiaasignadacurso_set.all():
                            curso.modeloevaluativo = form.cleaned_data['modelo']
                            curso.save(request)
                            evaluaciones = EvaluacionGenericaCurso.objects.filter(materiaasignadacurso=m)
                            evaluaciones.delete()
                            m.evaluacion_generica()
                            m.notafinal = 0
                            m.save(request)
                        log(u'Modifico modelo evaluativo: %s' % materia, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'actualizarrecord':
                try:
                    materiaasignada = MateriaAsignadaCurso.objects.get(pk=request.POST['id'])
                    materiaasignada.cierre_materia_asignada()
                    log(u'Actualizar record desde cursos y escuelas: %s' % materiaasignada, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'pasarrecord':
                try:
                    cursocomplementario = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    if cursocomplementario.record is True:
                        cursocomplementario.record=False
                    else:
                        cursocomplementario.record=True
                    cursocomplementario.save()
                    log(u'Activo Pasar Record del curso: %s' % cursocomplementario, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'activarcomplexivo':
                try:
                    cursocomplementario = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    if cursocomplementario.examencomplexivo is True:
                        cursocomplementario.examencomplexivo=False
                    else:
                        cursocomplementario.examencomplexivo = True
                    cursocomplementario.save()
                    log(u'Activa Examen Complexivo del curso: %s' % cursocomplementario, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'activarlibreconfiguracion':
                try:
                    cursocomplementario = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    if cursocomplementario.libreconfiguracion is True:
                        cursocomplementario.libreconfiguracion=False
                    else:
                        cursocomplementario.libreconfiguracion = True
                    cursocomplementario.save()
                    log(u'Activa Libre configuracion del curso: %s' % cursocomplementario, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'calculosalario':
                try:
                    materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    if 'ch' in request.POST:
                        materia.costohora = null_to_numeric(request.POST['ch'], 2)
                    else:
                        materia.costohora = 0

                    if 'hp' in request.POST:
                        materia.horasapagar = null_to_numeric(request.POST['hp'], 2)
                    else:
                        materia.horasapagar = 0
                    materia.save()
                    log(u'Modifico horas o costo a profesor curso escuela : %s-%s' % (
                        materia.profesor, materia.id), request, "add")
                    return ok_json(data={'salario': materia.salario})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

        if action == 'aprobado_financiero':
            try:
                materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                materia.aprobadofinanciero = request.POST['valor'] == 'true'
                materia.fechaaprobadofinanciero = datetime.now()
                materia.save(request)
                log(u"Aprobado por financiero curso escuela: %s" % materia.profesor, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'aprobado_decano':
            try:
                materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                materia.aprobadodecano = request.POST['valor'] == 'true'
                materia.fechaaprobadodecano = datetime.now()
                materia.save(request)
                log(u"Aprobado por decano curso escuela: %s" % materia.profesor, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'codigocontrato_doc':
            try:
                materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                materia.codigocontrato = null_to_text(request.POST['valor'])
                materia.fechacontrato = datetime.now()
                materia.save(request)
                log(u'Adiciono codigo de contrato  curso escuela : %s' % materia.profesor, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'formalizar':
            try:
                matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                matricula.formalizada = True
                matricula.save(request)
                log(u'Formalizo matricula en curso: %s' % matricula, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'noformalizar':
            try:
                matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                matricula.formalizada = False
                matricula.save(request)
                log(u'Quito formalizo matricula en curso: %s' % matricula, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'asignarlms':
            try:
                materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                form = AsignarLmsForm(request.POST)
                if form.is_valid():
                    if materia.cerrada:
                        return bad_json(mensaje=u"La materia se encuentra cerrada.")
                    materia.lms = form.cleaned_data['lms']
                    materia.plantillaslms = form.cleaned_data['plantillalms']
                    materia.profesorexportadolms = False
                    materia.save(request)
                    materia.materiaasignadacurso_set.update(exportadolms=False)
                    log(u'Modifico Lms y plantilla Lms: %s' % materia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'exportaralms':
            try:
                materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                form = ExportarMateriaLmsForm(request.POST)
                if form.is_valid():
                    if materia.lms.logica_general:
                        local_scope = {}
                        exec(materia.lms.logica_general, globals(), local_scope)
                        logica_general_materia_curso = local_scope['logica_general_materia_curso']
                        logica_general_materia_curso(materia, estudiantes=form.cleaned_data['exportarestudiante'], profesores=form.cleaned_data['exportarprofesor'])
                    materia.save(request)
                    log(u'Se exporto a lms la materia: %s' % materia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'plantillalms':
            try:
                lms = Lms.objects.get(pk=request.POST['id'])
                nlista = {}
                lista = []
                for plantilla in PlantillasLms.objects.filter(lms=lms, activo=True).distinct():
                    if not plantilla in lista:
                        lista.append(plantilla)
                        nlista.update({plantilla.id: {'id': plantilla.id, 'nombre': plantilla.nombre}})
                return ok_json({'lista': nlista})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'delprofesor':
            try:
                materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                log(u'Quito profesor %s de materia de curso: %s' % (materia.profesor, materia.curso), request, "edit")
                materia.profesor = None
                materia.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addprofesor':
            try:
                materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.POST['mid'])
                form = ProfesorMateriaCursoForm(request.POST)
                if form.is_valid():
                    if MateriaCursoEscuelaComplementaria.objects.filter(pk=request.POST['mid'], profesor_id=form.cleaned_data['profesor']).exists():
                        return bad_json(mensaje=u"El docente ya esta registrado en la materia.")
                    MateriaCursoEscuelaComplementaria.objects.filter(pk=request.POST['mid']).update(profesor_id=form.cleaned_data['profesor'])
                    profesor = Profesor.objects.get(pk=form.cleaned_data['profesor'])
                    log(u'Adiciono profesor: %s a la materia de curso: %s' % (profesor, materia.curso), request, "add")
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
            if action == 'pasarrecord':
                try:
                    data['title'] = u'Activar la opción de Pasar al Record'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/pasarrecord.html", data)
                except Exception as ex:
                    pass
            if action == 'activarcomplexivo':
                try:
                    data['title'] = u'Activar la opción de Examen Complexivo'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/activarcomplexivo.html", data)
                except Exception as ex:
                    pass
            if action == 'activarlibreconfiguracion':
                try:
                    data['title'] = u'Activar la opción de Libre Configuración'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/activarlibreconfiguracion.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminar':
                try:
                    data['title'] = u'Eliminar curso o escuela'
                    data['actividad'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/eliminar.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cerrar':
                try:
                    actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    if actividad.permite_cerrar():
                        actividad.cerrado = True
                        actividad.save()
                        for matricula in actividad.matriculacursoescuelacomplementaria_set.all():
                            matricula.actualiza_estado()
                    return HttpResponseRedirect('/adm_cursoscomplementarios')
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'abrir':
                try:
                    actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    actividad.cerrado = False
                    actividad.save()
                    for matricula in actividad.matriculacursoescuelacomplementaria_set.all():
                        matricula.actualiza_estado()
                    return HttpResponseRedirect('/adm_cursoscomplementarios')
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cerrarmateria':
                try:
                    data['title'] = u'Cerrar Materia'
                    data['materia'] = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/cerrarmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'abrirmateria':
                try:
                    data['title'] = u'Abrir Materia'
                    data['materia'] = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/abrirmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'hideclase':
                try:
                    clase = Clase.objects.get(pk=request.GET['id'])
                    clase.activo = False
                    clase.save()
                    return HttpResponseRedirect('/adm_cursoscomplementarios?action=horariomateria&id=' + str(clase.materiacurso.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'editar':
                try:
                    data['title'] = u'Editar curso o escuela'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = CursoEscuelaForm(initial={'nombre': actividad.nombre,
                                                     'mallacurso': actividad.mallacurso,
                                                     'tema': actividad.tema,
                                                     'permiteregistrootramodalidad': actividad.permiteregistrootramodalidad,
                                                     'usamodeloevaluativo': actividad.usamodeloevaluativo,
                                                     'modeloevaluativo': actividad.modeloevaluativo,
                                                     'penalizar': actividad.penalizar,
                                                     'prerequisitos': actividad.prerequisitos,
                                                     'fechainicio': actividad.fecha_inicio,
                                                     'fechafin': actividad.fecha_fin,
                                                     'periodo': actividad.periodo,
                                                     'sesion': actividad.sesion,
                                                     'modalidad': actividad.modalidad,
                                                     'codigo': actividad.codigo,
                                                     'departamento': actividad.departamento,
                                                     'solicitante': actividad.solicitante.id if actividad.solicitante else 0,
                                                     'paralelo': actividad.paralelo,
                                                     'tipocurso': actividad.tipocurso,
                                                     'sincupo': actividad.sincupo,
                                                     'registrootrasede': actividad.registrootrasede,
                                                     'registroonline': actividad.registroonline,
                                                     'registrointerno': actividad.registrointerno,
                                                     'record': actividad.record,
                                                     'examencomplexivo': actividad.examencomplexivo,
                                                     'libreconfiguracion': actividad.libreconfiguracion,
                                                     'optativa': actividad.optativa,
                                                     'nivelacion': actividad.nivelacion,
                                                     'costodiferenciado': actividad.costodiferenciado,
                                                     'cupo': actividad.cupo,
                                                     'costomatricula': actividad.costomatricula,
                                                     'costocuota': actividad.costocuota,
                                                     'costototal': actividad.costo(),
                                                     'cuotas': actividad.cuotas,
                                                     'depositorequerido': actividad.depositorequerido,
                                                     'depositoobligatorio': actividad.depositoobligatorio},)
                    form.editar(request.session['coordinacionseleccionada'], actividad)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/editar.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Adicionar curso o escuela - corto'
                    form = CursoEscuelaForm()
                    form.adicionar(request.session['coordinacionseleccionada'], request.session['periodo'])
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/add.html", data)
                except Exception as ex:
                    pass

            if action == 'addcosto':
                try:
                    data['title'] = u'Adicionar tipo de costo'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['form'] = CostoCursoEscuelaForm()
                    return render(request, "adm_cursoscomplementarios/addcosto.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiarmodelo':
                try:
                    data['title'] = u'Cambiar modelo evaluativo'
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = ListaModeloEvaluativoForm()
                    form.excluir_modeloactual(curso.modeloevaluativo)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/cambiarmodelo.html", data)
                except Exception as ex:
                    pass

            if action == 'addespecialidad':
                try:
                    data['title'] = u'Adicionar curso o escuela - especialidad'
                    form = CursoEscuelaForm()
                    form.adicionar(True, request.session['coordinacionseleccionada'])
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/addespecialidad.html", data)
                except Exception as ex:
                    pass

            if action == 'registrados':
                try:
                    data['title'] = u'Registrados en curso o escuela'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['registrados'] = actividad.matriculacursoescuelacomplementaria_set.all().order_by('inscripcion__persona')
                    data['reporte_0'] = obtener_reporte('ficha_registro')
                    data['reporte_1'] = obtener_reporte('registro_curso')
                    data['reporte_2'] = obtener_reporte('certificado_de_creditos_libre_conf')
                    data['reporte_3'] = obtener_reporte('certificado_de_promocion_ingles_cursos')
                    data['reporte_4'] = obtener_reporte('certificado_de_promocion_cursos')
                    return render(request, "adm_cursoscomplementarios/registrados.html", data)
                except Exception as ex:
                    pass

            if action == 'descuentos':
                try:
                    data['title'] = u'Descuentos en curso o escuela'
                    data['curso'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['descuentos'] = actividad.porcentajedescuentocursos_set.all().order_by('descuento')
                    return render(request, "adm_cursoscomplementarios/descuentos.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiartiporegistro':
                try:
                    data['title'] = u'Cambiar tipo de registro'
                    data['matricula'] = matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['form'] = form = CambiarTipoRegistroForm(initial={'tipo':matricula.tipoestudiantecurso})
                    return render(request, "adm_cursoscomplementarios/cambiartipo.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiarinscripcion':
                try:
                    data['title'] = u'Cambiar ficha de inscripcion'
                    data['matricula'] = matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = CambiarFichaInscripcionForm()
                    form.adicionar(matricula.inscripcion.persona)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/cambiarinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'costodiferenciado':
                try:
                    data['title'] = u'Tabla de costos segun tipo de registro'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['costos'] = actividad.tipocurso.mis_costos_periodo(actividad.periodo, actividad.coordinacion.sede).costodiferenciadocursoperiodo_set.all()
                    return render(request, "adm_cursoscomplementarios/costodiferenciado.html", data)
                except Exception as ex:
                    pass

            if action == 'formalizar':
                try:
                    data['title'] = u'Formalizar Matrícula'
                    data['matricula'] = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/formalizar.html", data)
                except Exception as ex:
                    pass

            if action == 'noformalizar':
                try:
                    data['title'] = u'Formalizar Matrícula'
                    data['matricula'] = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/noformalizar.html", data)
                except Exception as ex:
                    pass

            if action == 'registromasivo':
                try:
                    data['title'] = u'Registro Masivo'
                    data['form'] = ImportarArchivoXLSForm()
                    data['curso'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/importar.html", data)
                except Exception as ex:
                    pass


            if action == 'registrar':
                try:
                    data['title'] = u'Registrar en curso'
                    data['actividad'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = ActividadInscripcionForm()
                    form.adicionar(curso)
                    data['form'] = form
                    data['otra_sede'] = curso.registrootrasede
                    data['mooc'] = True if curso.coordinacion.id == 28 else False
                    return render(request, "adm_cursoscomplementarios/registrar.html", data)
                except Exception as ex:
                    pass

            if action == 'registrarn':
                try:
                    data['title'] = u'Registrar en curso'
                    data['actividad'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = NuevaInscripcionExternaForm()
                    form.adicionar(curso)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/registrarn.html", data)
                except Exception as ex:
                    pass

            if action == 'delmatricula':
                try:
                    data['title'] = u'Borrar matricula'
                    data['matricula'] = matricula = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/delmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'anularmatricula':
                try:
                    data['title'] = u'Anular matricula de estudiante'
                    data['matricula'] = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/anularmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'registradosmaterias':
                try:
                    data['title'] = u'Materias en curso o escuela'
                    data['registrado'] = registrado = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['materias'] = registrado.materiaasignadacurso_set.all()
                    return render(request, "adm_cursoscomplementarios/registradosmaterias.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'verdocumentos':
                try:
                    data['title'] = u'Documentación Ingresada por Estudiante'
                    data['registrado'] = registrado = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['documentos'] = DocumentosPersona.objects.filter(persona=registrado.inscripcion.persona)
                    return render(request, "adm_cursoscomplementarios/verdocumentos.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'adddoc':
                try:
                    data['title'] = u'Añadir Documento'
                    data['registrado'] = registrado = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['form'] = AddDocumentoCursosComplementariosForm()
                    return render(request, "adm_cursoscomplementarios/adddoc.html", data)
                except Exception as ex:
                    pass

            if action == 'deldoc':
                try:
                    data['title'] = u'Eliminar Documento'
                    data['registrado'] = registrado = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['idm'])
                    data['doc'] = DocumentosPersona.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/deldoc.html", data)
                except Exception as ex:
                    pass

            if action == 'actualizarrecord':
                try:
                    data['title'] = u'Actualizar record'
                    data['materia'] = MateriaAsignadaCurso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/actualizarrecord.html", data)
                except Exception as ex:
                    pass

            if action == 'calificaciontardia':
                try:
                    data['title'] = u'Ingreso de calificaciones'
                    data['registrado'] = materia = MateriaAsignadaCurso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/calificaciontardia.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cursos':
                try:
                    data['title'] = u'Registrar en cursos o escuela'
                    inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    cursos = CursoEscuelaComplementaria.objects.filter(fecha_fin__gte=datetime.now().date())
                    data['cursos'] = cursos
                    data['inscripcion'] = inscripcion
                    return render(request, "adm_cursoscomplementarios/cursos.html", data)
                except Exception as ex:
                    pass

            if action == 'addcurso':
                try:
                    data['title'] = u'Registrar en curso o escuela'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['idc'])
                    return render(request, "adm_cursoscomplementarios/addcurso.html", data)
                except Exception as ex:
                    pass

            if action == 'retirar':
                try:
                    data['title'] = u'Retiro de curso'
                    data['form'] = RetiradoMatriculaForm()
                    data['matricula'] = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/retirar.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cambiarlocacion':
                try:
                    data['title'] = u'Cambiar locacion'
                    data['form'] = LocacionCursoForm()
                    data['matricula'] = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/cambiarlocacion.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'materias':
                try:
                    data['title'] = u'Materias del curso o escuela'
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['materias'] = materias = curso.materiacursoescuelacomplementaria_set.all()
                    data['reporte_0'] = obtener_reporte('acta_calificacion_curso')
                    return render(request, "adm_cursoscomplementarios/materias.html", data)
                except Exception as ex:
                    pass

            if action == 'delprofesor':
                try:
                    data['title'] = u'Eliminar profesor de materia'
                    data['materia'] = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/delprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'addprofesor':
                try:
                    data['title'] = u'Adicionar profesor a materia de curso'
                    data['materia'] = materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['mid'])
                    data['form'] = ProfesorMateriaCursoForm()
                    return render(request, "adm_cursoscomplementarios/addprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'tomandom':
                try:
                    data['title'] = u'Tomando la materia'
                    data['materia'] = materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['materiasasignadas'] = materia.materiaasignadacurso_set.all().order_by('matricula__inscripcion__persona')
                    return render(request, "adm_cursoscomplementarios/tomandom.html", data)
                except Exception as ex:
                    pass

            if action == 'sububicaciones':
                try:
                    data['title'] = u'Locaciones'
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['locaciones'] = curso.locacionescurso_set.all()
                    return render(request, "adm_cursoscomplementarios/locaciones.html", data)
                except Exception as ex:
                    pass

            if action == 'horariomateria':
                try:
                    data['title'] = u'Horarios de clases del período'
                    data['materiacurso'] = materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['curso'] = curso = materia.curso
                    data['horario_resumido'] = HORARIO_RESUMIDO
                    data['dias'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                    return render(request, "adm_cursoscomplementarios/horariomateria.html", data)
                except Exception as ex:
                    pass

            if action == 'right':
                try:
                    miclase = Clase.objects.get(pk=request.GET['id'])
                    sesion = miclase.turno.sesion
                    for i in range(miclase.dia + 1, 7):
                        if sesion.dia_habilitado(i):
                            if not Clase.objects.filter(materiacurso=miclase.materiacurso, turno=miclase.turno, inicio=miclase.inicio, fin=miclase.fin, aula=miclase.aula, dia=i).exists():
                                clase_clon = Clase(materiacurso=miclase.materiacurso,
                                                   turno=miclase.turno,
                                                   inicio=miclase.inicio,
                                                   fin=miclase.fin,
                                                   aula=miclase.aula,
                                                   dia=i,
                                                   activo=True)
                                clase_clon.save()
                    return HttpResponseRedirect('/adm_cursoscomplementarios?action=horariomateria&id=' + str(miclase.materiacurso.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'delclase':
                try:
                    data['title'] = u'Eliminar Clase'
                    data['clase'] = Clase.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/delclase.html", data)
                except Exception as ex:
                    pass

            if action == 'editclase':
                try:
                    data['title'] = u'Editar clase de horario'
                    data['clase'] = clase = Clase.objects.get(pk=request.GET['id'])
                    form = ClaseCursoForm(initial={'materia': clase.materiacurso,
                                                   'turno': clase.turno,
                                                   'inicio': clase.inicio,
                                                   'aula': clase.aula,
                                                   'fin': clase.fin})
                    form.editar(clase.materiacurso.curso)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/editclase.html", data)
                except Exception as ex:
                    pass

            if action == 'addclase':
                try:
                    data['title'] = u'Adicionar materia a horario'
                    data['materia'] = materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = ClaseCursoForm(initial={'inicio': materia.fecha_inicio,
                                                   'fin': materia.fecha_fin,
                                                   'materia': materia})
                    form.adicionar(materia.curso)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/addclase.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiaraulaclase':
                try:
                    data['title'] = u'Cambiar aula de materia en el horario'
                    data['materia'] = materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['form'] = CambiarAulaCursoComplemetarioForm()
                    return render(request, "adm_cursoscomplementarios/cambiaraulaclase.html", data)
                except Exception as ex:
                    pass

            if action == 'addmateria':
                try:
                    data['title'] = u' Adicionar materias'
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = MateriasCursoEscuelaForm(initial={'fechainicio': curso.fecha_inicio,
                                                             'fechafin': curso.fecha_fin})
                    form.adicionar_curso(curso)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/addmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'adddescuento':
                try:
                    data['title'] = u' Adicionar materias'
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = PorcentajeDescuentoCursoForm()
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/adddescuento.html", data)
                except Exception as ex:
                    pass

            if action == 'addlocacion':
                try:
                    data['title'] = u' Adicionar locación'
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = LocacionCursoEscuelaForm()
                    form.adicionar(request.session['coordinacionseleccionada'].sede)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/addlocacion.html", data)
                except Exception as ex:
                    pass

            if action == 'nuevalocacion':
                try:
                    data['title'] = u' Adicionar locación'
                    data['form'] = LocacionForm()
                    data['curso'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/nuevalocacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editlocacion':
                try:
                    data['title'] = u' Editar locación'
                    data['locacion'] = locacion = LocacionesCurso.objects.get(pk=request.GET['id'])
                    form = LocacionCursoEscuelaForm(initial={'locacion': locacion.locacion,
                                                             'cupo': locacion.cupo})
                    form.adicionar(request.session['coordinacionseleccionada'].sede)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/editlocacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editmateria':
                try:
                    data['title'] = u'Editar materia'
                    data['materia'] = materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['form'] = MateriasCursoEscuelaForm(initial={'asignatura': materia.asignatura,
                                                                     'profesor_id': materia.profesor.id,
                                                                     'fechainicio': materia.fecha_inicio,
                                                                     'calificar': materia.calificar,
                                                                     'califmaxima': materia.calfmaxima,
                                                                     'califminima': materia.calfminima,
                                                                     'asistminima': materia.asistminima,
                                                                     'horas': materia.horas,
                                                                     'creditos': materia.creditos,
                                                                     'validacreditos': materia.validacreditos,
                                                                     'fechafin': materia.fecha_fin})
                    return render(request, "adm_cursoscomplementarios/editmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'editdescuento':
                try:
                    data['title'] = u'Editar descuento'
                    data['descuento'] = descuento = PorcentajeDescuentoCursos.objects.get(pk=request.GET['id'])
                    data['curso'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['cid'])
                    data['form'] = PorcentajeDescuentoCursoForm(initial={'descuento':descuento.descuento,
                                                                         'porcentaje':descuento.porcentaje})
                    return render(request, "adm_cursoscomplementarios/editdescuento.html", data)
                except Exception as ex:
                    pass

            if action == 'delmateria':
                try:
                    data['title'] = u'Eliminar materia'
                    data['materia'] = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/delmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'deldescuento':
                try:
                    data['title'] = u'Eliminar descuento'
                    data['descuento'] = PorcentajeDescuentoCursos.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/deldescuento.html", data)
                except Exception as ex:
                    pass

            if action == 'dellocacion':
                try:
                    data['title'] = u'Eliminar locacion'
                    data['locacion'] = LocacionesCurso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/dellocacion.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarfin':
                try:
                    data['title'] = u'Aprobación de financiero'
                    data['curso'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/aprobarfin.html", data)
                except Exception as ex:
                    pass

            if action == 'desaprobarfin':
                try:
                    data['title'] = u'Aprobación de financiero'
                    data['curso'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/desaprobarfin.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivar':
                try:
                    data['title'] = u'Desactivar curso'
                    data['curso'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/desactivar.html", data)
                except Exception as ex:
                    pass

            if action == 'activar':
                try:
                    data['title'] = u'Activar curso'
                    data['curso'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/activar.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivarlocacion':
                try:
                    data['title'] = u'Desactivar locacion'
                    data['locacion'] = LocacionesCurso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/desactivarlocacion.html", data)
                except Exception as ex:
                    pass

            if action == 'activarlocacion':
                try:
                    data['title'] = u'Activar locacion'
                    data['locacion'] = LocacionesCurso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/activarlocacion.html", data)
                except Exception as ex:
                    pass

            if action == 'continuar':
                try:
                    data['title'] = u'Continuar curso'
                    data['matricula'] = MatriculaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursoscomplementarios/continuar.html", data)
                except Exception as ex:
                    pass

            if action == 'pagos':
                try:
                    data['title'] = u'Cronograma de pagos'
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    pagos = curso.pagoscursoescuelacomplementaria_set.all()
                    data['curso'] = curso
                    data['pagos'] = pagos
                    return render(request, "adm_cursoscomplementarios/pagos.html", data)
                except Exception as ex:
                    pass

            if action == 'addpagos':
                try:
                    data['title'] = u'Adicionar pago'
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['curso'] = curso
                    form = PagoCursoEscuelaForm()
                    form.excluir_tipos(curso)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/addpagos.html", data)
                except Exception as ex:
                    pass

            if action == 'editpagos':
                try:
                    data['title'] = u'Editar pago'
                    data['pagocurso'] = pagocurso = PagosCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['curso'] = pagocurso.curso
                    data['tipo'] = pagocurso.nombre
                    form = PagoCursoEscuelaForm(initial={'tipo': pagocurso.tipo,
                                                         'fecha': pagocurso.fecha,
                                                         'valor': pagocurso.valor})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/editpagos.html", data)
                except Exception as ex:
                    pass

            if action == 'dividir':
                try:
                    data['title'] = u'Dividir curso o escuela'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['registrados'] = actividad.matriculacursoescuelacomplementaria_set.all().order_by('inscripcion__persona')
                    form = DividirCursoEscuelaForm()
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/dividir.html", data)
                except Exception as ex:
                    pass

            if action == 'mover':
                try:
                    data['title'] = u'Mover de curso o escuela'
                    data['actividad'] = actividad = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    data['registrados'] = actividad.matriculacursoescuelacomplementaria_set.all().order_by('inscripcion__persona')
                    form = MoverCursoEscuelaForm()
                    form.adicionar(actividad)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/mover.html", data)
                except Exception as ex:
                    pass

            if action == 'delpagos':
                try:
                    pagocurso = PagosCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    curso = pagocurso.curso
                    log(u'Elimino pago de curso: %s' % pagocurso, request, "del")
                    pagocurso.delete()
                    return HttpResponseRedirect("/adm_cursoscomplementarios?action=pagos&id=" + str(curso.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'asignarlms':
                try:
                    data['title'] = u'Cambiar Lms'
                    data['materia'] = materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = AsignarLmsForm(initial={'lms': materia.lms, 'plantillalms': materia.plantillaslms})
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/asignarlms.html", data)
                except Exception as ex:
                    pass

            if action == 'exportaralms':
                try:
                    data['materia'] = materia = MateriaCursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = ExportarMateriaLmsForm(initial={'materia': materia})
                    form.adicionar(materia)
                    data['form'] = form
                    return render(request, "adm_cursoscomplementarios/exportaralms.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Cursos y escuelas complementarias'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    actividades = CursoEscuelaComplementaria.objects.filter(
                        Q(matriculacursoescuelacomplementaria__inscripcion__persona__apellido1__icontains=search) |
                        Q(matriculacursoescuelacomplementaria__inscripcion__persona__apellido2__icontains=search) |
                        Q(matriculacursoescuelacomplementaria__inscripcion__persona__cedula__icontains=search) |
                        Q(nombre__icontains=search),
                        coordinacion=data['coordinacionseleccionada'],
                        periodo=data['periodo'],
                        actualizacionconocimiento=False,
                        coordinacion__sede=data['coordinacionseleccionada'].sede
                    ).distinct().order_by('-fecha_fin')
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    actividades = CursoEscuelaComplementaria.objects.filter(id=ids, periodo=data['periodo'],
                                                                            actualizacionconocimiento=False,
                                                                            coordinacion=data['coordinacionseleccionada'],
                                                                            coordinacion__sede=data['coordinacionseleccionada'].sede)
                else:
                    actividades = CursoEscuelaComplementaria.objects.filter(coordinacion__sede=data['coordinacionseleccionada'].sede, coordinacion=data['coordinacionseleccionada'],
                                                                            periodo=data['periodo'],
                                                                            actualizacionconocimiento=False).order_by('-fecha_fin')

                paging = MiPaginador(actividades, 20)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_cursoscomplementarios':
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
                request.session['paginador_url'] = 'adm_cursoscomplementarios'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['actividades'] = page.object_list
                data['periodo'] = request.session['periodo']
                data['reporte_0'] = obtener_reporte("listado_estudiantes_curso")
                data['reporte_1'] = obtener_reporte("registro_general_curso")
                data['reporte_2'] = obtener_reporte("listado_estudiantes_curso_plataforma_virtual")
                data['reporte_3'] = obtener_reporte("listado_estudiantes_curso_detallado")
                data['reporte_4'] = obtener_reporte("c_promocion_principal_masivo_ingles_cursos")
                return render(request, "adm_cursoscomplementarios/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
