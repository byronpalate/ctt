# coding=utf-8
import json
from datetime import datetime

import xlrd
import openpyxl
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.template import RequestContext
from django.utils.encoding import smart_str
from dateutil.relativedelta import relativedelta

from decorators import secure_module, last_access

from settings import ALUMNOS_GROUP_ID, EMAIL_DOMAIN
from ctt.commonviews import adduserdata, obtener_reporte
from ctt.forms import InscripcionForm, RecordAcademicoForm, HistoricoRecordAcademicoForm, CargarFotoForm, \
    CambiomallaForm, NuevaInscripcionForm, \
    CambionivelmallaForm, EstudioEducacionSuperiorForm, EstudioEducacionBasicaForm, \
    CambiaDatosCarreraForm, ImportarArchivoXLSForm, \
    CambioitinerarioForm, \
    RetiradoCarreraForm, \
    CambiarFichaInscripcionForm, \
    ImportarArchivoXLSPeriodoForm

from ctt.funciones import log, generar_usuario, \
    generar_nombre, resetear_clave, MiPaginador, bad_json, ok_json, url_back, generar_email, \
    puede_modificar_inscripcion_post, convertir_fecha, remover_tildes
from ctt.models import InscripcionMalla, InscripcionItinerarrio, EstudioPersona, ModuloMalla

from ctt.models import Persona, Inscripcion, RecordAcademico, HistoricoRecordAcademico, \
    FotoPersona, Archivo, NivelMalla, EjeFormativo, AsignaturaMalla, Periodo, \
    Carrera,  Asignatura, Nivel, Matricula, Clase, RetiroCarrera, \
    Modalidad, Sede, Administrativo, Profesor, Materia, Turno,  Rubro, Pago, Sesion, Malla

