# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import RequestContext

from decorators import secure_module, last_access
from settings import PERSONA_MODIFICA_MALLA_ID
from ctt.commonviews import adduserdata
from ctt.forms import MallaForm, AsignaturaMallaForm,  \
    AsignaturaMallaPredecesoraForm,EvidenciaMallaForm, InformacionSedeMallaForm, InfoMallasedeForm, \
    CompetenciaEspecificaMallaForm, CompetenciaGenericaMallaForm, AsignaturaMallaCompetenciaForm, ClonarMallaForm, \
    AsignaturaMallaHorasDocenciaForm
from ctt.funciones import log, generar_nombre, ok_json, bad_json, url_back
from ctt.models import Malla, NivelMalla, EjeFormativo, AsignaturaMalla, Asignatura, AsignaturaMallaPredecesora, Periodo, EvidenciaMalla, InformacionSedeMalla, CompetenciaEspecifica, CompetenciaGenerica, \
    SilaboAsignaturaMalla


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = Periodo.objects.all().order_by('-fin')[0]
    miscarreras = persona.lista_carreras_coordinacion(data['coordinacionseleccionada'])

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                form = MallaForm(request.POST)
                if form.is_valid():
                    if form.cleaned_data['inicio'] >= form.cleaned_data['fin']:
                        return bad_json(mensaje=u'Fechas incorrectas.')
                    if form.cleaned_data['nivelhoraspracticas'].id > form.cleaned_data['nivelesregulares']:
                        return bad_json(mensaje=u'No puede elegir un nivel de inicio de prácticas mayor a la cantidad de niveles de la malla.')
                    if form.cleaned_data['nivelhorasvinculacion'].id > form.cleaned_data['nivelesregulares']:
                        return bad_json(mensaje=u'No puede elegir un nivel de inicio de vinculación mayor a la cantidad de niveles de la malla.')
                    if form.cleaned_data['nivelproyecto'].id > form.cleaned_data['nivelesregulares']:
                        return bad_json(mensaje=u'No puede elegir un nivel de inicio de proyectos mayor a la cantidad de niveles de la malla.')
                    malla = Malla(carrera=request.session['carreraseleccionada'],
                                  resolucion=form.cleaned_data['resolucion'],
                                  codigo=form.cleaned_data['codigo'],
                                  tipo=form.cleaned_data['tipo'],
                                  modalidad=form.cleaned_data['modalidad'],
                                  tipoduraccionmalla=form.cleaned_data['tipoduraccionmalla'],
                                  inicio=form.cleaned_data['inicio'],
                                  fin=form.cleaned_data['fin'],
                                  vigencia=form.cleaned_data['vigencia'],
                                  nivelesregulares=form.cleaned_data['nivelesregulares'],
                                  nivelacion=form.cleaned_data['nivelacion'],
                                  organizacionaprendizaje=form.cleaned_data['organizacionaprendizaje'],
                                  maximomateriasonline=form.cleaned_data['maximomateriasonline'],
                                  cantidadarrastres=form.cleaned_data['arrastres'],
                                  libreopcion=form.cleaned_data['libreopcion'],
                                  optativas=form.cleaned_data['optativas'],
                                  horaspracticas=form.cleaned_data['horaspracticas'],
                                  nivelhoraspracticas=form.cleaned_data['nivelhoraspracticas'],
                                  horasvinculacion=form.cleaned_data['horasvinculacion'],
                                  nivelhorasvinculacion=form.cleaned_data['nivelhorasvinculacion'],
                                  niveltrabajotitulacion=form.cleaned_data['nivelproyecto'],
                                  modelosibalo=form.cleaned_data['modelosibalo'],
                                  perfildeegreso=form.cleaned_data['perfildeegreso'],
                                  observaciones=form.cleaned_data['observaciones'])
                    malla.save(request)
                    log(u'Adiciono malla: %s' % malla, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'editmalla':
            try:
                form = MallaForm(request.POST)
                malla = Malla.objects.get(pk=request.POST['id'])
                nivelesregulares = malla.nivelesregulares
                if form.is_valid():
                    if form.cleaned_data['nivelesregulares']:
                        nivelesregulares = form.cleaned_data['nivelesregulares']
                    if form.cleaned_data['inicio'] >= form.cleaned_data['fin']:
                        return bad_json(mensaje=u'Fechas incorrectas.')
                    if form.cleaned_data['nivelhoraspracticas'].id > nivelesregulares:
                        return bad_json(mensaje=u'No puede elegir un nivel de inicio de prácticas mayor a la cantidad de niveles de la malla.')
                    if form.cleaned_data['nivelhorasvinculacion'].id > nivelesregulares:
                        return bad_json(mensaje=u'No puede elegir un nivel de inicio de vinculación mayor a la cantidad de niveles de la malla.')
                    if form.cleaned_data['nivelproyecto'].id > nivelesregulares:
                        return bad_json(mensaje=u'No puede elegir un nivel de inicio de proyectos mayor a la cantidad de niveles de la malla.')
                    malla.resolucion = form.cleaned_data['resolucion']
                    malla.codigo = form.cleaned_data['codigo']
                    malla.tituloobtenido = form.cleaned_data['titulo']
                    malla.tipoduraccionmalla = form.cleaned_data['tipoduraccionmalla']
                    malla.inicio = form.cleaned_data['inicio']
                    malla.fin = form.cleaned_data['fin']
                    malla.vigencia = form.cleaned_data['vigencia']
                    malla.organizacionaprendizaje = form.cleaned_data['organizacionaprendizaje']
                    malla.nivelesregulares = nivelesregulares
                    if not malla.tiene_estudiantes_usando() and malla.puede_eliminarse() :
                        malla.nivelacion = form.cleaned_data['nivelacion']
                        malla.arrastres = form.cleaned_data['arrastres']
                        malla.libreopcion = form.cleaned_data['libreopcion']
                        malla.optativas = form.cleaned_data['optativas']
                    malla.maximomateriasonline = form.cleaned_data['maximomateriasonline']
                    malla.horaspracticas = form.cleaned_data['horaspracticas']
                    malla.nivelhoraspracticas = form.cleaned_data['nivelhoraspracticas']
                    malla.horasvinculacion = form.cleaned_data['horasvinculacion']
                    malla.nivelhorasvinculacion = form.cleaned_data['nivelhorasvinculacion']
                    malla.niveltrabajotitulacion = form.cleaned_data['nivelproyecto']
                    malla.modelosibalo = form.cleaned_data['modelosibalo']
                    malla.perfildeegreso = form.cleaned_data['perfildeegreso']
                    malla.observaciones = form.cleaned_data['observaciones']
                    malla.save(request)
                    log(u'Modifico malla: %s' % malla, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'clonarmalla':
            try:
                form = ClonarMallaForm(request.POST)
                malla = Malla.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if form.cleaned_data['inicio'] >= form.cleaned_data['fin']:
                        return bad_json(mensaje=u'Fechas incorrectas.')
                    mallanueva = Malla(carrera=malla.carrera,
                                       resolucion=form.cleaned_data['resolucion'],
                                       codigo=form.cleaned_data['codigo'],
                                       tipo=malla.tipo,
                                       modalidad=form.cleaned_data['modalidad'],
                                       tituloobtenido=malla.tituloobtenido,
                                       tipoduraccionmalla=malla.tipoduraccionmalla,
                                       inicio=form.cleaned_data['inicio'],
                                       fin=form.cleaned_data['fin'],
                                       vigencia=form.cleaned_data['vigencia'],
                                       nivelesregulares=malla.nivelesregulares,
                                       nivelacion=malla.nivelacion,
                                       organizacionaprendizaje=malla.organizacionaprendizaje,
                                       maximomateriasonline=malla.maximomateriasonline,
                                       cantidadarrastres=malla.cantidadarrastres,
                                       libreopcion=malla.libreopcion,
                                       optativas=malla.optativas,
                                       horaspracticas=malla.horaspracticas,
                                       nivelhoraspracticas=malla.nivelhoraspracticas,
                                       horasvinculacion=malla.horasvinculacion,
                                       nivelhorasvinculacion=malla.nivelhorasvinculacion,
                                       niveltrabajotitulacion=malla.niveltrabajotitulacion,
                                       modelosibalo=malla.modelosibalo,
                                       perfildeegreso=malla.perfildeegreso,
                                       observaciones=form.cleaned_data['observaciones'])
                    mallanueva.save(request)
                    for am in malla.asignaturamalla_set.all():
                        asignaturamalla = AsignaturaMalla(malla=mallanueva,
                                                          asignatura=am.asignatura,
                                                          tipomateria=am.tipomateria,
                                                          campoformacion=am.campoformacion,
                                                          areaconocimiento=am.areaconocimiento,
                                                          nivelmalla=am.nivelmalla,
                                                          ejeformativo=am.ejeformativo,
                                                          horassemanales=am.horassemanales,
                                                          horas=am.horas,
                                                          horasdocencia=am.horasdocencia,
                                                          horascolaborativas=am.horascolaborativas,
                                                          horasasistidas=am.horasasistidas,
                                                          horasorganizacionaprendizaje=am.horasorganizacionaprendizaje,
                                                          horasautonomas=am.horasautonomas,
                                                          horaspracticas=am.horaspracticas,
                                                          creditos=am.creditos,
                                                          cantidadmatriculas=am.cantidadmatriculas,
                                                          sinasistencia=am.sinasistencia,
                                                          titulacion=am.titulacion,
                                                          validacreditos=am.validacreditos,
                                                          validapromedio=am.validapromedio,
                                                          obligatoria=am.obligatoria,
                                                          practicas=am.practicas,
                                                          codigopracticas=am.codigopracticas,
                                                          identificacion=am.identificacion,
                                                          matriculacion=am.matriculacion)
                        asignaturamalla.save(request)
                        mallanueva = asignaturamalla.malla
                        mallanueva.save(request)
                    for info in malla.informacionsedemalla_set.all():
                        informacionsedemalla = InformacionSedeMalla(sede=info.sede,
                                                                    malla=mallanueva,
                                                                    codigo=info.codigo)
                        informacionsedemalla.save(request)
                    log(u'Clono malla: %s' % malla, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)



        if action == 'addasign':
            try:
                form = AsignaturaMallaForm(request.POST)
                if form.is_valid():
                    malla = Malla.objects.get(pk=int(request.POST['malla']))
                    if 'nivel' in request.POST:
                        nivel = NivelMalla.objects.get(pk=request.POST['nivel'])
                        eje = EjeFormativo.objects.get(pk=request.POST['eje'])
                    else:
                        nivel = form.cleaned_data['nivelmalla']
                        eje = form.cleaned_data['ejeformativo']
                    if AsignaturaMalla.objects.filter(asignatura=form.cleaned_data['asignatura'], malla_id=request.POST['malla']).exists():
                        return bad_json(mensaje=u'Ya existe registrada la asignatura en ese itinerario, o en las comunes.')

                    horastotales = form.cleaned_data['horas']

                    asignaturamalla = AsignaturaMalla(malla=malla,
                                                      asignatura=form.cleaned_data['asignatura'],
                                                      tipomateria=form.cleaned_data['tipomateria'],
                                                      areaconocimiento=form.cleaned_data['areaconocimiento'],
                                                      nivelmalla=nivel,
                                                      ejeformativo=eje,
                                                      horassemanales=form.cleaned_data['horassemanales'],
                                                      horas=horastotales,
                                                      creditos=form.cleaned_data['creditos'],
                                                      cantidadmatriculas=form.cleaned_data['cantidadmatriculas'],
                                                      sinasistencia=form.cleaned_data['sinasistencia'],
                                                      validacreditos=form.cleaned_data['validacreditos'],
                                                      validapromedio=form.cleaned_data['validapromedio'],
                                                      obligatoria=form.cleaned_data['obligatoria'],
                                                      practicas=form.cleaned_data['practicas'],
                                                      codigopracticas=form.cleaned_data['codigopracticas'],
                                                      identificacion=form.cleaned_data['identificacion'],
                                                      matriculacion=form.cleaned_data['matriculacion'],
                                                      totalhorasaprendizajecontactodocente=form.cleaned_data['totalhorasaprendizajecontactodocente'],
                                                      totalhorasaprendizajepracticoexperimental=form.cleaned_data['totalhorasaprendizajepracticoexperimental'],
                                                      totalhorasaprendizajeautonomo=form.cleaned_data['totalhorasaprendizajeautonomo'])
                    asignaturamalla.save(request)
                    malla = asignaturamalla.malla
                    malla.save(request)
                    log(u'Adiciono asignatura malla: %s' % asignaturamalla, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)



        if action == 'aprueba':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                malla.aprobado = True
                malla.persona_aprueba = persona
                malla.fecha_aprueba = datetime.now()
                malla.save()
                log(u'Se APRUEBA la malla con el id: %s ' % malla.id, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                pass

        if action == 'desaprobar':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                malla.aprobado = False
                malla.persona_aprueba = persona
                malla.fecha_aprueba = datetime.now()
                malla.save()
                log(u'Se DESAPRUEBA la malla con el id: %s ' % malla.id, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                pass

        if action == 'apruebafinanciero':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                malla.activo = True
                malla.save()
                log(u'Se HABILITA el ingreso de valores a financiero de la malla con el id: %s ' % malla.id, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                pass

        if action == 'desaprobarfinanciero':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                malla.activo = False
                malla.save()
                log(u'Se DESHABILITA el ingreso de valores a financiero de la malla con el id: %s ' % malla.id, request, "add")
                return ok_json()

            except Exception as ex:
                transaction.set_rollback(True)
                pass

        if action == 'addpredecesora':
            try:
                asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['id'])
                form = AsignaturaMallaPredecesoraForm(request.POST)
                if form.is_valid():
                    if AsignaturaMallaPredecesora.objects.filter(asignaturamalla=asignaturamalla, predecesora=form.cleaned_data['predecesora']).exists():
                        return bad_json(mensaje=u'Ya se encuentra registrada.')
                    predecesora = AsignaturaMallaPredecesora(asignaturamalla=asignaturamalla,
                                                             predecesora=form.cleaned_data['predecesora'])
                    predecesora.save(request)
                    log(u'Adiciono predecesora asignatura malla: %s' % asignaturamalla, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)



        if action == 'editasign':
            try:
                form = AsignaturaMallaForm(request.POST)
                asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if form.cleaned_data['nivelmalla'].id != asignaturamalla.nivelmalla.id:
                        for requisito in AsignaturaMallaPredecesora.objects.filter(predecesora=asignaturamalla):
                            if requisito.asignaturamalla.nivelmalla.id <= form.cleaned_data['nivelmalla'].id:
                                return bad_json(mensaje=u'No puede elegir un nivel igual o superior a la predecesora %s.' % requisito.asignaturamalla)
                        for requisito in AsignaturaMallaPredecesora.objects.filter(asignaturamalla=asignaturamalla):
                            if requisito.predecesora.nivelmalla.id >= form.cleaned_data['nivelmalla'].id:
                                return bad_json(mensaje=u'No puede elegir un nivel igual o menor a la antecesora %s.' % requisito.predecesora)
                    asignaturamalla.nivelmalla = form.cleaned_data['nivelmalla']
                    asignaturamalla.ejeformativo = form.cleaned_data['ejeformativo']
                    asignaturamalla.areaconocimiento = form.cleaned_data['areaconocimiento']
                    asignaturamalla.tipomateria = form.cleaned_data['tipomateria']
                    asignaturamalla.campoformacion = form.cleaned_data['campoformacion']
                    asignaturamalla.identificacion = form.cleaned_data['identificacion']
                    asignaturamalla.practicas = form.cleaned_data['practicas']
                    asignaturamalla.codigopracticas = form.cleaned_data['codigopracticas']
                    asignaturamalla.obligatoria = form.cleaned_data['obligatoria']
                    asignaturamalla.matriculacion = form.cleaned_data['matriculacion']
                    asignaturamalla.horassemanales = form.cleaned_data['horassemanales']
                    asignaturamalla.horas = form.cleaned_data['horas']
                    asignaturamalla.horasdocencia = form.cleaned_data['horasdocencia']
                    asignaturamalla.horascolaborativas = form.cleaned_data['horascolaborativas']
                    asignaturamalla.horasasistidas = form.cleaned_data['horasasistidas']
                    asignaturamalla.horasorganizacionaprendizaje = form.cleaned_data['horasorganizacionaprendizaje']
                    asignaturamalla.horasautonomas = form.cleaned_data['horasautonomas']
                    asignaturamalla.horaspracticas = form.cleaned_data['horaspracticas']
                    asignaturamalla.creditos = form.cleaned_data['creditos']
                    asignaturamalla.cantidadmatriculas = form.cleaned_data['cantidadmatriculas']
                    asignaturamalla.sinasistencia = form.cleaned_data['sinasistencia']
                    asignaturamalla.titulacion = form.cleaned_data['titulacion']
                    asignaturamalla.validacreditos = form.cleaned_data['validacreditos']
                    asignaturamalla.validapromedio = form.cleaned_data['validapromedio']
                    asignaturamalla.competencia = form.cleaned_data['competencia']
                    asignaturamalla.totalhorasaprendizajeautonomo = form.cleaned_data['totalhorasaprendizajeautonomo']
                    asignaturamalla.totalhorasaprendizajecontactodocente = form.cleaned_data['totalhorasaprendizajecontactodocente']
                    asignaturamalla.totalhorasaprendizajepracticoexperimental = form.cleaned_data['totalhorasaprendizajepracticoexperimental']
                    asignaturamalla.practicasasistenciales = form.cleaned_data['practicasasistenciales']
                    asignaturamalla.lms = form.cleaned_data['lms']
                    asignaturamalla.plantillaslms = form.cleaned_data['plantillalms']
                    asignaturamalla.save(request)
                    malla = asignaturamalla.malla
                    malla.save(request)
                    log(u'Modifico asignatura en malla: %s' % asignaturamalla, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editasigncompetencia':
            try:
                form = AsignaturaMallaCompetenciaForm(request.POST)
                asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    asignaturamalla.identificacion = form.cleaned_data['identificacion']
                    if asignaturamalla.practicas:
                        asignaturamalla.codigopracticas = form.cleaned_data['codigopracticas']
                    asignaturamalla.competencia = form.cleaned_data['competencia']
                    asignaturamalla.save(request)
                    log(u'Modifico competencia de asignatura malla: %s' % asignaturamalla, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edithorasdocencia':
            try:
                form = AsignaturaMallaHorasDocenciaForm(request.POST)
                asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    asignaturamalla.totalhorasaprendizajepracticoexperimental = form.cleaned_data['totalhorasaprendizajepracticoexperimental']
                    asignaturamalla.totalhorasaprendizajeautonomo = form.cleaned_data['totalhorasaprendizajeautonomo']
                    asignaturamalla.totalhorasaprendizajecontactodocente = form.cleaned_data['totalhorasaprendizajecontactodocente']
                    asignaturamalla.save(request)
                    log(u'Modifico horas docencia: %s' % asignaturamalla, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delmodulo':
            try:
                modulo = ModuloMalla.objects.get(pk=request.POST['id'])
                if not modulo.malla.permite_modificar():
                    return bad_json(mensaje=u'La malla esta aprobada y en vigencia no puede eliminar ninguna información.')
                for predecesora in modulo.modulomallapredecesora_set.all():
                    predecesora.delete()
                log(u'Elimino asignatura modulo: %s' % modulo, request, "del")
                modulo.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delasign':
            try:
                asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['id'])
                if not asignaturamalla.puede_modificarse():
                    return bad_json(mensaje=u'Asignatura en uso no puede eliminarse.')
                for predecesora in asignaturamalla.asignaturamallapredecesora_set.all():
                    predecesora.delete()
                log(u'Elimino asignatura de malla: %s' % asignaturamalla, request, "del")
                asignaturamalla.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delsyllabus':
            try:
                silabo = SilaboAsignaturaMalla.objects.filter(asignaturamalla__malla__carrera__in=miscarreras).get(pk=request.POST['id'])
                asignaturamalla = silabo.asignaturamalla
                log(u'Elimino plantilla de silabo: %s' % asignaturamalla, request, "del")
                silabo.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)


        if action == 'delete':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                log(u'Elimino malla: %s' % malla, request, "del")
                malla.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'info':
            try:
                asignatura = Asignatura.objects.get(pk=request.POST['aid'])
                return ok_json({'codigo': asignatura.codigo})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'editinfomalla':
            try:
                infomalla = InformacionSedeMalla.objects.get(pk=request.POST['id'])
                form = InformacionSedeMallaForm(request.POST)
                if form.is_valid():
                    infomalla.codigo = form.cleaned_data['codigo']
                    infomalla.save()
                return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'delpredecesora':
            try:
                predecesora = AsignaturaMallaPredecesora.objects.get(pk=request.POST['id'])
                asignaturamalla = predecesora.asignaturamalla
                log(u'Elimino predecesora de malla: %s' % asignaturamalla, request, "del")
                predecesora.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)


        if action == 'delpredecesoramodulo':
            try:
                predecesora = ModuloMallaPredecesora.objects.get(pk=request.POST['id'])
                modulomalla = predecesora.modulomalla
                log(u'Elimino predecesora de modulo: %s' % modulomalla, request, "del")
                predecesora.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'aprobarsyllabus':
            try:
                silabo = SilaboAsignaturaMalla.objects.get(pk=request.POST['id'])
                silabo.habilitado = True
                silabo.save(request)
                log(u'Habilito plantilla silabo asignatura malla: %s' % silabo.asignaturamalla, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desaprobarsyllabus':
            try:
                silabo = SilaboAsignaturaMalla.objects.get(pk=request.POST['id'])
                silabo.habilitado = False
                silabo.save(request)
                log(u'Deshabilito plantilla silabo asignatura malla: %s' % silabo.asignaturamalla, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'aprobarsyllabusmodulo':
            try:
                silabo = SilaboModuloMalla.objects.get(pk=request.POST['id'])
                silabo.habilitado = True
                silabo.save(request)
                log(u'Habilito plantilla silabo modulo malla: %s' % silabo.modulomalla, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desaprobarsyllabusmodulo':
            try:
                silabo = SilaboModuloMalla.objects.get(pk=request.POST['id'])
                silabo.habilitado = False
                silabo.save(request)
                log(u'Deshabilito plantilla silabo modulo malla: %s' % silabo.modulomalla, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addevidencia':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                form = EvidenciaMallaForm(request.POST, request.FILES)
                if form.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("evidencia_malla", newfile._name)
                    evidencia = EvidenciaMalla(malla=malla,
                                               nombre=form.cleaned_data['nombre'],
                                               fecha=form.cleaned_data['fecha'],
                                               descripcion=form.cleaned_data['descripcion'],
                                               archivo=newfile)
                    evidencia.save(request)
                    log(u'Adiciono evidencia malla: %s' % evidencia, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delevidencia':
            try:
                evidencia = EvidenciaMalla.objects.get(pk=request.POST['id'])
                log(u'Elimino evidencia malla: %s' % evidencia, request, "del")
                evidencia.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editevidencia':
            try:
                evidencia = EvidenciaMalla.objects.get(pk=request.POST['id'])
                form = EvidenciaMallaForm(request.POST, request.FILES)
                if form.is_valid():
                    newfile = evidencia.archivo
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("evidencia_mala", newfile._name)
                        evidencia.archivo = newfile
                    evidencia.fecha = form.cleaned_data['fecha']
                    evidencia.nombre = form.cleaned_data['nombre']
                    evidencia.descripcion = form.cleaned_data['descripcion']
                    evidencia.save(request)
                    log(u'Modifico evidencia convocatoria vinculacion: %s' % evidencia, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editinfosede':
            try:
                informacionsedemalla = InformacionSedeMalla.objects.get(pk=request.POST['id'])
                form = InfoMallasedeForm(request.POST)
                if form.is_valid():
                    informacionsedemalla.codigo = form.cleaned_data['codigo']
                    informacionsedemalla.lugar = form.cleaned_data['lugar'].upper()
                    informacionsedemalla.save(request)
                    log(u'modifico codigo ejecucion sede: %s' % informacionsedemalla, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addinfosede':
            try:
                malla = Malla.objects.get(pk=request.POST['id'])
                form = InfoMallasedeForm(request.POST)
                if form.is_valid():
                    if InformacionSedeMalla.objects.filter(sede=form.cleaned_data['sede'], malla=malla).exists():
                        return bad_json(mensaje=u"Ya se encuentra registrada la sede.")
                    informacionsedemalla = InformacionSedeMalla(sede=form.cleaned_data['sede'],
                                                                malla=malla,
                                                                codigo=form.cleaned_data['codigo'],
                                                                lugar=form.cleaned_data['lugar'].upper())
                    informacionsedemalla.save(request)
                    log(u'Adiciono codigo ejecucion sede: %s' % informacionsedemalla, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delinfosede':
            try:
                infosede = InformacionSedeMalla.objects.get(pk=request.POST['id'])
                log(u'Elimino informacion de ejecucion: %s' % infosede, request, "del")
                infosede.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delcompee':
            try:
                competenciaespecifica = CompetenciaEspecifica.objects.get(pk=request.POST['id'])
                malla = Malla.objects.get(pk=request.POST['idm'])
                log(u'Elimino competencia especifica: %s' % competenciaespecifica, request, "del")
                malla.competenciasespecificas.remove(competenciaespecifica)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delcompeg':
            try:
                competenciagenerica = CompetenciaGenerica.objects.get(pk=request.POST['id'])
                malla = Malla.objects.get(pk=request.POST['idm'])
                log(u'Elimino competencia generica: %s' % competenciagenerica, request, "del")
                malla.competenciasgenericas.remove(competenciagenerica)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'addcompee':
            try:
                form = CompetenciaEspecificaMallaForm(request.POST)
                if form.is_valid():
                    malla = Malla.objects.get(pk=request.POST['id'])
                    malla.competenciasespecificas.add(form.cleaned_data['competencia'])
                    log(u'Adiciono competencia especifica a malla: %s' % form.cleaned_data['competencia'], request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addcompeg':
            try:
                form = CompetenciaGenericaMallaForm(request.POST)
                if form.is_valid():
                    malla = Malla.objects.get(pk=request.POST['id'])
                    malla.competenciasgenericas.add(form.cleaned_data['competencia'])
                    log(u'Adiciono competencia generica a malla: %s' % form.cleaned_data['competencia'], request, "add")
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

            if action == 'add':
                try:
                    data['title'] = u'Adicionar malla curricular'
                    form = MallaForm()
                    data['form'] = form
                    return render(request, "adm_mallas/add.html", data)
                except Exception as ex:
                    pass

            if action == 'clonarmalla':
                try:
                    data['title'] = u'Adicionar malla curricular'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    form = ClonarMallaForm()
                    data['form'] = form
                    return render(request, "adm_mallas/clonarmalla.html", data)
                except Exception as ex:
                    pass

            if action == 'delasign':
                try:
                    data['title'] = u'Eliminar asignatura'
                    data['asignatura'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=request.GET['id'])
                    return render(request, "adm_mallas/delasign.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar malla curricular'
                    data['malla'] = Malla.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/delete.html", data)
                except Exception as ex:
                    pass

            if action == 'delmodulo':
                try:
                    data['title'] = u'Eliminar módulo'
                    data['modulo'] = ModuloMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=request.GET['id'])
                    return render(request, "adm_mallas/delmodulo.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar malla curricular'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['ejesformativos'] = EjeFormativo.objects.filter(asignaturamalla__malla=malla).distinct()
                    data['permite_modificar'] = malla.permite_modificar()
                    return render(request, "adm_mallas/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'editinfomalla':
                try:
                    data['title'] = u'Editar código de sede'
                    data['infomalla'] = info = InformacionSedeMalla.objects.get(pk=request.GET['id'])
                    data['form'] = InformacionSedeMallaForm(initial={'codigo':info.codigo})
                    return render(request, "adm_mallas/editinfomalla.html", data)
                except Exception as ex:
                    pass

            if action == 'modulos':
                try:
                    data['title'] = u'Módulos anexos a la carrera'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['modulos'] = malla.modulomalla_set.all()
                    data['permite_modificar'] = malla.permite_modificar()
                    return render(request, "adm_mallas/modulos.html", data)
                except Exception as ex:
                    pass




            if action == 'predecesora':
                try:
                    data['title'] = u'Predecesora de asignatura'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.get(pk=request.GET['id'])
                    data['malla'] = malla = asignaturamalla.malla
                    data['predecesoras'] = asignaturamalla.asignaturamallapredecesora_set.all().order_by('predecesora__asignatura')
                    data['permite_modificar'] = malla.permite_modificar()
                    return render(request, "adm_mallas/predecesora.html", data)
                except Exception as ex:
                    pass

            if action == 'planificacionasignaturamalla':
                try:
                    data['title'] = u'Planificación'
                    data['silabo'] = silabo = SilaboAsignaturaMalla.objects.get(pk=request.GET['id'])
                    data['planificacionmateria'] = planificacionmateria = silabo.planificacionmateria
                    data['talleres'] = planificacionmateria.tallerplanificacionmateria_set.all()
                    data['guias'] = planificacionmateria.guiaspracticasmateria_set.all()
                    data['rubrica'] = planificacionmateria.mi_rubrica()
                    return render(request, "adm_mallas/planificacion.html", data)
                except Exception as ex:
                    pass


            if action == 'predecesoramodulo':
                try:
                    data['title'] = u'Predecesora de módulo'
                    data['modulomalla'] = modulomalla = ModuloMalla.objects.get(pk=request.GET['id'])
                    data['malla'] = malla = modulomalla.malla
                    data['predecesoras'] = modulomalla.modulomallapredecesora_set.all().order_by('predecesora__asignatura')
                    data['permite_modificar'] = malla.permite_modificar()
                    return render(request, "adm_mallas/predecesoramodulo.html", data)
                except Exception as ex:
                    pass

            if action == 'addpredecesora':
                try:
                    data['title'] = u'Predecesora de asignatura'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.get(pk=request.GET['id'])
                    form = AsignaturaMallaPredecesoraForm()
                    form.for_exclude_asignatura(asignaturamalla)
                    data['form'] = form
                    return render(request, "adm_mallas/addpredecesora.html", data)
                except Exception as ex:
                    pass

            if action == 'aprueba':
                try:
                    data['title'] = u'Aprobar Malla'
                    data['malla'] = Malla.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/aprobar.html", data)
                except Exception as ex:
                    pass

            if action == 'apruebafinanciero':
                try:
                    data['title'] = u'Aprobar Ingreso valores financiero'
                    data['malla'] = Malla.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/aprobarfinanciero.html", data)
                except Exception as ex:
                    pass

            if action == 'desaprobar':
                try:
                    data['title'] = u'Desaprobar Malla'
                    data['malla'] = Malla.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/desaprobar.html", data)
                except Exception as ex:
                    pass

            if action == 'desaprobarfinanciero':
                try:
                    data['title'] = u'Desaprobar Ingreso valores financiero'
                    data['malla'] = Malla.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/desaprobarfinanciero.html", data)
                except Exception as ex:
                    pass


            if action == 'delsyllabus':
                try:
                    data['title'] = u'Eliminar plantilla de silabo'
                    data['silabo'] = silabo = SilaboAsignaturaMalla.objects.get(pk=request.GET['id'])
                    data['asignaturamalla'] = silabo.asignaturamalla
                    return render(request, "adm_mallas/delsyllabus.html", data)
                except Exception as ex:
                    pass


            if action == 'aprobarsyllabus':
                try:
                    data['title'] = u'Habilitar plantilla de silabo'
                    data['silabo'] = silabo = SilaboAsignaturaMalla.objects.get(pk=request.GET['id'])
                    data['asignaturamalla'] = silabo.asignaturamalla
                    return render(request, "adm_mallas/aprobarsyllabus.html", data)
                except Exception as ex:
                    pass

            if action == 'desaprobarsyllabus':
                try:
                    data['title'] = u'Deshabilitar plantilla de silabo'
                    data['silabo'] = silabo = SilaboAsignaturaMalla.objects.get(pk=request.GET['id'])
                    data['asignaturamalla'] = silabo.asignaturamalla
                    return render(request, "adm_mallas/desaprobarsyllabus.html", data)
                except Exception as ex:
                    pass

            if action == 'editmalla':
                try:
                    data['title'] = u'Editar malla curricular'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    form = MallaForm(initial={"resolucion": malla.resolucion,
                                              "codigo": malla.codigo,
                                              "tipo": malla.tipo,
                                              "modalidad": malla.modalidad,
                                              "titulo": malla.tituloobtenido,
                                              "tipoduraccionmalla": malla.tipoduraccionmalla,
                                              "inicio": malla.inicio,
                                              "fin": malla.fin,
                                              "vigencia": malla.vigencia,
                                              "nivelesregulares": malla.nivelesregulares,
                                              "nivelacion": malla.nivelacion,
                                              "organizacionaprendizaje": malla.organizacionaprendizaje,
                                              "maximomateriasonline": malla.maximomateriasonline,
                                              "libreopcion": malla.libreopcion,
                                              "optativas": malla.optativas,
                                              "arrastres": malla.cantidadarrastres,
                                              "horaspracticas": malla.horaspracticas,
                                              "nivelhoraspracticas": malla.nivelhoraspracticas,
                                              "horasvinculacion": malla.horasvinculacion,
                                              "nivelhorasvinculacion": malla.nivelhorasvinculacion,
                                              "nivelproyecto": malla.niveltrabajotitulacion,
                                              "modelosibalo": malla.modelosibalo,
                                              "perfildeegreso": malla.perfildeegreso,
                                              "observaciones": malla.observaciones})
                    form.editar(malla)
                    data['form'] = form
                    data['permite_modificar'] = malla.permite_modificar()
                    return render(request, "adm_mallas/editmalla.html", data)
                except Exception as ex:
                    pass

            if action == 'addasign':
                try:
                    data['title'] = u'Adicionar asignatura a malla curricular'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    eje = None
                    nivel = None
                    if 'eje' in request.GET:
                        data['eje'] = eje = EjeFormativo.objects.get(pk=request.GET['eje'])
                        data['nivel'] = nivel = NivelMalla.objects.get(pk=request.GET['nivel'])
                    form = AsignaturaMallaForm(initial={'organizacionaprendizaje': malla.organizacionaprendizaje,
                                                        'ejeformativo': eje,
                                                        'nivelmalla': nivel})
                    # form.noes_itinerario()
                    form.adicionar(malla)
                    data['form'] = form
                    return render(request, "adm_mallas/addasign.html", data)
                except Exception as ex:
                    pass

            if action == 'editasign':
                try:
                    data['title'] = u'Editar asignatura de malla curricular'
                    data['asignaturamalla'] = am = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['malla'] = malla = am.malla
                    form = AsignaturaMallaForm(initial={"asignatura": am.asignatura,
                                                        "nivelmalla": am.nivelmalla,
                                                        "ejeformativo": am.ejeformativo,
                                                        "areaconocimiento": am.areaconocimiento,
                                                        "tipomateria": am.tipomateria,
                                                        "campoformacion": am.campoformacion,
                                                        "identificacion": am.identificacion,
                                                        "practicas": am.practicas,
                                                        "codigopracticas": am.codigopracticas,
                                                        "practicasasistenciales": am.practicasasistenciales,
                                                        "obligatoria": am.obligatoria,
                                                        "matriculacion": am.matriculacion,
                                                        "horassemanales": am.horassemanales,
                                                        "horas": am.horas,
                                                        "horasdocencia": am.horasdocencia,
                                                        "horascolaborativas": am.horascolaborativas,
                                                        "horasasistidas": am.horasasistidas,
                                                        "organizacionaprendizaje": am.malla.organizacionaprendizaje,
                                                        "horasorganizacionaprendizaje": am.horasorganizacionaprendizaje,
                                                        "horasautonomas": am.horasautonomas,
                                                        "horaspracticas": am.horaspracticas,
                                                        "creditos": am.creditos,
                                                        "cantidadmatriculas": am.cantidadmatriculas,
                                                        "sinasistencia": am.sinasistencia,
                                                        "titulacion": am.titulacion,
                                                        "validacreditos": am.validacreditos,
                                                        "validapromedio": am.validapromedio,
                                                        "competencia": am.competencia,
                                                        "totalhorasaprendizajecontactodocente": am.totalhorasaprendizajecontactodocente,
                                                        "totalhorasaprendizajepracticoexperimental": am.totalhorasaprendizajepracticoexperimental,
                                                        "totalhorasaprendizajeautonomo": am.totalhorasaprendizajeautonomo,
                                                        "lms": am.lms,
                                                        "plantillalms": am.plantillaslms})
                    if malla.permite_modificar():
                        form.editar(malla)
                    else:
                        form.editarcompetencia(malla)
                    form.noes_itinerario()
                    data['form'] = form
                    data['permite_modificar'] = am.malla.permite_modificar()
                    return render(request, "adm_mallas/editasign.html", data)
                except Exception as ex:
                    pass

            if action == 'editasigncompetencia':
                try:
                    data['title'] = u'Editar datos'
                    data['asignaturamalla'] = am = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['malla'] = malla = am.malla
                    form = AsignaturaMallaCompetenciaForm(initial={"identificacion": am.identificacion,
                                                                   "codigopracticas": am.codigopracticas,
                                                                   "competencia": am.competencia})
                    form.editar(am)
                    data['form'] = form
                    data['permite_modificar'] = am.malla.permite_modificar()
                    return render(request, "adm_mallas/editasigncompetencia.html", data)
                except Exception as ex:
                    pass

            if action == 'edithorasdocencia':
                try:
                    data['title'] = u'Editar Horas de docencia'
                    data['asignaturamalla'] = am = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['malla'] = malla = am.malla
                    form = AsignaturaMallaHorasDocenciaForm(initial={"totalhorasaprendizajecontactodocente": am.totalhorasaprendizajecontactodocente,
                                                                       "totalhorasaprendizajepracticoexperimental": am.totalhorasaprendizajepracticoexperimental,
                                                                       "totalhorasaprendizajeautonomo": am.totalhorasaprendizajeautonomo})
                    data['form'] = form
                    data['permite_modificar'] = not malla.aprobado and not malla.activo
                    return render(request, "adm_mallas/edithorasdocencia.html", data)
                except Exception as ex:
                    pass

            if action == 'syllabus':
                try:
                    data['title'] = u'Plantillas de sílabo'
                    data['asignaturamalla'] = asignaturamalla = AsignaturaMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['silabos'] = asignaturamalla.silaboasignaturamalla_set.all()
                    data['permite_modificar'] = asignaturamalla.malla.permite_modificar()
                    return render(request, "adm_mallas/syllabus.html", data)
                except Exception as ex:
                    pass

            if action == 'syllabusmodulo':
                try:
                    data['title'] = u'Plantillas de sílabo'
                    data['modulomalla'] = modulomalla = ModuloMalla.objects.filter(malla__carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['silabos'] = modulomalla.silabomodulomalla_set.all()
                    data['permite_modificar'] = modulomalla.malla.permite_modificar()
                    return render(request, "adm_mallas/syllabusmodulo.html", data)
                except Exception as ex:
                    pass

            if action == 'delpredecesora':
                try:
                    data['title'] = u'Eliminar predecesora malla'
                    data['predecesora'] = AsignaturaMallaPredecesora.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/delpredecesora.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'delpredecesoramodulo':
                try:
                    data['title'] = u'Eliminar predecesora modulo'
                    data['predecesora'] = ModuloMallaPredecesora.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/delpredecesoramodulo.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'delpredecesoraasignaturamodulo':
                try:
                    data['title'] = u'Eliminar predecesora modulo'
                    data['predecesoramodulo'] = AsignaturaModuloMallaPredecesora.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/delpredecesoraasignaturamodulo.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'evidencias':
                try:
                    data['title'] = u'Evidencias de la Malla'
                    data['malla'] = malla = Malla.objects.get(pk=request.GET['id'])
                    data['evidencias'] = malla.evidenciamalla_set.all()
                    data['permite_modificar'] = malla.permite_modificar()
                    return render(request, "adm_mallas/evidencias.html", data)
                except Exception as ex:
                    pass

            if action == 'otrosrequisitos':
                try:
                    data['title'] = u'Otros Requisitos de la Malla'
                    data['malla'] = malla = Malla.objects.get(pk=request.GET['id'])
                    data['otrosrequisitos'] = malla.otrosrequisitosmalla_set.all()
                    data['permite_modificar'] = malla.permite_modificar()
                    return render(request, "adm_mallas/otrosrequisitos.html", data)
                except Exception as ex:
                    pass

            if action == 'addotrosrequisitos':
                try:
                    data['title'] = u'Adicionar Otros Requisitos'
                    data['malla'] = malla = Malla.objects.get(pk=request.GET['id'])
                    data['form'] = OtrosRequisitosMallaForm()
                    return render(request, "adm_mallas/addotrosrequisitos.html", data)
                except Exception as ex:
                    pass

            if action == 'editotrosrequisitos':
                try:
                    data['title'] = u'Editar evidencia'
                    data['otrosrequisitos'] = otrosrequisitos = OtrosRequisitosMalla.objects.get(pk=request.GET['id'])
                    form = OtrosRequisitosMallaForm(initial={'nombre': otrosrequisitos.nombre,
                                                             'descripcion': otrosrequisitos.descripcion})
                    data['form'] = form
                    return render(request, "adm_mallas/editotrosrequisitos.html", data)
                except Exception as ex:
                    pass

            if action == 'delotrosrequisitos':
                try:
                    data['title'] = u'Eliminar evidencia'
                    data['otrosrequisitos'] = OtrosRequisitosMalla.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/delotrosrequisitos.html", data)
                except Exception as ex:
                    pass

            if action == 'addevidencia':
                try:
                    data['title'] = u'Adicionar evidencia'
                    data['malla'] = malla = Malla.objects.get(pk=request.GET['id'])
                    data['form'] = EvidenciaMallaForm()
                    return render(request, "adm_mallas/addevidencia.html", data)
                except Exception as ex:
                    pass

            if action == 'delevidencia':
                try:
                    data['title'] = u'Eliminar evidencia'
                    data['evidencia'] = EvidenciaMalla.objects.get(pk=request.GET['id'])
                    return render(request, "adm_mallas/delevidencia.html", data)
                except Exception as ex:
                    pass

            if action == 'editevidencia':
                try:
                    data['title'] = u'Editar evidencia'
                    data['evidencia'] = evidencia = EvidenciaMalla.objects.get(pk=request.GET['id'])
                    form = EvidenciaMallaForm(initial={'nombre': evidencia.nombre,
                                                       'fecha': evidencia.fecha,
                                                       'descripcion': evidencia.descripcion})
                    data['form'] = form
                    return render(request, "adm_mallas/editevidencia.html", data)
                except Exception as ex:
                    pass

            if action == 'addinfosede':
                try:
                    data['title'] = u'Adicionar codigo de ejecución'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['form'] = InfoMallasedeForm()
                    return render(request, "adm_mallas/addinfosede.html", data)
                except Exception as ex:
                    pass

            if action == 'editinfosede':
                try:
                    data['title'] = u'Editar codigo de ejecución'
                    data['infosede'] = infosede = InformacionSedeMalla.objects.get(pk=request.GET['id'])
                    form = InfoMallasedeForm(initial={'sede': infosede.sede,
                                                      'lugar': infosede.lugar,
                                                      'codigo': infosede.codigo})
                    form.editar()
                    data['form'] = form
                    data['permite_modificar'] = infosede.malla.permite_modificar()
                    return render(request, "adm_mallas/editinfosede.html", data)
                except Exception as ex:
                    pass

            if action == 'delinfosede':
                try:
                    data['title'] = u'Eliminar información de ejecución'
                    data['infosede'] = infosede=InformacionSedeMalla.objects.get(pk=request.GET['id'])
                    data['permite_modificar'] = infosede.malla.permite_modificar()
                    return render(request, "adm_mallas/delinfosede.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'infosede':
                try:
                    data['title'] = u'Información del lugar de ejecución'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['sedes'] = malla.informacionsedemalla_set.all()
                    return render(request, "adm_mallas/infosede.html", data)
                except Exception as ex:
                    pass

            if action == 'competenciase':
                try:
                    data['title'] = u'Competencias específicas'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['competemcias'] = malla.competenciasespecificas.all()
                    return render(request, "adm_mallas/competenciase.html", data)
                except Exception as ex:
                    pass

            if action == 'competenciasg':
                try:
                    data['title'] = u'Competencias genéricas'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    data['competemcias'] = malla.competenciasgenericas.all()
                    return render(request,'adm_mallas/competenciasg.html', data)
                except Exception as ex:
                    pass

            if action == 'delcompee':
                try:
                    data['title'] = u'Eliminar competencia especifica'
                    data['malla'] = Malla.objects.get(pk=request.GET['id'])
                    data['competemcia'] = CompetenciaEspecifica.objects.get(pk=request.GET['idc'])
                    return render(request, "adm_mallas/delcompee.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'delcompeg':
                try:
                    data['title'] = u'Eliminar competencia generica'
                    data['malla'] = Malla.objects.get(pk=request.GET['id'])
                    data['competemcia'] = CompetenciaGenerica.objects.get(pk=request.GET['idc'])
                    return render(request, "adm_mallas/delcompeg.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'addcompee':
                try:
                    data['title'] = u'Adicionar competencia específica a malla curricular'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    form = CompetenciaEspecificaMallaForm()
                    form.adicionar(malla.carrera)
                    data['form'] = form
                    return render(request, "adm_mallas/addcompee.html", data)
                except Exception as ex:
                    pass

            if action == 'addcompeg':
                try:
                    data['title'] = u'Adicionar competencia genérica a malla curricular'
                    data['malla'] = malla = Malla.objects.filter(carrera__in=miscarreras).get(pk=request.GET['id'])
                    form = CompetenciaGenericaMallaForm()
                    data['form'] = form
                    return render(request, "adm_mallas/addcompeg.html", data)
                except Exception as ex:
                    pass



            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Mallas curriculares'
                carrera = None
                data['carreras'] = carreras = persona.lista_carreras_coordinacion(request.session['coordinacionseleccionada'])
                if 'carreraseleccionada' in request.session:
                    carrera = request.session['carreraseleccionada']
                    if carrera not in carreras:
                        carrera = carreras[0]
                else:
                    if carreras:
                        carrera = carreras[0]
                    request.session['carreraseleccionada'] = carrera
                if 'c' in request.GET:
                    carrera = carreras.filter(id=int(request.GET['c']))[0]
                    request.session['carreraseleccionada'] = carrera
                data['mallas'] = Malla.objects.filter(carrera=carrera).distinct()
                data['carrera'] = carrera
                return render(request, "adm_mallas/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
