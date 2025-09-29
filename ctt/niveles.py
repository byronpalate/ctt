# coding=utf-8
import json
from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.db.models.aggregates import Sum
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.core import serializers
from copy import deepcopy


from decorators import secure_module, last_access
from settings import TIPO_DOCENTE_TEORIA, TIPO_DOCENTE_PRACTICA, CAPACIDAD_MATERIA_INICIAL, VERIFICAN_HORAS_HORARIO, \
    RESPONSABLES_DISTRIBUTIVO_GRUPO_ID, PERSONA_ADMINS_ACADEMICO_ID, PERSONA_ADMINS_ACADEMICO_POSGRADO_ID
from ctt.commonviews import adduserdata, obtener_reporte, conflicto_materias_seleccionadas
from ctt.forms import NivelForm, NivelFormEdit, ProfesorMateriaForm, MateriaDividirForm, MateriaNivelForm, \
    MateriaNivelMallaForm, CambiarAulaForm, ListaModeloEvaluativoForm, CalificacionDiaForm, \
    FechafinAsistenciasForm, MateriaOtrasCarrerasForm, MateriasCompartidasForm, NivelMatriculaForm, EvaluacionDiaForm, \
    RubricaTallerPlanificacionForm
from ctt.funciones import log, convertir_fecha, url_back, bad_json, ok_json, detectar_cambios, diff_log
from ctt.models import Nivel, Materia, ProfesorMateria, MateriaAsignada, AsignaturaMalla, \
    Malla, NivelMalla, EvaluacionGenerica, Leccion, AlumnosPracticaMateria, ModuloMalla, \
    ParaleloMateria, LeccionGrupo, Matricula, RecordAcademico, HistoricoRecordAcademico, Carrera, \
    Asignatura, null_to_numeric, NivelEstudiantesMatricula, TallerPlanificacionMateria, \
    ActividadesAprendizajeCondocenciaAsistida, ActividadesAprendizajeColaborativas, PlanificacionMateria, Persona, \
    ProfesorDistributivoHoras, Clase, \
    ActualizacionAsistencia, FlujoAprobacion, PasoFlujo, SolicitudCambio