from ctt.tasks import send_mail, send_html_mail


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    coordinacionseleccionada = request.session['coordinacionseleccionada']
    data['PERSONA_ADMINS_ACADEMICO_ID'] = False
    if persona.id in PERSONA_ADMINS_ACADEMICO_ID:
        data['PERSONA_ADMINS_ACADEMICO_ID'] = True

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'delete':
            try:
                aux1 = 0
                aux=0
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                estudiante=Persona.objects.get(pk=inscripcion.persona_id)
                rubro=Rubro.objects.filter(inscripcion_id=inscripcion)
                for rubros in rubro:
                    if Pago.objects.filter(rubro_id=rubros.id).exists():
                        return bad_json(mensaje=u'Existe un rubro con abono relacionado a esta inscripción')
                if estudiante.es_administrativo():
                    return bad_json(mensaje=u'No se puede borrar porque es administrativo')
                if estudiante.es_profesor():
                    return bad_json(mensaje=u'No se puede borrar porque es docente')
                if inscripcion.tiene_matriculas():
                    return bad_json(mensaje=u'Existe una matricula relacionada a esta inscripción')
                inscritos = Inscripcion.objects.filter(persona=estudiante.id)
                for incrito in inscritos:
                    aux1 = aux1+1
                if aux1 == 1:
                    log(u'Elimino Inscripcion: %s' % inscripcion, request, "del")
                    log(u'Elimino Persona: %s' % estudiante, request, "del")
                    log(u'Elimino usuario: %s' % estudiante.usuario, request, "del")
                    incrito.delete()
                    estudiante.delete()
                    estudiante.usuario.delete()

                    return ok_json()
                if aux1 > 1:
                    log(u'Elimino Inscripcion: %s' % inscripcion, request, "del")
                    inscripcion.delete()

                    return ok_json()
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'actualizarpromediogeneral':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                promedioactual=inscripcion.promediogeneral
                if inscripcion.actualiza_promedio_record():
                    log(u'Se actualizo el promedio general del estudiante: %s de %s a %s' % (inscripcion,str(promedioactual),str(inscripcion.promediogeneral)), request, "edit")
                else:
                    return bad_json(mensaje=u"No se puede actualizar el promedio general.")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'periodo':
            try:
                periodo = Periodo.objects.get(pk=request.POST['id'])
                sede = Sede.objects.get(pk=request.POST['ids'])
                carrera = Carrera.objects.get(pk=request.POST['idc'])
                modalidad = Modalidad.objects.get(pk=request.POST['idm'])
                nlista = []
                lista = []
                for nivel in Nivel.objects.filter(periodo=periodo,sede=sede, materia__asignaturamalla__malla__carrera=carrera, modalidad=modalidad).distinct():
                    if nivel not in lista:
                        lista.append(nivel)
                        nlista.append({'id': nivel.id, 'nombre': nivel.paralelo})
                return ok_json({'lista': nlista, 'posgrado':  periodo.es_posgrado()})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'carrerasmalla':
            try:
                carrera = Carrera.objects.get(pk=int(request.POST['idcarrera']))
                modalidad = Modalidad.objects.get(pk=int(request.POST['idmodalidad']))
                lista = []
                for malla in Malla.objects.filter(carrera=carrera, modalidad=modalidad,aprobado=True):
                    lista.append([malla.id, malla.__str__()])
                return ok_json({'lista': lista})
            except:
                return bad_json(error=3)

        if action == 'asignarcanvas':
            try:
                inscripcion = Inscripcion.objects.get(pk=int(request.POST['inscripcion']))
                persona=Persona.objects.get(pk=inscripcion.persona.id)
                form = AsignarCanvasForm(request.POST)
                if form.is_valid():
                    persona.id_canvas=form.cleaned_data['id_canvas']
                    persona.save()
                    log(u'Modifico el id de CANVAS PARA LA PERSONA: %s' % (persona), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except:
                return bad_json(error=3)

        if action == 'periodoscarrera':
            try:
                carrera = Carrera.objects.get(pk=int(request.POST['idcarrera']))
                lista = []
                # if carrera.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
                #     for periodo in Periodo.objects.filter(tipo__id=TIPO_PERIODO_POSGRADO):
                #         lista.append([periodo.id, periodo.__str__()])
                # else:
                #     for periodo in Periodo.objects.filter(tipo__id=TIPO_PERIODO_GRADO):
                #         lista.append([periodo.id, periodo.__str__()])

                for periodo in Periodo.objects.all():
                    lista.append([periodo.id, periodo.__str__()])


                return ok_json({'lista': lista})
            except:
                return bad_json(error=3)

        if action == 'verificar_posgrado':
            try:
                carrera =  Carrera.objects.get(pk=int(request.POST['carrera_id']))
                return ok_json({'es_posgrado': carrera.posgrado})
            except Carrera.DoesNotExist:
                return ok_json({'es_posgrado': False})

        if action == 'cambiomalla':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = CambiomallaForm(request.POST)
                if form.is_valid():
                    malla = inscripcion.inscripcionmalla_set.all()
                    malla.delete()
                    im = InscripcionMalla(inscripcion=inscripcion,
                                          malla=form.cleaned_data['malla_nueva'])
                    im.save(request)
                    inscripcion.actualizar_creditos()
                    inscripcion.actualizar_nivel()
                    log(u'Modifico malla de inscripcion: %s - %s' % (inscripcion.persona, im.malla), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cambionivel':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = CambionivelmallaForm(request.POST)
                if form.is_valid():
                    nivelfinal = form.cleaned_data['nuevonivel'].id
                    malla = inscripcion.mi_malla()
                    if form.cleaned_data['nuevonivel'].id > malla.nivelesregulares:
                        nivelfinal = malla.nivelesregulares
                    inscripcion.nivelhomologado_id = nivelfinal
                    inscripcion.save(request)
                    inscripcion.actualizar_nivel()
                    if inscripcion.matricula_set.filter(cerrada=False).exists():
                        ultimamatricula = inscripcion.matricula_set.filter(cerrada=False)[0]
                        ultimamatricula.nivelmalla = inscripcion.mi_nivel().nivel
                        ultimamatricula.save(request)
                    log(u'Modifico nivel de inscripcion: %s - %s' % (inscripcion.persona, inscripcion.nivelhomologado), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'activarcertificadonoadeudar':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                inscripcion.activocertificadonoadeudar=True
                if CodigoCertificadoNoAdeudar.objects.filter(pk=1).exists():
                    certid = CodigoCertificadoNoAdeudar.objects.all().order_by('-id')[0].id
                else:
                    certid = int(0)
                codigo = 'CNA-'+ inscripcion.sede.alias + '-' + inscripcion.carrera.alias + '-' + str(certid + 1)
                certificado = CodigoCertificadoNoAdeudar(
                    inscripcion = inscripcion,
                    codigo = codigo
                )
                certificado.save()
                log(u'Se activa para aprobar el certificado de no adeudar: %s' % (inscripcion.persona), request, "edit")
                inscripcion.save()
                personalcolecturia = Persona.objects.filter(cedula__in=[1315278539,1803005964])
                if inscripcion.sede.id == 2:
                    personalcolecturia = Persona.objects.filter(cedula__in=[1719298687,1803005964])
                if inscripcion.sede.id == 1 and (inscripcion.coordinacion.id == 2 or inscripcion.coordinacion.id == 21 or inscripcion.coordinacion.id == 6 ):
                    personalcolecturia = Persona.objects.filter(cedula__in=[1801769405,1803005964])

                #
                send_mail(subject='Certificado no adeudar.',
                          html_template='emails/aprobarcertificadonoadeudar.html',
                          data={'inscripcion': inscripcion},
                          recipient_list=personalcolecturia)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'aprobarcertificadonoadeudar':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                opcion = int(request.POST['opcion'])
                if opcion == 2:
                    inscripcion.certificadoaprobadosecretaria=True
                    inscripcion.personasecretaria = persona.id
                    inscripcion.fechasecretaria = datetime.now()
                    log(u'Colecturia Aprueba certificado de no adeudar: %s' % (inscripcion.persona), request, "edit")
                if opcion == 1:
                    inscripcion.certificadoaprobadocolecturia = True
                    inscripcion.personacolecturia = persona.id
                    inscripcion.fechacolecturia = datetime.now()
                    log(u'Secretaria Aprueba certificado de no adeudar: %s' % (inscripcion.persona), request, "edit")
                if opcion == 3:
                    inscripcion.certificadoaprobadobiblioteca=True
                    inscripcion.personabiblioteca = persona.id
                    inscripcion.fechabiblioteca = datetime.now()
                    log(u'Biblioteca Aprueba certificado de no adeudar: %s' % (inscripcion.persona), request, "edit")
                inscripcion.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)


        if action == 'resetearcertificado':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                inscripcion.certificadoaprobadosecretaria=False
                inscripcion.personasecretaria = None
                inscripcion.fechasecretaria = None
                inscripcion.certificadoaprobadocolecturia = False
                inscripcion.personacolecturia = None
                inscripcion.fechacolecturia = None
                inscripcion.certificadoaprobadobiblioteca=False
                inscripcion.personabiblioteca = None
                inscripcion.fechabiblioteca = None
                log(u'reseteo proceso de certificado: %s' % (inscripcion.persona), request, "edit")
                inscripcion.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cambionivelmatricula':
            try:
                matricula = Matricula.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, matricula.inscripcion):
                    return bad_json(error=8)
                form = CambionivelmallaForm(request.POST)
                if form.is_valid():
                    nivelfinal = form.cleaned_data['nuevonivel'].id
                    matricula.nivelmalla_id = nivelfinal
                    matricula.save(request)
                    log(u'Modifico nivel de matricula: %s - %s' % (matricula.inscripcion.persona, matricula.nivelmalla), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cambiocohorte':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = CambioCohortePosgradoForm(request.POST)
                if form.is_valid():
                    cohortefinal = form.cleaned_data['nuevacohorte']
                    inscripcion.fechascorteposgrado = cohortefinal
                    inscripcion.save(request)
                    log(u'Modifico cohorthe de inscripcion: %s' % (inscripcion.persona), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'generarrubrosparqueo':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                matricula = inscripcion.matricula_periodo(request.session['periodo'])
                tipovehiculo = int(request.POST['tipovehiculo'])
                tiempo = int(request.POST['tiempo'])
                if matricula:
                    duplicado = 1
                    if not inscripcion.generar_rubro_parqueadero(inscripcion.sede, request.session['periodo'], matricula.nivel.modalidad, tipovehiculo, tiempo, inscripcion.carrera.posgrado, duplicado):
                        return bad_json(mensaje=u"No existen valores para esta modalidad o periodo. Favor comuníquese con el Dept. Financiero")
                    log(u'genero rubros de parqueo para : %s - inscripcion: %s' % (inscripcion.persona, str(inscripcion.id)), request,"edit")
                    return ok_json()
                else:
                    return bad_json(mensaje=u"No esta matriculado en este periodo.")
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'generarrubrosparqueoadicional':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                matricula = inscripcion.matricula_periodo(request.session['periodo'])
                tipovehiculo = int(request.POST['tipovehiculo'])
                tiempo = int(request.POST['tiempo'])
                if matricula:
                    duplicado = 2
                    if not inscripcion.generar_rubro_parqueadero(inscripcion.sede, request.session['periodo'], matricula.nivel.modalidad, tipovehiculo, tiempo, inscripcion.carrera.posgrado, duplicado):
                        return bad_json(mensaje=u"No existen valores para esta modalidad o periodo. Favor comuníquese con el Dept. Financiero")
                    log(u'genero rubros de parqueo para : %s - inscripcion: %s' % (inscripcion.persona, str(inscripcion.id)), request,"edit")
                    return ok_json()
                else:
                    return bad_json(mensaje=u"No esta matriculado en este periodo.")
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addrecord':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = RecordAcademicoForm(request.POST)
                if form.is_valid():
                    if inscripcion.recordacademico_set.filter(asignatura=form.cleaned_data['asignatura']).exists():
                        return bad_json(mensaje=u"Ya existe la asignatura en el record, modifíquela desde el histórico.")
                    record = RecordAcademico(inscripcion=inscripcion,
                                             asignatura=form.cleaned_data['asignatura'],
                                             modulomalla=inscripcion.asignatura_en_modulomalla(form.cleaned_data['asignatura']),
                                             asignaturamalla=inscripcion.asignatura_en_asignaturamalla(form.cleaned_data['asignatura']),
                                             nota=form.cleaned_data['nota'],
                                             asistencia=form.cleaned_data['asistencia'],
                                             fecha=form.cleaned_data['fecha'],
                                             aprobada=form.cleaned_data['aprobada'],
                                             libreconfiguracion=form.cleaned_data['libreconfiguracion'],
                                             optativa=form.cleaned_data['optativa'],
                                             pendiente=False,
                                             creditos=form.cleaned_data['creditos'],
                                             horas=form.cleaned_data['horas'],
                                             validacreditos=form.cleaned_data['validacreditos'],
                                             validapromedio=form.cleaned_data['validapromedio'],
                                             observaciones=form.cleaned_data['observaciones'])
                    record.save(request)
                    record.actualizar()
                    inscripcion.actualizar_nivel()
                    inscripcion.actualiza_matriculas(record.asignatura)
                    inscripcion.save(request)
                    inscripcion.actualizar_homologacion()
                    if inscripcion.egresado():
                        dato = inscripcion.datos_egresado()
                        dato.notaegreso = inscripcion.promedio_record()
                        dato.save()
                    log(u'Adiciono record academico: %s - %s' % (record, record.inscripcion.persona), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addrecordhomologada':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = RecordAcademicoForm(request.POST)
                if form.is_valid():
                    if inscripcion.historicorecordacademico_set.filter(asignatura=form.cleaned_data['asignatura'], fecha=form.cleaned_data['fecha']).exists():
                        return bad_json(mensaje=u"Registro existente en esa fecha.")
                    if inscripcion.historicorecordacademico_set.filter(Q(convalidacion=True) | Q(homologada=True), asignatura=form.cleaned_data['asignatura']).exists():
                        return bad_json(mensaje=u"Ya existe un registro de homologacion para esta asignatura.")
                    aprueba = True
                    if (form.cleaned_data['nota']<7):
                        aprueba = False
                    else:
                        aprueba = True
                    record = HistoricoRecordAcademico(inscripcion=inscripcion,
                                                      asignatura=form.cleaned_data['asignatura'],
                                                      modulomalla=inscripcion.asignatura_en_modulomalla(form.cleaned_data['asignatura']),
                                                      asignaturamalla=inscripcion.asignatura_en_asignaturamalla(form.cleaned_data['asignatura']),
                                                      nota=form.cleaned_data['nota'],
                                                      fecha=form.cleaned_data['fecha'],
                                                      aprobada= aprueba,
                                                      convalidacion=form.cleaned_data['convalidacion'],
                                                      validacreditos=form.cleaned_data['validacreditos'],
                                                      validapromedio=form.cleaned_data['validapromedio'],
                                                      creditos=form.cleaned_data['creditos'],
                                                      horas=form.cleaned_data['horas'],
                                                      homologada=form.cleaned_data['homologada'],
                                                      observaciones='HOMOLOGACIÓN '+str(form.cleaned_data['periodo'].nombre),
                                                      asistencia=100)
                    record.save(request)
                    record.actualizar()
                    if form.cleaned_data['convalidacion']:
                        if form.cleaned_data['institucion'] and form.cleaned_data['carrera_he'] and form.cleaned_data['asignatura_he']:
                            convalidacion = ConvalidacionInscripcion(record=record.recordacademico,
                                                                     periodo=form.cleaned_data['periodo'],
                                                                     institucion_id=int(form.cleaned_data['institucion']),
                                                                     carrera=form.cleaned_data['carrera_he'],
                                                                     tiporeconocimiento=form.cleaned_data['tiporeconocimiento'],
                                                                     tiemporeconocimiento=form.cleaned_data['tiemporeconocimiento'],
                                                                     asignatura=form.cleaned_data['asignatura_he'],
                                                                     anno=form.cleaned_data['anno_he'],
                                                                     nota_ant=form.cleaned_data['nota_ant_he'],
                                                                     observaciones=form.cleaned_data['observaciones_he'],
                                                                     creditos=form.cleaned_data['creditos_he'])
                            convalidacion.save(request)
                            if 'archivo' in request.FILES:
                                archivo = request.FILES['archivo']
                                archivo._name = generar_nombre("archivo_", archivo._name)
                                convalidacion.archivo = archivo
                                convalidacion.save(request)
                    else:
                        if form.cleaned_data['carrera_hi'] and form.cleaned_data['modalidad_hi'] and form.cleaned_data['asignatura_hi']:
                            homologacion = HomologacionInscripcion(record=record.recordacademico,
                                                                   periodo=form.cleaned_data['periodo'],
                                                                   carrera=form.cleaned_data['carrera_hi'],
                                                                   modalidad=form.cleaned_data['modalidad_hi'],
                                                                   asignatura=form.cleaned_data['asignatura_hi'],
                                                                   fecha=form.cleaned_data['fecha_hi'],
                                                                   nota_ant=form.cleaned_data['nota_ant_hi'],
                                                                   observaciones=form.cleaned_data['observaciones_hi'],
                                                                   creditos=form.cleaned_data['creditos_hi'])
                            homologacion.save(request)
                            if 'archivo' in request.FILES:
                                archivo = request.FILES['archivo']
                                archivo._name = generar_nombre("archivo_", archivo._name)
                                homologacion.archivo = archivo
                                homologacion.save(request)
                    inscripcion.actualizar_nivel()
                    inscripcion.actualiza_matriculas(form.cleaned_data['asignatura'])
                    inscripcion.save(request)
                    inscripcion.actualizar_homologacion()
                    if inscripcion.egresado():
                        dato = inscripcion.datos_egresado()
                        dato.notaegreso = inscripcion.promedio_record()
                        dato.save()
                    log(u'Adiciono record academico: %s - %s' % (record, record.inscripcion.persona), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addrecordhomologadamasiva':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                datos = json.loads(request.POST['lista'])
                tipo = int(request.POST['tipo'])
                tipor = int(request.POST['tipor'])
                tipoh = int(request.POST['tipoh'])
                tiempo = float(request.POST['tiempo'])
                for dato in datos:
                    asignatura = Asignatura.objects.get(pk=int(dato['id']))
                    if inscripcion.historicorecordacademico_set.filter(asignatura=asignatura, fecha=convertir_fecha(dato['fecha'])).exists():
                        return bad_json(mensaje=u"Registro existente en esa fecha.")
                    if inscripcion.historicorecordacademico_set.filter(Q(convalidacion=True) | Q(homologada=True), asignatura=asignatura).exists():
                        return bad_json(mensaje=u"Ya existe un rgistro de homologacion para esta asignatura %s." % asignatura)
                    historico = HistoricoRecordAcademico(inscripcion=inscripcion,
                                                         asignatura=asignatura,
                                                         modulomalla=inscripcion.asignatura_en_modulomalla(asignatura),
                                                         asignaturamalla=inscripcion.asignatura_en_asignaturamalla(asignatura),
                                                         nota=float(dato['nota']),
                                                         fecha=convertir_fecha(dato['fecha']),
                                                         aprobada=True,
                                                         homologada=True if tipo == 1 else False,
                                                         convalidacion=True if tipo == 2 else False,
                                                         asistencia=100)
                    historico.save(request)
                    historico.actualizar()
                    record = RecordAcademico.objects.filter(inscripcion=inscripcion, asignatura=asignatura)[0]
                    if tipo == 1:
                        if int(dato['carrerai']) and int(dato['asignaturai']):
                            homologacion = HomologacionInscripcion(record=record,
                                                                   carrera_id=int(dato['carrerai']),
                                                                   tipohomologacion_id=tipoh,
                                                                   asignatura_id=int(dato['asignaturai']),
                                                                   fecha=convertir_fecha(dato['fecha']),
                                                                   nota_ant=float(dato['notae']))
                            if int(request.POST['periodo']) > 0:
                                homologacion.periodo_id = int(request.POST['periodo'])
                            homologacion.save(request)
                    else:
                        if dato['carrerae'] and dato['asignaturae']:
                            convalidacion = ConvalidacionInscripcion(record=record,
                                                                     periodo_id=int(request.POST['periodo']),
                                                                     tiporeconocimiento_id=tipor,
                                                                     tipohomologacion_id=tipoh,
                                                                     tiemporeconocimiento=tiempo,
                                                                     carrera=dato['carrerae'],
                                                                     asignatura=dato['asignaturae'],
                                                                     nota_ant=dato['notae'])
                            convalidacion.save(request)
                            if int(request.POST['periodo']) > 0:
                                convalidacion.periodo_id = int(request.POST['periodo'])
                    inscripcion.actualiza_matriculas(asignatura)
                    inscripcion.save(request)
                    inscripcion.actualizar_homologacion()
                    log(u'Adiciono record academico: %s - %s' % (record, record.inscripcion.persona), request, "add")
                inscripcion.actualizar_creditos()
                inscripcion.actualizar_nivel()
                if inscripcion.egresado():
                    dato = inscripcion.datos_egresado()
                    dato.notaegreso = inscripcion.promedio_record()
                    dato.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addhistorico':
            try:
                record = RecordAcademico.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, record.inscripcion):
                    return bad_json(error=8)
                form = HistoricoRecordAcademicoForm(request.POST)
                if form.is_valid():
                    if record.historicorecordacademico_set.filter(fecha=form.cleaned_data['fecha']).exists():
                        return bad_json(mensaje=u"Registro existente en esa fecha.")
                    if form.cleaned_data['aprobada']:
                        if record.historicorecordacademico_set.filter(aprobada=True).exists():
                            return bad_json(mensaje=u"Ya tiene esta materia aprobada en el Historico.")
                    historico = HistoricoRecordAcademico(recordacademico=record,
                                                         inscripcion=record.inscripcion,
                                                         asignatura=record.asignatura,
                                                         modulomalla=record.inscripcion.asignatura_en_modulomalla(form.cleaned_data['asignatura']),
                                                         asignaturamalla=record.inscripcion.asignatura_en_asignaturamalla(form.cleaned_data['asignatura']),
                                                         nota=form.cleaned_data['nota'],
                                                         asistencia=form.cleaned_data['asistencia'],
                                                         optativa=form.cleaned_data['optativa'],
                                                         libreconfiguracion=form.cleaned_data['libreconfiguracion'],
                                                         fecha=form.cleaned_data['fecha'],
                                                         aprobada=form.cleaned_data['aprobada'],
                                                         creditos=form.cleaned_data['creditos'],
                                                         horas=form.cleaned_data['horas'],
                                                         validacreditos=form.cleaned_data['validacreditos'],
                                                         validapromedio=form.cleaned_data['validapromedio'],
                                                         observaciones=form.cleaned_data['observaciones'])
                    historico.save(request)
                    historico.actualizar()
                    record.inscripcion.actualizar_nivel()
                    record.inscripcion.actualiza_matriculas(record.asignatura)
                    if historico.inscripcion.egresado():
                        dato = historico.inscripcion.datos_egresado()
                        dato.notaegreso = historico.inscripcion.promedio_record()
                        dato.save()
                    log(u'Adiciono historico y registro: %s - %s' % (historico, historico.inscripcion.persona), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'validapromedio':
            try:
                record = RecordAcademico.objects.get(pk=request.POST['rec'])
                # historico=HistoricoRecordAcademico.objects.get(recordacademico=record,inscripcion=record.inscripcion)
                historico=record.historicorecordacademico_set.all().order_by('-fecha')[0]
                record.validapromedio=True
                record.save()
                historico.validapromedio=True
                historico.save()
                historico.actualizar()
                log(u'Se valida el promedio para la asignatura: %s - %s' % (record.asignatura, record.inscripcion.persona), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'novalidapromedio':
            try:
                record = RecordAcademico.objects.get(pk=request.POST['rec'])
                # historico=HistoricoRecordAcademico.objects.get(recordacademico=record)
                historico=record.historicorecordacademico_set.all().order_by('-fecha')[0]
                record.validapromedio=False
                record.save()
                historico.validapromedio=False
                historico.save()
                historico.actualizar()
                log(u'NO se valida el promedio para la asignatura: %s - %s' % (record.asignatura, record.inscripcion.persona), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edithistorico':
            try:
                historico = HistoricoRecordAcademico.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, historico.inscripcion):
                    return bad_json(error=8)
                form = HistoricoRecordAcademicoForm(request.POST)
                if form.is_valid():
                    if (form.cleaned_data['nota'] < 7) and (form.cleaned_data['aprobada']):
                        return bad_json('Revise la nota', error=6)
                    if HistoricoRecordAcademico.objects.filter(inscripcion=historico.inscripcion, asignatura=historico.asignatura, fecha=form.cleaned_data['fecha']).exclude(id=historico.id).exists():
                        return bad_json(mensaje=u"Registro existente en esa fecha.")
                    historico.modulomalla = historico.inscripcion.asignatura_en_modulomalla(form.cleaned_data['asignatura'])
                    historico.asignaturamalla = historico.inscripcion.asignatura_en_asignaturamalla(form.cleaned_data['asignatura'])
                    historico.fecha = form.cleaned_data['fecha']
                    historico.nota = form.cleaned_data['nota']
                    historico.asistencia = form.cleaned_data['asistencia']
                    if not historico.convalidacion and not historico.homologada:
                        historico.aprobada = form.cleaned_data['aprobada']
                    historico.libreconfiguracion = form.cleaned_data['libreconfiguracion']
                    historico.optativa = form.cleaned_data['optativa']
                    historico.creditos = form.cleaned_data['creditos']
                    historico.horas = form.cleaned_data['horas']
                    historico.observaciones = form.cleaned_data['observaciones']
                    historico.validacreditos = form.cleaned_data['validacreditos']
                    historico.validapromedio = form.cleaned_data['validapromedio']
                    historico.save(request)
                    historico.actualizar()
                    historico.inscripcion.actualizar_nivel()
                    historico.inscripcion.actualiza_matriculas(historico.asignatura)
                    if historico.inscripcion.egresado():
                        dato = historico.inscripcion.datos_egresado()
                        dato.notaegreso = historico.inscripcion.promedio_record()
                        dato.save()
                    log(u'Modifico historico de record academico: %s - %s' % (historico, historico.inscripcion.persona), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delrecord':
            try:
                record = RecordAcademico.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, record.inscripcion):
                    return bad_json(error=8)
                asignatura = record.asignatura
                inscripcion = record.inscripcion
                homologacion = record.homologacioninscripcion_set.all()
                homologacion.delete()
                convalidacion = record.convalidacioninscripcion_set.all()
                convalidacion.delete()
                historico = record.historicorecordacademico_set.all()
                historico.delete()
                log(u'Elimino registro academico: %s - %s' % (record, record.inscripcion.persona), request, "del")
                record.delete()
                inscripcion.actualizar_nivel()
                inscripcion.actualiza_matriculas(asignatura)
                inscripcion.actualizar_homologacion()
                if inscripcion.egresado():
                    dato = inscripcion.datos_egresado()
                    dato.notaegreso = inscripcion.promedio_record()
                    dato.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delhistorico':
            try:
                historico = HistoricoRecordAcademico.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, historico.inscripcion):
                    return bad_json(error=8)
                asignatura = historico.asignatura
                inscripcion = historico.inscripcion
                log(u'Elimino historico de registro academico: %s - %s' % (historico, historico.inscripcion.persona), request, "del")
                historico.delete()
                if HistoricoRecordAcademico.objects.filter(asignatura=asignatura, inscripcion=inscripcion).exists():
                    historico = HistoricoRecordAcademico.objects.filter(asignatura=asignatura, inscripcion=inscripcion)[0]
                    historico.actualizar()
                else:
                    record = RecordAcademico.objects.filter(asignatura=asignatura, inscripcion=inscripcion)
                    record.delete()
                inscripcion.actualizar_nivel()
                inscripcion.actualiza_matriculas(asignatura)
                inscripcion.actualizar_homologacion()
                if historico.inscripcion.egresado():
                    dato = historico.inscripcion.datos_egresado()
                    dato.notaegreso = historico.inscripcion.promedio_record()
                    dato.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'convalidar':
            try:
                record = RecordAcademico.objects.get(pk=int(request.POST['id']))
                if not puede_modificar_inscripcion_post(request, record.inscripcion):
                    return bad_json(error=8)
                form = ConvalidacionInscripcionForm(request.POST, request.FILES)
                if form.is_valid():
                    convalidacion = record.datos_convalidacion()
                    if convalidacion:
                        convalidacion.periodo = form.cleaned_data['periodo']
                        convalidacion.institucion_id = form.cleaned_data['institucion']
                        convalidacion.tipohomologacion = form.cleaned_data['tipohomologacion']
                        convalidacion.tiporeconocimiento = form.cleaned_data['tiporeconocimiento']
                        convalidacion.tiemporeconocimiento = form.cleaned_data['tiemporeconocimiento']
                        convalidacion.carrera = form.cleaned_data['carrera']
                        convalidacion.asignatura = form.cleaned_data['asignatura']
                        convalidacion.anno = form.cleaned_data['anno']
                        convalidacion.nota_ant = form.cleaned_data['nota_ant']
                        convalidacion.observaciones = form.cleaned_data['observaciones']
                        convalidacion.creditos = form.cleaned_data['creditos']
                        convalidacion.save(request)
                    else:
                        convalidacion = ConvalidacionInscripcion(record=record,
                                                                 periodo=form.cleaned_data['periodo'],
                                                                 institucion_id=form.cleaned_data['institucion'],
                                                                 carrera=form.cleaned_data['carrera'],
                                                                 tipohomologacion=form.cleaned_data['tipohomologacion'],
                                                                 tiporeconocimiento=form.cleaned_data['tiporeconocimiento'],
                                                                 tiemporeconocimiento=form.cleaned_data['tiemporeconocimiento'],
                                                                 asignatura=form.cleaned_data['asignatura'],
                                                                 anno=form.cleaned_data['anno'],
                                                                 nota_ant=form.cleaned_data['nota_ant'],
                                                                 observaciones=form.cleaned_data['observaciones'],
                                                                 creditos=form.cleaned_data['creditos'])
                        convalidacion.save(request)
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        archivo._name = generar_nombre("archivo_", archivo._name)
                        convalidacion.archivo = archivo
                        convalidacion.save(request)
                    log(u'Modifico homologacion externa: %s - %s' % (convalidacion, convalidacion.record.inscripcion.persona), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'homologar':
            try:
                record = RecordAcademico.objects.get(pk=int(request.POST['id']))
                if not puede_modificar_inscripcion_post(request, record.inscripcion):
                    return bad_json(error=8)
                form = HomologacionInscripcionForm(request.POST, request.FILES)
                if form.is_valid():
                    homologacion = record.datos_homologacion()
                    if homologacion:
                        homologacion.carrera = form.cleaned_data['carrera']
                        homologacion.periodo = form.cleaned_data['periodo']
                        homologacion.modalidad = form.cleaned_data['modalidad']
                        homologacion.tipohomologacion = form.cleaned_data['tipohomologacion']
                        homologacion.asignatura = form.cleaned_data['asignatura']
                        homologacion.fecha = form.cleaned_data['fecha']
                        homologacion.nota_ant = form.cleaned_data['nota_ant']
                        homologacion.observaciones = form.cleaned_data['observaciones']
                        homologacion.creditos = form.cleaned_data['creditos']
                        homologacion.save(request)
                    else:
                        homologacion = HomologacionInscripcion(record=record,
                                                               periodo=form.cleaned_data['periodo'],
                                                               carrera=form.cleaned_data['carrera'],
                                                               modalidad=form.cleaned_data['modalidad'],
                                                               tipohomologacion=form.cleaned_data['tipohomologacion'],
                                                               asignatura=form.cleaned_data['asignatura'],
                                                               fecha=form.cleaned_data['fecha'],
                                                               nota_ant=form.cleaned_data['nota_ant'],
                                                               observaciones=form.cleaned_data['observaciones'],
                                                               creditos=form.cleaned_data['creditos'])
                        homologacion.save(request)
                    if 'archivo' in request.FILES:
                        archivo = request.FILES['archivo']
                        archivo._name = generar_nombre("archivo_", archivo._name)
                        homologacion.archivo = archivo
                        homologacion.save(request)
                    log(u'Modifico homologacion interna: %s - %s' % (homologacion, homologacion.record.inscripcion.persona), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cargarfoto':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = CargarFotoForm(request.POST, request.FILES)
                if form.is_valid():
                    persona = inscripcion.persona
                    newfile = request.FILES['foto']
                    newfile._name = generar_nombre("foto_", newfile._name)
                    foto = persona.foto()
                    if foto:
                        foto.foto = newfile
                    else:
                        foto = FotoPersona(persona=persona,
                                           foto=newfile)
                    foto.save(request)
                    make_thumb_picture(persona)
                    make_thumb_fotopersona(persona)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'add':
            try:
                form = InscripcionForm(request.POST)
                if form.is_valid():
                    cedula = remover_tildes(form.cleaned_data['cedula'].strip())
                    pasaporte = form.cleaned_data['pasaporte'].strip()
                    nacimiento = form.cleaned_data['nacimiento']
                    if not cedula and not pasaporte:
                        return bad_json(mensaje=u"Debe ingresar una identificación.")
                    if not nacimiento:
                        return bad_json(mensaje=u"Debe ingresar la fecha de nacimiento.")
                    if cedula:
                        if Persona.objects.filter(cedula=cedula).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if pasaporte:
                        if Persona.objects.filter(pasaporte=pasaporte).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if nacimiento:
                        hoy = datetime.now().date()
                        fechavalida = hoy.year - 16
                        if (nacimiento.year) > fechavalida:
                            return bad_json(mensaje=u"La fecha de nacimiento no es válida.")
                    if form.cleaned_data['colegio']:
                        if not form.cleaned_data['especialidad']:
                            return bad_json(mensaje=u'Debe ingresar la especialidad.')
                    coordinacion = form.cleaned_data['coordinacion']
                    carrera = form.cleaned_data['carrera']
                    sesion = form.cleaned_data['sesion']
                    modalidad = form.cleaned_data['modalidad']
                    sede = form.cleaned_data['sede']
                    alumnoa=form.cleaned_data['alumnoantiguo']
                    mocs = form.cleaned_data['mocs']
                    if mocs==False:
                        costo_periodo = carrera.precio_modulo_inscripcion_carrera(form.cleaned_data['periodo'], sede, modalidad,carrera,form.cleaned_data['malla'])
                        if costo_periodo != None:
                            if not costo_periodo.sininscripcion:
                                if costo_periodo.precioinscripcion <= 0:
                                    return bad_json(mensaje=u"En este periodo no esta asignado el valor de inscripción. Favor comunicarse con el Depto. Financiero")
                            if not sede.coordinacion_set.filter(carrera=carrera).exists():
                                return bad_json(mensaje=u"No existe una coordinacion para esta carrera en esta sede.")
                            if form.cleaned_data['homologar']:
                                if costo_periodo.preciohomologacion <= 0:
                                    return bad_json(mensaje=u"En este periodo no esta asignado el valor de Homologación. Favor comunicarse con el Depto. Financiero")
                    coordinacion = sede.coordinacion_set.filter(carrera=carrera)[0]
                    estudiante = Persona(nombre1=remover_tildes(form.cleaned_data['nombre1']),
                                         nombre2=remover_tildes(form.cleaned_data['nombre2']),
                                         apellido1=remover_tildes(form.cleaned_data['apellido1']),
                                         apellido2=remover_tildes(form.cleaned_data['apellido2']),
                                         cedula=remover_tildes(cedula),
                                         pasaporte=pasaporte,
                                         nacimiento=form.cleaned_data['nacimiento'],
                                         sexo=form.cleaned_data['sexo'],
                                         nacionalidad=form.cleaned_data['nacionalidad'],
                                         paisnac=form.cleaned_data['paisnac'],
                                         provincianac=form.cleaned_data['provincianac'],
                                         cantonnac=form.cleaned_data['cantonnac'],
                                         parroquianac=form.cleaned_data['parroquianac'],
                                         pais=form.cleaned_data['pais'],
                                         provincia=form.cleaned_data['provincia'],
                                         canton=form.cleaned_data['canton'],
                                         parroquia=form.cleaned_data['parroquia'],
                                         sector=remover_tildes(form.cleaned_data['sector']),
                                         direccion=remover_tildes(form.cleaned_data['direccion']),
                                         direccion2=remover_tildes(form.cleaned_data['direccion2']),
                                         num_direccion=remover_tildes(form.cleaned_data['num_direccion']),
                                         telefono=remover_tildes(form.cleaned_data['telefono']),
                                         telefono_conv=remover_tildes(form.cleaned_data['telefono_conv']),
                                         email=form.cleaned_data['email'],
                                         sangre=form.cleaned_data['sangre'],
                                         ubicacionresidenciasalesforce=form.cleaned_data['ubicacionresidenciasalesforce'],
                                         otraubicacionsalesforce=form.cleaned_data['otraubicacionsalesforce'],
                                         nombrecompletomadre=form.cleaned_data['nombrescompletosmadre'],
                                         nombrecompletopadre=form.cleaned_data['nombrescompletospadre'])
                    estudiante.save(request)
                    generar_usuario(persona=estudiante, group_id=ALUMNOS_GROUP_ID)
                    if EMAIL_INSTITUCIONAL_AUTOMATICO_ESTUDIANTES:
                        estudiante.emailinst = generar_email(estudiante, estudiante=True)
                    else:
                        estudiante.emailinst = form.cleaned_data['emailinst']
                    estudiante.save(request)
                    inscripcion = Inscripcion(persona=estudiante,
                                              fecha=datetime.now().date(),
                                              hora=datetime.now().time(),
                                              identificador=form.cleaned_data['identificador'],
                                              centroinformacion=form.cleaned_data['centroinformacion'] if modalidad.id == 3 or modalidad.id == 4 else None,
                                              carrera=carrera,
                                              modalidad=modalidad,
                                              sesion=sesion,
                                              sede=sede,
                                              coordinacion=coordinacion,
                                              mocs=form.cleaned_data['mocs'],
                                              periodo=form.cleaned_data['periodo'],
                                              nivel=form.cleaned_data['nivel'] if form.cleaned_data['nivel'] else None,
                                              condicionado=form.cleaned_data['condicionado'],
                                              observaciones=form.cleaned_data['observaciones'],
                                              fechascorteposgrado=form.cleaned_data['cohorte'] if carrera.posgrado else None,
                                              orientacion=form.cleaned_data['orientacion'],
                                              examenubicacionidiomas=form.cleaned_data['examenubicacionidiomas'],
                                              intercambio=form.cleaned_data['intercambio'],
                                              alumnoantiguo=form.cleaned_data['alumnoantiguo'],
                                              personainscribio=request.session['persona'],
                                              fuente=form.cleaned_data['fuente'],
                                              becapromocional=form.cleaned_data['becapromocional'],
                                              fuentefinanciacion = form.cleaned_data['fuentefinanciacion'],
                                              otrofuentefinanciacion = form.cleaned_data['otrofuentefinanciacion'] if form.cleaned_data['otrofuentefinanciacion'] else '')
                    inscripcion.save(request)
                    if inscripcion.becapromocional=='1':
                        send_html_mail(subject="Beca Promocional.",
                                       html_template="emails/becapromocional.html",
                                       data={'inscripcion':inscripcion}, recipient_list=inscripcion.persona.lista_emails_correo(),
                                       recipient_list_cc=[inscripcion.persona.email])

                    if not puede_modificar_inscripcion_post(request, inscripcion):
                        transaction.set_rollback(True)
                        return bad_json(error=4)
                    if form.cleaned_data['colegio']:
                        estudio = EstudioPersona(persona=estudiante,
                                                 institucioneducacionbasica_id=int(form.cleaned_data['colegio']),
                                                 titulocolegio=form.cleaned_data['titulocolegio'],
                                                 especialidadeducacionbasica_id=form.cleaned_data['especialidad'])
                        estudio.save(request)
                    # SNNA
                    snna = estudiante.datos_snna()
                    snna.rindioexamen = form.cleaned_data['rindioexamen']
                    snna.fechaexamen = form.cleaned_data['fechaexamensnna']
                    snna.puntaje = form.cleaned_data['puntajesnna']
                    snna.save(request)
                    # DOCUMENTOS DE INSCRIPCION
                    documentos = inscripcion.documentos_entregados()
                    documentos.homologar = form.cleaned_data['homologar']
                    documentos.reconocimientointerno = form.cleaned_data['reconocimientointerno']
                    # documentos.titulo = form.cleaned_data['titulo']
                    # documentos.cedula = form.cleaned_data['reg_cedula']
                    # documentos.votacion = form.cleaned_data['votacion']
                    # documentos.fotos = form.cleaned_data['fotos']
                    # documentos.cert_med = form.cleaned_data['cert_med']
                    documentos.conveniohomologacion = form.cleaned_data['conveniohomologacion']
                    documentos.eshomologacionexterna = False
                    documentos.save(request)
                    # EXAMEN DE UBICACIÓN
                    if documentos.homologar == True or documentos.reconocimientointerno == True:
                        inscripcion.examenubicacionidiomas = False
                        inscripcion.save()
                    # INSCRIPCION FLAGS
                    flag = inscripcion.mis_flag()
                    flag.permitepagoparcial = True
                    flag.save()
                    # SEGUIMIENTO LABORAL
                    if form.cleaned_data['trabaja']:
                        trabajo = TrabajoPersona(persona=estudiante,
                                                 empresa=form.cleaned_data['empresa'],
                                                 ocupacion=form.cleaned_data['ocupacion'],
                                                 titulogrado=form.cleaned_data['titulogrado'],
                                                 universidadgrado=form.cleaned_data['universidadgrado'],
                                                 responsabilidades='',
                                                 personascargo=0,
                                                 ejerce=False,
                                                 fecha=form.cleaned_data['fecha_ingreso'])
                        trabajo.save(request)
                    # DATOS DE FACTURACION
                    clientefacturacion = inscripcion.clientefacturacion(request)
                    clientefacturacion.nombre = remover_tildes(form.cleaned_data['facturanombre'])
                    clientefacturacion.direccion = remover_tildes(form.cleaned_data['facturadireccion'])
                    clientefacturacion.identificacion = form.cleaned_data['facturaidentificacion']
                    clientefacturacion.telefono = remover_tildes(form.cleaned_data['facturatelefono'])
                    clientefacturacion.tipo = form.cleaned_data['facturatipoidentificacion']
                    clientefacturacion.email = form.cleaned_data['facturaemail']
                    clientefacturacion.save()
                    # PREGUNTAS
                    preguntasinscripcion = inscripcion.preguntas_inscripcion()
                    if form.cleaned_data['comoseinformo']:
                        preguntasinscripcion.comoseinformo = form.cleaned_data['comoseinformo']
                    if form.cleaned_data['razonesmotivaron']:
                        preguntasinscripcion.razonesmotivaron = form.cleaned_data['razonesmotivaron']
                    if form.cleaned_data['comoseinformootras']:
                        preguntasinscripcion.comoseinformootras = form.cleaned_data['comoseinformootras']
                    if form.cleaned_data['comoseinformoredsocial']:
                        preguntasinscripcion.comoseinformoredsocial = form.cleaned_data['comoseinformoredsocial']
                    preguntasinscripcion.save(request)
                    # PERFIL DE USUARIO
                    estudiante.crear_perfil(inscripcion=inscripcion)
                    perfil = estudiante.mi_perfil()
                    perfil.raza = form.cleaned_data['etnia']
                    perfil.nacionalidadindigena = form.cleaned_data['nacionalidadindigena']
                    perfil.tienediscapacidad = form.cleaned_data['tienediscapacidad']
                    perfil.tipodiscapacidad = form.cleaned_data['tipodiscapacidad']
                    perfil.porcientodiscapacidad = form.cleaned_data['porcientodiscapacidad']
                    perfil.carnetdiscapacidad = form.cleaned_data['carnetdiscapacidad']
                    perfil.save(request)
                    mocs = form.cleaned_data['mocs']
                    if int(coordinacion.id) == 22 or int(coordinacion.id) == 28 or int(coordinacion.id) == 23 or alumnoa == True or documentos.homologar == True:
                        #No Genera valores
                        True
                    else:
                        inscripcion.generar_rubro_inscripcion(form.cleaned_data['malla'])
                    inscripcion.mi_malla(form.cleaned_data['malla'])
                    inscripcion.mi_itinerario()
                    inscripcion.actualizar_nivel()
                    # REGISTRO TIPO DE INSCRIPCION
                    inscripcion.actualiza_tipo_inscripcion()
                    if inscripcion.mi_nivel().nivel_id == 1:
                        inscripcion.permitematriculacondeuda = True
                        inscripcion.save()

                    # ACEPTACION TERMINOS Y ACUERDOS SOBRE PRIVACIDAD DE DATOS
                    tipoacuer=TipoTerminosAcuerdos.objects.get(pk=1)
                    if not AceptacionTerminosAcuerdos.objects.filter(persona=estudiante,tipoacuerdo=tipoacuer):
                        terminos=AceptacionTerminosAcuerdos(persona=estudiante,
                                                            tipoacuerdo=tipoacuer,
                                                            fechaaceptacion=datetime.now())
                        terminos.save()
                        log(u'Inscrito acepta terminos y condiciones sobre privacidad de datos: %s' % inscripcion, request, "add")
                    tipoacuer2 = TipoTerminosAcuerdos.objects.get(pk=2)
                    if not AceptacionTerminosAcuerdos.objects.filter(persona=estudiante, tipoacuerdo=tipoacuer2):
                        terminos = AceptacionTerminosAcuerdos(persona=estudiante,
                                                              tipoacuerdo=tipoacuer2,
                                                              fechaaceptacion=datetime.now())
                        terminos.save()
                        log(u'Inscrito acepta no realizar homologaciones una vez matriculado en 1er semestre: %s' % inscripcion, request, "add")
                    log(u'Adiciono inscripcion: %s' % inscripcion, request, "add")
                    if len(estudiante.emailinst.strip()) <= 5:
                        estudiante.emailinst = generar_email(estudiante, estudiante=True)
                        estudiante.save(request)
                    return ok_json({"id": inscripcion.id})
                else:
                    return bad_json(mensaje=u'Completar la información de facturación por favor')
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'infoasignatura':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['iid'])
                malla = inscripcion.mi_malla()
                if malla.asignaturamalla_set.filter(asignatura__id=request.POST['id']).exists():
                    asignaturamalla = malla.asignaturamalla_set.filter(asignatura__id=request.POST['id'])[0]
                    return ok_json({'creditos': asignaturamalla.creditos, 'horas': asignaturamalla.horas})
                elif malla.modulomalla_set.filter(asignatura__id=request.POST['id']).exists():
                    modulomalla = malla.modulomalla_set.filter(asignatura__id=request.POST['id'])[0]
                    return ok_json({'creditos': modulomalla.creditos, 'horas': modulomalla.horas})
                else:
                    asignatura = Asignatura.objects.get(pk=request.POST['id'])
                    return ok_json({'creditos': 0, 'horas': 0})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'cambiodatoscarrera':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                estudiante = inscripcion.persona
                form = CambiaDatosCarreraForm(request.POST)
                if form.is_valid():
                    if inscripcion.tiene_matriculas():
                        return bad_json(mensaje=u'La Inscripcion ya contine Matricula')
                    inscripcion.sede = form.cleaned_data['sede']
                    inscripcion.coordinacion = form.cleaned_data['coordinacion']
                    inscripcion.carrera = form.cleaned_data['carrera']
                    inscripcion.modalidad = form.cleaned_data['modalidad']
                    inscripcion.periodo = form.cleaned_data['periodo']
                    inscripcion.sesion = form.cleaned_data['sesion']
                    inscripcion.save(request)
                    inscripcion.inscripcionmalla_set.all().delete()
                    inscripcionmalla = InscripcionMalla(inscripcion=inscripcion, malla=form.cleaned_data['malla'])
                    inscripcionmalla.save()
                    inscripcion.mi_itinerario()
                    inscripcion.actualizar_nivel()
                    inscripcion.generar_rubro_inscripcion(form.cleaned_data['malla'])
                    log(u'Modifico de Datos de Carrera: %s' % inscripcion, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'adicionarotracarrera':
            try:
                form = NuevaInscripcionForm(request.POST)
                if form.is_valid():
                    inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                    sede = form.cleaned_data['sede']
                    coordinacion = form.cleaned_data['coordinacion']
                    if coordinacion.id == 28:
                        carrera = Carrera.objects.get(pk=55)
                        sesion = Sesion.objects.get(pk=1)
                        modalidad = Modalidad.objects.get(pk=4)
                        malla = Malla.objects.get(pk=191)
                    else:
                        carrera = form.cleaned_data['carrera']
                        sesion = form.cleaned_data['sesion']
                        modalidad = form.cleaned_data['modalidad']
                        malla = form.cleaned_data['malla']
                    mocs = form.cleaned_data['mocs']
                    alumnoa = form.cleaned_data['alumnoantiguo']
                    reconocimientointerno = form.cleaned_data['reconocimientointerno']
                    if int(coordinacion.id) == 22 or int(coordinacion.id) == 28 or int(coordinacion.id) == 23 or alumnoa == True or reconocimientointerno == True:
                        True
                    else:
                        if carrera.precio_modulo_inscripcion_carrera(form.cleaned_data['periodo'], sede,modalidad, carrera,malla):
                            costo_periodo = carrera.precio_modulo_inscripcion_carrera(form.cleaned_data['periodo'], sede,modalidad, carrera,malla)
                        else:
                            return bad_json(mensaje=u"El Periodo, modalidad, carrera y malla que esta seleccionando NO TIENE ASIGNADO VALORES. Favor comunicarse con el Depto. Financiero")

                        if persona.id in PERSONA_ADMINS_ACADEMICO_ID:
                            if alumnoa:
                                if costo_periodo is not None:
                                    if not mocs:
                                        if not costo_periodo.sininscripcion:
                                            if costo_periodo.precioinscripcion <= 0:
                                                return bad_json(mensaje=u"El Periodo, modalidad, carrera y malla que esta seleccionando no tiene asignado un VALOR DE INSCRIPCION. Favor comunicarse con el Depto. Financiero")
                        else:
                            if not mocs:
                                if not costo_periodo.sininscripcion:
                                    if costo_periodo.precioinscripcion <= 0:
                                        return bad_json(mensaje=u"El Periodo, modalidad, carrera y malla que esta seleccionando no tiene asignado un VALOR DE INSCRIPCION. Favor comunicarse con el Depto. Financiero")
                    nuevainscripcion = Inscripcion(persona=inscripcion.persona,
                                                   fecha=datetime.now().date(),
                                                   hora=datetime.now().time(),
                                                   fechainiciocarrera=form.cleaned_data['fechainiciocarrera'],
                                                   periodo=form.cleaned_data['periodo'],
                                                   carrera=carrera,
                                                   modalidad=modalidad,
                                                   sesion=sesion,
                                                   sede=sede,
                                                   centroinformacion=inscripcion.centroinformacion,
                                                   coordinacion=coordinacion,
                                                   mocs=form.cleaned_data['mocs'],
                                                   fechascorteposgrado=form.cleaned_data['cohorte'],
                                                   personainscribio=request.session['persona'] ,
                                                   condicionado=form.cleaned_data['condicionado'])
                    nuevainscripcion.save(request)
                    nuevainscripcion.mi_malla(form.cleaned_data['malla'])
                    nuevainscripcion.mi_itinerario()
                    nuevainscripcion.actualiza_fecha_inicio_carrera()
                    if not puede_modificar_inscripcion_post(request, nuevainscripcion):
                        transaction.set_rollback(True)
                        return bad_json(error=4)
                    inscripcion.persona.crear_perfil(inscripcion=nuevainscripcion)
                    for documento in inscripcion.archivodocumentoinscripcion_set.all():
                        documenton = ArchivoDocumentoInscripcion(inscripcion=nuevainscripcion,
                                                                 fecha=datetime.now(),
                                                                 tipodocumentoinscripcion=documento.tipodocumentoinscripcion,
                                                                 archivo=documento.archivo,
                                                                 observaciones=documento.observaciones)
                        documenton.save(request)
                    if form.cleaned_data['copiarecord']:
                        for record in inscripcion.recordacademico_set.all():
                            asignaturamodulo = None
                            asignaturamalla = None
                            asignaturamodulo = nuevainscripcion.asignatura_en_modulomalla(record.asignatura)
                            asignaturamalla = nuevainscripcion.asignatura_en_asignaturamalla(record.asignatura)
                            if asignaturamalla:
                                validacreditos = asignaturamalla.validacreditos
                                validapromedio = asignaturamalla.validapromedio
                                creditos = asignaturamalla.creditos
                                horas = asignaturamalla.horas
                            elif asignaturamodulo:
                                validacreditos = asignaturamodulo.validacreditos
                                validapromedio = asignaturamodulo.validapromedio
                                creditos = asignaturamodulo.creditos
                                horas = asignaturamodulo.horas
                            else:
                                validacreditos = record.validacreditos
                                validapromedio = record.validapromedio
                                creditos = record.creditos
                                horas = record.horas
                            nuevorecord = RecordAcademico(inscripcion=nuevainscripcion,
                                                          asignatura=record.asignatura,
                                                          nota=record.nota,
                                                          asistencia=record.asistencia,
                                                          fecha=record.fecha,
                                                          noaplica=record.noaplica,
                                                          convalidacion=False,
                                                          homologada=True if record.aprobada else False,
                                                          aprobada=record.aprobada,
                                                          pendiente=record.pendiente,
                                                          creditos=creditos,
                                                          horas=horas,
                                                          validacreditos=validacreditos,
                                                          validapromedio=validapromedio,
                                                          observaciones=record.observaciones)
                            nuevorecord.save(request)
                            nuevorecord.actualizar()
                        nuevainscripcion.save(request)
                        # PREGUNTAS EN INSCRIPCION
                    minivel = nuevainscripcion.mi_nivel()
                    if form.cleaned_data['prenivelacion']:
                        nuevainscripcion.nivelhomologado = form.cleaned_data['nivelmalla']
                        nuevainscripcion.save(request)
                    nuevainscripcion.actualizar_nivel()
                    nuevainscripcion.actualiza_tipo_inscripcion()
                    # DOCUMENTOS ENTREGADOS
                    documentos = nuevainscripcion.documentos_entregados()
                    documentos.pre = form.cleaned_data['prenivelacion']
                    documentos.observaciones_pre = form.cleaned_data['observacionespre']
                    documentos.reingreso = form.cleaned_data['reingreso']
                    documentos.homologar = form.cleaned_data['homologar']
                    documentos.reconocimientointerno = form.cleaned_data['reconocimientointerno']
                    documentos.save(request)
                    nuevainscripcion.actualizar_nivel()
                    reconocimientointerno = form.cleaned_data['reconocimientointerno']


                    # Lógica combinada según tu requerimiento
                    if nuevainscripcion.carrera.posgrado and inscripcion.carrera.posgrado and documentos.reingreso:
                        crear_homologacion = True
                    elif documentos.reconocimientointerno:
                        crear_homologacion = True
                    else:
                        crear_homologacion = False

                    if crear_homologacion:
                        if not PreHomologacionInscripcionInformacion.objects.filter(inscripcion=nuevainscripcion).exists():
                            homologacion = PreHomologacionInscripcionInformacion(inscripcion=nuevainscripcion,
                                                                                 periodo=nuevainscripcion.periodo,
                                                                                 fecha=datetime.now().date(),
                                                                                 tipohomo=4)
                            homologacion.save()
                            if Inscripcion.objects.filter(pk=int(request.POST['id']), habilitadomatricula=True):
                                Inscripcion.objects.filter(pk=int(request.POST['id'])).update(habilitadomatricula=False)
                                if DocumentosDeInscripcion.objects.filter(inscripcion_id=int(request.POST['id']), homologar=True):
                                    DocumentosDeInscripcion.objects.filter(inscripcion_id=int(request.POST['id']), homologar=True).update(homologar=True)
                            Inscripcion.objects.filter(pk=nuevainscripcion.id).update(habilitadomatricula=True)
                            log(u'Adiciono registro homologacion tipo RECONOCIMIENTO INTERNO desde cambio de carrera %s' % homologacion.inscripcion, request, "add")
                    if int(coordinacion.id) == 22 or int(coordinacion.id) == 28 or int(coordinacion.id) == 23 or alumnoa == True or reconocimientointerno == True:
                        True
                    else:
                        nuevainscripcion.generar_rubro_inscripcion(form.cleaned_data['malla'])
                    # SNNA
                    snna = inscripcion.persona.datos_snna()
                    snna.rindioexamen = form.cleaned_data['rindioexamen']
                    snna.fechaexamen = form.cleaned_data['fechaexamensnna']
                    snna.puntaje = form.cleaned_data['puntajesnna']
                    snna.save(request)
                    if not inscripcion.persona.emailinst:
                        inscripcion.persona.emailinst = generar_email(inscripcion.persona, estudiante=True)
                        inscripcion.persona.save()
                    log(u'Adiciono inscripcion desde otra carrera: %s' % inscripcion, request, "add")
                    return ok_json({"id": nuevainscripcion.id})
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'predecesora':
            try:
                asignaturamalla = AsignaturaMalla.objects.get(pk=request.POST['id'])
                lista = []
                for predecesora in asignaturamalla.asignaturamallapredecesora_set.all():
                    lista.append([predecesora.predecesora.asignatura.nombre, predecesora.predecesora.nivelmalla.nombre])
                return ok_json({"lista": lista})
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'edit':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                per = request.session['persona']
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                estudiante = inscripcion.persona
                form = InscripcionForm(request.POST)
                if form.is_valid():
                    cedula = form.cleaned_data['cedula'].strip()
                    pasaporte = form.cleaned_data['pasaporte'].strip()
                    nacimiento = form.cleaned_data['nacimiento']
                    if not cedula and not pasaporte:
                        return bad_json(mensaje=u"Debe ingresar una identificación.")
                    if cedula:
                        if Persona.objects.filter(cedula=cedula).exclude(id=estudiante.id).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if pasaporte:
                        if Persona.objects.filter(pasaporte=pasaporte).exclude(id=estudiante.id).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if nacimiento:
                        hoy = datetime.now().date()
                        fechavalida = hoy.year - 16
                        if (nacimiento.year) > fechavalida:
                            return bad_json(mensaje=u"La fecha de nacimiento no es válida.")
                    estudiante.nombre1 = remover_tildes(form.cleaned_data['nombre1'])
                    estudiante.nombre2 = remover_tildes(form.cleaned_data['nombre2'])
                    estudiante.apellido1 = remover_tildes(form.cleaned_data['apellido1'])
                    estudiante.apellido2 = remover_tildes(form.cleaned_data['apellido2'])
                    estudiante.cedula = remover_tildes(form.cleaned_data['cedula'])
                    estudiante.pasaporte = form.cleaned_data['pasaporte']
                    estudiante.nacimiento = form.cleaned_data['nacimiento']
                    estudiante.nacionalidad = form.cleaned_data['nacionalidad']
                    estudiante.paisnac = form.cleaned_data['paisnac']
                    estudiante.provincianac = form.cleaned_data['provincianac']
                    estudiante.cantonnac = form.cleaned_data['cantonnac']
                    estudiante.parroquianac = form.cleaned_data['parroquianac']
                    estudiante.sexo = form.cleaned_data['sexo']
                    estudiante.pais = form.cleaned_data['pais']
                    estudiante.provincia = form.cleaned_data['provincia']
                    estudiante.canton = form.cleaned_data['canton']
                    estudiante.parroquia = form.cleaned_data['parroquia']
                    estudiante.sector = form.cleaned_data['sector']
                    estudiante.ubicacionresidenciasalesforce = form.cleaned_data['ubicacionresidenciasalesforce']
                    estudiante.otraubicacionsalesforce = form.cleaned_data['otraubicacionsalesforce']
                    estudiante.nombrecompletomadre = form.cleaned_data['nombrescompletosmadre']
                    estudiante.nombrecompletopadre = form.cleaned_data['nombrescompletospadre']
                    estudiante.direccion = remover_tildes(form.cleaned_data['direccion'])
                    estudiante.direccion2 = remover_tildes(form.cleaned_data['direccion2'])
                    estudiante.num_direccion = remover_tildes(form.cleaned_data['num_direccion'])
                    estudiante.telefono = form.cleaned_data['telefono']
                    estudiante.telefono_conv = form.cleaned_data['telefono_conv']
                    estudiante.email = form.cleaned_data['email']
                    estudiante.emailinst = form.cleaned_data['emailinst']
                    estudiante.sangre = form.cleaned_data['sangre']
                    estudiante.save(request)
                    # DATOS DE LA INSCRIPCION
                    if not inscripcion.matriculado() and not inscripcion.graduado() and not inscripcion.egresado():
                        inscripcion.sesion = form.cleaned_data['sesion']
                    if per.usuario.id in PERSONA_ADMINS_ACADEMICO_ID:
                        inscripcion.centroinformacion = form.cleaned_data['centroinformacion']
                    inscripcion.identificador = form.cleaned_data['identificador']
                    inscripcion.observaciones = form.cleaned_data['observaciones']
                    inscripcion.fechascorteposgrado = form.cleaned_data['cohorte']
                    inscripcion.orientacion = form.cleaned_data['orientacion']
                    inscripcion.intercambio = form.cleaned_data['intercambio']
                    inscripcion.alumnoantiguo = form.cleaned_data['alumnoantiguo']
                    inscripcion.fuente = form.cleaned_data['fuente']
                    inscripcion.becapromocional=form.cleaned_data['becapromocional']
                    # DATOS DE INICIO Y FIN DE CARRERA
                    malla = inscripcion.mi_malla()
                    minivel = inscripcion.mi_nivel().nivel.id
                    mallaniveles = malla.nivelesregulares
                    if form.cleaned_data['fechainiciocarrera']:
                        inscripcion.fechainiciocarrera = form.cleaned_data['fechainiciocarrera']
                    inscripcion.save(request)
                    inscripcion.actualiza_fecha_inicio_carrera()
                    # SNNA
                    snna = estudiante.datos_snna()
                    snna.rindioexamen = form.cleaned_data['rindioexamen']
                    snna.fechaexamen = form.cleaned_data['fechaexamensnna']
                    snna.puntaje = form.cleaned_data['puntajesnna']
                    snna.save(request)
                    # ACTUALIZA LAS PREGUNTAS DE INSCRIPCION
                    preguntas = inscripcion.preguntas_inscripcion()
                    preguntas.comoseinformo = form.cleaned_data['comoseinformo']
                    preguntas.razonesmotivaron = form.cleaned_data['razonesmotivaron']
                    preguntas.comoseinformootras = form.cleaned_data['comoseinformootras']
                    preguntas.comoseinformoredsocial = form.cleaned_data['comoseinformoredsocial']
                    preguntas.save(request)
                    # DOCUMENTOS
                    documentos = inscripcion.documentos_entregados()
                    # documentos.titulo = form.cleaned_data['titulo']
                    # documentos.cedula = form.cleaned_data['reg_cedula']
                    # documentos.votacion = form.cleaned_data['votacion']
                    # documentos.fotos = form.cleaned_data['fotos']
                    # documentos.cert_med = form.cleaned_data['cert_med']
                    documentos.conveniohomologacion = form.cleaned_data['conveniohomologacion']
                    documentos.save(request)
                    # EXAMEN DE UBICACIÓN
                    if documentos.homologar == True:
                        inscripcion.examenubicacionidiomas = False
                        inscripcion.save()
                    if documentos.homologar:
                        if inscripcion.registrofechapreinscripcion_set.exists():
                            registro = inscripcion.registrofechapreinscripcion_set.all()[0]
                            registro.homologar = True
                            registro.save()
                    inscripcion.actualizar_homologacion()
                    perfil = inscripcion.persona.mi_perfil()
                    perfil.raza = form.cleaned_data['etnia']
                    perfil.nacionalidadindigena = form.cleaned_data['nacionalidadindigena']
                    perfil.tienediscapacidad = form.cleaned_data['tienediscapacidad']
                    perfil.tipodiscapacidad = form.cleaned_data['tipodiscapacidad']
                    perfil.porcientodiscapacidad = form.cleaned_data['porcientodiscapacidad']
                    perfil.carnetdiscapacidad = form.cleaned_data['carnetdiscapacidad']
                    perfil.save(request)
                    # DATOS DE FACTURACION
                    clientefacturacion = inscripcion.clientefacturacion(request)
                    clientefacturacion.nombre = form.cleaned_data['facturanombre']
                    clientefacturacion.direccion = form.cleaned_data['facturadireccion']
                    clientefacturacion.identificacion = form.cleaned_data['facturaidentificacion']
                    clientefacturacion.telefono = form.cleaned_data['facturatelefono']
                    clientefacturacion.tipo = form.cleaned_data['facturatipoidentificacion']
                    clientefacturacion.email = form.cleaned_data['facturaemail']
                    clientefacturacion.save()
                    # OTRAS ACCIONES
                    inscripcion.actualizar_nivel()
                    proceso_inscripcion = inscripcion.mi_preinscripcion()
                    if proceso_inscripcion:
                        proceso_inscripcion.save(request)
                    log(u'Modifico de inscripcion: %s' % inscripcion, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'tipotrabajotitulacion':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = TipoTitulacionForm(request.POST)
                if form.is_valid():
                    inscripcion.tipotrabajotitulacion = form.cleaned_data['tipotrabajotitulacion']
                    if inscripcion.malla_nueva():
                        if inscripcion.carrera.posgrado or inscripcion.carrera.id in [CARRERA_ENFERMERIA_ID, CARRERA_MEDICINA_ID, CARRERA_ODONTOLOGIA_ID]:
                            inscripcion.save(request)
                            log(u'Modifico de inscripcion tipo trabajo titulacion: %s' % inscripcion, request, "edit")
                            return ok_json()
                        else:
                            if inscripcion.matriculado_periodo(request.session['periodo']):
                                if inscripcion.generar_rubro_titulacion(request.session['periodo']):
                                    inscripcion.save(request)
                                    log(u'Modifico de inscripcion tipo trabajo titulacion creo valores: %s' % inscripcion, request, "edit")
                                    return ok_json()
                                else:
                                    return bad_json(mensaje=u"No existe valores para titulación en este periodo %s, favor comunicarse con el Depto. financiero." % request.session['periodo'])
                            else:
                                return bad_json(mensaje=u"El alumno no esta matriculado en el periodo %s." % request.session['periodo'])
                    else:
                        inscripcion.save(request)
                        log(u'Modifico de inscripcion tipo trabajo titulacion: %s' % inscripcion, request, "edit")
                        return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'notatrabajotitulacion':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = NotaTrabajoTitulacionForm(request.POST)
                if form.is_valid():
                    inscripcion.notatitulacion = form.cleaned_data['nota']
                    inscripcion.save(request)
                    log(u'Modifico de inscripcion la nota de titulacion: %s' % inscripcion, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'idsalesforce':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                form = SalesForceSolicitudIdForm(request.POST)
                if form.is_valid():
                    if Inscripcion.objects.filter(idsalesforcei=form.cleaned_data['nombre']).exists():
                        return bad_json(mensaje=u'Ya existe ese id de inscripcion')
                    inscripcion.idsalesforcei = form.cleaned_data['nombre']
                    inscripcion.save(request)
                    log(u'Modifico de inscripcion el id de salesforce: %s' % inscripcion, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'darperiodo':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                form = PeriodoInscripcionForm(request.POST)
                if form.is_valid():
                    inscripcion.periodo = form.cleaned_data['periodo']
                    inscripcion.save(request)
                    log(u'Asigno periodo a inscripcion: %s - %s' % (inscripcion,inscripcion.periodo), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cambioperiodohomologacion':
            try:
                documentos = DocumentosDeInscripcion.objects.get(pk=request.POST['id'])
                form = PeriodoInscripcionForm(request.POST)
                if form.is_valid():
                    documentos.periodo_homologacion = form.cleaned_data['periodo']
                    documentos.save(request)
                    log(u'Asigno periodo a la homologacion : %s - %s' % (documentos.inscripcion,documentos.inscripcion.periodo), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'novalidar':
            try:
                record = RecordAcademico.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, record.inscripcion):
                    return bad_json(error=8)
                form = ConsiderarForm(request.POST)
                if form.is_valid():
                    motivo = form.cleaned_data['motivo']
                    record.validacreditos = False
                    record.save(request)
                    historico = record.mi_historico()
                    historico.validacreditos = record.validacreditos
                    historico.save(request)
                    historico.inscripcion.save(request)
                    log(u'No considerar creditos: %s - %s - %s' % (record.inscripcion, record, motivo), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'validar':
            try:
                record = RecordAcademico.objects.get(pk=request.POST['id'])
                form = ConsiderarForm(request.POST)
                if form.is_valid():
                    motivo = form.cleaned_data['motivo']
                    record.validacreditos = True
                    record.save(request)
                    historico = record.mi_historico()
                    historico.validacreditos = record.validacreditos
                    historico.save(request)
                    historico.inscripcion.save(request)
                    log(u'Considerar creditos: %s - %s - %s' % (record.inscripcion, record, motivo), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'novalidarpromedio':
            try:
                record = RecordAcademico.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, record.inscripcion):
                    return bad_json(error=8)
                form = ConsiderarForm(request.POST)
                if form.is_valid():
                    motivo = form.cleaned_data['motivo']
                    record.validapromedio = False
                    record.save(request)
                    historico = record.mi_historico()
                    historico.validapromedio = record.validapromedio
                    historico.save(request)
                    historico.inscripcion.save(request)
                    log(u'No considerar promedio: %s - %s - %s' % (record.inscripcion, record, motivo), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'validarpromedio':
            try:
                record = RecordAcademico.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, record.inscripcion):
                    return bad_json(error=8)
                form = ConsiderarForm(request.POST)
                if form.is_valid():
                    motivo = form.cleaned_data['motivo']
                    record.validapromedio = True
                    record.save(request)
                    historico = record.mi_historico()
                    historico.validapromedio = record.validapromedio
                    historico.save(request)
                    historico.inscripcion.save(request)
                    log(u'Considerar promedio: %s - %s - %s' % (record.inscripcion, record, motivo), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'adddocumento':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['inscripcion'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = DocumentoInscripcionForm(request.POST, request.FILES)
                if form.is_valid():
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("documentos_", nfile._name)
                    archivo = ArchivoDocumentoInscripcion(tipodocumentoinscripcion=form.cleaned_data['tipo'],
                                                          observaciones=form.cleaned_data['observaciones'],
                                                          fecha=datetime.now(),
                                                          archivo=nfile,
                                                          inscripcion=inscripcion)
                    archivo.save()
                    log(u'Adiciono documento de inscripcion: %s - %s' % (inscripcion, archivo), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addobservacioncertificadonoadeuda':
            try:
                form = ObservacionCertificadoNoAdeudarForm(request.POST)
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    observacion = ObservacionCertificadoNoAdeudar(
                        inscripcion = inscripcion,
                        tipo = request.POST['op'],
                        encargado = persona,
                        observacion = form.cleaned_data['nombre']
                    )
                    observacion.save()
                    log(u'Adiciono observacion: %s - %s ' % (inscripcion,observacion.observacion ), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editdocumento':
            try:
                documento = ArchivoDocumentoInscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, documento.inscripcion):
                    return bad_json(error=8)
                form = DocumentoInscripcionForm(request.POST, request.FILES)
                if form.is_valid():
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("documentos_", nfile._name)
                        documento.archivo = nfile
                    documento.tipodocumentoinscripcion = form.cleaned_data['tipo']
                    documento.observaciones = form.cleaned_data['observaciones']
                    documento.fecha = datetime.now()
                    documento.save()
                    log(u'Modifico documento de inscripcion: %s - %s' % (documento.inscripcion, documento), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editmovilidad':
            try:
                movilidad = MovilidadInscripcion.objects.get(pk=request.POST['id'])
                form = RegistroMovilidadForm(request.POST)
                if form.is_valid():
                    movilidad.periodo = form.cleaned_data['periodo']
                    movilidad.inscripcion = form.cleaned_data['inscripcion']
                    movilidad.instituto = form.cleaned_data['instituto']
                    movilidad.tipomovilidad = form.cleaned_data['tipomovilidad']
                    movilidad.homologacion = form.cleaned_data['homologacion']
                    movilidad.asignaturas = form.cleaned_data['asignaturas']
                    movilidad.tipomovilidadacademica = form.cleaned_data['tipomovilidadacademica']
                    movilidad.save()
                    log(u'Modifico informacion movilidad: %s ' % movilidad.inscripcion, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addestudio':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = EstudioEducacionBasicaForm(request.POST)
                if form.is_valid():
                    estudio = EstudioPersona(persona=inscripcion.persona,
                                             institucioneducacionbasica_id=int(form.cleaned_data['colegio']),
                                             abanderado=int(form.cleaned_data['abanderado']),
                                             titulocolegio=form.cleaned_data['titulocolegio'],
                                             especialidadeducacionbasica_id=form.cleaned_data['especialidad'])
                    estudio.save(request)
                    log(u'Adiciono estudios basicos: %s' % inscripcion.persona, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editestudio':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                estudio = EstudioPersona.objects.get(pk=request.POST['id'])
                form = EstudioEducacionBasicaForm(request.POST)
                if form.is_valid():
                    estudio.institucioneducacionbasica_id = form.cleaned_data['colegio']
                    estudio.especialidadeducacionbasica_id = form.cleaned_data['especialidad']
                    estudio.titulocolegio = form.cleaned_data['titulocolegio']
                    estudio.abanderado = form.cleaned_data['abanderado']
                    estudio.save(request)
                    log(u"Modifico estudio: %s" % estudio.persona, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addestudiosuperior':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = EstudioEducacionSuperiorForm(request.POST)
                if form.is_valid():
                    estudio = EstudioPersona(persona=inscripcion.persona,
                                             superior=True,
                                             institucioneducacionsuperior_id=form.cleaned_data['institucion'],
                                             carrera=form.cleaned_data['carrera'],
                                             niveltitulacion=form.cleaned_data['niveltitulacion'],
                                             detalleniveltitulacion=form.cleaned_data['detalleniveltitulacion'],
                                             titulo=form.cleaned_data['titulo'],
                                             aliastitulo=form.cleaned_data['aliastitulo'],
                                             fechainicio=form.cleaned_data['fechainicio'],
                                             fechafin=form.cleaned_data['fechafin'],
                                             fecharegistro = form.cleaned_data['fecharegistro'],
                                             fechagraduacion=form.cleaned_data['fechagraduacion'],
                                             registro=form.cleaned_data['registro'],
                                             cursando=form.cleaned_data['cursando'],
                                             cicloactual=form.cleaned_data['cicloactual'],
                                             aplicabeca=form.cleaned_data['aplicabeca'],
                                             tipobeca=form.cleaned_data['tipobeca'],
                                             montobeca=form.cleaned_data['montobeca'],
                                             tipofinanciamientobeca=form.cleaned_data['tipofinanciamientobeca'])
                    estudio.save(request)
                    log(u'Adiciono estudio superior: %s' % inscripcion.persona, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addtrabajo':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = TrabajoPersonaForm(request.POST)
                if form.is_valid():
                    laborando = form.cleaned_data['labora']
                    if laborando:
                        if form.cleaned_data['fecha'] > datetime.now().date():
                            return bad_json(mensaje=u'Fecha incorrecta.')
                    else:
                        if form.cleaned_data['fecha'] > datetime.now().date() or form.cleaned_data['fechafin'] > datetime.now().date() or form.cleaned_data['fecha'] > form.cleaned_data['fechafin']:
                            return bad_json(mensaje=u'Fecha incorrecta.')
                    seguimiento = TrabajoPersona(persona=inscripcion.persona,
                                                 empresa=form.cleaned_data['empresa'],
                                                 industria=form.cleaned_data['industria'],
                                                 tipocontrato=form.cleaned_data['tipocontrato'],
                                                 afiliacioniess=form.cleaned_data['afiliacioniess'],
                                                 cargo=form.cleaned_data['cargo'],
                                                 ocupacion=form.cleaned_data['ocupacion'],
                                                 responsabilidades=form.cleaned_data['responsabilidades'],
                                                 telefono=form.cleaned_data['telefono'],
                                                 email=form.cleaned_data['email'],
                                                 sueldo=form.cleaned_data['sueldo'],
                                                 fecha=form.cleaned_data['fecha'],
                                                 fechafin=form.cleaned_data['fechafin'])
                    seguimiento.save(request)
                    inscripcion.persona.actualiza_situacion_laboral()
                    log(u"Adiciono seguimiento estudiante: %s" % inscripcion.persona, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edittrabajo':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                trabajo = TrabajoPersona.objects.get(pk=request.POST['id'])
                form = TrabajoPersonaForm(request.POST)
                if form.is_valid():
                    laborando = form.cleaned_data['labora']
                    if laborando:
                        if form.cleaned_data['fecha'] > datetime.now().date():
                            return bad_json(mensaje=u'Fecha incorrecta.')
                    else:
                        if form.cleaned_data['fecha'] > datetime.now().date() or form.cleaned_data['fechafin'] > datetime.now().date() or form.cleaned_data['fecha'] > form.cleaned_data['fechafin']:
                            return bad_json(mensaje=u'Fecha incorrecta.')
                    trabajo.empresa = form.cleaned_data['empresa']
                    trabajo.industria = form.cleaned_data['industria']
                    trabajo.tipocontrato = form.cleaned_data['tipocontrato']
                    trabajo.afiliacioniess = form.cleaned_data['afiliacioniess']
                    trabajo.cargo = form.cleaned_data['cargo']
                    trabajo.ocupacion = form.cleaned_data['ocupacion']
                    trabajo.responsabilidades = form.cleaned_data['responsabilidades']
                    trabajo.telefono = form.cleaned_data['telefono']
                    trabajo.email = form.cleaned_data['email']
                    trabajo.sueldo = form.cleaned_data['sueldo']
                    trabajo.fecha = form.cleaned_data['fecha']
                    trabajo.fechafin = form.cleaned_data['fechafin'] if not form.cleaned_data['labora'] else None
                    trabajo.save(request)
                    trabajo.persona.actualiza_situacion_laboral()
                    log(u'Modifico seguimiento laboral: %s' % trabajo.persona, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'acualizasituacionlaboral':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                fichasocioeconomica = inscripcion.persona.mi_ficha()
                fichasocioeconomica.situacionlaboral = int(request.POST['valor'])
                fichasocioeconomica.save(request)
                inscripcion.persona.actualiza_situacion_laboral()
                fichasocioeconomica = inscripcion.persona.mi_ficha()
                log(u'Modifico situacion laboral: %s' % fichasocioeconomica.persona, request, "edit")
                return ok_json(data={'ide': fichasocioeconomica.situacionlaboral})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'deltrabajo':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                trabajo = TrabajoPersona.objects.get(pk=request.POST['id'])
                log(u'Elimino seguimiento laboral: %s' % trabajo.persona, request, "del")
                trabajo.delete()
                trabajo.persona.actualiza_situacion_laboral()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'editestudiosuperior':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                estudio = EstudioPersona.objects.get(pk=request.POST['id'])
                form = EstudioEducacionSuperiorForm(request.POST)
                if form.is_valid():
                    estudio.institucioneducacionsuperior_id = form.cleaned_data['institucion']
                    estudio.niveltitulacion = form.cleaned_data['niveltitulacion']
                    estudio.detalleniveltitulacion = form.cleaned_data['detalleniveltitulacion']
                    estudio.carrera = form.cleaned_data['carrera']
                    estudio.titulo = form.cleaned_data['titulo']
                    estudio.aliastitulo = form.cleaned_data['aliastitulo']
                    estudio.fechainicio = form.cleaned_data['fechainicio']
                    estudio.fechafin = form.cleaned_data['fechafin']
                    estudio.fechagraduacion = form.cleaned_data['fechagraduacion']
                    estudio.fecharegistro = form.cleaned_data['fecharegistro']
                    estudio.cursando = form.cleaned_data['cursando']
                    estudio.cicloactual = form.cleaned_data['cicloactual']
                    estudio.registro = form.cleaned_data['registro']
                    estudio.aplicabeca = form.cleaned_data['aplicabeca']
                    estudio.tipobeca = form.cleaned_data['tipobeca']
                    estudio.montobeca = form.cleaned_data['montobeca']
                    estudio.tipofinanciamientobeca = form.cleaned_data['tipofinanciamientobeca']
                    estudio.save(request)
                    log(u"Modifico estudio superior: %s" % estudio.persona, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delestudio':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                estudio = EstudioPersona.objects.get(pk=request.POST['id'])
                log(u'Elimino estudio: %s' % estudio.persona, request, "del")
                estudio.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delexamen':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                examen = ExamenInscripcion.objects.get(pk=request.POST['id'])
                log(u'Elimino examen: %s' % examen.inscripcion.persona, request, "del")
                examen.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delentrevista':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                entrevista = InscripcionEntrevista.objects.get(pk=request.POST['id'])
                log(u'Elimino examen: %s' % entrevista.inscripcion.persona, request, "del")
                entrevista.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'addidioma':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = IdiomaDominaForm(request.POST)
                if form.is_valid():
                    if IdiomaDomina.objects.filter(persona=inscripcion.persona, idioma=form.cleaned_data['idioma']).exists():
                        return bad_json(mensaje=u'Ya existe un registro de este idioma.')
                    idioma = IdiomaDomina(persona=inscripcion.persona,
                                          idioma=form.cleaned_data['idioma'],
                                          lectura=form.cleaned_data['lectura'],
                                          escritura=form.cleaned_data['escritura'],
                                          oral=form.cleaned_data['oral'])
                    idioma.save(request)
                    log(u'Adiciono idioma que domina: %s' % inscripcion, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addentrevista':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                form = EntrevistaInscripcionForm(request.POST)
                if form.is_valid():
                    if InscripcionEntrevista.objects.filter(Q(respuestaentrevista__isnull=True) | Q(respuestaentrevista__confirmada=False), inscripcion=inscripcion).exists():
                        return bad_json(mensaje=u'Tiene una entrevista pendiente de responder')
                    entrevista = InscripcionEntrevista(inscripcion=inscripcion,
                                                       entrevista=form.cleaned_data['entrevista'])
                    entrevista.save(request)
                    log(u'Adiciono entrevista inscripcion: %s' % entrevista, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addexamen':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                # if not puede_modificar_inscripcion_post(request, inscripcion):
                #     return bad_json(error=8)
                form = ExamenInscripcionForm(request.POST)
                if form.is_valid():
                    if ExamenInscripcion.objects.filter(respuestaexamenadmision__isnull=True, inscripcion=inscripcion).exclude(inscripcion__carrera__id__in=[63,64,119]).exists():
                        return bad_json(mensaje=u'Tiene un exámen pendiente de responder')
                    if ExamenInscripcion.objects.filter(respuestaexamenadmision__isnull=False, respuestaexamenadmision__fecha__isnull=True, inscripcion=inscripcion).exists():
                        return bad_json(mensaje=u'Tiene un exámen pendiente de responder')
                    if ExamenInscripcion.objects.filter(respuestaexamenadmision__isnull=False, respuestaexamenadmision__fecha__isnull=False, respuestaexamenadmision__finalizado=False, inscripcion=inscripcion).exists():
                        return bad_json(mensaje=u'Tiene un exámen pendiente de responder')
                    examen = ExamenInscripcion(inscripcion=inscripcion,
                                               examenadmision=form.cleaned_data['examenadmision'],
                                               fecha=form.cleaned_data['fecha'],
                                               hora=form.cleaned_data['hora'],
                                               aula=form.cleaned_data['aula'])
                    examen.save(request)
                    inscripcion.habilitadoexamen = True
                    inscripcion.save(request)
                    try:
                        if examen.inscripcion.idsalesforcei:
                            idins = inscripcion.idsalesforcei
                            fecha = str(examen.fecha)
                            hora = str(examen.hora)
                            api_token_sf2.enviar_datos_examen(idins,fecha,hora)
                        if examen.inscripcion.idsalesforcei:
                            if inscripcion.modalidad.id == 3 or inscripcion.modalidad.id == 4:
                                api_token_sf2.enviar_examen_aptitud(inscripcion.idsalesforcei, 7, 0, 'Aprobado')
                    except Exception as ex:
                        print(ex)
                        pass
                    log(u'Adiciono examen inscripcion: %s - %s - %s' % (inscripcion,examen.fecha,examen.hora), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addexameni':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = ExamenIndividualForm(request.POST)
                if form.is_valid():
                    if ExamenInscripcion.objects.filter(respuestaexamenadmision__isnull=True, inscripcion=inscripcion).exists():
                        return bad_json(mensaje=u'Tiene un exámen pendiente de responder')
                    examen = ExamenAdmision(nombre=u'EXÁMEN DE ADMISIÓN INDIVIDUAL',
                                            tiempomaximo=form.cleaned_data['tiempomaximo'],
                                            maximo=form.cleaned_data['maximo'],
                                            minimoaplica=form.cleaned_data['minimoaplica'],
                                            habilitado=True,
                                            individual=True)
                    examen.save(request)
                    examen.carreras.add(inscripcion.carrera)
                    examen.sede.add(inscripcion.sede)
                    examen.modalidad.add(inscripcion.modalidad)
                    exameni = ExamenInscripcion(inscripcion=inscripcion,
                                                examenadmision=examen,
                                                fecha=form.cleaned_data['fecha'],
                                                hora=form.cleaned_data['hora'],
                                                aula=form.cleaned_data['aula'])
                    exameni.save(request)
                    inscripcion.habilitadoexamen = True
                    inscripcion.save(request)
                    area = form.cleaned_data['areabancopregunta']
                    preguntas = form.cleaned_data['preguntas']
                    porcentaje = 100
                    porcentajepregunta = null_to_numeric(100.0 / preguntas, 2)
                    examenarea = ExamenAreaBancoPreguntas(examenadmision=examen,
                                                          areabancopregunta=area,
                                                          cantidadpreguntas=preguntas,
                                                          porcentaje=porcentaje,
                                                          valor=null_to_numeric(examen.maximo * (porcentaje / 100), 5))
                    examenarea.save(request)
                    for preg in area.preguntaadmision_set.filter(activa=True).order_by('?')[:form.cleaned_data['preguntas']]:
                        exam = PreguntasExamenAdmision(examenareabancopreguntas=examenarea,
                                                       preguntaadmision=preg,
                                                       porcentaje=porcentajepregunta,
                                                       valor=null_to_numeric(examenarea.valor * (porcentajepregunta / 100), 5))
                        exam.save(request)
                    log(u'Adiciono examen inscripcion: %s' % inscripcion, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'examen_ins':
            try:
                exameni = ExamenInscripcion.objects.get(pk=request.POST['idi'])
                if int(request.POST['id']) > 0:
                    examen = ExamenAdmision.objects.get(pk=request.POST['id'])
                    exameni.examenadmision = examen
                    exameni.save(request)
                    return ok_json(data={'fecha': exameni.fecha.strftime('%d-%m-%Y'), 'hora': exameni.hora.strftime("%H:%M"), 'lugar': exameni.aula.id if exameni.aula else 0})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'entrevista_ins':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if int(request.POST['id']) > 0:
                    entrevista = Entrevista.objects.get(pk=request.POST['id'])
                    if InscripcionEntrevista.objects.filter(inscripcion=inscripcion).exists():
                        entrevistai = InscripcionEntrevista.objects.filter(inscripcion=inscripcion)[0]
                        entrevistai.entrevista = entrevista
                        entrevistai.save(request)
                    else:
                        entrevistai = InscripcionEntrevista(entrevista=entrevista, inscripcion=inscripcion)
                        entrevistai.save(request)
                    return ok_json()
                else:
                    InscripcionEntrevista.objects.filter(inscripcion=inscripcion).delete()
                    return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'actualizafecha':
            try:
                exameni = ExamenInscripcion.objects.get(pk=request.POST['id'])
                valor = convertir_fecha(request.POST['valor'])
                exameni.fecha = valor
                exameni.save(request)
                log(u'Edito fecha de examen inscripcion: %s - %s - %s' % (exameni.inscripcion,exameni.fecha,exameni.hora), request, "add")
                try:
                    if exameni.inscripcion.idsalesforcei:
                        idins = exameni.inscripcion.idsalesforcei
                        fecha = str(exameni.fecha)
                        hora = str(exameni.hora)
                        api_token_sf2.enviar_datos_examen(idins, fecha, hora)
                except Exception as ex:
                    pass
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'actualizalugar':
            try:
                exameni = ExamenInscripcion.objects.get(pk=request.POST['idi'])
                aula = Aula.objects.get(pk=int(request.POST['id']))
                exameni.aula = aula
                exameni.save(request)
                log(u'Edito lugar de  examen inscripcion: %s' % exameni, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'actualizahora':
            try:
                exameni = ExamenInscripcion.objects.get(pk=request.POST['id'])
                valor = request.POST['valor']
                exameni.hora = valor
                exameni.save(request)
                log(u'Edito hora de  examen inscripcion: %s - %s - %s' % (exameni.inscripcion,exameni.fecha,exameni.hora), request, "add")
                if exameni.inscripcion.idsalesforcei:
                    idins = exameni.inscripcion.idsalesforcei
                    fecha = str(exameni.fecha)
                    hora = str(exameni.hora)
                    api_token_sf2.enviar_datos_examen(idins, fecha, hora)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editidioma':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                idioma = IdiomaDomina.objects.get(pk=request.POST['id'])
                form = IdiomaDominaForm(request.POST)
                if form.is_valid():
                    idioma.idioma = form.cleaned_data['idioma']
                    idioma.lectura = form.cleaned_data['lectura']
                    idioma.escritura = form.cleaned_data['escritura']
                    idioma.oral = form.cleaned_data['oral']
                    idioma.save(request)
                    log(u"Modifico idioma: %s" % idioma.persona, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delidioma':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                idioma = IdiomaDomina.objects.get(pk=request.POST['id'])
                log(u"Elimino idioma que domina: %s" % idioma.persona, request, "del")
                idioma.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'verificarestudio':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['inscripcionid'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                estudio = EstudioPersona.objects.get(pk=request.POST['id'])
                estudio.verificado = (request.POST['valor'] == 'true')
                estudio.save(request)
                log(u"Verifico datos de estudio: %s" % estudio, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'importar':
            try:
                #  SE NECESITA EN LA PLANTILLA EXCEL SUBIR EL ID DE PAIS, CANTON, PROVINCIA,PARROQUIA
                #  ESTOS DATOS SE UTILIZA PARA CARGAR CLIENTES EN-SEVEN"
                form = ImportarArchivoXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION INSCRIPCIONES',
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
                                persona = None
                                if cedula:
                                    if Persona.objects.filter(cedula=cedula).exists():
                                        persona = Persona.objects.filter(cedula=cedula)[0]
                                elif pasaporte:
                                    if Persona.objects.filter(pasaporte=pasaporte).exists():
                                        persona = Persona.objects.filter(pasaporte=pasaporte)[0]
                                if not persona:
                                    persona = Persona(cedula=cedula,
                                                      pasaporte=pasaporte,
                                                      apellido1=smart_str(cols[2]),
                                                      apellido2=smart_str(cols[3]),
                                                      nombre1=smart_str(cols[4]),
                                                      nombre2=smart_str(cols[5]),
                                                      sexo_id=int(cols[6]),
                                                      nacimiento=xlrd.xldate.xldate_as_datetime(cols[7], workbook.datemode).date(),
                                                      email=smart_str(cols[8]),
                                                      telefono_conv=smart_str(cols[9]),
                                                      telefono=smart_str(cols[10]),
                                                      direccion=smart_str(cols[11]))
                                    persona.save(request)
                                    generar_usuario(persona=persona, group_id=ALUMNOS_GROUP_ID)
                                if EMAIL_INSTITUCIONAL_AUTOMATICO_ESTUDIANTES:
                                    persona.emailinst = generar_email(persona, estudiante=True)
                                    persona.save(request)
                                sede = Sede.objects.get(pk=int(cols[12]))
                                coordinacion = sede.coordinacion_set.get(pk=int(cols[13]))
                                carrera = coordinacion.carrera.get(pk=int(cols[14]))
                                modalidad = Modalidad.objects.get(pk=int(cols[15]))
                                sesion =  sede.sesion_set.get(pk=int(cols[16]))
                                malla = carrera.malla_set.get(pk=int(cols[17]))
                                periodo = None
                                if Periodo.objects.filter(id=int(cols[20])).exists():
                                    periodo = Periodo.objects.filter(id=int(cols[20]))[0]
                                existe = False
                                for i in Inscripcion.objects.filter(persona__cedula=cedula):
                                    if i.coordinacion == coordinacion and i.carrera == carrera:
                                        existe = True
                                if not existe:
                                    inscripcion = Inscripcion(persona=persona,
                                                              fecha=datetime.now().date(),
                                                              hora=datetime.now().time(),
                                                              fechainiciocarrera=xlrd.xldate.xldate_as_datetime(cols[19], workbook.datemode).date(),
                                                              carrera=carrera,
                                                              modalidad=modalidad,
                                                              sesion=sesion,
                                                              sede=sede,
                                                              periodo=periodo,
                                                              tipogratuidad_id=TIPO_GRATUIDAD_NINGUNA)
                                    inscripcion.save(request)
                                    persona.crear_perfil(inscripcion=inscripcion)
                                    documentos = DocumentosDeInscripcion(inscripcion=inscripcion,
                                                                         pre=True if smart_str(cols[21]) == 'S' else False,
                                                                         observaciones_pre=smart_str(cols[22]))
                                    documentos.save(request)
                                    inscripcion.preguntas_inscripcion()
                                    inscripcion.persona.mi_perfil()
                                    inscripcion.generar_rubro_inscripcion(malla)
                                    inscripcion.mi_malla(malla=malla)
                                    inscripcion.mi_itinerario()
                                    inscripcion.actualizar_nivel()
                                    inscripcion.actualiza_tipo_inscripcion()
                                    log(u'Importo inscripcion: %s' % persona.identificacion(), request, "add")
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

        if action == 'importarcanvas':
            try:
                # DepurarAdmisiones.objects.all().delete()
                form = ImportarArchivoXLSPeriodoForm(request.POST, request.FILES)
                if form.is_valid():
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("idcanvas_", nfile._name)
                    archivo = Archivo(nombre='idcanvas',
                                      fecha=datetime.now(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_PUBLICO)
                    archivo.save(request)
                    workbook = openpyxl.load_workbook(archivo.archivo.file.name)
                    sheet = workbook.worksheets[0]
                    linea = 1
                    periodoid = form.cleaned_data['periodo'].id
                    matriculados = Matricula.objects.filter(inscripcion__periodo__id=periodoid,inscripcion__persona__id_canvas=0)
                    print(datetime.now().time())
                    for rowx in sheet.iter_rows(values_only=True):
                        if linea >= 2:
                            # en cols se almacena toda la tupla que trae de excel
                            cols = rowx
                            for matricula in matriculados:
                                persona=matricula.inscripcion.persona
                                if persona.cedula==str(cols[1]):
                                    persona.id_canvas=cols[0]
                                    persona.save()
                                    break
                        linea += 1
                        print(linea)
                    print(datetime.now().time())
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'fechainicioconvalidacion':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = FechaInicioConvalidacionInscripcionForm(request.POST)
                if form.is_valid():
                    inscripcion.fechainicioconvalidacion = form.cleaned_data['fecha']
                    inscripcion.save(request)
                    log(u'Adiciono fecha inicio convalidacion: ' % inscripcion, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deldocumento':
            try:
                archivo = ArchivoDocumentoInscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, archivo.inscripcion):
                    return bad_json(error=8)
                archivo.delete()
                log(u'Elimino documento de inscripcion: %s' % archivo, request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'asignaturas':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if int(request.POST['tipo']) == 1:
                    asignaturas = Asignatura.objects.filter(Q(id__in=[x.asignatura.id for x in inscripcion.mi_malla().asignaturamalla_set.all()]) | Q(id__in=[x.asignatura.id for x in inscripcion.mi_malla().modulomalla_set.all()])).distinct()
                else:
                    asignaturas = Asignatura.objects.all()
                return ok_json({'listado': [(x.id, x.nombre) for x in asignaturas]})
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=3)

        if action == 'activar':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                ui = inscripcion.persona.usuario
                ui.is_active = True
                ui.save()
                log(u'Activo el usuario inscripcion: %s' % inscripcion, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desactivar':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                ui = inscripcion.persona.usuario
                ui.is_active = False
                ui.save()
                log(u'Desactivo el usuario inscripcion: %s' % inscripcion, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desactivarperfil':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                inscripcion.activo = False
                inscripcion.save(request)
                log(u'Desactivo perfil de usuario: %s' % inscripcion, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'activarperfil':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                inscripcion.activo = True
                inscripcion.save(request)
                log(u'Activo perfil de usuario: %s' % inscripcion, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'asignaturacarrera':
            try:
                carrera = Carrera.objects.get(pk=int(request.POST['id']))
                lista = []
                for asignatura in Asignatura.objects.filter(Q(asignaturamalla__malla__carrera=carrera) | Q(modulomalla__malla__carrera=carrera)).distinct():
                    lista.append([asignatura.id, asignatura.nombre])
                return ok_json({'lista': lista})
            except:
                return bad_json(error=3)

        if action == 'resetear':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                resetear_clave(inscripcion.persona)
                inscripcion.persona.cambiar_clave()
                log(u'Reseteo clave de inscripcion: %s' % inscripcion, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'entrega_doc':
            try:
                tipodocumento = TipoDocumentoInscripcion.objects.get(pk=request.POST['id'])
                inscripcion = Inscripcion.objects.get(pk=request.POST['idinscripcion'])
                if request.POST['estado'] == 'true':
                    archivo = ArchivoDocumentoInscripcion(tipodocumentoinscripcion=tipodocumento,
                                                          fecha=datetime.now(),
                                                          inscripcion=inscripcion)
                    archivo.save()
                    log(u"Alumno %s entrega %s" % (inscripcion.persona,tipodocumento), request, "edit")

                else:
                    archivo = ArchivoDocumentoInscripcion.objects.filter(tipodocumentoinscripcion=tipodocumento,inscripcion=inscripcion)
                    archivo.delete()
                    log(u"Se retira %s de %s" % (tipodocumento,inscripcion.persona), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'recalcularcreditos':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                inscripcion.actualizar_creditos()
                inscripcion.actualiza_tipo_inscripcion()
                inscripcion.actualiza_gratuidad()
                inscripcion.actualizar_nivel()
                inscripcion.save(request)
                inscripcion.actualizar_homologacion()
                log(u'Actualizo creditos: %s' % inscripcion, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'retirocarrera':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = RetiradoCarreraForm(request.POST)
                if form.is_valid():
                    if not inscripcion.retirocarrera_set.exists():
                        retiro = RetiroCarrera(inscripcion=inscripcion,
                                               fecha=form.cleaned_data['fecha'],
                                               motivo=form.cleaned_data['motivo'])
                        retiro.save(request)
                        inscripcion.habilitadomatricula = False
                        inscripcion.save(request)
                    log(u'Retiro de carrera: %s' % inscripcion, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addadministrativo':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if inscripcion.persona.es_administrador():
                    return bad_json(mensaje=u"Ya existe un perfil administrativo para este usuario.")
                administrativo = Administrativo(persona=inscripcion.persona,
                                                sede=request.session['coordinacionseleccionada'].sede)
                administrativo.save(request)
                g = Group.objects.get(pk=ADMINISTRATIVOS_GROUP_ID)
                g.user_set.add(inscripcion.persona.usuario)
                g.save()
                inscripcion.persona.crear_perfil(administrativo=administrativo)
                log(u'Adiciono personal administrativo: %s' % administrativo, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'adddocente':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if inscripcion.persona.es_profesor():
                    return bad_json(mensaje=u"Ya existe un perfil de docente para este usuario.")
                profesor = Profesor(persona=inscripcion.persona,
                                    activo=True,
                                    fechainiciodocente=datetime.now().date(),
                                    coordinacion=request.session['coordinacionseleccionada'],
                                    dedicacion_id=TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID,
                                    nivelescalafon_id=ESCALAFON_TITULAR_PRINCIPAL_ID)
                profesor.save(request)
                grupo = Group.objects.get(pk=PROFESORES_GROUP_ID)
                grupo.user_set.add(inscripcion.persona.usuario)
                grupo.save()
                inscripcion.persona.crear_perfil(profesor=profesor)
                log(u'Adiciono profesor: %s' % profesor, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cambioitinerario':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                form = CambioitinerarioForm(request.POST)
                if form.is_valid():
                    itinerario = inscripcion.inscripcionitinerarrio_set.all()
                    itinerario.delete()
                    ii = InscripcionItinerarrio(inscripcion=inscripcion,
                                                itinerario=form.cleaned_data['itinerario'])
                    ii.save(request)
                    inscripcion.actualizar_creditos()
                    inscripcion.actualizar_nivel()
                    log(u'Modifico itinerario de inscripcion: %s - %s' % (inscripcion.persona, ii.itinerario), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'habilitarmatricula':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                inscripcion.habilitadomatricula = True
                inscripcion.save(request)
                log(u'habilito matricula de inscripcion: %s' % inscripcion.persona, request,"edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deshabilitarmatricula':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                inscripcion.habilitadomatricula = False
                inscripcion.save(request)
                log(u'deshabilito matricula de inscripcion: %s' % inscripcion.persona, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'habilitarcambiomodalidad':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if inscripcion.tiene_deuda():
                    return bad_json(mensaje=u"El estudiante tiene deuda con la institución.", error=8)
                if inscripcion.tiene_tercera_matricula():
                    return bad_json(mensaje=u"El estudiante posee segunda o tercera matrícula.", error=8)
                if inscripcion.matriculado():
                    return bad_json(mensaje=u"El estudiante se encuentra matriculado.", error=8)
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                inscripcion.habilitadocambiomodalidad = True
                inscripcion.save(request)
                log(u'Habilito para cambio de modalidad: %s' % inscripcion.persona, request,"edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deshabilitarcambiomodalidad':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                inscripcion.habilitadocambiomodalidad = False
                inscripcion.save(request)
                log(u'Deshabilito para cambio de modalidad: %s' % inscripcion.persona, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'habilitarhomologacion':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                registro = inscripcion.mi_preinscripcion()
                if registro:
                    registro.homologar = True
                    registro.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deshabilitarhomologacion':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                registro = inscripcion.mi_preinscripcion()
                if registro:
                    registro.homologar = False
                    registro.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'habilitarhomologacionpre':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                registro = inscripcion.documentos_entregados()
                if registro:
                    registro.pre = True
                    registro.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deshabilitarhomologacionpre':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                registro = inscripcion.documentos_entregados()
                if registro:
                    registro.pre = False
                    registro.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'habilitarexamen':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                # if not puede_modificar_inscripcion_post(request, inscripcion):
                #     return bad_json(error=8)
                inscripcion.habilitadoexamen = True
                inscripcion.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deshabilitarexamen':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, inscripcion):
                    return bad_json(error=8)
                inscripcion.habilitadoexamen = False
                inscripcion.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'confirmarentrevista':
            try:
                respuesta = RespuestaEntrevista.objects.get(pk=request.POST['id'])
                respuesta.confirmada = True
                respuesta.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'act_observ_respuesta':
            try:
                respuesta = RespuestaEntrevista.objects.get(pk=request.POST['idr'])
                texto = request.POST['texto']
                respuesta.observaciones = texto
                respuesta.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'act_respuesta':
            try:
                respuesta = RespuestaPreguntaEntrevista.objects.get(pk=request.POST['idr'])
                valor = int(request.POST['id'])
                respuesta.valor = valor
                respuesta.save(request)
                detalle = respuesta.respuestadetallecompetenciaentrevista
                detalle.actualiza_valor()
                comp = detalle.respuestacompetenciaentrevista
                comp.actualiza_valor()
                preg = comp.respuestaentrevista
                preg.actualiza_valor()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addtribunal':
            try:
                form = TribunalProyectoGradoForm(request.POST)
                proyecto = DefensaProyectoGrado.objects.get(pk=request.POST['id'])
                remplazo = None
                if form.is_valid():
                    if form.cleaned_data['remplazo']:
                        remplazo = int(form.cleaned_data['remplazo'])
                    if TribunalDefensaProyectoGrado.objects.filter(defensaproyectogrado=proyecto, persona=form.cleaned_data['persona']).exists():
                        return bad_json(mensaje=u'Esta persona ya consta en el tribunal de este proyecto')
                    precio = form.cleaned_data['pago']
                    if proyecto.proyectogrado.posgrado():
                        valor = precio.pagoposgrados
                    else:
                        valor = precio.pago
                    tribunal = TribunalDefensaProyectoGrado(defensaproyectogrado=proyecto,
                                                            persona_id=int(form.cleaned_data['persona']),
                                                            remplazo_id=remplazo,
                                                            factura=form.cleaned_data['factura'],
                                                            horario=form.cleaned_data['hora'],
                                                            tipofactura=form.cleaned_data['tipofactura'],
                                                            sede=form.cleaned_data['sede'],
                                                            dedicacion=form.cleaned_data['dedicacion'],
                                                            pago=form.cleaned_data['pago'],
                                                            fecharegistro=datetime.today(),
                                                            valor=valor)
                    tribunal.save(request)
                    log(u'Asignacion tribunal defensa: %s' % tribunal, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edittribunal':
            try:
                form = TribunalProyectoGradoForm(request.POST)
                tribunal = TribunalDefensaProyectoGrado.objects.get(pk=request.POST['id'])
                proyecto = tribunal.defensaproyectogrado
                remplazo = None
                if form.is_valid():
                    if form.cleaned_data['remplazo']:
                        remplazo = int(form.cleaned_data['remplazo'])
                    if TribunalDefensaProyectoGrado.objects.filter(defensaproyectogrado=proyecto, persona=form.cleaned_data['persona']).exclude(pk=tribunal.id).exists():
                        return bad_json(mensaje=u'Esta persona ya consta en el tribunal de este proyecto')
                    tribunal.persona_id = int(form.cleaned_data['persona'])
                    tribunal.factura = form.cleaned_data['factura']
                    tribunal.horario = form.cleaned_data['hora']
                    tribunal.sede = form.cleaned_data['sede']
                    tribunal.dedicacion = form.cleaned_data['dedicacion']
                    tribunal.fecharegistro = datetime.today()
                    tribunal.tipofactura = form.cleaned_data['tipofactura']
                    tribunal.save()
                    log(u'Asignacion tribunal defensa: %s' % tribunal, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'adddefensa':
            try:
                form = DefensaProyectoGradoForm(request.POST)
                proyecto = ProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    fecha = form.cleaned_data['fechasustentacion']
                    fecha1 = fecha.isocalendar()[1]
                    dia = datetime.now().date().isocalendar()[2]
                    if dia == 6 or dia == 7:
                        hoy = datetime.now().date().isocalendar()[1] + 1
                    else:
                        hoy = datetime.now().date().isocalendar()[1]
                    hora = form.cleaned_data['horasustentacion']
                    if DefensaProyectoGrado.objects.filter(fechadefensa=fecha,horadefensa=hora).exists():
                        return bad_json(mensaje=u'Ya se registra esta hora en otra defensa')
                    defensa = DefensaProyectoGrado(proyectogrado=proyecto,
                                                   fechadefensa=form.cleaned_data['fechasustentacion'],
                                                   horadefensa=form.cleaned_data['horasustentacion'],
                                                   lugardefensa=form.cleaned_data['lugar'],
                                                   numerooportunidad=form.cleaned_data['numerooportunidad'],
                                                   observaciones=form.cleaned_data['observacion'])
                    defensa.save(request)
                    log(u'Asignacion tribunal defensa: %s' % proyecto, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editdefensa':
            try:
                form = DefensaProyectoGradoForm(request.POST)
                defensaproyecto = DefensaProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    fecha = form.cleaned_data['fechasustentacion']
                    fecha1 = fecha.isocalendar()[1]
                    dia = datetime.now().date().isocalendar()[2]
                    if dia == 6 or dia == 7:
                        hoy = datetime.now().date().isocalendar()[1] + 1
                    else:
                        hoy = datetime.now().date().isocalendar()[1]
                    defensaproyecto.fechadefensa = form.cleaned_data['fechasustentacion']
                    defensaproyecto.horadefensa = form.cleaned_data['horasustentacion']
                    defensaproyecto.lugardefensa = form.cleaned_data['lugar']
                    defensaproyecto.foliodefensa = form.cleaned_data['folio']
                    defensaproyecto.numeroactadefensa = form.cleaned_data['acta']
                    defensaproyecto.numerooportunidad = form.cleaned_data['numerooportunidad']
                    defensaproyecto.observaciones = form.cleaned_data['observacion']
                    defensaproyecto.save(request)
                    log(u'Edita datos defensa proyecto: %s' % defensaproyecto, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editdefensaextra':
            try:
                form = DefensaProyectoGradoExtraForm(request.POST)
                defensaproyecto = DefensaProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    defensaproyecto.foliodefensa = form.cleaned_data['folio']
                    defensaproyecto.numeroactadefensa = form.cleaned_data['acta']
                    defensaproyecto.save(request)
                    log(u'Edita datos defensa proyecto: %s' % defensaproyecto, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'notificartribunal':
            try:
                proyecto = DefensaProyectoGrado.objects.get(pk=int(request.POST['id']))
                for tribunal in proyecto.tribunaldefensaproyectogrado_set.all():
                    log(u'Notificó a tribunal: %s' % proyecto.proyectogrado, request, "add")
                    send_mail(subject='Notificación de Tribunal de Sustentación.',
                              html_template='emails/notificaciontribunal.html',
                              data={'tribunal': tribunal},
                              recipient_list=[tribunal.persona])
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deltribunal':
            try:
                tribunal = TribunalDefensaProyectoGrado.objects.get(pk=request.POST['id'])
                log(u'Elimino miembro tribunal: %s' % tribunal, request, "del")
                tribunal.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deldefensa':
            try:
                defensaproyecto = DefensaProyectoGrado.objects.get(pk=request.POST['id'])
                log(u'Elimino defensa: %s' % defensaproyecto, request, "del")
                defensaproyecto.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'actualizahorasvinculacion':
            try:
                participanteproyectovinculacion = ParticipanteProyectoVinculacion.objects.get(pk=int(request.POST['idp']))
                participanteproyectovinculacion.horas = request.POST['valor']
                participanteproyectovinculacion.save()
                log(u'Actualización de horas : %s' % participanteproyectovinculacion.proyecto, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'abrirmatricula':
            try:
                matricula = Matricula.objects.get(pk=request.POST['id'])
                matricula.cerrada = False
                matricula.save()
                log(u'Apertura de matricula: %s' % matricula, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addreconocimiento':
            # Solo debe agregar un reconocimento de estudios
            try:
                form = ReconocimientoGraduadoForm(request.POST)
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    reconocimiento = TipoReconocimientoInscripcion(inscripcion=inscripcion,
                                                                   institucion_id=form.cleaned_data['institucion'] if form.cleaned_data['institucion'] else None,
                                                                   tiporeconocimiento=form.cleaned_data['tiporeconocimiento'],
                                                                   tiemporeconocimiento=form.cleaned_data['tiemporeconocimiento'],
                                                                   conocimientos=form.cleaned_data['conocimientos'],
                                                                   contenidos=form.cleaned_data['contenidos'],
                                                                   carrera=form.cleaned_data['carrera'])
                    reconocimiento.save(request)
                    log(u'Adiciono un reconocimiento de estudios al estudiante: %s' % inscripcion, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editreconocimiento':
            try:
                reconocimiento = TipoReconocimientoInscripcion.objects.get(pk=request.POST['id'])
                form = ReconocimientoGraduadoForm(request.POST)
                if form.is_valid():
                    reconocimiento.tiporeconocimiento = form.cleaned_data['tiporeconocimiento']
                    reconocimiento.tiemporeconocimiento = form.cleaned_data['tiemporeconocimiento']
                    if form.cleaned_data['institucion']:
                        reconocimiento.institucion_id = int(form.cleaned_data['institucion'])
                    else:
                        reconocimiento.institucion = None
                    reconocimiento.conocimientos = form.cleaned_data['conocimientos']
                    reconocimiento.contenidos = form.cleaned_data['contenidos']
                    reconocimiento.carrera = form.cleaned_data['carrera']
                    reconocimiento.save(request)
                    log(u'Modifico reconocimiento del estudiante: %s' % reconocimiento.inscripcion, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delreconocimiento':
            try:
                reconocimiento = TipoReconocimientoInscripcion.objects.get(pk=request.POST['id'])
                log(u'Elimino reconocimiento del estudiante %s' % reconocimiento.inscripcion, request, "del")
                reconocimiento.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addotrosrequisitos':
            try:
                form = OtrosRequisitosInscripcionForm(request.POST, request.FILES)
                inscripcion = Inscripcion.objects.get(pk=request.POST['inscripcion'])
                otrorequistiomalla = OtrosRequisitosMalla.objects.get(pk=request.POST['requisito'])

                if form.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("otrorequisitomalla_", newfile._name)
                    otrorequisito = OtrosRequisitosCumplirInscripcion(inscripcion=inscripcion,
                                                                      otrosrequisitos=otrorequistiomalla,
                                                                      observaciones=form.cleaned_data['observaciones'],
                                                                      fecha=form.cleaned_data['fecha'])
                    otrorequisito.save(request)
                    log(u'Asignacion de otro requisito malla: %s' % otrorequisito, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editotrosrequisitos':
            try:
                otrosrequisitos = OtrosRequisitosCumplirInscripcion.objects.get(pk=request.POST['id'])
                if not puede_modificar_inscripcion_post(request, otrosrequisitos.inscripcion):
                    return bad_json(error=8)
                form = OtrosRequisitosInscripcionForm(request.POST, request.FILES)
                if form.is_valid():
                    if 'archivo' in request.FILES:
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("otrorequisitomalla_", nfile._name)
                        otrosrequisitos.archivo = nfile
                    otrosrequisitos.observaciones = form.cleaned_data['observaciones']
                    otrosrequisitos.fecha = form.cleaned_data['fecha']
                    otrosrequisitos.save()
                    log(u'Modifico otros requisitos malla de inscripcion: %s - %s' % (otrosrequisitos.inscripcion, otrosrequisitos), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delotrosrequisitos':
            try:
                otrosrequisitos = OtrosRequisitosCumplirInscripcion.objects.get(pk=request.POST['id'])
                log(u'Elimino otros requisitos de la inscripcion %s' % otrosrequisitos.inscripcion, request, "del")
                otrosrequisitos.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'movilidad':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                form = RegistroMovilidadForm(request.POST)
                if form.is_valid():
                    inscripcion.intercambio = True
                    movilidad = MovilidadInscripcion(periodo=form.cleaned_data['periodo'],
                                                     inscripcion=inscripcion,
                                                     tipomovilidad=form.cleaned_data['tipomovilidad'],
                                                     instituto_id=form.cleaned_data['universidad'],
                                                     homologacion=form.cleaned_data['homologacion'],
                                                     asignaturas=form.cleaned_data['asignaturas'],
                                                     tipomovilidadacademica=form.cleaned_data['tipomovilidadacademica'])
                    movilidad.save()
                    inscripcion.save()
                    log(u'Actualizo movilidad %s' % inscripcion, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delmovilidad':
            try:
                movilidad = MovilidadInscripcion.objects.get(pk=request.POST['id'])
                inscripcion = movilidad.inscripcion
                inscripcion.intercambio = False
                inscripcion.save()
                movilidad.delete()
                log(u'Elimino movilidad: %s' % movilidad, request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cambiarinscripcion':
            try:
                form = CambiarFichaInscripcionForm(request.POST)
                participante = ParticipanteProyectoVinculacion.objects.get(pk=request.POST['id'])
                inscripcion = participante.inscripcion
                if form.is_valid():
                    nuevainscripcion = Inscripcion.objects.filter(inscripcionmalla__malla=form.cleaned_data['malla'], persona=inscripcion.persona)[0]
                    if inscripcion == nuevainscripcion:
                        return bad_json(mensaje=u"Se debe escojer una ficha diferente a la misma.")
                    participante.inscripcion = nuevainscripcion
                    participante.save(request)
                    log(u'Cambio de ficha vinculacion: %s' % participante.inscripcion, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'cambiarinscripcionpasantia':
            try:
                form = CambiarFichaInscripcionForm(request.POST)
                pasantia = Pasantia.objects.get(pk=request.POST['id'])
                inscripcion = pasantia.inscripcion
                if form.is_valid():
                    nuevainscripcion = Inscripcion.objects.filter(inscripcionmalla__malla=form.cleaned_data['malla'], persona=inscripcion.persona)[0]
                    if inscripcion == nuevainscripcion:
                        return bad_json(mensaje=u"Se debe escojer una ficha diferente a la misma.")
                    pasantia.inscripcion = nuevainscripcion
                    pasantia.save(request)
                    log(u'Cambio de pasantia a ficha: %s' % pasantia.inscripcion, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'cambiorecordhomologacion':
            try:
                historico = HistoricoRecordAcademico.objects.get(pk=request.POST['id'])
                form = CambioRecordHomologacionForm(request.POST)
                if form.is_valid():
                    historico.homologada = form.cleaned_data['homologada']
                    historico.convalidacion = form.cleaned_data['convalidacion']
                    historico.save(request)
                    historico.actualizar()
                    log(u'Modifico homologada historico de record academico: %s - %s' % (historico, historico.inscripcion.persona), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'aprobado_requisitoprehomologacion':
            try:
                documento = DocumentosDeInscripcion.objects.get(pk=request.POST['id'])
                documento.necesario_para_prehomologacion = request.POST['valor'] == 'true'
                documento.save(request)
                log(u"Aprobado como un requisito de pre homologacion: %s" % documento.inscripcion, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1)

        if action == 'aprobado_homologacion':
            try:
                solicitud = SolicitudHomologacion.objects.get(pk=request.POST['id'])
                solicitud.aprobado_admision = request.POST['valor'] == 'true'
                solicitud.persona_aprobo_admision = persona.usuario
                solicitud.fecha_aprobo_admision = datetime.now()
                solicitud.save(request)
                log(u"Aprobado por departamento de homologacion el documento: %s" % solicitud.inscripcion, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1)

        if action == 'aprobado_secretaria':
            try:
                solicitud = SolicitudHomologacion.objects.get(pk=request.POST['id'])
                solicitud.aprobado_secretaria = request.POST['valor'] == 'true'
                solicitud.persona_aprobo_secretaria = persona.usuario
                solicitud.fecha_aprobo_secretaria = datetime.now()
                solicitud.save(request)
                log(u"Aprobado por secretaria el docuemnto de homologacion: %s" % solicitud.inscripcion, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1)

        if action == 'addsolicitudhomologacion':
            try:
                inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                form = SolicitudHomologacionForm(request.POST)
                if form.is_valid():
                    solicitud = SolicitudHomologacion(inscripcion=inscripcion,
                                                      fecha_solicitud=datetime.now(),
                                                      periodo_homologacion=form.cleaned_data['periodo'])
                    solicitud.save(request)
                    solicitudes_homologacion = solicitud.inscripcion.solicitudhomologacion_set.all().order_by('-periodo_homologacion__inicio')
                    if solicitudes_homologacion.exists():
                        primera_solicitud = solicitudes_homologacion.first()
                        periodo_solicitud= primera_solicitud.periodo_homologacion
                    else:
                        periodo_solicitud = solicitud.inscripcion.periodo
                    inscripcion.periodo_homologacion = periodo_solicitud
                    inscripcion.save()
                    inscripcion.generar_rubro_homologacion(inscripcion.mi_malla(), solicitud.periodo_homologacion)
                    log(u'Adiciono la solicitud de homologacion %s' % (solicitud.inscripcion), request, "add")
                    return ok_json()
                else:
                    return bad_json(mensaje=u'Completar')
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delsolicitudhomologacion':
            try:
                solicitud = SolicitudHomologacion.objects.get(pk=request.POST['id'])
                solicitud.delete()
                log(u'Elimino registro academico: %s - %s' % (solicitud, solicitud.inscripcion.persona), request, "del")
                solicitudes_homologacion = solicitud.inscripcion.solicitudhomologacion_set.all().order_by('-periodo_homologacion__inicio')
                if solicitudes_homologacion.exists():
                    primera_solicitud = solicitudes_homologacion.first()
                    periodo_solicitud = primera_solicitud.periodo_homologacion
                else:
                    periodo_solicitud = solicitud.inscripcion.periodo
                inscripcion = solicitud.inscripcion
                inscripcion.periodo_homologacion = periodo_solicitud
                inscripcion.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'anularsolicitud':
            try:
                solicitud = SolicitudHomologacion.objects.get(pk=request.POST['id'])
                hoy = datetime.now().date()
                solicitud.anulado = True
                solicitud.save(request)
                log(u'Anulo la solicitud: %s' % solicitud, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'moverexamen':
            try:
                examen = ExamenInscripcion.objects.get(pk=request.POST['id'])
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                form = MoverExamenInscripcionForm(request.POST)
                if form.is_valid():
                    examen.inscripcion = form.cleaned_data['inscripcion']
                    examen.save()
                    log(u'Muevo examen de inscripcion: %s' % examen, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'moverentrevista':
            try:
                entrevista = InscripcionEntrevista.objects.get(pk=request.POST['id'])
                inscripcion = Inscripcion.objects.get(pk=request.POST['idi'])
                form = MoverExamenInscripcionForm(request.POST)
                if form.is_valid():
                    entrevista.inscripcion = form.cleaned_data['inscripcion']
                    entrevista.save()
                    log(u'Muevo entrevista de inscripcion: %s' % entrevista, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        data['title'] = u'Listado de inscripciones'
        persona = request.session['persona']
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar inscripcion'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/delete.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiomalla':
                try:
                    data['title'] = u'Cambio de malla'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = CambiomallaForm()
                    form.mallas(inscripcion)
                    data['form'] = form
                    return render(request, "inscripciones/cambiomalla.html", data)
                except Exception as ex:
                    pass

            if action == 'retirocarrera':
                try:
                    data['title'] = u'Retiro de Carrera'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = RetiradoCarreraForm()
                    return render(request, "inscripciones/retirocarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'cambionivel':
                try:
                    data['title'] = u'Cambio de nivel malla'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = CambionivelmallaForm(initial={'nuevonivel': inscripcion.mi_nivel().nivel})
                    form.editar(inscripcion)
                    data['form'] = form
                    return render(request, "inscripciones/cambionivel.html", data)
                except Exception as ex:
                    pass

            if action == 'activarcertificadonoadeudar':
                try:

                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/activarcertificadonoadeudar.html", data)
                except Exception as ex:
                    pass

            if action == 'resetearcertificado':
                try:

                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/resetearcertificado.html", data)
                except Exception as ex:
                    pass

            if action == 'solicitudnoadeudar':
                try:
                    data['title'] = u'Solicitud de no adeudar'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['observacionesc'] = inscripcion.observacioncertificadonoadeudar_set.filter(tipo=1)
                    data['observacioness'] = inscripcion.observacioncertificadonoadeudar_set.filter(tipo=2)
                    data['observacionesb'] = inscripcion.observacioncertificadonoadeudar_set.filter(tipo=3)
                    data['pagado'] = True if RubroEspecieValorada.objects.filter(rubro__inscripcion=inscripcion,rubro__cancelado=True).exists() else False
                    fecha_pago = Pago.objects.filter(rubro__cancelado=True, rubro__rubroespecievalorada__solicitud__inscripcion=inscripcion).last()
                    if fecha_pago is not None:
                        diferencia = relativedelta(datetime.now().date(), fecha_pago.fecha)
                        data['atiempo'] = False if diferencia.months > 3 or diferencia.years > 0 else True
                    return render(request, "inscripciones/solicitudnoadeudar.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarcertificadonoadeuda':
                try:

                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    opcion = int(request.GET['op'])
                    if opcion == 1:
                        data['title'] = u'Aprobar desde Colecturia el certificado de no adeudar'
                    if opcion == 2:
                        data['title'] = u'Aprobar desde Secretaria de Carrera el certificado de no adeudar'
                    if opcion == 3:
                        data['title'] = u'Aprobar desde Biblioteca el certificado de no adeudar'
                    data['opcion'] = opcion
                    return render(request, "inscripciones/aprobarcertificadonoadeudar.html", data)
                except Exception as ex:
                    pass

            if action == 'addobservacioncertificadonoadeuda':
                try:

                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    opcion = int(request.GET['op'])
                    data['form'] = ObservacionCertificadoNoAdeudarForm()
                    if opcion == 1:
                        data['title'] = u'Aprobar desde Colecturia el certificado de no adeudar'
                    if opcion == 2:
                        data['title'] = u'Aprobar desde Secretaria de Carrera el certificado de no adeudar'
                    if opcion == 3:
                        data['title'] = u'Aprobar desde Biblioteca el certificado de no adeudar'
                    data['opcion'] = opcion

                    return render(request, "inscripciones/addobservacioncertificadonoadeuda.html", data)
                except Exception as ex:
                    pass

            if action == 'cambionivelmatricula':
                try:
                    data['title'] = u'Cambio de nivel malla'
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    form = CambionivelmallaForm(initial={'nuevonivel': matricula.nivelmalla})
                    data['form'] = form
                    return render(request, "inscripciones/cambionivelmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiocohorte':
                try:
                    data['title'] = u'Cambio de Cohorte Posgrado'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = CambioCohortePosgradoForm(initial={'nuevacohorte': inscripcion.fechascorteposgrado})
                    data['form'] = form
                    return render(request, "inscripciones/cambiocohorte.html", data)
                except Exception as ex:
                    pass

            if action == 'generarrubrosparqueo':
                try:
                    data['title'] = u'Generar rubros para el servicio de parqueadero'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['tipovehiculo'] = request.GET['tv']
                    data['tiempo'] = request.GET['t']
                    return render(request, "inscripciones/generarrubrosparqueo.html", data)
                except Exception as ex:
                    pass

            if action == 'generarrubrosparqueoadicional':
                try:
                    data['title'] = u'Generar rubros para el servicio de parqueadero ADICIONAL'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['tipovehiculo'] = request.GET['tv']
                    data['tiempo'] = request.GET['t']
                    return render(request, "inscripciones/generarrubrosparqueoadicional.html", data)
                except Exception as ex:
                    pass

            if action == 'proyectos':
                try:
                    data['title'] = u'Proyecto de vinculacion'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['proyectos'] = inscripcion.participanteproyectovinculacion_set.all().order_by('-proyecto__fin')
                    return render(request, "inscripciones/proyectos.html", data)
                except Exception as ex:
                    pass

            if action == 'cursos':
                try:
                    data['title'] = u'Cursos y Escuelas Complementarias'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['matriculas'] = inscripcion.matriculacursoescuelacomplementaria_set.all()
                    data['matriculastitulacion'] = inscripcion.matriculacursounidadtitulacion_set.all()
                    return render(request, "inscripciones/cursos.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Nueva inscripción'
                    form = InscripcionForm()
                    form.adicionar(persona)
                    data['form'] = form
                    data['email_institucional_automatico'] = EMAIL_INSTITUCIONAL_AUTOMATICO_ESTUDIANTES
                    data['email_domain'] = EMAIL_DOMAIN
                    data['email_domain_estudiante'] = EMAIL_DOMAIN_ESTUDIANTES
                    data['nacionalidad_indigena_id'] = NACIONALIDAD_INDIGENA_ID
                    data['pais_ecuador_id'] = PAIS_ECUADOR_ID
                    data['modalidad_distancia'] = MODALIDAD_DISTANCIA
                    return render(request, "inscripciones/add.html", data)
                except Exception as ex:
                    pass

            if action == 'asignarcanvas':
                try:
                    data['title'] = u'Asignar ID CANVAS'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = AsignarCanvasForm(initial={'id_canvas': inscripcion.persona.id_canvas})
                    data['form'] = form
                    return render(request, "inscripciones/asignarcanvas.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiodatoscarrera':
                try:
                    data['title'] = u'Cambiar Datos Carrera'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = CambiaDatosCarreraForm()
                    form.adicionar(persona)
                    data['form'] = form
                    return render(request, "inscripciones/cambiodatoscarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'adicionarotracarrera':
                try:
                    data['title'] = u'Inscripción de alumno en otra carrera'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    documentos = inscripcion.documentos_entregados()
                    form = NuevaInscripcionForm(initial={'prenivelacion': documentos.pre,
                                                         # 'copiarecord': inscripcion.recordacademico_set.all(),
                                                         'observacionespre': documentos.observaciones_pre,
                                                         'fecha': inscripcion.fecha,
                                                         'fechainiciocarrera': inscripcion.fechainiciocarrera,
                                                         'condicionado': inscripcion.condicionado,
                                                         'reingreso': documentos.reingreso})
                    form.adicionar(persona, inscripcion.coordinacion)
                    data['form'] = form
                    return render(request, "inscripciones/adicionarotracarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar inscripción'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    documentos = inscripcion.documentos_entregados()
                    perfil = inscripcion.persona.mi_perfil()
                    preguntas_inscripcion = inscripcion.preguntas_inscripcion()
                    snna = inscripcion.persona.datos_snna()
                    clientefacturacion = inscripcion.clientefacturacion(request)
                    form = InscripcionForm(initial={'nombre1': inscripcion.persona.nombre1,
                                                    'nombre2': inscripcion.persona.nombre2,
                                                    'apellido1': inscripcion.persona.apellido1,
                                                    'apellido2': inscripcion.persona.apellido2,
                                                    'cedula': inscripcion.persona.cedula,
                                                    'pasaporte': inscripcion.persona.pasaporte,
                                                    'periodo': inscripcion.periodo,
                                                    'nivel': inscripcion.nivel,
                                                    'centroinformacion': inscripcion.centroinformacion,
                                                    'nacionalidad': inscripcion.persona.nacionalidad,
                                                    'paisnac': inscripcion.persona.paisnac,
                                                    'provincianac': inscripcion.persona.provincianac,
                                                    'cantonnac': inscripcion.persona.cantonnac,
                                                    'parroquianac': inscripcion.persona.parroquianac,
                                                    'nacimiento': inscripcion.persona.nacimiento,
                                                    'sexo': inscripcion.persona.sexo,
                                                    'sangre': inscripcion.persona.sangre,
                                                    'pais': inscripcion.persona.pais,
                                                    'provincia': inscripcion.persona.provincia,
                                                    'canton': inscripcion.persona.canton,
                                                    'parroquia': inscripcion.persona.parroquia,
                                                    'sector': inscripcion.persona.sector,
                                                    'ubicacionresidenciasalesforce': inscripcion.persona.ubicacionresidenciasalesforce,
                                                    'otraubicacionsalesforce': inscripcion.persona.otraubicacionsalesforce,
                                                    'nombrescompletosmadre': inscripcion.persona.nombrecompletomadre,
                                                    'nombrescompletospadre': inscripcion.persona.nombrecompletopadre,
                                                    'direccion': inscripcion.persona.direccion,
                                                    'direccion2': inscripcion.persona.direccion2,
                                                    'num_direccion': inscripcion.persona.num_direccion,
                                                    'telefono': inscripcion.persona.telefono,
                                                    'telefono_conv': inscripcion.persona.telefono_conv,
                                                    'email': inscripcion.persona.email,
                                                    'emailinst': inscripcion.persona.emailinst,
                                                    'fecha': inscripcion.fecha,
                                                    'fechainiciocarrera': inscripcion.fecha_inicio_carrera(),
                                                    'sede': inscripcion.sede,
                                                    'coordinacion': inscripcion.coordinacion,
                                                    'carrera': inscripcion.carrera,
                                                    'modalidad': inscripcion.modalidad,
                                                    'sesion': inscripcion.sesion,
                                                    'identificador': inscripcion.identificador,
                                                    'becapromocional':inscripcion.becapromocional,
                                                    'facturaidentificacion': clientefacturacion.identificacion,
                                                    'facturatipoidentificacion': clientefacturacion.tipo,
                                                    'facturanombre': clientefacturacion.nombre,
                                                    'facturadireccion': clientefacturacion.direccion,
                                                    'facturatelefono': clientefacturacion.telefono,
                                                    'facturaemail': clientefacturacion.email,
                                                    'prenivelacion': documentos.pre,
                                                    'observacionespre': documentos.observaciones_pre,
                                                    'comoseinformo': preguntas_inscripcion.comoseinformo,
                                                    'comoseinformootras': preguntas_inscripcion.comoseinformootras,
                                                    'comoseinformoredsocial': preguntas_inscripcion.comoseinformoredsocial,
                                                    'razonesmotivaron': preguntas_inscripcion.razonesmotivaron,
                                                    'etnia': perfil.raza,
                                                    'nacionalidadindigena': perfil.nacionalidadindigena,
                                                    'condicionado': inscripcion.condicionado,
                                                    'rindioexamen': snna.rindioexamen,
                                                    'fechaexamensnna': snna.fechaexamen,
                                                    'puntajesnna': snna.puntaje,
                                                    'homologar': documentos.homologar,
                                                    'examenubicacionidiomas': inscripcion.examenubicacionidiomas,
                                                    'malla': inscripcion.mi_malla(),
                                                    'observaciones': inscripcion.observaciones,
                                                    "tienediscapacidad": perfil.tienediscapacidad,
                                                    "tipodiscapacidad": perfil.tipodiscapacidad,
                                                    "porcientodiscapacidad": perfil.porcientodiscapacidad,
                                                    "carnetdiscapacidad": perfil.carnetdiscapacidad,
                                                    # "titulo": documentos.titulo,
                                                    # "fotos": documentos.fotos,
                                                    # "reg_cedula": documentos.cedula,
                                                    # "votacion": documentos.votacion,
                                                    # "cert_med": documentos.cert_med,
                                                    "eshomologacionexterna": documentos.eshomologacionexterna,
                                                    "cohorte": inscripcion.fechascorteposgrado,
                                                    "orientacion": inscripcion.orientacion,
                                                    "intercambio": inscripcion.intercambio,
                                                    "alumnoantiguo": inscripcion.alumnoantiguo,
                                                    "fuente": inscripcion.fuente,
                                                    "conveniohomologacion": documentos.conveniohomologacion})
                    form.editar(inscripcion)
                    form.sin_trabajo()
                    data['form'] = form
                    data['email_domain'] = EMAIL_DOMAIN
                    data['email_domain_estudiante'] = EMAIL_DOMAIN_ESTUDIANTES
                    data['pais_ecuador_id'] = PAIS_ECUADOR_ID
                    data['email_institucional_automatico'] = EMAIL_INSTITUCIONAL_AUTOMATICO_ESTUDIANTES
                    data['nacionalidad_indigena_id'] = NACIONALIDAD_INDIGENA_ID
                    data['modalidad_distancia'] = MODALIDAD_DISTANCIA
                    return render(request, "inscripciones/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'tipotrabajotitulacion':
                try:
                    data['title'] = u'Cambiar tipo trabajo de titulación'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['permite_modificar'] = True if persona.tiene_permiso('ctt.puede_modificar_inscripciones') else False
                    data['form'] = TipoTitulacionForm(initial={'tipotrabajotitulacion': inscripcion.tipotrabajotitulacion})
                    return render(request, "inscripciones/trabajotitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'notatrabajotitulacion':
                try:
                    data['title'] = u'Nota trabajo de titulación'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = NotaTrabajoTitulacionForm(initial={'nota': inscripcion.notatitulacion})
                    return render(request, "inscripciones/notatrabajotitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'extracurricular':
                try:
                    data['title'] = u'Otras Notas'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['pasantias'] = inscripcion.pasantias()
                    data['talleres'] = inscripcion.talleres()
                    data['practicas'] = inscripcion.practicas()
                    data['titulacion'] = inscripcion.titulacion()
                    data['vccs'] = inscripcion.vcc()
                    return render(request, "inscripciones/extracurricular.html", data)
                except Exception as ex:
                    pass

            if action == 'record':
                try:
                    data['title'] = u'Registro académico'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['records'] = inscripcion.recordacademico_set.all().order_by('asignaturamalla__nivelmalla', 'asignatura', 'fecha')
                    data['aprobadasmalla'] = inscripcion.recordacademico_set.filter(aprobada=True, asignaturamalla__isnull=False).count()
                    data['aprobadasotras'] = inscripcion.recordacademico_set.filter(aprobada=True, asignaturamalla__isnull=True).count()
                    data['reprobadasmalla'] = inscripcion.recordacademico_set.filter(aprobada=False, asignaturamalla__isnull=False).count()
                    data['reprobadasotras'] = inscripcion.recordacademico_set.filter(aprobada=False, asignaturamalla__isnull=True).count()
                    malla = inscripcion.mi_malla()
                    aprobadasmalla = AsignaturaMalla.objects.filter(recordacademico__inscripcion=inscripcion, recordacademico__aprobada=True).values_list('id', flat=True)
                    data['ampendientes'] = malla.asignaturamalla_set.filter(Q(itinerario=inscripcion.mi_itinerario()) | Q(itinerario__isnull=True)).exclude(id__in=aprobadasmalla).order_by('itinerario', 'nivelmalla', 'asignatura')
                    aprobadasmodulos = ModuloMalla.objects.filter(recordacademico__inscripcion=inscripcion, recordacademico__aprobada=True).values_list('id', flat=True)
                    data['mmpendientes'] = ModuloMalla.objects.filter(malla=malla).exclude(id__in=aprobadasmodulos).order_by('asignatura')
                    data['reporte_0'] = obtener_reporte("record_academico_btn_impresion_alumno")
                    data['reporte_1'] = obtener_reporte("homologacion_preliminar")
                    data['muestra_estado_nivelacion'] = MUESTRA_ESTADO_NIVELACION
                    data['homologa'] = inscripcion.documentos_entregados().homologar
                    return render(request, "inscripciones/record.html", data)
                except Exception as ex:
                    pass

            if action == 'historico':
                try:
                    data['title'] = u'Histórico de notas'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['record'] = record = RecordAcademico.objects.get(pk=request.GET['rec'])
                    data['historicos'] = record.historicorecordacademico_set.all().order_by('-fecha')
                    data['muestra_estado_nivelacion'] = MUESTRA_ESTADO_NIVELACION

                    if persona.id in PERSONA_ADMINS_ACADEMICO_ID:
                        data['menusinrestriccion'] = True

                    if persona.id in EDITA_NOTAS_RECORD_ACADEMICO_HISTORICO:
                        data['editanotashistorico'] = True
                    if persona.id in EDITA_NOTAS_RECORD_ACADEMICO_HISTORICO_INGLES:
                        data['editanotashistoricoingles'] = True
                    return render(request, "inscripciones/historico.html", data)
                except Exception as ex:
                    pass

            if action == 'realizar_ent':
                try:
                    data['title'] = u'Realizar entrevista'
                    data['inscripcion'] = inscripcion = InscripcionEntrevista.objects.get(pk=request.GET['id'])
                    data['respuesta'] = inscripcion.respuesta()
                    data['competencias'] = inscripcion.entrevista.competenciaentrevista_set.all().order_by('id')
                    return render(request, "inscripciones/aplicarentrevista.html", data)
                except Exception as ex:
                    pass

            if action == 'confirmarentrevista':
                try:
                    data['title'] = u'Confirmar entrevista'
                    data['proceso'] = proceso = RespuestaEntrevista.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/confirmarentrevista.html", data)
                except Exception as ex:
                    pass

            if action == 'addrecord':
                try:
                    data['title'] = u'Adicionar registro académico'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = RecordAcademicoForm()
                    form.record_normal()
                    form.adicionar(inscripcion)
                    data['form'] = form
                    return render(request, "inscripciones/addrecord.html", data)
                except Exception as ex:
                    pass

            if action == 'addrecordhomologada':
                try:
                    data['title'] = u'Adicionar homologación'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    convalidacion = None
                    homologacion = None
                    if ConvalidacionInscripcion.objects.filter(record__inscripcion=inscripcion).exists():
                        convalidacion = ConvalidacionInscripcion.objects.filter(record__inscripcion=inscripcion)[0]
                    elif HomologacionInscripcion.objects.filter(record__inscripcion=inscripcion).exists():
                        homologacion = HomologacionInscripcion.objects.filter(record__inscripcion=inscripcion)[0]
                    form = RecordAcademicoForm(initial={"convalidacion": True,
                                                        "carrera_he": convalidacion.carrera if convalidacion else '',
                                                        "anno_he": convalidacion.anno if convalidacion else datetime.now().year,
                                                        "observaciones_he": convalidacion.observaciones if convalidacion else '',
                                                        "carrera_hi": homologacion.carrera if homologacion else None,
                                                        "fecha_hi": homologacion.fecha if homologacion else datetime.now().date(),
                                                        "modalidad_hi": homologacion.modalidad if homologacion else None,
                                                        "observaciones_hi": homologacion.observaciones if homologacion else ''})
                    form.homologacion(inscripcion)
                    form.adicionar(inscripcion)
                    data['form'] = form
                    data['convalidacion'] = convalidacion
                    data['homologacion'] = homologacion
                    return render(request, "inscripciones/addrecordhomologada.html", data)
                except Exception as ex:
                    pass

            if action == 'addrecordhomologadamasiva':
                try:
                    data['title'] = u'Adicionar homologaciones'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['malla'] = malla = inscripcion.mi_malla()
                    data['ahora'] = datetime.now().date()
                    aprobadas = Asignatura.objects.filter(recordacademico__aprobada=True, asignaturamalla__recordacademico__inscripcion=inscripcion)
                    data['asignaturasmalla'] = AsignaturaMalla.objects.filter(malla=malla).exclude(asignatura__in=aprobadas).order_by('nivelmalla', 'asignatura')
                    data['asignaturasmodulo'] = ModuloMalla.objects.filter(malla=malla).exclude(asignatura__in=aprobadas).order_by('asignatura')
                    data['carreras'] = Carrera.objects.all()
                    data['tipos'] = TipoReconocimiento.objects.all()
                    data['tiposh'] = TipoHomologacion.objects.all()
                    if inscripcion.carrera.tipogrado.id == CUARTO_NIVEL_TITULACION_ID:
                        data['periodoshomologacion'] = Periodo.objects.filter(tipo__id=TIPO_PERIODO_POSGRADO)
                    else:
                        data['periodoshomologacion'] = Periodo.objects.filter(tipo__id=TIPO_PERIODO_GRADO)
                    return render(request, "inscripciones/addrecordhomologadamasiva.html", data)
                except Exception as ex:
                    pass

            if action == 'addhistorico':
                try:
                    data['title'] = u'Adicionar historico de registro académico'
                    data['record'] = record = RecordAcademico.objects.get(pk=request.GET['idr'])
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = HistoricoRecordAcademicoForm(initial={'asignatura': record.asignatura})
                    form.solo_asignatura(record.asignatura.id)
                    data['form'] = form
                    return render(request, "inscripciones/addhistorico.html", data)
                except Exception as ex:
                    pass

            if action == 'edithistorico':
                try:
                    data['title'] = u'Editar histórico de registro académico'
                    data['historico'] = historico = HistoricoRecordAcademico.objects.get(pk=request.GET['id'])
                    form = HistoricoRecordAcademicoForm(initial={"asignatura": historico.asignatura,
                                                                 "creditos": historico.creditos,
                                                                 "horas": historico.horas,
                                                                 "nota": historico.nota,
                                                                 "sinasistencia": historico.sinasistencia,
                                                                 "asistencia": historico.asistencia,
                                                                 "fecha": historico.fecha,
                                                                 "noaplica": historico.noaplica,
                                                                 "aprobada": historico.aprobada,
                                                                 "validacreditos": historico.validacreditos,
                                                                 "validapromedio": historico.validapromedio,
                                                                 "libreconfiguracion": historico.libreconfiguracion,
                                                                 "optativa": historico.optativa,
                                                                 "convalidacion": historico.convalidacion,
                                                                 "homologada": historico.homologada,
                                                                 "observaciones": historico.observaciones})
                    form.editar(historico)
                    data['form'] = form
                    return render(request, "inscripciones/edithistorico.html", data)
                except Exception as ex:
                    pass

            if action == 'delrecord':
                try:
                    data['title'] = u'Eliminar registro académico'
                    data['record'] = record = RecordAcademico.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/delrecord.html", data)
                except Exception as ex:
                    pass

            if action == 'delhistorico':
                try:
                    data['title'] = u'Eliminar histórico de registro acédemico'
                    data['historico'] = historico = HistoricoRecordAcademico.objects.get(pk=request.GET['id'])
                    if historico.inscripcion.historicorecordacademico_set.filter(asignatura=historico.asignatura).count() == 1:
                        data['url_back'] = '/inscripciones?action=record&id=' + str(historico.inscripcion.id)
                    else:
                        data['url_back'] = '/inscripciones?action=historico&id=' + str(historico.inscripcion.id) + ' &rec=' + str(historico.recordacademico.id)
                    return render(request, "inscripciones/delhistorico.html", data)
                except Exception as ex:
                    pass

            if action == 'convalidar':
                try:
                    data['title'] = u'Homologación de materia'
                    data['record'] = record = RecordAcademico.objects.get(pk=request.GET['id'])
                    data['convalidacion'] = convalidacion = record.datos_convalidacion()
                    if convalidacion:
                        form = ConvalidacionInscripcionForm(initial={'institucion': convalidacion.institucion.id if convalidacion.institucion else None,
                                                                     'carrera': convalidacion.carrera,
                                                                     'periodo': convalidacion.periodo,
                                                                     'tipohomologacion': convalidacion.tipohomologacion,
                                                                     'tiporeconocimiento': convalidacion.tiporeconocimiento,
                                                                     'tiemporeconocimiento': convalidacion.tiemporeconocimiento,
                                                                     'asignatura': convalidacion.asignatura,
                                                                     'anno': convalidacion.anno,
                                                                     'nota_ant': convalidacion.nota_ant,
                                                                     'creditos': convalidacion.creditos,
                                                                     'observaciones': convalidacion.observaciones})
                    else:
                        form = ConvalidacionInscripcionForm()
                    form.editar(convalidacion, record.inscripcion)
                    data['form'] = form
                    return render(request, "inscripciones/convalidar.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'homologar':
                try:
                    data['title'] = u'Homologacion de materia'
                    data['record'] = record = RecordAcademico.objects.get(pk=request.GET['id'])
                    data['homologacion'] = homologacion = record.datos_homologacion()
                    if homologacion:
                        form = HomologacionInscripcionForm(initial={'carrera': homologacion.carrera,
                                                                    'periodo': homologacion.periodo,
                                                                    'tipohomologacion': homologacion.tipohomologacion,
                                                                    'asignatura': homologacion.asignatura,
                                                                    'fecha': homologacion.fecha,
                                                                    'nota_ant': homologacion.nota_ant,
                                                                    'creditos': homologacion.creditos,
                                                                    'modalidad': homologacion.modalidad,
                                                                    'observaciones': homologacion.observaciones})
                    else:
                        form = HomologacionInscripcionForm()
                    form.editar(record.inscripcion)
                    data['form'] = form
                    return render(request, "inscripciones/homologar.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cargarfoto':
                try:
                    data['title'] = u'Subir foto'
                    data['form'] = CargarFotoForm()
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/cargarfoto.html", data)
                except Exception as ex:
                    pass

            if action == 'documentos':
                try:
                    data['title'] = u'Documentos y archivos'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['archivos'] = inscripcion.archivodocumentoinscripcion_set.all().order_by('fecha')
                    data['documentos'] = TipoDocumentoInscripcion.objects.all()
                    return render(request, "inscripciones/documentos.html", data)
                except Exception as ex:
                    pass

            if action == 'otrosrequisitosmalla':
                try:
                    data['title'] = u'Documentos y archivos'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['otrosrequisitos'] = inscripcion.mi_malla().otrosrequisitosmalla_set.all()
                    return render(request, "inscripciones/otrosrequisitosmalla.html", data)
                except Exception as ex:
                    pass

            if action == 'otrosrequisitosinscripcion':
                try:
                    data['title'] = u'Otros Requisitos de la Malla'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['idi'])
                    data['requisito'] = requisito = OtrosRequisitosMalla.objects.get(pk=request.GET['id'])
                    data['archivos'] = inscripcion.otrosrequisitoscumplirinscripcion_set.filter(otrosrequisitos=requisito)
                    return render(request, "inscripciones/otrosrequisitosinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'addotrosrequisitos':
                try:
                    data['title'] = u'Adicionar archivos'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    data['requisito'] = OtrosRequisitosMalla.objects.get(pk=request.GET['id'])
                    data['form'] = OtrosRequisitosInscripcionForm()
                    return render(request, "inscripciones/addotrosrequisitos.html", data)
                except Exception as ex:
                    pass

            if action == 'editotrosrequisitos':
                try:
                    data['title'] = u'Ediar archivos'
                    data['otrosrequisitos'] = otrosrequisitos = OtrosRequisitosCumplirInscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = OtrosRequisitosInscripcionForm(initial={'fecha': otrosrequisitos.fecha,
                                                                           'observaciones': otrosrequisitos.observaciones})
                    return render(request, "inscripciones/editotrosrequisitos.html", data)
                except Exception as ex:
                    pass

            if action == 'adddocumento':
                try:
                    data['title'] = u'Adicionar archivos'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = DocumentoInscripcionForm()
                    return render(request, "inscripciones/adddocumento.html", data)
                except Exception as ex:
                    pass

            if action == 'editdocumento':
                try:
                    data['title'] = u'Ediar archivos'
                    data['documento'] = documento = ArchivoDocumentoInscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = DocumentoInscripcionForm(initial={'tipo': documento.tipodocumentoinscripcion,
                                                                     'observaciones': documento.observaciones})
                    return render(request, "inscripciones/editdocumento.html", data)
                except Exception as ex:
                    pass

            if action == 'estudio':
                try:
                    data['title'] = u'Estudios realizados por el alumno'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['estudios'] = inscripcion.persona.estudiopersona_set.all().order_by('-fechainicio')
                    data['trabajos'] = inscripcion.persona.trabajopersona_set.all()
                    data['idiomas'] = inscripcion.persona.idiomadomina_set.all().order_by('idioma')
                    data['ficha'] = inscripcion.persona.mi_ficha()
                    data['movilidad'] = inscripcion.movilidadinscripcion_set.all()
                    return render(request, "inscripciones/estudio.html", data)
                except Exception as ex:
                    pass

            if action == 'infohomolacion':
                try:
                    data['title'] = u'Informacion Homologacion'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['solicitudes'] = solicitud = inscripcion.solicitudhomologacion_set.all().order_by('-periodo_homologacion__inicio')
                    data['persona_admision'] = persona.usuario.groups.filter(id__in=[12]).exists()
                    data['persona_secretaria'] = persona.usuario.groups.filter(id__in=[4]).exists()
                    return render(request, "inscripciones/infohomologacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addtrabajo':
                try:
                    data['title'] = u'Adicionar historial laboral'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = TrabajoPersonaForm()
                    return render(request, "inscripciones/addtrabajo.html", data)
                except Exception as ex:
                    pass

            if action == 'edittrabajo':
                try:
                    data['title'] = u'Editar historial laboral del estudiante'
                    data['trabajo'] = trabajo = TrabajoPersona.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    data['form'] = TrabajoPersonaForm(initial={'empresa': trabajo.empresa,
                                                               'industria': trabajo.industria,
                                                               'tipocontrato': trabajo.tipocontrato,
                                                               'afiliacioniess': trabajo.afiliacioniess,
                                                               'cargo': trabajo.cargo,
                                                               'ocupacion': trabajo.ocupacion,
                                                               'responsabilidades': trabajo.responsabilidades,
                                                               'telefono': trabajo.telefono,
                                                               'email': trabajo.email,
                                                               'sueldo': trabajo.sueldo,
                                                               'labora': False if trabajo.fechafin else True,
                                                               'fecha': trabajo.fecha,
                                                               'fechafin': trabajo.fechafin})
                    return render(request, "inscripciones/edittrabajo.html", data)
                except Exception as ex:
                    pass

            if action == 'deltrabajo':
                try:
                    data['title'] = u'Borrar seguimiento laboral del estudiante'
                    data['trabajo'] = TrabajoPersona.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    return render(request, "inscripciones/deltrabajo.html", data)
                except Exception as ex:
                    pass

            if action == 'addestudio':
                try:
                    data['title'] = u'Adicionar estudios basicos'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = EstudioEducacionBasicaForm()
                    return render(request, "inscripciones/addestudio.html", data)
                except Exception as ex:
                    pass

            if action == 'addestudiosuperior':
                try:
                    data['title'] = u'Adicionar estudios superiores'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    form = EstudioEducacionSuperiorForm()
                    form.adicionar()
                    data['form'] = form
                    data['cuarto_nivel_titulacion_id'] = CUARTO_NIVEL_TITULACION_ID
                    return render(request, "inscripciones/addestudiosuperior.html", data)
                except Exception as ex:
                    pass

            if action == 'editestudio':
                try:
                    data['title'] = u'Editar estudios basicos realizados'
                    data['estudio'] = estudio = EstudioPersona.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    form = EstudioEducacionBasicaForm(initial={'colegio': estudio.institucioneducacionbasica_id,
                                                               'titulocolegio': estudio.titulocolegio,
                                                               'abanderado': estudio.abanderado,
                                                               'especialidad': estudio.especialidadeducacionbasica_id})
                    form.editar(estudio)
                    data['form'] = form
                    data['permite_modificar'] = persona.tiene_permiso('ctt.puede_modificar_inscripciones')
                    return render(request, "inscripciones/editestudio.html", data)
                except Exception as ex:
                    pass

            if action == 'editestudiosuperior':
                try:
                    data['title'] = u'Editar estudios superiores realizados'
                    data['estudio'] = estudio = EstudioPersona.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    form = EstudioEducacionSuperiorForm(initial={'institucion': estudio.institucioneducacionsuperior_id,
                                                                 'niveltitulacion': estudio.niveltitulacion,
                                                                 'detalleniveltitulacion': estudio.detalleniveltitulacion,
                                                                 'carrera': estudio.carrera,
                                                                 'fechainicio': estudio.fechainicio,
                                                                 'fechafin': estudio.fechafin,
                                                                 'fecharegistro': estudio.fecharegistro,
                                                                 'cursando': estudio.cursando,
                                                                 'cicloactual': estudio.cicloactual,
                                                                 'titulo': estudio.titulo,
                                                                 'aliastitulo': estudio.aliastitulo,
                                                                 'fechagraduacion': estudio.fechagraduacion,
                                                                 'aplicabeca': estudio.aplicabeca,
                                                                 'montobeca': estudio.montobeca,
                                                                 'tipobeca': estudio.tipobeca,
                                                                 'tipofinanciamientobeca': estudio.tipofinanciamientobeca,
                                                                 'registro': estudio.registro})
                    form.editar(estudio)
                    data['form'] = form
                    data['cuarto_nivel_titulacion_id'] = CUARTO_NIVEL_TITULACION_ID
                    data['permite_modificar'] = persona.tiene_permiso('puede_modificar_inscripciones')
                    return render(request, "inscripciones/editestudiosuperior.html", data)
                except Exception as ex:
                    pass

            if action == 'delestudio':
                try:
                    data['title'] = u'Eliminar estudios realizados'
                    data['estudio'] = EstudioPersona.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    return render(request, "inscripciones/delestudio.html", data)
                except Exception as ex:
                    pass

            if action == 'validapromedio':
                try:
                    data['title'] = u'Valida Promedio'
                    data['record'] = RecordAcademico.objects.get(pk=request.GET['rec'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/validapromedio.html", data)
                except Exception as ex:
                    pass

            if action == 'novalidapromedio':
                try:
                    data['title'] = u'No Valida Promedio'
                    data['record'] = RecordAcademico.objects.get(pk=request.GET['rec'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/novalidapromedio.html", data)
                except Exception as ex:
                    pass

            if action == 'moverexamen':
                try:
                    data['title'] = u'Mover examen de inscripcion'
                    data['examen'] = ExamenInscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['idi'])
                    form = MoverExamenInscripcionForm()
                    form.mover(inscripcion)
                    data['form'] = form
                    return render(request, "inscripciones/moverexamen.html", data)
                except Exception as ex:
                    pass

            if action == 'moverentrevista':
                try:
                    data['title'] = u'Mover entrevista de inscripcion'
                    data['entrevista'] = InscripcionEntrevista.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['idi'])
                    form = MoverExamenInscripcionForm()
                    form.mover(inscripcion)
                    data['form'] = form
                    return render(request, "inscripciones/moverentrevista.html", data)
                except Exception as ex:
                    pass

            if action == 'delexamen':
                try:
                    data['title'] = u'Eliminar examen de inscripcion'
                    data['examen'] = ExamenInscripcion.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    return render(request, "inscripciones/delexamen.html", data)
                except Exception as ex:
                    pass

            if action == 'delentrevista':
                try:
                    data['title'] = u'Eliminar entrevista de inscripcion'
                    data['entrevista'] = InscripcionEntrevista.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    return render(request, "inscripciones/delentrevista.html", data)
                except Exception as ex:
                    pass

            if action == 'addidioma':
                try:
                    data['title'] = u'Adicionar estudios de idiomas realizados'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = IdiomaDominaForm()
                    return render(request, "inscripciones/addidioma.html", data)
                except Exception as ex:
                    pass

            if action == 'editidioma':
                try:
                    data['title'] = u'Editar idioma'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    data['idioma'] = idioma = IdiomaDomina.objects.get(pk=request.GET['id'])
                    data['form'] = IdiomaDominaForm(initial={'idioma': idioma.idioma,
                                                             'escritura': idioma.escritura,
                                                             'oral': idioma.oral,
                                                             'lectura': idioma.lectura})
                    data['permite_modificar'] = persona.tiene_permiso('puede_modificar_inscripciones')
                    return render(request, "inscripciones/editidioma.html", data)
                except Exception as ex:
                    pass

            if action == 'delidioma':
                try:
                    data['title'] = u'Eliminar idioma'
                    data['idioma'] = idioma = IdiomaDomina.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    return render(request, "inscripciones/delidioma.html", data)
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar inscripciones'
                    data['form'] = ImportarArchivoXLSForm()
                    return render(request, "inscripciones/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'deldocumento':
                try:
                    data['title'] = u'Eliminar archivo o documento'
                    data['archivo'] = archivo = ArchivoDocumentoInscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/deldocumento.html", data)
                except Exception as ex:
                    pass

            if action == 'fechainicioconvalidacion':
                try:
                    data['title'] = u'Fecha inicio convalidacion'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = FechaInicioConvalidacionInscripcionForm(initial={'fecha': inscripcion.fechainicioconvalidacion if inscripcion.fechainicioconvalidacion else datetime.now().date()})
                    return render(request, "inscripciones/fechainicioconvalidacion.html", data)
                except Exception as ex:
                    pass

            if action == 'alumalla':
                try:
                    data['title'] = u'Malla del alumno'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['malla'] = malla = inscripcion.mi_malla()
                    data['nivelesdemallas'] = NivelMalla.objects.all().order_by('id')
                    data['ejesformativos'] = EjeFormativo.objects.all().order_by('nombre')
                    data['modulos'] = malla.modulomalla_set.all()
                    return render(request, "inscripciones/alumalla.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'novalidar':
                try:
                    data['title'] = u'No considerar créditos'
                    data['record'] = record = RecordAcademico.objects.get(pk=request.GET['id'])
                    data['form'] = ConsiderarForm()
                    return render(request, "inscripciones/novalidar.html", data)
                except Exception as ex:
                    pass

            if action == 'validar':
                try:
                    data['title'] = u'Considerar créditos'
                    data['record'] = record = RecordAcademico.objects.get(pk=request.GET['id'])
                    data['form'] = ConsiderarForm()
                    return render(request, "inscripciones/validar.html", data)
                except Exception as ex:
                    pass

            if action == 'novalidarpromedio':
                try:
                    data['title'] = u'No considerar para promedio'
                    data['record'] = record = RecordAcademico.objects.get(pk=request.GET['id'])
                    data['form'] = ConsiderarForm()
                    return render(request, "inscripciones/novalidarpromedio.html", data)
                except Exception as ex:
                    pass

            if action == 'validarpromedio':
                try:
                    data['title'] = u'Considerar para promedio'
                    data['record'] = record = RecordAcademico.objects.get(pk=request.GET['id'])
                    data['form'] = ConsiderarForm()
                    return render(request, "inscripciones/validarpromedio.html", data)
                except Exception as ex:
                    pass

            if action == 'recalcularcreditos':
                try:
                    data['title'] = u'Recalcular creditos'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/recalcularcreditos.html", data)
                except Exception as ex:
                    pass

            if action == 'actalizarnivel':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    inscripcion.actualizar_nivel()
                    return HttpResponseRedirect("/inscripciones?id=" + request.GET['id'])
                except Exception as ex:
                    pass

            if action == 'desactivar':
                try:
                    data['title'] = u'Desactivar usuario'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/desactivar.html", data)
                except Exception as ex:
                    pass

            if action == 'activar':
                try:
                    data['title'] = u'Activar usuario'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/activar.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivarperfil':
                try:
                    data['title'] = u'Desactivar perfil de usuario'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/desactivarperfil.html", data)
                except Exception as ex:
                    pass

            if action == 'activarperfil':
                try:
                    data['title'] = u'Activar perfil de usuario'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/activarperfil.html", data)
                except Exception as ex:
                    pass

            if action == 'resetear':
                try:
                    data['title'] = u'Resetear clave del usuario'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/resetear.html", data)
                except Exception as ex:
                    pass

            if action == 'actividades':
                try:
                    data['title'] = u'Actividades extracurriculares'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['actividades'] = inscripcion.participanteactividadextracurricular_set.all().order_by('-actividad__fechafin')
                    return render(request, "inscripciones/actividades.html", data)
                except Exception as ex:
                    pass

            if action == 'examenesadmision':
                try:
                    data['title'] = u'Exámenes de admisión'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['examenes'] = inscripcion.exameninscripcion_set.all()
                    data['entrevistas'] = inscripcion.inscripcionentrevista_set.all()
                    data['reporte_0'] = obtener_reporte('resumen_entrevista')
                    return render(request, "inscripciones/examenesadmision.html", data)
                except Exception as ex:
                    pass

            if action == 'addexamen':
                try:
                    data['title'] = u'Adicionar exámen'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = ExamenInscripcionForm(initial={'hora': datetime.now().time().strftime("%H:%M"),
                                                          'fecha': datetime.now().date()})
                    form.adicionar(inscripcion)
                    data['form'] = form
                    return render(request, "inscripciones/addexamen.html", data)
                except Exception as ex:
                    pass

            if action == 'addexameni':
                try:
                    data['title'] = u'Adicionar exámen individual'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = ExamenIndividualForm(initial={'hora': datetime.now().time().strftime("%H:%M"),
                                                         'fecha': datetime.now().date()})
                    data['form'] = form
                    return render(request, "inscripciones/addexameni.html", data)
                except Exception as ex:
                    pass

            if action == 'addentrevista':
                try:
                    data['title'] = u'Adicionar entrevista'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = EntrevistaInscripcionForm()
                    data['form'] = form
                    return render(request, "inscripciones/addentrevista.html", data)
                except Exception as ex:
                    pass

            if action == 'horario':
                try:
                    data['title'] = u'Horario del estudiante'
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    periodo = matricula.nivel.periodo
                    data['materiasregulares'] = materiasregulares = Materia.objects.filter(materiaasignada__matricula=matricula).distinct()
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miércoles'], [4, 'Jueves'], [5, 'Viernes'],[6, 'Sábado'], [7, 'Domingo']]
                    data['clases'] = clases = Clase.objects.filter(materia__in=materiasregulares, activo=True).distinct()
                    data['turnos'] = Turno.objects.filter(clase__in=clases).distinct().order_by('comienza')
                    return render(request, "inscripciones/horario.html", data)
                except Exception as ex:
                    pass

            if action == 'addadministrativo':
                try:
                    data['title'] = u'Crear perfil de administrativo'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/addadministrativo.html", data)
                except Exception as ex:
                    pass

            if action == 'adddocente':
                try:
                    data['title'] = u'Crear perfil de profesor'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/adddocente.html", data)
                except Exception as ex:
                    pass

            if action == 'cambioitinerario':
                try:
                    data['title'] = u'Cambio de itinerario'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    malla = inscripcion.mi_malla()
                    form = CambioitinerarioForm(initial={'itinerario': inscripcion.mi_itinerario()})
                    form.itinerarios(malla)
                    data['form'] = form
                    return render(request, "inscripciones/cambioitinerario.html", data)
                except Exception as ex:
                    pass

            if action == 'habilitarmatricula':
                try:
                    data['title'] = u'Habilitar para matricula'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/habmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabilitarmatricula':
                try:
                    data['title'] = u'Deshabilitar para matricula'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/deshabmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'habilitarcambiomodalidad':
                try:
                    data['title'] = u'Habilitar para cambio de modalidad'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/habcambiomodalidad.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabilitarcambiomodalidad':
                try:
                    data['title'] = u'Deshabilitar para cambio de modalidad'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/deshabcambiomodalidad.html", data)
                except Exception as ex:
                    pass

            if action == 'abrirmatricula':
                try:
                    data['title'] = u'Administrador - Abrir Matricula'
                    data['matricula'] = matricula = Matricula.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['iid'])
                    data['nivel'] = nivel = matricula.nivel_cerrado()
                    return render(request, "inscripciones/abrirmatricula.html", data)
                except Exception as ex:
                    pass

            if action == 'habilitarhomologacion':
                try:
                    data['title'] = u'Habilitar homolgacion de proceso'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/habilitarhomologacion.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabilitarhomologacion':
                try:
                    data['title'] = u'Deshabilitar homolgacion de proceso'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/deshabilitarhomologacion.html", data)
                except Exception as ex:
                    pass

            if action == 'habilitarhomologacionpre':
                try:
                    data['title'] = u'Habilitar para matricula'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/habilitarhomologacionpre.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabilitarhomologacionpre':
                try:
                    data['title'] = u'Deshabilitar para matricula'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/deshabilitarhomologacionpre.html", data)
                except Exception as ex:
                    pass

            if action == 'habilitarexamen':
                try:
                    data['title'] = u'Habilitar para exámen'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/habexamen.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabilitarexamen':
                try:
                    data['title'] = u'Deshabilitar para exámen'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/deshabexamen.html", data)
                except Exception as ex:
                    pass

            if action == 'tribunaldefensa':
                try:
                    data['title'] = u'Tribunal de defensa'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    data['proyecto'] = proyectodefensa = DefensaProyectoGrado.objects.get(pk=request.GET['id'])
                    data['tribunal'] = proyectodefensa.tribunaldefensaproyectogrado_set.all()
                    return render(request, "inscripciones/listatribunal.html", data)
                except Exception as ex:
                    pass

            if action == 'editdefensa':
                try:
                    data['title'] = u'Establecer la defensa del proyecto'
                    data['proyecto'] = proyecto = DefensaProyectoGrado.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    form = DefensaProyectoGradoForm(initial={'lugar': proyecto.lugardefensa,
                                                             'fechasustentacion': proyecto.fechadefensa if proyecto.fechadefensa else proyecto.proyectogrado.fechalimite,
                                                             'horasustentacion': str(proyecto.horadefensa) if proyecto.horadefensa else '13:00',
                                                             'folio': proyecto.foliodefensa,
                                                             'acta': proyecto.numeroactadefensa,
                                                             'numerooportunidad': proyecto.numerooportunidad,
                                                             'observacion': proyecto.observaciones})
                    data['form'] = form
                    return render(request, "inscripciones/editdatosdefensa.html", data)
                except Exception as ex:
                    pass

            if action == 'editdefensaextra':
                try:
                    data['title'] = u'Establecer la defensa del proyecto'
                    data['proyecto'] = proyecto = DefensaProyectoGrado.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    form = DefensaProyectoGradoExtraForm(initial={'folio': proyecto.foliodefensa,
                                                                  'acta': proyecto.numeroactadefensa})
                    data['form'] = form
                    return render(request, "inscripciones/editdatosdefensaextra.html", data)
                except Exception as ex:
                    pass

            if action == 'deldefensa':
                try:
                    data['title'] = u'Elminar miembro tribunal'
                    data['proyecto'] = DefensaProyectoGrado.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    return render(request, "inscripciones/deldefensa.html", data)
                except Exception as ex:
                    pass

            if action == 'defensaproyecto':
                try:
                    data['title'] = u'Tribunal de defensa'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['proyecto'] = proyecto = inscripcion.mi_proyecto_grado()
                    data['defensas'] = proyecto.defensaproyectogrado_set.all()
                    return render(request, "inscripciones/listadefensa.html", data)
                except Exception as ex:
                    pass

            if action == 'editdefensaproyecto':
                try:
                    data['title'] = u'Establecer tribunal defensa'
                    data['proyecto'] = proyecto = ProyectoGrado.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    form = DefensaProyectoGradoForm(initial={'lugar': proyecto.lugardefensa,
                                                             'fechasustentacion': proyecto.fechadefensa if proyecto.fechadefensa else proyecto.fechalimite,
                                                             'horasustentacion': str(proyecto.horadefensa) if proyecto.horadefensa else '13:00'})
                    data['form'] = form
                    return render(request, "inscripciones/editdatosdefensa.html", data)
                except Exception as ex:
                    pass

            if action == 'notificartribunal':
                try:
                    data['title'] = u'Notificar Tribunal'
                    data['proyecto'] = DefensaProyectoGrado.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/notificartribunal.html", data)
                except Exception as ex:
                    pass

            if action == 'deltribunal':
                try:
                    data['title'] = u'Elminar miembro tribunal'
                    data['tribunal'] = TribunalDefensaProyectoGrado.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    return render(request, "inscripciones/deltribunal.html", data)
                except Exception as ex:
                    pass

            if action == 'addtribunal':
                try:
                    data['title'] = u'Establecer tribunal defensa'
                    data['defensas'] = defensas = DefensaProyectoGrado.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    form = TribunalProyectoGradoForm()
                    form.add(request.session['periodo'])
                    data['form'] = form
                    return render(request, "inscripciones/tribunal.html", data)
                except Exception as ex:
                    pass

            if action == 'edittribunal':
                try:
                    data['title'] = u'Editar tribunal defensa'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    data['tribunal'] = tribunal = TribunalDefensaProyectoGrado.objects.get(pk=request.GET['id'])
                    form = TribunalProyectoGradoForm(initial={'persona': tribunal.persona.id,
                                                              'hora': str(tribunal.horario) if tribunal.horario else '',
                                                              'factura': tribunal.factura,
                                                              'sede': tribunal.sede,
                                                              'tipofactura': tribunal.tipofactura,
                                                              'dedicacion': tribunal.dedicacion})
                    form.editar(request.session['periodo'], tribunal.persona)
                    data['form'] = form
                    return render(request, "inscripciones/edittribunal.html", data)
                except Exception as ex:
                    pass

            if action == 'adddefensa':
                try:
                    data['title'] = u'Establecer Fecha de Defensa'
                    data['defensas'] = proyecto = ProyectoGrado.objects.get(pk=request.GET['id'])
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['idi'])
                    data['form'] = DefensaProyectoGradoForm()
                    return render(request, "inscripciones/adddefensa.html", data)
                except Exception as ex:
                    pass

            if action == 'reconocimientoestudios':
                try:
                    data['title'] = u'Reconocimiento de Estudios'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['existereconocimiento'] = inscripcion.tiporeconocimientoinscripcion_set.exists()
                    data['reconocimiento'] = inscripcion.tiporeconocimientoinscripcion_set.all()
                    return render(request, "inscripciones/reconocimientoestudios.html", data)
                except Exception as ex:
                    pass

            if action == 'addreconocimiento':
                try:
                    data['title'] = u'Establecer Fecha de Defensa'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = ReconocimientoGraduadoForm()
                    return render(request, "inscripciones/addreconocimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'editreconocimiento':
                try:
                    data['title'] = u'Editar reconocimiento estudios'
                    data['reconocimiento'] = reconocimiento = TipoReconocimientoInscripcion.objects.get(pk=request.GET['id'])
                    form = ReconocimientoGraduadoForm(initial={'tiporeconocimiento': reconocimiento.tiporeconocimiento,
                                                               'institucion': reconocimiento.institucion_id,
                                                               'carrera': reconocimiento.carrera,
                                                               'conocimientos': reconocimiento.conocimientos,
                                                               'contenidos': reconocimiento.contenidos,
                                                               'tiemporeconocimiento': reconocimiento.tiemporeconocimiento})
                    form.editar(reconocimiento)
                    data['form'] = form
                    return render(request, "inscripciones/editreconocimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'delreconocimiento':
                try:
                    data['title'] = u'Eliminar Reconocimiento'
                    data['reconocimiento'] = reconocimiento = TipoReconocimientoInscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/delreconocimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'delotrosrequisitos':
                try:
                    data['title'] = u'Eliminar Reconocimiento'
                    data['otrosrequisitos'] = otrosrequisitos = OtrosRequisitosCumplirInscripcion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/delotrosrequisitos.html", data)
                except Exception as ex:
                    pass

            if action == 'movilidad':
                try:
                    data['title'] = u'Registrar estudiante con movilidad'
                    data['inscripcion'] = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = RegistroMovilidadForm()
                    data['cuarto_nivel_titulacion_id'] = CUARTO_NIVEL_TITULACION_ID
                    return render(request, "inscripciones/movilidad.html", data)
                except Exception as ex:
                    pass

            if action == 'editmovilidad':
                try:
                    data['title'] = u'Editar información de movilidad'
                    data['movilidad'] = movilidad = MovilidadInscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = RegistroMovilidadForm(initial={'periodo': movilidad.periodo,
                                                                  'universidad': movilidad.instituto,
                                                                  'asignaturas': movilidad.asignaturas,
                                                                  'tipomovilidad': movilidad.tipomovilidad,
                                                                  'homologacion': movilidad.homologacion,
                                                                  'tipomovilidadacademica': movilidad.tipomovilidadacademica})
                    return render(request, "inscripciones/editmovilidad.html", data)
                except Exception as ex:
                    pass

            if action == 'delmovilidad':
                try:
                    data['title'] = u'Eliminar registro movilidad'
                    inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['movilidad'] = inscripcion.movilidadinscripcion_set.all()[0]
                    return render(request, "inscripciones/delmovilidad.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiarinscripcion':
                try:
                    data['title'] = u'Cambiar ficha de inscripcion'
                    data['participante'] = participante = ParticipanteProyectoVinculacion.objects.get(pk=request.GET['id'])
                    form = CambiarFichaInscripcionForm()
                    form.adicionar(participante.inscripcion.persona)
                    data['form'] = form
                    return render(request, "inscripciones/cambiarinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiarinscripcionpasantia':
                try:
                    data['title'] = u'Cambiar pasantia a otra ficha de inscripcion'
                    data['pasantia'] = pasantia = Pasantia.objects.get(pk=request.GET['id'])
                    form = CambiarFichaInscripcionForm()
                    form.adicionar(pasantia.inscripcion.persona)
                    data['form'] = form
                    return render(request, "inscripciones/cambiarinscripcionpasantia.html", data)
                except Exception as ex:
                    pass

            if action == 'darperiodo':
                try:
                    data['title'] = u'Asignar Período a inscripción'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = PeriodoInscripcionForm()
                    data['form'] = form
                    return render(request, "inscripciones/darperiodo.html", data)
                except Exception as ex:
                    pass


            if action == 'cambiorecordhomologacion':
                try:
                    data['title'] = u'Editar homologacion historico'
                    data['historico'] = historico = HistoricoRecordAcademico.objects.get(pk=request.GET['id'])
                    data['form'] = CambioRecordHomologacionForm(initial={
                        "convalidacion": historico.convalidacion,
                        "homologada": historico.homologada})

                    return render(request, "inscripciones/cambiorecordhomologacion.html", data)
                except Exception as ex:
                    pass

            if action == 'importarcanvas':
                try:
                    data['title'] = u'Importar ID´S CANVAS'
                    data['form'] = ImportarArchivoXLSPeriodoForm()
                    return render(request, "inscripciones/importarcanvas.html", data)
                except Exception as ex:
                    pass

            if action == 'idsalesforce':
                try:
                    data['title'] = u'Agregar un ID de solicitud de SF'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['form'] = SalesForceSolicitudIdForm(initial={'nombre': inscripcion.idsalesforcei})
                    return render(request, "inscripciones/idsalesforce.html", data)
                except Exception as ex:
                    pass


            if action == 'addsolicitudhomologacion':
                try:
                    data['title'] = u'Nueva Solicitud'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    form = SolicitudHomologacionForm()
                    data['form'] = form
                    return render(request, "inscripciones/addsolicitudhomologacion.html", data)
                except Exception as ex:
                    pass

            if action == 'delsolicitudhomologacion':
                try:
                    data['title'] = u'Eliminar solicitud de homologacion'
                    data['solicitud'] = SolicitudHomologacion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/delsolicitudhomologacion.html", data)
                except Exception as ex:
                    pass

            if action == 'anularsolicitud':
                try:
                    data['title'] = u'Anular solicitud'
                    data['solicitud'] = solicitud = SolicitudHomologacion.objects.get(pk=request.GET['id'])
                    return render(request, "inscripciones/anularsolicitud.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de inscripciones'
                inscripciones = Inscripcion.objects.all()
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        inscripciones = inscripciones.filter(Q(persona__nombre1__icontains=search) |
                                                             Q(persona__nombre2__icontains=search) |
                                                             Q(persona__apellido1__icontains=search) |
                                                             Q(persona__apellido2__icontains=search) |
                                                             Q(persona__cedula__icontains=search) |
                                                             Q(persona__pasaporte__icontains=search) |
                                                             Q(identificador__icontains=search) |
                                                             Q(carrera__nombre__icontains=search) |
                                                             Q(persona__usuario__username__icontains=search)).distinct()
                    else:
                        inscripciones = inscripciones.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                             Q(persona__apellido2__icontains=ss[1])).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    inscripciones = inscripciones.filter(id=ids)
                else:
                    inscripciones = inscripciones.all()
                paging = MiPaginador(inscripciones, 15)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'inscripciones':
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
                request.session['paginador_url'] = 'inscripciones'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['inscripciones'] = page.object_list
                data['reporte_0'] = obtener_reporte('ficha_inscripcion')
                data['reporte_1'] = obtener_reporte("record_academico_btn_impresion_alumno")
                data['reporte_2'] = obtener_reporte('registro_matricula')
                data['reporte_3'] = obtener_reporte('certificado_matricula')
                data['reporte_4'] = obtener_reporte('certificado_de_promocion')
                data['reporte_5'] = obtener_reporte('certificado_de_promocion_ingles')
                data['reporte_6'] = obtener_reporte('certificado_cursounidadtitulacion_nota_n_inscripcion')
                data['reporte_7'] = obtener_reporte('seguimiento_silabus_matricula')
                data['reporte_8'] = obtener_reporte('certificado_no_adeudar_v1')
                data['control_unico_credenciales'] = CONTROL_UNICO_CREDENCIALES
                persona = request.session['persona']
                data['puede_modificar_matricula_admin'] = persona.cargoinstitucion_set.filter(cargo_id=3).exists()
                data['coordinacion'] = persona.en_grupo(11)
                data['admisiones'] = True if persona.en_grupo(12) else False
                data['sistemas'] = True if persona.en_grupo(3) else False
                data['centro'] = persona.en_grupo(47)
                if persona.id in PERM_ENTRAR_COMO_USUARIO:
                    data['entrar_como_usuario'] = True
                return render(request, "inscripciones/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