from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

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
    if persona.id in PERSONA_ADMINS_ACADEMICO_ID:
        data['PERSONA_ADMINS_ACADEMICO_ID'] = True

    if persona.id in PERSONA_ADMINS_ACADEMICO_POSGRADO_ID:
        data['PERSONA_ADMINS_ACADEMICO_POSGRADO_ID'] = True
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                form = NivelForm(request.POST)
                if form.is_valid():
                    # Se permite temporalmente el registro de niveles con fechas 3 meses antes y después del período - Carlos Aldás
                    coordinacion = request.session['coordinacionseleccionada']

                    if periodo.fin < form.cleaned_data['fin']:
                        return bad_json(mensaje=u"Fecha fin incorrecta.")
                    if periodo.inicio > form.cleaned_data['inicio']:
                        return bad_json(mensaje=u"Fecha inicio incorrecta.")
                    if form.cleaned_data['fechatopematriculaesp'] < form.cleaned_data['fechatopematriculaext'] or form.cleaned_data['fechatopematriculaesp'] > form.cleaned_data['fin']:
                        return bad_json(mensaje=u"Fecha tope matricula especial incorrecta.")
                    if form.cleaned_data['fechatopematriculaext'] < form.cleaned_data['fechatopematricula']:
                        return bad_json(mensaje=u"Fecha tope matricula incorrecta.")
                    nivel = Nivel(periodo=periodo,
                                  sesion=form.cleaned_data['sesion'],
                                  inicio=form.cleaned_data['inicio'],
                                  fin=form.cleaned_data['fin'],
                                  fechacierre=form.cleaned_data['fechacierre'],
                                  paralelo=form.cleaned_data['paralelo'],
                                  modalidad=form.cleaned_data['modalidad'],
                                  sede=coordinacion.sede,
                                  cerrado=False,
                                  fechatopematricula=form.cleaned_data['fechatopematricula'],
                                  fechatopematriculaex=form.cleaned_data['fechatopematriculaext'],
                                  fechatopematriculaes=form.cleaned_data['fechatopematriculaesp'],
                                  nivelgrado=False,
                                  mensaje=form.cleaned_data['mensaje'],
                                  aplicabecas=True)
                    nivel.save(request)
                    nivel.coordinacion(coordinacion)
                    log(u'Adiciono nivel: %s' % nivel, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'nivelvisible':
            try:
                nivel = Nivel.objects.get(pk=request.POST['nid'])
                status = True if request.POST['status'] == "1" else False
                ext = nivel.extension()
                ext.modificarhorario = status
                ext.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'nivelmatricular':
            try:
                nivel = Nivel.objects.get(pk=request.POST['nid'])
                status = True if request.POST['status'] == "1" else False
                ext = nivel.extension()
                ext.modificarcupo = status
                ext.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'dividir':
            try:
                form = MateriaDividirForm(request.POST)
                if form.is_valid():
                    for ma_id in request.POST.getlist('ins'):
                        ma = MateriaAsignada.objects.get(pk=ma_id)
                        ma.materia = form.cleaned_data['materia']
                        ma.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addnivelmatricula':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                form = NivelMatriculaForm(request.POST)
                if form.is_valid():
                    if NivelEstudiantesMatricula.objects.filter(nivel=nivel, nivelmalla=form.cleaned_data['nivelmalla'], carrera=form.cleaned_data['carrera'], modalidad=nivel.modalidad).exists():
                        return bad_json(mensaje=u'Ya existe un registro con estos parametros.')
                    nivelmatricula = NivelEstudiantesMatricula(nivel=nivel,
                                                               nivelmalla=form.cleaned_data['nivelmalla'],
                                                               carrera=form.cleaned_data['carrera'],
                                                               modalidad=nivel.modalidad)
                    nivelmatricula.save(request)
                    log(u'Adicionado nivel de matricula: %s' % nivel, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delnivelmatricula':
            try:
                nivelmatricula = NivelEstudiantesMatricula.objects.get(pk=request.POST['id'])
                log(u"Elimino nivel de matriculacion: %s" % nivelmatricula, request, "del")
                nivelmatricula.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'edit':
            try:
                form = NivelFormEdit(request.POST)
                nivel = Nivel.objects.get(pk=request.POST['id'])
                nivel_original = deepcopy(nivel)  # ② copia en memoria
                coordinacion = request.session['coordinacionseleccionada']
                if form.is_valid():
                    if not nivel.tiene_matriculados():
                        if form.cleaned_data['fechatopematriculaesp'] < form.cleaned_data['fechatopematriculaext'] or form.cleaned_data['fechatopematriculaesp'] > form.cleaned_data['fin']:
                            return bad_json(mensaje=u"Fecha tope matricula especial incorrecta.")
                        if form.cleaned_data['fechatopematriculaext'] < form.cleaned_data['fechatopematricula']:
                            return bad_json(mensaje=u"Fecha tope matricula incorrecta.")
                    campos_mapeados = {
                        'inicio': 'inicio',
                        'fin': 'fin',
                        'fechacierre': 'fechacierre',
                        'fechatopematricula': 'fechatopematricula',
                        'fechatopematriculaext': 'fechatopematriculaex',
                        'fechatopematriculaesp': 'fechatopematriculaes',
                    }
                    cambios = detectar_cambios(nivel, form.cleaned_data, campos_mapeados)
                    nivel.inicio = form.cleaned_data['inicio']
                    nivel.fin = form.cleaned_data['fin']
                    nivel.fechacierre = form.cleaned_data['fechacierre']
                    nivel.fechatopematricula = form.cleaned_data['fechatopematricula']
                    nivel.fechatopematriculaex = form.cleaned_data['fechatopematriculaext']
                    nivel.fechatopematriculaes = form.cleaned_data['fechatopematriculaesp']
                    nivel.mensaje = form.cleaned_data['mensaje']
                    nivel.save(request)
                    # Logs
                    # log(f"Nivel {nivel.id} editado exitosamente.", request, "edit")
                    # if cambios:
                    #     log(u'Cambios detectados en nivel %s: %s' % (nivel.id, "; ".join(cambios)), request, "edit")
                    # else:
                    #     log(u'Nivel %s editado sin cambios en fechas clave.' % nivel.id, request, "edit")

                    cambios = diff_log(nivel_original, nivel)

                    if cambios:
                        msg = "; ".join(f"{c['field']}: '{c['old']}' → '{c['new']}'" for c in cambios)
                        log(f"Cambios en nivel {nivel.id}: {msg}", request, "edit")
                    else:
                        log(f"Nivel {nivel.id} guardado sin cambios", request, "edit")

                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'del':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                if not nivel.puede_eliminarse():
                    return bad_json(mensaje=u"No se puede eliminar el nivel.")
                log(u'Elimino nivel: %s' % nivel, request, "del")
                nivel.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'addmateriamalla':
            try:
                nivel = Nivel.objects.get(pk=request.POST['nid'])
                form = MateriaNivelMallaForm(request.POST)
                mnm = 0
                if form.is_valid():
                    listado = request.POST['seleccionados']
                    listadomodulos = request.POST['seleccionadosmodulos']
                    listadointensivos = request.POST['seleccionadosintensivos']
                    usalms = form.cleaned_data['usalms']
                    lmsdesdemalla = form.cleaned_data['lmsdesdemalla']
                    if listado:
                        for materiamalla in AsignaturaMalla.objects.filter(id__in=[int(x) for x in listado.split(',')]):
                            if (nivel.coordinacion() and listadointensivos and (nivel.coordinacion().id == 16 or nivel.coordinacion().id == 17)):
                                for materiamalla in AsignaturaMalla.objects.filter(id__in=[int(x) for x in listadointensivos.split(',')]):
                                    if Materia.objects.filter(asignaturamalla=materiamalla, nivel=nivel, paralelomateria=form.cleaned_data['paralelomateria'], intensivo=True).exists():
                                        return bad_json(mensaje=u'Ya se encuentra registrada la materia como intensivo: %s en el paralelo: %s' % (materiamalla.asignatura, form.cleaned_data['paralelomateria']))
                            else:
                                if Materia.objects.filter(asignaturamalla=materiamalla, nivel=nivel, paralelomateria=form.cleaned_data['paralelomateria'], intensivo=False).exists():
                                    return bad_json(mensaje=u'Ya se encuentra registrada la materia: %s en el paralelo: %s' % (materiamalla.asignatura, form.cleaned_data['paralelomateria']))
                    if listadomodulos:
                        if (nivel.coordinacion() and (nivel.carrera.posgrado)):
                            mnm = NivelMalla.objects.get(pk=int(request.POST['modulonivelmalla']))
                            for modulo in ModuloMalla.objects.filter(id__in=[int(x) for x in listadomodulos.split(',')]):
                                if Materia.objects.filter(modulomalla=modulo, nivel=nivel, paralelomateria=form.cleaned_data['paralelomateria'], modulonivelmalla=mnm).exists():
                                    return bad_json(mensaje=u'Ya se encuentra registrada la materia: %s en el paralelo: %s' % (modulo.asignatura, form.cleaned_data['paralelomateria']))
                        else:
                            for modulo in ModuloMalla.objects.filter(id__in=[int(x) for x in listadomodulos.split(',')]):
                                if Materia.objects.filter(modulomalla=modulo, nivel=nivel, paralelomateria=form.cleaned_data['paralelomateria']).exists():
                                    return bad_json(mensaje=u'Ya se encuentra registrada la materia: %s en el paralelo: %s' % (modulo.asignatura, form.cleaned_data['paralelomateria']))
                    if listado:
                        for materiamalla in AsignaturaMalla.objects.filter(id__in=[int(x) for x in listado.split(',')]):
                            if (nivel.coordinacion() and listadointensivos and (nivel.coordinacion().id == 16 or nivel.coordinacion().id == 17)):
                                for materiamalla in AsignaturaMalla.objects.filter(id__in=[int(x) for x in listadointensivos.split(',')]):
                                    lms = None
                                    plantillalms = None
                                    if usalms:
                                        if lmsdesdemalla:
                                            lms = materiamalla.lms
                                            plantillalms = materiamalla.plantillaslms
                                        else:
                                            lms = form.cleaned_data['lms']
                                            plantillalms = form.cleaned_data['plantillalms']
                                    materia = Materia(asignatura=materiamalla.asignatura,
                                                      asignaturamalla=materiamalla,
                                                      tipomateria=materiamalla.tipomateria,
                                                      nivel=nivel,
                                                      horas=materiamalla.horas,
                                                      horassemanales=materiamalla.horassemanales,
                                                      creditos=materiamalla.creditos,
                                                      paralelomateria=form.cleaned_data['paralelomateria'],
                                                      inicio=nivel.inicio,
                                                      fin=nivel.fin,
                                                      cerrado=False,
                                                      rectora=False,
                                                      practicas=materiamalla.practicas,
                                                      sinasistencia=materiamalla.sinasistencia,
                                                      tutoria=False,
                                                      grado=False,
                                                      validacreditos=True,
                                                      validapromedio=True,
                                                      modeloevaluativo=form.cleaned_data['modelo'],
                                                      cupo=CAPACIDAD_MATERIA_INICIAL,
                                                      intensivo=True,
                                                      lms=lms,
                                                      plantillaslms=plantillalms)
                                    materia.save(request)
                                    materia.actualiza_identificacion()
                                    log(u'Adiciono materia en nivel: %s' % materia, request, "add")
                            else:
                                lms = None
                                plantillalms = None
                                if usalms:
                                    if lmsdesdemalla:
                                        lms = materiamalla.lms
                                        plantillalms = materiamalla.plantillaslms
                                    else:
                                        lms = form.cleaned_data['lms']
                                        plantillalms = form.cleaned_data['plantillalms']
                                materia = Materia(asignatura=materiamalla.asignatura,
                                                  asignaturamalla=materiamalla,
                                                  tipomateria=materiamalla.tipomateria,
                                                  nivel=nivel,
                                                  horas=materiamalla.horas,
                                                  horassemanales=materiamalla.horassemanales,
                                                  creditos=materiamalla.creditos,
                                                  paralelomateria=form.cleaned_data['paralelomateria'],
                                                  inicio=nivel.inicio,
                                                  fin=nivel.fin,
                                                  cerrado=False,
                                                  rectora=False,
                                                  practicas=materiamalla.practicas,
                                                  sinasistencia=materiamalla.sinasistencia,
                                                  tutoria=False,
                                                  grado=False,
                                                  validacreditos=True,
                                                  validapromedio=True,
                                                  modeloevaluativo=form.cleaned_data['modelo'],
                                                  cupo=CAPACIDAD_MATERIA_INICIAL,
                                                  intensivo=False,
                                                  lms=lms,
                                                  plantillaslms=plantillalms)
                                materia.save(request)
                                materia.actualiza_identificacion()
                                log(u'Adiciono materia en nivel: %s' % materia, request, "add")
                    if listadomodulos:
                        for modulo in ModuloMalla.objects.filter(id__in=[int(x) for x in listadomodulos.split(',')]):
                            lms = None
                            plantillalms = None
                            if usalms:
                                if lmsdesdemalla:
                                    lms = modulo.lms
                                    plantillalms = modulo.plantillaslms
                                else:
                                    lms = form.cleaned_data['lms']
                                    plantillalms = form.cleaned_data['plantillalms']
                            materia = Materia(asignatura=modulo.asignatura,
                                              modulomalla=modulo,
                                              tipomateria=modulo.tipomateria,
                                              nivel=nivel,
                                              horas=modulo.horas,
                                              creditos=modulo.creditos,
                                              horassemanales=0,
                                              paralelomateria=form.cleaned_data['paralelomateria'],
                                              inicio=nivel.inicio,
                                              fin=nivel.fin,
                                              cerrado=False,
                                              rectora=True,
                                              sinasistencia=modulo.sinasistencia,
                                              practicas=False,
                                              tutoria=False,
                                              grado=False,
                                              validacreditos=modulo.validacreditos,
                                              validapromedio=modulo.validapromedio,
                                              modeloevaluativo=form.cleaned_data['modelo'],
                                              cupo=CAPACIDAD_MATERIA_INICIAL,
                                              modulonivelmalla=mnm,
                                              lms=lms,
                                              plantillaslms=plantillalms)
                            materia.save(request)
                            materia.actualiza_identificacion()
                            log(u'Adiciono materia en nivel: %s' % materia, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editmateria':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = MateriaNivelForm(request.POST)
                if form.is_valid():
                    if not form.cleaned_data['practicas'] and materia.practicas and materia.profesormateria_set.filter(tipoprofesor__id=TIPO_DOCENTE_PRACTICA).exists():
                        return bad_json(mensaje=u"Existen docentes de practica en la materia.")
                    if not form.cleaned_data['practicas'] and materia.practicas and materia.practicapreprofesional_set.exists():
                        return bad_json(mensaje=u"Existen practicas realizadas en la materia.")
                    if Leccion.objects.filter(clase__materia=materia, fecha__lt=form.cleaned_data['inicio']).exists():
                        return bad_json(mensaje=u"Existen clases impartidas antes de esta fecha.")
                    if Leccion.objects.filter(clase__materia=materia, fecha__gt=form.cleaned_data['fin']).exists():
                        return bad_json(mensaje=u"Existen clases impartidas después de esta fecha.")
                    if form.cleaned_data['inicio'] < materia.nivel.inicio or form.cleaned_data['inicio'] > materia.nivel.fin or form.cleaned_data['inicio'] > form.cleaned_data['fin']:
                        return bad_json(mensaje=u"Fecha inicio incorrecta.")
                    materia.horassemanales = form.cleaned_data['horassemanales']
                    materia.inicio = form.cleaned_data['inicio']
                    materia.alias = form.cleaned_data['alias']
                    materia.fin = form.cleaned_data['fin']
                    materia.validapromedio = form.cleaned_data['validapromedio']
                    materia.validacreditos = form.cleaned_data['validacreditos']
                    materia.intensivo = form.cleaned_data['intensivo']
                    materia.rectora = form.cleaned_data['rectora']
                    materia.integracioncurricular = form.cleaned_data['integracioncurricular']
                    if not materia.rectora:
                        materia.materiascompartidas_set.all().delete()
                    if materia.integracioncurricular:
                        materia.tipointegracion = form.cleaned_data['tipointegracion']
                    else:
                        materia.tipointegracion = None

                    materia.practicas = form.cleaned_data['practicas']
                    materia.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deletemateria':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                tiene_contrato = ProfesorDistributivoHoras.objects.filter(periodo=materia.nivel.periodo,
                                                                          profesor__in=[x.profesor for x in materia.profesores_materia()]).exclude(
                    codigocontrato="").exclude(codigocontrato=None).exists()
                if tiene_contrato:
                    return bad_json(mensaje=u"La materia ya tiene un contrato asignado, favor comunicarse con T.H. y Financiero.")
                log(u'Elimino materia: %s' % materia, request, "del")
                if not materia.tiene_matriculas():
                    materia.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'deletegrupopracticas':
            try:
                grupo = GruposPracticas.objects.get(pk=request.POST['id'])
                grupo.delete()
                log(u'Elimino grupo practicas: %s' % grupo, request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'deleteclases':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                for clase in materia.clase_set.filter(activo=True):
                    clase.activo = False
                    clase.save()
                log(u'Elimino horarios de materia: %s' % materia, request, "del")
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'addprofesor':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                form = ProfesorMateriaForm(request.POST)
                if form.is_valid():
                    inicio = form.cleaned_data['desde']
                    fin = form.cleaned_data['hasta']
                    if materia.profesormateria_set.filter(profesor_id=form.cleaned_data['profesor']).exists():
                        return bad_json(mensaje=u"El docente ya esta registrado en la materia.")
                    principal = False
                    if form.cleaned_data['tipoprofesor'].id == TIPO_DOCENTE_TEORIA:
                        if not materia.profesormateria_set.filter(tipoprofesor__id=TIPO_DOCENTE_TEORIA, principal=True).exists():
                            principal = True
                    pm = ProfesorMateria(materia=materia,
                                         profesor_id=form.cleaned_data['profesor'],
                                         principal=principal,
                                         tipoprofesor=form.cleaned_data['tipoprofesor'],
                                         desde=inicio,
                                         hasta=fin,
                                         horassemanales=materia.horassemanales,
                                         motivo=form.cleaned_data['motivo'])
                    pm.save(request)
                    pm.profesor.actualizar_distributivo_horas(pm.materia.nivel.periodo)
                    if pm.materia.nivel.distributivoaprobado:
                        for per in Persona.objects.filter(usuario__groups__id=RESPONSABLES_DISTRIBUTIVO_GRUPO_ID):
                            pm.mail_notificacion_distributivo(persona, per)
                        log(u'Adiciono profesor de materia luego de estar aprobado el distributivo: %s' % pm, request, "add")
                    else:
                        log(u'Adiciono profesor de materia: %s' % pm, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addprofesorficticio':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                form = ProfesorMateriaFicticioForm(request.POST)
                if form.is_valid():
                    inicio = form.cleaned_data['desde']
                    fin = form.cleaned_data['hasta']
                    if materia.profesorficticiomateria_set.filter(profesor_ficticio=form.cleaned_data['profesor']).exists():
                        return bad_json(mensaje=u"El docente ya esta registrado en la materia.")
                    if not materia.profesorficticiomateria_set.filter(es_principal=True).exists():
                        principal = True
                    pm = ProfesorFicticioMateria(materia=materia,
                                         profesor_ficticio=form.cleaned_data['profesor'],
                                         es_principal=principal,
                                         fecha_inicio=inicio,
                                         fecha_fin=fin,
                                         horas_semanales=materia.horassemanales)
                    pm.save(request)
                    log(u'Adiciono profesor fictico de materia: %s' % pm, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addprofesorpractica':
            try:
                grupo = GruposPracticas.objects.get(pk=request.POST['mid'])
                form = ProfesorMateriaPracticaForm(request.POST)
                if form.is_valid():
                    inicio = form.cleaned_data['desde']
                    fin = form.cleaned_data['hasta']
                    if grupo.profesormateriapracticas_set.filter(profesor=form.cleaned_data['profesor']).exists():
                        return bad_json(mensaje=u"El docente ya esta registrado en la materia.")
                    principal = False
                    if not grupo.profesormateriapracticas_set.filter(principal=True).exists():
                        principal = True
                    pm = ProfesorMateriaPracticas(grupo=grupo,
                                                  profesor_id=form.cleaned_data['profesor'],
                                                  principal=principal,
                                                  desde=inicio,
                                                  hasta=fin,
                                                  horassemanales=grupo.materia.horassemanales,
                                                  motivo=form.cleaned_data['motivo'])
                    pm.save(request)
                    pm.profesor.actualizar_distributivo_horas(pm.grupo.materia.nivel.periodo)
                    if pm.grupo.materia.nivel.distributivoaprobado:
                        for per in Persona.objects.filter(usuario__groups__id=RESPONSABLES_DISTRIBUTIVO_GRUPO_ID):
                            pm.mail_notificacion_distributivo(persona, per)
                        log(u'Adiciono profesor al grupo de practicas de la materia luego de estar aprobado el distributivo: %s' % pm.profesor, request, "add")
                    else:
                        log(u'Adiciono profesor al grupo de practicas de la  materia: %s' % pm, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'addprofesorficticiopractica':
            try:
                grupo = GruposPracticas.objects.get(pk=request.POST['mid'])
                form = ProfesorMateriaFicticioForm(request.POST)
                if form.is_valid():
                    inicio = form.cleaned_data['desde']
                    fin = form.cleaned_data['hasta']
                    if grupo.profesorficticiomateriapracticas_set.filter(profesor_ficticio=form.cleaned_data['profesor']).exists():
                        return bad_json(mensaje=u"El docente ya esta registrado en la materia.")
                    principal = False
                    if not grupo.profesorficticiomateriapracticas_set.filter(es_principal=True).exists():
                        principal = True
                    pm = ProfesorFicticioMateriaPracticas(grupo=grupo,
                                                  profesor_ficticio=form.cleaned_data['profesor'],
                                                  es_principal=principal,
                                                  fecha_inicio=inicio,
                                                  fecha_fin=fin,
                                                  horas_semanales=grupo.materia.horassemanales)
                    pm.save(request)
                    log(u'Adiciono profesor fictico al grupo de practicas de la materia: %s' % pm, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editprofesor':
            try:
                profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
                form = ProfesorMateriaForm(request.POST)
                if form.is_valid():
                    if form.cleaned_data['desde'] < profesormateria.materia.inicio or form.cleaned_data['hasta'] > profesormateria.materia.fin:
                        return bad_json(mensaje=u"Fechas incorrectas.")
                    profesormateria.tipoprofesor = form.cleaned_data['tipoprofesor']
                    profesormateria.desde = form.cleaned_data['desde']
                    profesormateria.hasta = form.cleaned_data['hasta']
                    profesormateria.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editprofesorpractica':
            try:
                profesormateria = ProfesorMateriaPracticas.objects.get(pk=request.POST['id'])
                form = ProfesorMateriaPracticaForm(request.POST)
                if form.is_valid():
                    if form.cleaned_data['desde'] < profesormateria.grupo.materia.inicio or form.cleaned_data['hasta'] > profesormateria.grupo.materia.fin:
                        return bad_json(mensaje=u"Fechas incorrectas.")
                    profesormateria.desde = form.cleaned_data['desde']
                    profesormateria.hasta = form.cleaned_data['hasta']
                    profesormateria.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updateprincpal':
            try:
                profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
                profesormateria.materia.profesormateria_set.update(principal=False)
                profesormateria.principal = True
                profesormateria.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updateprincipalficticio':
            try:
                profesormateria = ProfesorFicticioMateria.objects.get(pk=request.POST['id'])
                profesormateria.materia.profesorficticiomateria_set.update(es_principal=False)
                profesormateria.es_principal = True
                profesormateria.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updateplanifica':
            try:
                profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
                profesormateria.materia.profesormateria_set.update(planifica=False)
                profesormateria.planifica = request.POST['valor'] == 'true'  # Asume que es un valor booleano en forma de string
                profesormateria.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updateprincpalpractica':
            try:
                profesormateria = ProfesorMateriaPracticas.objects.get(pk=request.POST['id'])
                profesormateria.grupo.profesormateriapracticas_set.update(principal=False)
                profesormateria.principal = True
                profesormateria.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updateprincpalpracticaficticio':
            try:
                profesormateria = ProfesorFicticioMateriaPracticas.objects.get(pk=request.POST['id'])
                profesormateria.grupo.profesorficticiomateriapracticas_set.update(es_principal=False)
                profesormateria.principal = True
                profesormateria.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delprofesor':
            try:
                pm = ProfesorMateria.objects.get(pk=request.POST['id'])
                log(u'Elimino profesor de materia: %s' % pm, request, "del")
                profesor = pm.profesor
                pm.delete()
                profesor.actualizar_distributivo_horas(pm.materia.nivel.periodo)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delprofesorficticio':
            try:
                pm = ProfesorFicticioMateria.objects.get(pk=request.POST['id'])
                log(u'Elimino profesor ficticio de la materia: %s' % pm, request, "del")
                profesor = pm.profesor_ficticio
                pm.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delprofesorpractica':
            try:
                pm = ProfesorMateriaPracticas.objects.get(pk=request.POST['id'])
                log(u'Elimino profesor de materia de practicas: %s' % pm.profesor, request, "del")
                profesor = pm.profesor
                pm.delete()
                profesor.actualizar_distributivo_horas(pm.grupo.materia.nivel.periodo)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delprofesorpracticaficticio':
            try:
                pm = ProfesorFicticioMateriaPracticas.objects.get(pk=request.POST['id'])
                log(u'Elimino profesor ficticio de materia de practicas: %s' % pm.profesor_ficticio, request, "del")
                profesor = pm.profesor_ficticio
                pm.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatefechainicio':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                fechainicio = convertir_fecha(request.POST['fecha'])
                if fechainicio < materia.nivel.inicio or fechainicio > materia.nivel.fin or fechainicio > materia.fin:
                    return bad_json(mensaje=u"Fecha inicio incorrecta.")
                if Leccion.objects.filter(clase__materia=materia, fecha__lt=fechainicio).exists():
                    return bad_json(mensaje=u"Existen clases impartidas antes de esta fecha.")
                for pm in materia.profesormateria_set.all():
                    pm.desde = fechainicio
                    pm.save(request)
                materia.inicio = fechainicio
                materia.save(request)
                return ok_json({'fecha': materia.inicio.strftime("%d-%m-%Y"), 'profesores': materia.profesores_materia().count()})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatefechafin':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                fechafin = convertir_fecha(request.POST['fecha'])
                if Leccion.objects.filter(clase__materia=materia, fecha__gt=fechafin).exists():
                    return bad_json(mensaje=u"Existen clases impartidas después de esta fecha.")
                for pm in materia.profesormateria_set.all():
                    pm.hasta = fechafin
                    pm.save(request)
                materia.fin = fechafin
                materia.fechafinasistencias = fechafin
                materia.save(request)
                for asig in materia.asignados_a_esta_materia():
                    asig.save(request)
                    asig.actualiza_estado()
                    asig.actualiza_notafinal()
                return ok_json({'fecha': materia.fin.strftime("%d-%m-%Y"), 'profesores': materia.profesores_materia().count()})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatecupomateria':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                valor = int(request.POST['valor'])
                if valor < materia.cantidad_matriculas_materia():
                    return bad_json(mensaje=u"No puede establecer un cupo menor a %s." % materia.cantidad_matriculas_materia())
                materia.cupo = valor
                materia.save(request)
                log(u'Modifico cupo: %s' % materia, request, "edit")
                return ok_json({'valor': materia.cupo})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatehorassemanales':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                valor = float(request.POST['valor'])
                horas_programadas = materia.horas_restantes_horario()
                pm = []
                if materia.nivel.modalidad_id in VERIFICAN_HORAS_HORARIO:
                    if valor < horas_programadas:
                        return bad_json(mensaje=u"No puede establecer un valor menor a %s." % horas_programadas)
                materia.horassemanales = valor
                materia.save(request)
                for profesormateria in materia.profesormateria_set.all():
                    profesormateria.horassemanales = valor
                    profesormateria.save()
                    profesormateria.profesor.actualizar_distributivo_horas(profesormateria.materia.nivel.periodo)
                    pm.append([profesormateria.id, valor])
                log(u'Modifico horas semanales: %s' % materia, request, "edit")
                return ok_json({'valor': valor, "lista": pm})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatehorassemanalesdocente':
            try:
                profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
                valor = float(request.POST['valor'])
                if profesormateria.materia.nivel.modalidad_id in VERIFICAN_HORAS_HORARIO:
                    if valor > profesormateria.materia.horassemanales:
                        return bad_json(mensaje=u"No puede establecer un valor mayor a %s." % profesormateria.materia.horassemanales)
                profesormateria.horassemanales = valor
                profesormateria.save(request)
                profesormateria.profesor.actualizar_distributivo_horas(profesormateria.materia.nivel.periodo)
                log(u'Modifico horas semanales del docente: %s' % profesormateria, request, "edit")
                return ok_json({'valor': valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatehorassemanalesdocenteficticio':
            try:
                profesormateria = ProfesorFicticioMateria.objects.get(pk=request.POST['id'])
                valor = float(request.POST['valor'])
                if profesormateria.materia.nivel.modalidad_id in VERIFICAN_HORAS_HORARIO:
                    if valor > profesormateria.materia.horassemanales:
                        return bad_json(mensaje=u"No puede establecer un valor mayor a %s." % profesormateria.materia.horassemanales)
                profesormateria.horassemanales = valor
                profesormateria.save(request)
                log(u'Modifico horas semanales del docente ficticio: %s' % profesormateria, request, "edit")
                return ok_json({'valor': valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatehorassemanalesdocentepractica':
            try:
                profesormateria = ProfesorMateriaPracticas.objects.get(pk=request.POST['id'])
                valor = float(request.POST['valor'])
                profesormateria.horassemanales = valor
                profesormateria.save(request)
                profesormateria.profesor.actualizar_distributivo_horas(profesormateria.grupo.materia.nivel.periodo)
                log(u'Modifico horas semanales del docente: %s' % profesormateria.profesor, request, "edit")
                return ok_json({'valor': valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatehorassemanalesdocentepracticaficticio':
            try:
                profesormateria = ProfesorFicticioMateriaPracticas.objects.get(pk=request.POST['id'])
                valor = float(request.POST['valor'])
                profesormateria.horas_semanales = valor
                profesormateria.save(request)
                log(u'Modifico horas semanales del docente ficticio en grupos: %s' % profesormateria.profesor_ficticio, request, "edit")
                return ok_json({'valor': valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatecupocompartido':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                valor = float(request.POST['valor'])
                if valor > materia.cupo:
                    return bad_json(mensaje=u"No puede establecer un cupo mayor a %s." % materia.cupo)
                registrados = materia.materiaasignada_set.filter(matricula__retiromatricula__isnull=True).exclude(matricula__inscripcion__carrera=materia.asignaturamalla.malla.carrera).count()
                if 0 < valor < registrados:
                    valor = registrados
                materia.cupocompartido = valor
                materia.save(request)
                log(u'Modifico cupo compartido: %s' % materia, request, "edit")
                return ok_json({'valor': materia.cupocompartido})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatecuponivel':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                valor = int(request.POST['valor'])
                if valor < nivel.cantidad_matriculados():
                    return bad_json(mensaje=u"No puede establecer un cupo menor a %s." % nivel.cantidad_matriculados())
                nivel.capacidadmatricula = valor
                nivel.save(request)
                log(u'Modifico cupo de nivel: %s' % nivel, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cambiaraula':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = CambiarAulaForm(request.POST)
                if form.is_valid():
                    clases = materia.clase_set.filter(activo=True)
                    for c in clases:
                        c.aula = form.cleaned_data['aula']
                        c.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cambiarmodelo':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = ListaModeloEvaluativoForm(request.POST)
                if form.is_valid():
                    if materia.cerrado:
                        return bad_json(mensaje=u"La materia se encuentra cerrada.")
                    if materia.materiaasignada_set.filter(notafinal__gt=0).exists():
                        return bad_json(mensaje=u"No se puede cambiar el modelo, existen calificaciones ingresadas.")
                    materia.modeloevaluativo = form.cleaned_data['modelo']
                    materia.save(request)
                    evaluaciones = EvaluacionGenerica.objects.filter(materiaasignada__materia=materia)
                    evaluaciones.delete()
                    for maa in materia.asignados_a_esta_materia():
                        maa.evaluacion()
                        maa.notafinal = 0
                        maa.save(request)
                    if materia.cronogramaevaluacionmodelo_set.exists():
                        cronograma = materia.cronogramaevaluacionmodelo_set.all()[0]
                        cronograma.materias.remove(materia)
                    log(u'Modifico modelo evaluativo: %s' % materia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'asignarlms':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = AsignarLmsForm(request.POST)
                if form.is_valid():
                    if materia.cerrado:
                        return bad_json(mensaje=u"La materia se encuentra cerrada.")
                    materia.lms = form.cleaned_data['lms']
                    materia.plantillaslms = form.cleaned_data['plantillalms']
                    materia.save(request)
                    materia.materiaasignada_set.update(exportadolms=False)
                    materia.profesormateria_set.update(exportadolms=False)
                    log(u'Modifico Lms y plantilla Lms: %s' % materia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'vaciarcalificaciones':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                if materia.cerrado:
                    return bad_json(mensaje=u"La materia se encuentra cerrada.")
                EvaluacionGenerica.objects.filter(materiaasignada__materia=materia).update(valor=0)
                for asignado in materia.asignados_a_esta_materia():
                    if not asignado.convalidada() and not asignado.homologada():
                        asignado.notafinal = 0
                        asignado.save(request)
                log(u'Elimino calificaciones de materia: %s' % materia, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'diasacalificar':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = CalificacionDiaForm(request.POST)
                if form.is_valid():
                    materia.usaperiodocalificaciones = form.cleaned_data['usaperiodocalificaciones']
                    materia.diasactivacioncalificaciones = form.cleaned_data['diasactivacioncalificaciones'] if not form.cleaned_data['usaperiodocalificaciones'] else 1
                    materia.save(request)
                    log(u'Cambio en fecha de calificaciones de materia: %s' % materia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'diasaevaluar':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = EvaluacionDiaForm(request.POST)
                if form.is_valid():
                    materia.usaperiodoevaluacion = form.cleaned_data['usaperiodoevaluacion']
                    if not form.cleaned_data['usaperiodoevaluacion']:
                        materia.diasactivacion = form.cleaned_data['diasactivacion']
                    materia.save(request)
                    log(u'Cambio en fecha de evaluaciones de materia: %s' % materia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'fechaasistencias':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = FechafinAsistenciasForm(request.POST)
                if form.is_valid():
                    materia.fechafinasistencias = form.cleaned_data['fecha']
                    materia.save(request)
                    materia.recalcularmateria()
                    log(u'Cambio fecha fin de asistencias de materia: %s' % materia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'bloqueohorarios':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                extension = nivel.extension()
                extension.modificarhorario = request.POST['val'] == 'true'
                extension.save(request)
                if extension.modificarhorario == True:
                    log(u'Activo check de MODIFICAR HORARIO: %s' % nivel, request, "edit")
                else:
                    log(u'Desactivo check de MODIFICAR HORARIO: %s' % nivel, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'bloqueoplanificacion':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                extension = nivel.extension()
                extension.modificarplanificacion = request.POST['val'] == 'true'
                extension.save(request)
                if extension.modificarplanificacion == True:
                    log(u'Activo check de MODIFICAR PLANIFICACION: %s' % nivel, request, "edit")
                else:
                    log(u'Desactivo check de MODIFICAR PLANIFICACION: %s' % nivel, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'bloqueocupos':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                extension = nivel.extension()
                extension.modificarcupo = request.POST['val'] == 'true'
                extension.save(request)
                if extension.modificarcupo == True:
                    log(u'Activo check de MODIFICAR CUPOS Y MATERIAS: %s' % nivel, request, "edit")
                else:
                    log(u'Desactivo check de MODIFICAR CUPOS Y MATERIAS: %s' % nivel, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'bloqueoprofesor':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                extension = nivel.extension()
                extension.modificardocente = request.POST['val'] == 'true'
                extension.save(request)
                if extension.modificardocente == True:
                    log(u'Activo check de MODIFICAR PROFESORES: %s' % nivel, request, "edit")
                else:
                    log(u'Desactivo check de MODIFICAR PROFESORES: %s' % nivel, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cierrema':
            try:
                ma = MateriaAsignada.objects.get(pk=request.POST['maid'])
                ma.cierre_materia_asignada()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cierremag':
            try:
                from ctt.adm_calculofinanzas import post_cierre_matricula
                matricula = Matricula.objects.get(pk=request.POST['maid'])
                matricula.cerrada = True
                matricula.save(request)
                post_cierre_matricula(matricula)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cerrarnivel':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                nivel.cerrado = True
                nivel.fechacierre = datetime.now()
                nivel.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cerrarm':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                if ActualizacionAsistencia.objects.filter(materia=materia).exists():
                    for ma in materia.materiaasignada_set.all():
                        ma.save(actualiza=True)
                        ma.actualiza_estado()
                    registro = ActualizacionAsistencia.objects.filter(materia=materia)[0]
                    registro.delete()
                materia.cerrado = True
                materia.fechacierre = datetime.now().date()
                if not materia.profesor_principal():
                    return bad_json(mensaje=u"La materia no tiene docente asignado, no puede cerrarse.")
                materia.save(request)
                for asig in materia.asignados_a_esta_materia():
                    asig.cerrado = True
                    asig.save(request)
                    asig.actualiza_estado()
                    asig.cierre_materia_asignada()
                for lg in LeccionGrupo.objects.filter(lecciones__clase__materia=materia, abierta=True):
                    lg.abierta = False
                    lg.horasalida = lg.turno.termina
                    lg.save(request)
                log(u'Cerro materia: %s' % materia, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'aprobardistributivo':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                nivel.responsableaprobacion = persona
                nivel.distributivoaprobado = True
                nivel.fechaprobacion = datetime.now().date()
                nivel.save(request)
                log(u'Aprobo distributivo: %s' % nivel.paralelo, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'aprobarfinanciero':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                nivel.responsableaprobacionfinanciero = persona
                nivel.aprobadofinanciero = True
                nivel.fechaprobacionfinanciero = datetime.now().date()
                nivel.save(request)
                for materia in nivel.materias():
                    materia.bloqueado = True
                    materia.save()
                ext = nivel.extension()
                ext.modificardocente = False
                ext.save(request)
                log(u'Aprobo distributivo financiero: %s' % nivel.paralelo, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desaprobarfinanciero':
            try:
                nivel = Nivel.objects.get(pk=request.POST['id'])
                nivel.responsableaprobacionfinanciero = persona
                nivel.aprobadofinanciero = False
                nivel.save(request)
                for materia in nivel.materias():
                    materia.bloqueado = False
                    materia.save()
                log(u'Desaprobo distributivo financiero: %s' % nivel.paralelo, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'abrirmatricula':
            try:
                matricula = Matricula.objects.get(pk=request.POST['id'])
                matricula.cerrada = False
                matricula.save(request)
                log(u'Abrir matricula desde materia: %s' % matricula, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'abrirtodasmatriculas':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                for m in request.POST['lista_items1'].split(','):
                    m = MateriaAsignada.objects.get(pk=m).matricula
                    m.cerrada = False
                    m.save(request)
                return ok_json({ 'materia': materia })
                log(u'Abrir todas matriculas desde materia: %s' % materia, request, "edit")
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cerrartodasmatriculas':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                for m in request.POST['lista_items1'].split(','):
                    m = MateriaAsignada.objects.get(pk=m).matricula
                    m.cerrada = True
                    m.save(request)
                log(u'Cerrar todas matriculas desde materia: %s' % materia, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cerrarmatricula':
            try:
                matricula = Matricula.objects.get(pk=request.POST['id'])
                matricula.cerrada = True
                if matricula.retirado():
                    matricula.estadomatricula = 3
                    matricula.save(request)
                else:
                    matricula.calcular_estado_matricula()
                log(u'Cerrar matricula desde materia: %s' % matricula, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'exportaralms':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = ExportarMateriaLmsForm(request.POST)
                if form.is_valid():
                    if materia.lms.logica_general:
                        local_scope = {}
                        exec(materia.lms.logica_general, globals(), local_scope)
                        logica_general_materia_periodo = local_scope['logica_general_materia_periodo']
                        logica_general_materia_periodo(materia, estudiantes=form.cleaned_data['exportarestudiante'], profesores=form.cleaned_data['exportarprofesor'])
                    materia.save(request)
                    log(u'Se exporto a lms la materia: %s' % materia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'abrirm':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                # if Matricula.objects.filter(cerrada=True, materiaasignada__materia=materia).exists():
                #     if not persona.usuario.is_superuser:
                #         return bad_json(mensaje=u'No se puede abrir la materia contiene matriculas ya cerradas.')
                materia.cerrado = False
                materia.save(request)
                for asig in materia.asignados_a_esta_materia():
                    asig.cerrado = False
                    asig.save(request)
                    asig.actualiza_estado()
                for r in RecordAcademico.objects.filter(materiaregular=materia):
                    r.delete()
                for h in HistoricoRecordAcademico.objects.filter(materiaregular=materia):
                    i = h.inscripcion
                    a = h.asignatura
                    h.delete()
                    if i.historicorecordacademico_set.filter(asignatura=a).exists():
                        o = i.historicorecordacademico_set.filter(asignatura=a)[0]
                        o.actualizar()
                log(u'Abrio materia: %s' % materia, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'abrirnivel':
            try:
                if periodo.cerrado:
                    return bad_json(mensaje='El periodo esta cerrado', error=0)
                n = Nivel.objects.get(pk=request.POST['id'])
                n.cerrado = False
                n.save(request)
                log(u'Abrio nivel: %s' % n, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'alumnospractica':
            try:
                profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
                log(u'Establecio alumnos de practica: %s' % profesormateria, request, "add")
                for materiaasignada in MateriaAsignada.objects.filter(id__in=[int(x) for x in request.POST['listamaterias'].split(',')]):
                    if AlumnosPracticaMateria.objects.filter(materia=profesormateria.materia, materiaasignada=materiaasignada).exists():
                        participantepractica = AlumnosPracticaMateria.objects.filter(materia=profesormateria.materia, materiaasignada=materiaasignada)[0]
                        if participantepractica.profesormateria != profesormateria:
                            participantepractica.delete()
                            participantepractica = AlumnosPracticaMateria(materia=profesormateria,
                                                                          materiaasignada=materiaasignada,
                                                                          profesor=profesormateria.profesor)
                            participantepractica.save(request)
                    else:
                        participantepractica = AlumnosPracticaMateria(materia=profesormateria,
                                                                      materiaasignada=materiaasignada,
                                                                      profesor=profesormateria.profesor)
                        participantepractica.save(request)
                    log(u'Adiciono a practicas: %s - %s' % (materiaasignada.matricula.inscripcion.persona, profesormateria.materia.nombre_completo()), request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'materiasmalla':
            try:
                malla = Malla.objects.get(pk=request.POST['mid'])
                data['materiasmalla'] = malla.asignaturamalla_set.all().order_by('nivelmalla', '-itinerario__id')
                data['materiasmodulo'] = malla.modulomalla_set.all().order_by('asignatura')
                data['coordinacion'] = coordinacion = request.session['coordinacionseleccionada']
                data['modulonivelesmalla'] = NivelMalla.objects.filter(pk__in=[1,2,3,4])
                segmento = render(request, "niveles/materiasmalla.html", data)
                return ok_json({"segmento": segmento.content.decode('utf-8')})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'addmateriaotrascarreras':
            try:
                materia = MateriasCompartidas.objects.get(pk=request.POST['id'])
                form = MateriaOtrasCarrerasForm(request.POST)
                if form.is_valid():
                    carreras = MateriaOtraCarreraModalidadSede(materiacompartida=materia,
                                                  asignatura=form.cleaned_data['asignatura'])
                    carreras.save()
                    log(u'Adiciono profesor de materia: %s' % carreras, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addmateriascompartidas':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = MateriasCompartidasForm(request.POST)
                if form.is_valid():
                    carreras = MateriasCompartidas(materia=materia,
                                                  carrera=form.cleaned_data['carrera'],
                                                  sede=form.cleaned_data['sede'],
                                                  modalidad=form.cleaned_data['modalidad'])
                    carreras.save()
                    log(u'Adiciono profesor de materia: %s' % carreras, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'asignaturascarrera':
            try:
                carrera = Carrera.objects.get(pk=request.POST['id'])
                lista = []
                for asignatura in Asignatura.objects.filter(Q(asignaturamalla__malla__carrera=carrera) | Q(modulomalla__malla__carrera=carrera)).distinct():
                    lista.append([asignatura.id, asignatura.nombre])
                return ok_json({'lista': lista})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=3)

        if action == 'delmateriaotrascarreras':
            try:
                materia = MateriaOtraCarreraModalidadSede.objects.get(pk=request.POST['id'])
                if materia.en_uso():
                    return bad_json(mensaje=u'Ya existen alumnos matriculados en esta materia de esta carrera.')
                log(u'Elimino materia de otra carrera: %s' % materia, request, "del")
                materia.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delmateriascompartidas':
            try:
                materia = MateriasCompartidas.objects.get(pk=request.POST['id'])
                if materia.en_uso():
                    return bad_json(mensaje=u'Ya existen alumnos matriculados en esta materia de esta carrera.')
                log(u'Elimino materia de otra carrera: %s' % materia, request, "del")
                materia.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'actualizacupocompartido':
            try:
                materiacompartida = MateriaOtraCarrera.objects.get(pk=request.POST['id'])
                materia = materiacompartida.materia
                cupocompartido = null_to_numeric(materia.materiaotracarrera_set.exclude(id=materiacompartida.id).aggregate(valor=Sum('cupo'))['valor'], 0)
                if cupocompartido + int(request.POST['valor']) > materia.cupo:
                    return bad_json(mensaje=u'El cupo compartido supera el valor de la capacidad de la materia.')
                materiacompartida.cupo = int(request.POST['valor'])
                materiacompartida.save()
                log(u'Actualizo cupo materia compartida: %s' % materia, request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'aprobarplanificacion':
            try:
                planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                planificacionmateria.aprobado = True
                planificacionmateria.aprueba = persona
                planificacionmateria.fechaaprobacion = datetime.now().date()
                planificacionmateria.save(request)
                log(u'Apruebo planificacion: %s' % planificacionmateria, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desaprobarplanificaciondistributivo':
            try:
                planificacionmateria = PlanificacionMateria.objects.get(pk=request.POST['id'])
                planificacionmateria.aprobado = False
                planificacionmateria.aprueba = persona
                planificacionmateria.fechaaprobacion = datetime.now().date()
                planificacionmateria.save(request)
                log(u'Desaprobo planificacion: %s' % planificacionmateria, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'sinasistenciaremota':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                materia.asistenciaremota = False
                materia.save(request)
                log(u'Materia sin asistencia remota: %s' % materia, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'conasistenciaremota':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                materia.asistenciaremota = True
                materia.save(request)
                log(u'Materia con asistencia remota: %s' % materia, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'movermateriasession':
            try:
                materia = Materia.objects.get(pk=request.POST['mid'])
                if not materia.tiene_capacidad():
                    return bad_json(mensaje=u"No existe cupo para esta materia")
                for x in request.POST['lista_items1'].split(','):
                    materiaasignada = MateriaAsignada.objects.get(pk=int(x))
                    if materia.capacidad_disponible() <= 0:
                        transaction.set_rollback(True)
                        return bad_json(mensaje=u'No existe capacidad para poder mover a los estudiantes.')
                    conservanotas = True
                    if materiaasignada.materia.modeloevaluativo != materia.modeloevaluativo:
                        conservanotas = False
                    asistencias = materiaasignada.asistencialeccion_set.all().delete()
                    if not conservanotas:
                        materiaasignada.evaluaciongenerica_set.all().delete()
                    materiaasignada.fechaasignacion = datetime.now().date()
                    materiaasignada.materia = materia
                    materiaasignada.save()
                    if not conservanotas:
                        materiaasignada.verifica_campos_modelo()
                    conflicto = conflicto_materias_seleccionadas(Materia.objects.filter(id__in=[x.materia.id for x in materiaasignada.matricula.materiaasignada_set.filter(verificahorario=True)]))
                    if conflicto:
                        transaction.set_rollback(True)
                        return bad_json(mensaje=conflicto)
                    materiaasignada.asistencias()
                    materiaasignada.save(actualiza=True)
                    materiaasignada.matricula.save()
                    log(u'Movio de materia: %s' % materiaasignada, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cambiargrupo':
            try:
                materia = MateriaAsignadaGrupoPracticas.objects.get(pk=request.POST['id'])
                form = CambiarGrupoPracticaForm(request.POST)
                if form.is_valid():
                    materia.grupo=form.cleaned_data['grupo']
                    materia.save()
                    log(u'Se cambia de grupo de paractica: %s' % materia.grupo, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addgrupopractica':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                form = GrupoMateriaForm(request.POST)
                if form.is_valid():
                    grupo = GruposPracticas(materia=materia,
                                            nombre=form.cleaned_data['nombre'])
                    grupo.save()
                    log(u'Adiciono grupo de materia: %s' % grupo.materia, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addestudiantegrupopractica':
            try:
                grupo = GruposPracticas.objects.get(pk=request.POST['grupo'])
                datos = json.loads(request.POST['lista'])
                if not datos:
                    return bad_json(mensaje=u'Debe seleccionar al menos un estudiante')
                for dato in datos:
                    materiaasignada = MateriaAsignada.objects.get(pk=int(dato['id']))
                    grupoestudiante = MateriaAsignadaGrupoPracticas(grupo=grupo,  materiaasignada=materiaasignada)
                    if not materiaasignada.materiaasignadagrupopracticas_set.exists():
                        grupoestudiante.save()
                    else:
                        transaction.set_rollback(True)
                        return bad_json(mensaje=u'El estudiante %s ya tiene el examen activo' % materiaasignada.matricula.inscripcion)
                log(u'Adiciono estudiante al grupo: %s' % grupoestudiante.grupo.nombre, request, "add")
                return ok_json(data={'id': grupo.id})

            except Exception as ex:
                return bad_json(error=1, ex=ex)

        if action == 'editgrupopractica':
            try:
                form = GrupoMateriaForm(request.POST)
                grupo = GruposPracticas.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    grupo.nombre = form.cleaned_data['nombre']
                    grupo.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delestudiantepractica':
            try:
                grupo = MateriaAsignadaGrupoPracticas.objects.get(pk=request.POST['id'])
                log(u"Elimino el estudiante del grupo: %s" % grupo.materiaasignada, request, "del")
                asistencias = grupo.asistencialeccionpractica_set.all().delete()
                grupo.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'actualizarhibridas':
            try:
                profesormateria = ProfesorMateria.objects.get(pk=request.POST['id'])
                log(u'Actualizo hibridas: %s' % profesormateria, request, "edit")
                for asignatura_malla_hibrida in profesormateria.materia.asignaturamalla.asignaturamallahibrida_set.all():
                    ProfesorMateriaAsignaturaMallaHibrida.objects.get_or_create(asignaturamallahibrida=asignatura_malla_hibrida,
                                                                                profesormateria=profesormateria)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'updatehorassemanaleshibridas':
            try:
                profesormateriahibrida = ProfesorMateriaAsignaturaMallaHibrida.objects.get(pk=request.POST['mid'])
                valorh = float(request.POST['valor'])
                profesormateriahibrida.horas = valorh
                profesormateriahibrida.save(request)
                valor = profesormateriahibrida.profesormateria.profesormateriaasignaturamallahibrida_set.aggregate(total_horas=Sum('horas'))['total_horas']
                profesormateria = profesormateriahibrida.profesormateria
                if profesormateria.materia.nivel.modalidad_id in VERIFICAN_HORAS_HORARIO:
                    if valor > profesormateria.materia.horassemanales:
                        return bad_json(
                            mensaje=u"No puede establecer un valor mayor a %s." % profesormateria.materia.horassemanales)
                profesormateria.horassemanales = valor
                profesormateria.save(request)
                profesormateria.profesor.actualizar_distributivo_horas(profesormateria.materia.nivel.periodo)
                log(u'Modifico horas semanales del docente: %s' % profesormateria, request, "edit")
                return ok_json({'valor': valor})
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


        if action == 'solicitudprofesormateria':
            try:
                materia = Materia.objects.get(pk=request.POST['id'])
                prof_dist = get_object_or_404(Materia, pk=materia.id)
                flujo = FlujoAprobacion.objects.get(pk=1)  # por ejemplo
                ct = ContentType.objects.get_for_model(Materia)
                form = AperturaSolicitudDistributivoForm(request.POST)
                solicitud_existente = SolicitudCambio.objects.filter(
                    content_type=ct,
                    object_id=prof_dist.id,
                    estado__in=[1, 2, 3]  # Pendiente, En Proceso, Desbloqueo
                ).exists()

                if solicitud_existente:
                    return bad_json(mensaje="Ya existe una solicitud activa para esta materia. Debe finalizar o rechazar la anterior antes de crear una nueva.")

                if form.is_valid():
                    solicitud = SolicitudCambio.objects.create(
                        flujo=flujo,
                        content_type=ct,
                        object_id=prof_dist.id,
                        etapa_actual=PasoFlujo.objects.filter(flujo=flujo, orden=1).first().area,
                        estado=1,
                        usuario_solicitante=request.user,
                        motivo_cambio=form.cleaned_data['motivo']
                    )
                log(u'Pidio apertura: %s' % solicitud, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'cerrarapertura':
            try:
                # Obtener la materia a partir del id pasado en la URL (GET)
                materia = Materia.objects.get(pk=request.POST['id'])
                ct = ContentType.objects.get_for_model(Materia)

                # Buscar la solicitud activa en estado DESBLOQUEO para esta materia
                solicitud = SolicitudCambio.objects.filter(
                    content_type=ct,
                    object_id=materia.id,
                    estado=3
                ).first()

                if solicitud:
                    # Si existe la solicitud, finalizar la edición (rebloquear, cambiar estado a APROBADO, etc.)
                    solicitud.finalizar_edicion(request.user, comentarios="Cierre automático de la solicitud.")
                    log(u'Cierre de solicitud: %s' % solicitud, request, "edit")
                    return ok_json()
                else:
                    # No se encontró una solicitud activa para cerrar
                    return bad_json(error=3, ex="No se encontró una solicitud activa para cerrar.")
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        return bad_json(error=0)
    else:
        data['title'] = u'Niveles académicos'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'solicitudprofesormateria':
                try:
                    data['title'] = u'Solicitar Profesor Materia'
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    data['form'] = AperturaSolicitudDistributivoForm()
                    return render(request, "niveles/solicitudprofesormateria.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Adicionar nivel académico'
                    periodo = request.session['periodo']
                    data['coordinacion'] = coordinacion = request.session['coordinacionseleccionada']
                    form = NivelForm(initial={'coordinacion': coordinacion,
                                              'inicio': periodo.inicio,
                                              'fin': periodo.fin,
                                              'fechacierre': periodo.fin,
                                              'fechatopematricula': periodo.fin,
                                              'fechatopematriculaext': periodo.fin,
                                              'fechatopematriculaesp': periodo.fin},
                                     )
                    form.adicionar(coordinacion, persona)
                    data['form'] = form
                    return render(request, "niveles/add.html", data)
                except Exception as ex:
                    pass

            if action == 'abrirn':
                try:
                    data['title'] = u'Abrir nivel'
                    data['nivel'] = Nivel.objects.get(pk=request.GET['nid'])
                    return render(request, "niveles/abrirn.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar nivel académico'
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    form = NivelFormEdit(initial={'paralelo': nivel.paralelo,
                                                  'inicio': nivel.inicio,
                                                  'fin': nivel.fin,
                                                  'fechacierre': nivel.fechacierre,
                                                  'mensaje': nivel.mensaje,
                                                  'fechatopematricula': nivel.fechatopematricula,
                                                  'capacidad': nivel.capacidadmatricula,
                                                  'fechatopematriculaext': nivel.fechatopematriculaex,
                                                  'fechatopematriculaesp': nivel.fechatopematriculaes})
                    form.editar(nivel)
                    data['form'] = form
                    return render(request, "niveles/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'del':
                try:
                    data['title'] = u'Borrar nivel académico'
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/del.html", data)
                except Exception as ex:
                    pass

            if action == 'vaciarcalificaciones':
                try:
                    data['title'] = u'Vaciar calificaciones'
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/vaciarcalificaciones.html", data)
                except Exception as ex:
                    pass

            if action == 'diasacalificar':
                try:
                    data['title'] = u'Días para calificar la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['form'] = CalificacionDiaForm(initial={'usaperiodocalificaciones': materia.usaperiodocalificaciones,
                                                                'diasactivacioncalificaciones': materia.diasactivacioncalificaciones})
                    return render(request, "niveles/diasacalificar.html", data)
                except Exception as ex:
                    pass

            if action == 'diasaevaluar':
                try:
                    data['title'] = u'Días para evaluar al docente de la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['form'] = EvaluacionDiaForm(initial={'usaperiodoevaluacion': materia.usaperiodoevaluacion,
                                                              'diasactivacion': materia.diasactivacion})
                    return render(request, "niveles/diasaevaluar.html", data)
                except Exception as ex:
                    pass

            if action == 'fechaasistencias':
                try:
                    data['title'] = u'Fechas a tomar en cuenta para asistencias'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['form'] = FechafinAsistenciasForm(initial={'fecha': materia.fechafinasistencias})
                    return render(request, "niveles/fechafinasistencias.html", data)
                except Exception as ex:
                    pass

            if action == 'exportaralms':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    form = ExportarMateriaLmsForm(initial={'materia': materia})
                    form.adicionar(materia)
                    data['form'] = form
                    return render(request, "niveles/exportaralms.html", data)
                except Exception as ex:
                    pass


            if action == 'abrirm':
                try:
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/abrirm.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrarm':
                try:
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/cerrarm.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrarapertura':
                try:
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/cerrarapertura.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobardistributivo':
                try:
                    data['nivel'] = Nivel.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/aprobardistributivo.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarfinanciero':
                try:
                    data['nivel'] = Nivel.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/aprobarfinanciero.html", data)
                except Exception as ex:
                    pass

            if action == 'desaprobarfinanciero':
                try:
                    data['nivel'] = Nivel.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/desaprobarfinanciero.html", data)
                except Exception as ex:
                    pass

            if action == 'abrirmatricula':
                try:
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    data['materia'] = Materia.objects.get(pk=request.GET['idm'])
                    return render(request, "niveles/abrirmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrarmatricula':
                try:
                    data['matricula'] = Matricula.objects.get(pk=request.GET['id'])
                    data['materia'] = Materia.objects.get(pk=request.GET['idm'])
                    return render(request, "niveles/cerrarmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'tomandom':
                try:
                    data['title'] = u'Tomando la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['materiasasignadas'] = materia.materiaasignada_set.all().order_by('matricula__inscripcion__persona')
                    data['nivel'] = materia.nivel
                    return render(request, "niveles/tomandom.html", data)
                except Exception as ex:
                    pass

            if action == 'movermateriasession':
                try:
                    data['title'] = u'Mover materia de session'
                    datos = request.GET['lista_items1']
                    data['datos'] = datos
                    data['materia_estaba'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['materias'] = Materia.objects.filter(asignatura=materia.asignatura, nivel__periodo=periodo, cerrado=False, nivel__cerrado=False).exclude(id=materia.id)
                    return render(request, "niveles/movermateriasession.html", data)
                except Exception as ex:
                    pass

            if action == 'materias':
                try:
                    data['title'] = u'Materias del nivel académico'
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    data['reporte_0'] = obtener_reporte('cronogramaperiodo_nivel_carrera')
                    data['reporte_1'] = obtener_reporte('cronogramaperiodo_nivel_carrera_paralelo_nivelmalla')
                    data['reporte_2'] = obtener_reporte('horario_nivel_carrera_paralelo_nivelmalla')
                    data['reporte_3'] = obtener_reporte('tomaron_materia')
                    data['reporte_4'] = obtener_reporte('resumen_final_notas_consolidado')
                    data['reporte_5'] = obtener_reporte('acta_notas')
                    data['reporte_6'] = obtener_reporte('acta_notas_parcial')
                    data['reporte_7'] = obtener_reporte('alumnos_matriculados_xnivel_paralelo')
                    data['reporte_8'] = obtener_reporte('clases_consolidado')
                    data['reporte_9'] = obtener_reporte('certificado_promocion_varios')
                    data['carreras'] = carreras = request.session['carreras']
                    data['paralelosmaterias'] = ParaleloMateria.objects.all()
                    data['nivelesmalla'] = NivelMalla.objects.all()
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
                    mallas = Malla.objects.filter(carrera__id=carreraid)
                    materias = nivel.materia_set.filter(Q(asignaturamalla__malla__in=mallas) | Q(modulomalla__malla__in=mallas)).distinct().order_by('asignaturamalla', 'modulomalla', 'paralelomateria', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
                    if nivelmallaid >= 0:
                        materias = materias.filter(asignaturamalla__nivelmalla__id=nivelmallaid)
                    if paralelomateriaid > 0:
                        materias = materias.filter(paralelomateria__id=paralelomateriaid)
                    data['carreraid'] = carreraid
                    data['nivelmallaid'] = nivelmallaid
                    data['paralelomateriaid'] = paralelomateriaid
                    data['materias'] = materias
                    data['extension'] = nivel.extension()
                    persona = request.session['persona']
                    data['puede_abrir_materias_admin'] = persona.cargoinstitucion_set.filter(cargo_id=3).exists()
                    return render(request, "niveles/materias.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarplanificaciondistributivo':
                try:
                    data['title'] = u' Aprobar planificación de la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = materia.mi_planificacion()
                    return render(request, "niveles/aprobarplanificaciondistributivo.html", data)
                except Exception as ex:
                    pass

            if action == 'sinasistenciaremota':
                try:
                    data['title'] = u' Aprobar materia sin asistencia remota'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/sinasistenciaremota.html", data)
                except Exception as ex:
                    pass

            if action == 'conasistenciaremota':
                try:
                    data['title'] = u'Aprobar materia con asistencia remota'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/conasistenciaremota.html", data)
                except Exception as ex:
                    pass

            if action == 'desaprobarplanificaciondistributivo':
                try:
                    data['title'] = u' Desaprobar planificación de la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = materia.mi_planificacion()
                    return render(request, "niveles/desaprobarplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'detalletaller':
                try:
                    data['taller'] = taller = TallerPlanificacionMateria.objects.get(pk=request.GET['id'])
                    data['title'] = u'Detalle Taller'
                    data['planificacionmateria'] = taller.planificacionmateria
                    data['actividadesaprendizajecondocenciaasistida'] = ActividadesAprendizajeCondocenciaAsistida.objects.all()
                    data['actividadesaprendizajecolaborativas'] = ActividadesAprendizajeColaborativas.objects.all()
                    return render(request, "niveles/detalletaller.html", data)
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
                                                                       'logromedio': rubrica.logromedio})
                    else:
                        data['planificacionmateria'] = planificacion = PlanificacionMateria.objects.get(pk=request.GET['p'])
                        materia = planificacion.materia
                        rubrica = planificacion.mi_rubrica()
                        form = RubricaTallerPlanificacionForm(initial={'criterio': rubrica.criterio,
                                                                       'logroexcelente': rubrica.logroexcelente,
                                                                       'logroavanzado': rubrica.logroavanzado,
                                                                       'logrobajo': rubrica.logrobajo,
                                                                       'logrodeficiente': rubrica.logrodeficiente,
                                                                       'logromedio': rubrica.logromedio})
                    if planificacion:
                        form.planificacion()
                    data['form'] = form
                    data['materia'] = materia
                    data['permite_modificar'] = False
                    return render(request, "niveles/rubrica.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarplanificacion':
                try:
                    data['title'] = u'Aprobar planificacion'
                    data['planificacionmateria'] = PlanificacionMateria.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/aprobarplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'otrascarreras':
                try:
                    data['title'] = u'Materias en otras carreras'
                    data['materia'] = materia = MateriasCompartidas.objects.get(pk=request.GET['id'])
                    data['materiasotras'] = materia.materiaotracarreramodalidadsede_set.all()
                    data['extension'] = materia.materia.nivel.extension()
                    return render(request, "niveles/otrascarreras.html", data)
                except Exception as ex:
                    pass

            if action == 'materiascompartidas':
                try:
                    data['title'] = u'Materias compartidas'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['materiascompartidas'] = materia.materiascompartidas_set.all()
                    data['extension'] = materia.nivel.extension()
                    return render(request, "niveles/materiascompartidas.html", data)
                except Exception as ex:
                    pass

            if action == 'addmateriaotrascarreras':
                try:
                    data['title'] = u'Materias en otras carreras'
                    data['materia'] = materia = MateriasCompartidas.objects.get(pk=request.GET['id'])
                    data['carreras'] = carreras = materia.materiaotracarreramodalidadsede_set.all()
                    form = MateriaOtrasCarrerasForm()
                    data['form'] = form
                    return render(request, "niveles/addmateriaotrascarreras.html", data)
                except Exception as ex:
                    pass

            if action == 'addmateriascompartidas':
                try:
                    data['title'] = u'Materias en otras carreras'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['carreras'] = carreras = materia.materiascompartidas_set.all()
                    form = MateriasCompartidasForm()
                    data['form'] = form
                    return render(request, "niveles/addmateriascompartidas.html", data)
                except Exception as ex:
                    pass

            if action == 'delmateriaotrascarreras':
                try:
                    data['title'] = u'Borrar materia de otras carreras'
                    data['materia'] = materia = MateriaOtraCarreraModalidadSede.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/delmateriaotrascarreras.html", data)
                except Exception as ex:
                    pass

            if action == 'delmateriascompartidas':
                try:
                    data['title'] = u'Borrar materia de otras carreras'
                    data['materia'] = materia = MateriasCompartidas.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/delmateriascompartidas.html", data)
                except Exception as ex:
                    pass

            if action == 'nivelesmatricula':
                try:
                    data['title'] = u'Niveles de Matrícula'
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    data['niveles_matricula'] = nivel.nivelestudiantesmatricula_set.all().order_by('nivelmalla')
                    return render(request, "niveles/nivelesmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'graficahorarios':
                try:
                    from collections import defaultdict
                    nivel_id = request.GET['id']
                    nivel = Nivel.objects.get(pk=nivel_id)
                    materias = Materia.objects.filter(nivel=nivel)

                    clases_por_materia = defaultdict(list)

                    def encontrar_fechas_clase(clase, inicio_nivel, fin_nivel):
                        fechas = []
                        inicio = max(clase.inicio, inicio_nivel)  # Asegura que la clase esté dentro del rango del nivel
                        fin = min(clase.fin, fin_nivel)

                        dia_actual = inicio
                        while dia_actual <= fin:
                            if dia_actual.weekday() == (clase.dia - 1): # Python cuenta los días desde 0 siendo el lunes
                                fechas.append(dia_actual.strftime("%Y-%m-%d"))
                            dia_actual += timedelta(days=1)
                        return fechas

                    for materia in materias:
                        clases = Clase.objects.filter(
                            activo=True,
                            materia=materia,
                            inicio__lte=nivel.fin,
                            fin__gte=nivel.inicio
                        )

                        for clase in clases:
                            fechas_clase = encontrar_fechas_clase(clase, nivel.inicio, nivel.fin)
                            if fechas_clase:
                                clases_por_materia[materia.id].extend(fechas_clase)
                    datos_clases = [
                        {
                            'nombre': Materia.objects.get(pk=materia_id).asignatura.nombre,
                            'fechas': fechas
                        } for materia_id, fechas in clases_por_materia.items()
                    ]

                    data['datos_clases_json'] = json.dumps(datos_clases)
                    return render(request, "niveles/graficahorarios.html", data)
                except Exception as ex:
                    pass

            if action == 'addnivelmatricula':
                try:
                    data['title'] = u'Adicionar nivel matrícula'
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    form = NivelMatriculaForm()
                    form.adicionar(nivel)
                    data['form'] = form
                    return render(request, "niveles/addnivelmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'delnivelmatricula':
                try:
                    data['title'] = u'Eliminar nivel de matriculacion'
                    data['nivelmatricula'] = NivelEstudiantesMatricula.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/delnivelmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiarmodelo':
                try:
                    data['title'] = u'Cambiar modelo evaluativo'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    form = ListaModeloEvaluativoForm()
                    form.excluir_modeloactual(materia.modeloevaluativo)
                    data['form'] = form
                    data['nivel'] = materia.nivel
                    return render(request, "niveles/cambiarmodelo.html", data)
                except Exception as ex:
                    pass

            if action == 'asignarlms':
                try:
                    data['title'] = u'Cambiar Lms'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    form = AsignarLmsForm(initial={'lms':materia.lms, 'plantillalms': materia.plantillaslms})
                    data['form'] = form
                    data['nivel'] = materia.nivel
                    return render(request, "niveles/asignarlms.html", data)
                except Exception as ex:
                    pass

            if action == 'dividir':
                try:
                    data['title'] = u'Dividir matriculados en una materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    form = MateriaDividirForm()
                    form.desde_materia(materia)
                    data['form'] = form
                    return render(request, "niveles/dividir.html", data)
                except Exception as ex:
                    pass

            if action == 'editmateria':
                try:
                    data['title'] = u'Editar materia de nivel académico'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    form = MateriaNivelForm(initial={'asignatura': materia.asignatura,
                                                     'horas': materia.horas,
                                                     'horassemanales': materia.horassemanales,
                                                     'modelo': materia.modeloevaluativo,
                                                     'creditos': materia.creditos,
                                                     'identificacion': materia.identificacion,
                                                     'alias': materia.alias,
                                                     'paralelomateria': materia.paralelomateria,
                                                     'practicas': materia.practicas,
                                                     'validacreditos': materia.validacreditos,
                                                     'validapromedio': materia.validapromedio,
                                                     'intensivo': materia.intensivo,
                                                     'rectora': materia.rectora,
                                                     'inicio': materia.inicio,
                                                     'fin': materia.fin,
                                                     'integracioncurricular':materia.integracioncurricular,
                                                     'tipointegracion':materia.tipointegracion})
                    form.editar(materia)
                    data['form'] = form
                    return render(request, "niveles/editmateria.html", data)
                except Exception as ex:
                    pass

            if action == 'addmateriamalla':
                try:
                    data['title'] = u'Adicionar materia a nivel académico de una malla'
                    data['nivel'] = nivel = Nivel.objects.get(pk=request.GET['id'])
                    form = MateriaNivelMallaForm()
                    carreraid = request.session['carreraid']
                    mallas = Malla.objects.filter(carrera__id=carreraid, modalidad=nivel.modalidad, aprobado=True)
                    form.mallas(mallas)
                    data['form'] = form
                    return render(request, "niveles/addmateriamalla.html", data)
                except Exception as ex:
                    pass

            if action == 'deletemateria':
                try:
                    data['title'] = u'Borrar materia de nivel académico'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['nivel'] = materia.nivel
                    return render(request, "niveles/deletemateria.html", data)
                except Exception as ex:
                    pass

            if action == 'deletegrupopracticas':
                try:
                    data['title'] = u'Borrar materia de nivel académico'
                    data['grupo'] = grupo = GruposPracticas.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/deletegrupopracticas.html", data)
                except Exception as ex:
                    pass

            if action == 'delprofesor':
                try:
                    data['title'] = u'Eliminar profesor de materia'
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
                    data['nivel'] = profesormateria.materia.nivel
                    return render(request, "niveles/delprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'delprofesorficticio':
                try:
                    data['title'] = u'Eliminar profesor de materia'
                    data['profesormateria'] = profesormateria = ProfesorFicticioMateria.objects.get(pk=request.GET['id'])
                    data['nivel'] = profesormateria.materia.nivel
                    return render(request, "niveles/delprofesorficticio.html", data)
                except Exception as ex:
                    pass

            if action == 'delprofesorpractica':
                try:
                    data['title'] = u'Eliminar profesor de materia'
                    data['profesormateria'] = profesormateria = ProfesorMateriaPracticas.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/delprofesorpractica.html", data)
                except Exception as ex:
                    pass

            if action == 'delprofesorpracticaficticio':
                try:
                    data['title'] = u'Eliminar profesor de materia'
                    data['profesormateria'] = profesormateria = ProfesorFicticioMateriaPracticas.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/delprofesorpracticaficticio.html", data)
                except Exception as ex:
                    pass

            if action == 'editprofesor':
                try:
                    data['title'] = u'Editar profesor'
                    data['profesor'] = profesor = ProfesorMateria.objects.get(pk=request.GET['id'])
                    form = ProfesorMateriaForm(initial={'profesor_id': profesor.profesor_id,
                                                        'tipoprofesor': profesor.tipoprofesor,
                                                        'desde': profesor.desde,
                                                        'hasta': profesor.hasta,
                                                        'horassemanales': profesor.horassemanales})
                    form.editar()
                    data['periodo'] = periodo
                    data['form'] = form
                    return render(request, "niveles/editprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'editprofesorpractica':
                try:
                    data['title'] = u'Editar profesor'
                    data['profesor'] = profesor = ProfesorMateriaPracticas.objects.get(pk=request.GET['id'])
                    form = ProfesorMateriaPracticaForm(initial={'profesor_id': profesor.profesor_id,
                                                                'desde': profesor.desde,
                                                                'hasta': profesor.hasta,
                                                                'horassemanales': profesor.horassemanales})
                    form.editar()
                    data['periodo'] = periodo
                    data['form'] = form
                    return render(request, "niveles/editprofesorpractica.html", data)
                except Exception as ex:
                    pass

            if action == 'alumnospractica':
                try:
                    data['title'] = u'Alumnos de practica'
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
                    data['materiasasignadas'] = profesormateria.materia.materiaasignada_set.all().order_by('matricula__inscripcion__persona')
                    data['nivel'] = profesormateria.materia.nivel
                    return render(request, "niveles/alumnospractica.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiaraula':
                try:
                    data['title'] = u'Cambiar aula de materia en el horario'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    form = CambiarAulaForm()
                    form.editar(materia)
                    data['form'] = form
                    data['nivel'] = materia.nivel
                    return render(request, "niveles/cambiaraula.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteclases':
                try:
                    data['title'] = u'Borrar clases de la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['nivel'] = materia.nivel
                    return render(request, "niveles/deleteclases.html", data)
                except Exception as ex:
                    pass

            if action == 'addprofesor':
                try:
                    data['title'] = u'Adicionar profesor a materia de nivel académico'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['mid'])
                    form = ProfesorMateriaForm(initial={'desde': materia.inicio,
                                                        'hasta': materia.fin})
                    if materia.nivel.distributivoaprobado:
                        data['form'] = form
                    else:
                        form.nuevo()
                        data['form'] = form
                    return render(request, "niveles/addprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'addprofesorficticio':
                try:
                    data['title'] = u'Adicionar profesor a materia de nivel académico'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['mid'])
                    form = ProfesorMateriaFicticioForm(initial={'desde': materia.inicio,
                                                        'hasta': materia.fin})
                    data['form'] = form
                    return render(request, "niveles/addprofesorficticio.html", data)
                except Exception as ex:
                    pass

            if action == 'addprofesorpractica':
                try:
                    data['title'] = u'Adicionar profesor a materia de nivel académico'
                    data['grupo'] = grupo = GruposPracticas.objects.get(pk=request.GET['mid'])
                    form = ProfesorMateriaPracticaForm(initial={'desde': grupo.materia.inicio,
                                                                'hasta': grupo.materia.fin})
                    if grupo.materia.nivel.distributivoaprobado:
                        data['form'] = form
                    else:
                        form.nuevo()
                        data['form'] = form
                    return render(request, "niveles/addprofesorpractica.html", data)
                except Exception as ex:
                    pass

            if action == 'addprofesorficticiopractica':
                try:
                    data['title'] = u'Adicionar profesor a materia de nivel académico'
                    data['grupo'] = grupo = GruposPracticas.objects.get(pk=request.GET['mid'])
                    form = ProfesorMateriaFicticioForm(initial={'desde': grupo.materia.inicio,
                                                                'hasta': grupo.materia.fin})

                    data['form'] = form
                    return render(request, "niveles/addprofesorficticiopractica.html", data)
                except Exception as ex:
                    pass

            if action == 'cerrarnivel':
                try:
                    data['title'] = u'Cerrar nivel'
                    data['nivel'] = Nivel.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/cerrarnivel.html", data)
                except Exception as ex:
                    pass

            if action == 'abrirnivel':
                try:
                    data['title'] = u'Abrir nivel'
                    data['nivel'] = Nivel.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/abrirnivel.html", data)
                except Exception as ex:
                    pass

            if action == 'grupospracticas':
                try:
                    data['title'] = u'Tomando la materia'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['grupospracticas'] = materia.grupospracticas_set.all()
                    data['extension'] = materia.nivel.extension()
                    data['nivel'] = materia.nivel
                    return render(request, "niveles/grupospracticas.html", data)
                except Exception as ex:
                    pass

            if action == 'tomandompracticas':
                try:
                    data['title'] = u'Tomando la Practica'
                    data['grupo'] = grupo = GruposPracticas.objects.get(pk=request.GET['id'])
                    data['materiasasignadas'] = grupo.materiaasignadagrupopracticas_set.all().order_by('materiaasignada__matricula__inscripcion__persona')
                    return render(request, "niveles/tomandompracticas.html", data)
                except Exception as ex:
                    pass

            if action == 'addgrupopractica':
                try:
                    data['title'] = u'Grupo'
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['id'])
                    data['form']  = GrupoMateriaForm()
                    return render(request, "niveles/addgrupopractica.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiargrupo':
                try:
                    data['title'] = u'Grupo'
                    data['materia'] = materia = MateriaAsignadaGrupoPracticas.objects.get(pk=request.GET['id'])
                    data['form']  = form = CambiarGrupoPracticaForm()
                    form.addgrupo(materia)
                    return render(request, "niveles/cambiargrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'editgrupopractica':
                try:
                    data['title'] = u'Grupo'
                    data['grupo'] = grupo = GruposPracticas.objects.get(pk=request.GET['id'])
                    data['form'] = GrupoMateriaForm(initial={'nombre': grupo.nombre})
                    return render(request, "niveles/editgrupopractica.html", data)
                except Exception as ex:
                    pass

            if action == 'addestudiantegrupopractica':
                try:
                    data['title'] = u'Añadir estudiantes grupo'
                    data['grupo'] = grupo = GruposPracticas.objects.get(pk=request.GET['id'])
                    data['alumnos'] = MateriaAsignada.objects.filter(materia=grupo.materia).exclude(materiaasignadagrupopracticas__isnull=False).order_by('matricula__inscripcion')
                    return render(request, "niveles/addestudiantegrupopractica.html", data)
                except Exception as ex:
                    pass

            if action == 'delestudiantepractica':
                try:
                    data['title'] = u'Elimninar del grupo'
                    data['materiasi']  = MateriaAsignadaGrupoPracticas.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/delestudiantepractica.html", data)
                except Exception as ex:
                    pass

            if action == 'horashibridas':
                try:
                    data['title'] = u'Hibrida'
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
                    data['hibridas'] = profesormateria.profesormateriaasignaturamallahibrida_set.all().order_by('asignaturamallahibrida__modalidad')
                    return render(request, "niveles/horashibridas.html", data)
                except Exception as ex:
                    pass

            if action == 'actualizarhibridas':
                try:
                    data['title'] = u'Actualizar distributivo'
                    data['profesormateria'] = ProfesorMateria.objects.get(pk=request.GET['id'])
                    return render(request, "niveles/actualizarhibridas.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['periodo'] = periodo = request.session['periodo']
                data['coordinacion'] = request.session['coordinacionseleccionada']
                data['reporte_0'] = obtener_reporte('matriculados_maestrias_con_materiasasignadas')
                return render(request, "niveles/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')

