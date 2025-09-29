# coding=utf-8
import json
from datetime import datetime

import xlrd
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

 
from decorators import last_access, secure_module
from settings import CAPACIDAD_MATERIA_INICIAL, ARCHIVO_TIPO_GENERAL, PERM_DIRECTOR_SIS
from ctt.commonviews import adduserdata
from ctt.forms import CoordinacionForm, \
    CargoPersonaForm, CajeroForm, SedeForm, AulaForm, CargoForm, \
    ParametrosClaseForm, ParametrosAplicacionForm, DatosCostosAplicacionForm, DatosBloqueoAplicacionForm, \
    DatosGeneralesForm, DatosFacturacionAplicacionForm, DatosUrlAplicacionForm,  PuntoVentaForm, \
    IvaForm, CuentaForm, TipoSolicitudForm, ReferenciaWebForm, CompetenciaGenericaForm, SesionForm, TurnoForm, \
    GrupoSistemaForm, ImportarArchivoXLSForm, InfoCorreoForm, EditarLogicaModeloForm, ApiForm

from ctt.funciones import log, bad_json, ok_json, url_back, generar_nombre, MiPaginador
from ctt.models import Sede, Coordinacion, CargoInstitucion, PuntoVenta, LugarRecaudacion, \
    IvaAplicado, Aula, Turno, Sesion, CuentaBanco, CompetenciaGenerica, Cargo, \
    Api, AulaCoordinacion, mi_institucion, Modulo, Reporte, GruposModulos, Archivo, Persona, null_to_text, ModeloEvaluativo


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    data['institucion'] = institucion = mi_institucion()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                try:
                    form = SedeForm(request.POST)
                    if form.is_valid():
                        sede = Sede(nombre=form.cleaned_data['nombre'],
                                    alias=form.cleaned_data['alias'],
                                    provincia=form.cleaned_data['provincia'],
                                    canton=form.cleaned_data['canton'],
                                    parroquia=form.cleaned_data['parroquia'],
                                    sector=form.cleaned_data['sector'],
                                    ciudad=form.cleaned_data['ciudad'],
                                    direccion=form.cleaned_data['direccion'],
                                    telefono=form.cleaned_data['telefono'])
                        sede.save(request)
                        log(u'Adiciono sede: %s' % sede, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addcoordinacion':
                try:
                    form = CoordinacionForm(request.POST)
                    if form.is_valid():
                        sede = Sede.objects.get(pk=request.POST['id'])
                        coordinacion = Coordinacion(nombre=form.cleaned_data['nombre'],
                                                    nombreingles=form.cleaned_data['nombreingles'],
                                                    sede=sede,
                                                    alias=form.cleaned_data['alias'])
                        coordinacion.save(request)
                        log(u'Adiciono coordinacion: %s' % coordinacion, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editar':
                try:
                    form = SedeForm(request.POST)
                    if form.is_valid():
                        sede = Sede.objects.get(pk=request.POST['id'])
                        sede.nombre = form.cleaned_data['nombre']
                        sede.provincia = form.cleaned_data['provincia']
                        sede.canton = form.cleaned_data['canton']
                        sede.parroquia = form.cleaned_data['parroquia']
                        sede.sector = form.cleaned_data['sector']
                        sede.ciudad = form.cleaned_data['ciudad']
                        sede.alias = form.cleaned_data['alias']
                        sede.direccion = form.cleaned_data['direccion']
                        sede.telefono = form.cleaned_data['telefono']
                        sede.save(request)
                        log(u'Modifico sede: %s' % sede, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addpersonacargo':
                try:
                    form = CargoPersonaForm(request.POST)
                    if form.is_valid():
                        cargo = form.cleaned_data['cargo']
                        persona = form.cleaned_data['persona']
                        if not cargo.multiples:
                            if CargoInstitucion.objects.filter(cargo=cargo).exists():
                                return bad_json(mensaje=u'Ya existe un responsable asignado a este cargo.')
                        cargoins = CargoInstitucion(cargo=cargo,
                                                    persona_id=form.cleaned_data['persona'])
                        cargoins.save(request)
                        log(u'Adiciono reponsable al cargo: %s a: %s' % (cargo, persona), request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addpersonacargosede':
                try:
                    form = CargoPersonaForm(request.POST)
                    if form.is_valid():
                        cargo = form.cleaned_data['cargo']
                        persona = form.cleaned_data['persona']
                        sede = Sede.objects.get(id=int(request.POST['id']))
                        if not cargo.multiples:
                            if CargoInstitucion.objects.filter(cargo=cargo).exists():
                                return bad_json(mensaje=u'Ya existe un responsable asignado a este cargo.')
                        cargoins = CargoInstitucion(cargo=cargo,
                                                    persona_id=form.cleaned_data['persona'],
                                                    sede=sede)
                        cargoins.save(request)
                        log(u'Adiciono reponsable al cargo sede: %s a: %s' % (cargo, persona), request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addcargo':
                try:
                    form = CargoForm(request.POST)
                    if form.is_valid():
                        nombre = form.cleaned_data['nombre']
                        if Cargo.objects.filter(nombre=nombre).exists():
                            return bad_json(mensaje=u'Ya existe un cargo con ese nombre.')
                        cargo = Cargo(nombre=nombre,
                                      multiples=form.cleaned_data['multiples'])
                        cargo.save(request)
                        log(u'Adiciono cargo: %s' % cargo, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delpersonacargo':
                try:
                    cargo = CargoInstitucion.objects.get(pk=request.POST['id'])
                    cargo.delete()
                    log(u'Elimino reponsable de cargo: %s' % cargo, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addbibliotecario':
                try:
                    form = ResponsableBibliotecaForm(request.POST)
                    biblioteca = Biblioteca.objects.get(pk=int(request.POST['id']))
                    if form.is_valid():
                        if ResponsableBiblioteca.objects.filter(biblioteca=biblioteca, persona_id=form.cleaned_data['persona']).exists():
                            return bad_json(mensaje=u'Ya existe esta persona registrada como responsable de esta biblioteca.')
                        bibliotecario = ResponsableBiblioteca(biblioteca=biblioteca,
                                                              persona_id=form.cleaned_data['persona'])
                        bibliotecario.save(request)
                        log(u'Adiciono bibliotecario de sede: %s' % bibliotecario, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addbiblioteca':
                try:
                    form = BibliotecaForm(request.POST)
                    sede = Sede.objects.get(pk=int(request.POST['id']))
                    if form.is_valid():
                        biblioteca = Biblioteca(sede=sede,
                                                nombre=form.cleaned_data['nombre'])
                        biblioteca.save(request)
                        log(u'Adiciono biblioteca a la sede: %s' % biblioteca, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addcajero':
                try:
                    form = CajeroForm(request.POST)
                    puntoventa = PuntoVenta.objects.get(pk=int(request.POST['id']))
                    if form.is_valid():
                        if LugarRecaudacion.objects.filter(puntodeventa=puntoventa, persona=form.cleaned_data['cajero']).exists():
                            lugarrecaudacion = LugarRecaudacion.objects.filter(puntodeventa=puntoventa, persona=form.cleaned_data['cajero'])[0]
                            lugarrecaudacion.activo = True
                            lugarrecaudacion.save(request)
                        else:
                            lugarrecaudacion = LugarRecaudacion(puntodeventa=puntoventa,
                                                                persona=form.cleaned_data['cajero'],
                                                                nombre=form.cleaned_data['nombre'])
                            lugarrecaudacion.save(request)
                        log(u'Adiciono o activo cajero: %s' % lugarrecaudacion, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delbibliotecario':
                try:
                    bibliotecario = ResponsableBiblioteca.objects.get(pk=request.POST['id'])
                    log(u'Elimino bibliotecario de la sede: %s' % bibliotecario, request, "del")
                    bibliotecario.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delcajero':
                try:
                    lugarrecaudacion = LugarRecaudacion.objects.get(pk=int(request.POST['id']))
                    if lugarrecaudacion.en_uso():
                        lugarrecaudacion.activo = False
                        lugarrecaudacion.save()
                        log(u'Desactivo cajero: %s' % lugarrecaudacion, request, "del")
                    else:
                        log(u'Elimino cajero: %s' % lugarrecaudacion, request, "del")
                        lugarrecaudacion.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'deshabilitarcajero':
                try:
                    lugarrecaudacion = LugarRecaudacion.objects.get(pk=int(request.POST['id']))
                    lugarrecaudacion.activo = False
                    lugarrecaudacion.save()
                    log(u'Desactivo cajero: %s' % lugarrecaudacion, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'habilitarcajero':
                try:
                    lugarrecaudacion = LugarRecaudacion.objects.get(pk=int(request.POST['id']))
                    lugarrecaudacion.activo = True
                    lugarrecaudacion.save()
                    log(u'Activo cajero: %s' % lugarrecaudacion, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'editcoordinacion':
                try:
                    form = CoordinacionForm(request.POST)
                    if form.is_valid():
                        coordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                        coordinacion.sede = form.cleaned_data['sede']
                        coordinacion.nombre = form.cleaned_data['nombre']
                        coordinacion.nombreingles = form.cleaned_data['nombreingles']
                        coordinacion.alias = form.cleaned_data['alias']
                        coordinacion.estado = form.cleaned_data['estado']
                        coordinacion.save(request)
                        log(u'Modifico coordinacion: %s' % coordinacion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delcoordinacion':
                try:
                    coordinacion = Coordinacion.objects.get(pk=int(request.POST['id']))
                    log(u'Elimino coordinacion: %s' % coordinacion, request, "del")
                    coordinacion.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addaula':
                try:
                    form = AulaForm(request.POST)
                    if form.is_valid():
                        sede = Sede.objects.get(pk=request.POST['id'])
                        aula = Aula(sede=sede,
                                    nombre=form.cleaned_data['nombre'],
                                    tipo=form.cleaned_data['tipo'],
                                    capacidad=form.cleaned_data['capacidad'])
                        aula.save(request)
                        for c in form.cleaned_data['coordinacion']:
                            ac = AulaCoordinacion(aula=aula,
                                                  coordinacion=c)
                            ac.save(request)
                        log(u'Adiciono aula: %s' % aula, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editaula':
                try:
                    form = AulaForm(request.POST)
                    if form.is_valid():
                        aula = Aula.objects.get(pk=request.POST['id'])
                        aula.nombre = form.cleaned_data['nombre']
                        aula.tipo = form.cleaned_data['tipo']
                        aula.capacidad = form.cleaned_data['capacidad']
                        aula.save()
                        aula.aulacoordinacion_set.all().delete()
                        for c in form.cleaned_data['coordinacion']:
                            ac = AulaCoordinacion(aula=aula,
                                                  coordinacion=c)
                            ac.save(request)
                        log(u'Adiciono aula: %s' % aula, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delaula':
                try:
                    aula = Aula.objects.get(pk=request.POST['id'])
                    aula.delete()
                    log(u'Elimino aula: %s' % aula, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addlms':
                try:
                    form = LmsForm(request.POST)
                    if form.is_valid():
                        lms = Lms(nombre= form.cleaned_data['nombre'],
                                  host = form.cleaned_data['host'],
                                  port = form.cleaned_data['puerto'],
                                  tipolms = form.cleaned_data['tipo'],
                                  key = form.cleaned_data['key'],
                                  activo = form.cleaned_data['activo'],
                                  logica_creacion_materia = form.cleaned_data['logica_creacion_materia'],
                                  logica_creacion_usuario = form.cleaned_data['logica_creacion_usuario'],
                                  logica_matricular_usuario_materia = form.cleaned_data['logica_matricular_usuario_materia'],
                                  logica_asignar_profesor_materia = form.cleaned_data['logica_asignar_profesor_materia'],
                                  logica_general = form.cleaned_data['logica_general'],
                                  logica_bloqueo_usuario = form.cleaned_data['logica_bloqueo_usuario'],
                                  logica_desbloqueo_usuario = form.cleaned_data['logica_desbloqueo_usuario'],
                                  logica_plantillas = form.cleaned_data['logica_plantillas'])
                        lms.save(request)
                        log(u'Adiciono LMS: %s' % lms, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editlms':
                try:
                    form = LmsForm(request.POST)
                    if form.is_valid():
                        lms = Lms.objects.get(pk=request.POST['id'])
                        lms.nombre = form.cleaned_data['nombre']
                        lms.host = form.cleaned_data['host']
                        lms.port = form.cleaned_data['puerto']
                        lms.tipolms = form.cleaned_data['tipo']
                        lms.key = form.cleaned_data['key']
                        lms.activo = form.cleaned_data['activo']
                        lms.logica_creacion_materia = form.cleaned_data['logica_creacion_materia']
                        lms.logica_creacion_usuario = form.cleaned_data['logica_creacion_usuario']
                        lms.logica_matricular_usuario_materia = form.cleaned_data['logica_matricular_usuario_materia']
                        lms.logica_asignar_profesor_materia = form.cleaned_data['logica_asignar_profesor_materia']
                        lms.logica_general = form.cleaned_data['logica_general']
                        lms.logica_bloqueo_usuario = form.cleaned_data['logica_bloqueo_usuario']
                        lms.logica_desbloqueo_usuario = form.cleaned_data['logica_desbloqueo_usuario']
                        lms.logica_plantillas = form.cleaned_data['logica_plantillas']
                        lms.save(request)
                        log(u'Edito informacion de LMS: %s' % lms, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'dellms':
                try:
                    lms = Lms.objects.get(pk=request.POST['id'])
                    lms.delete()
                    log(u'Elimino LMS: %s' % lms, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'editparametrosclases':
                try:
                    form = ParametrosClaseForm(request.POST)
                    if form.is_valid():
                        institucion.horarioestricto = form.cleaned_data['horarioestricto']
                        institucion.clasescontinuasautomaticas = form.cleaned_data['clasescontinuasautomaticas']
                        institucion.clasescierreautomatico = form.cleaned_data['clasescierreautomatico']
                        institucion.abrirmateriasenfecha = form.cleaned_data['abrirmateriasenfecha']
                        institucion.minutosapeturaantes = form.cleaned_data['minutosapeturaantes']
                        institucion.minutosapeturadespues = form.cleaned_data['minutosapeturadespues']
                        institucion.minutoscierreantes = form.cleaned_data['minutoscierreantes']
                        institucion.egresamallacompleta = form.cleaned_data['egresamallacompleta']
                        institucion.save(request)
                        log(u'Modifico parametros de clases: %s' % institucion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editdatosaplicacion':
                try:
                    form = ParametrosAplicacionForm(request.POST)
                    if form.is_valid():
                        institucion.defaultpassword = form.cleaned_data['defaultpassword']
                        institucion.claveusuariocedula = form.cleaned_data['claveusuariocedula']
                        institucion.controlunicocredenciales = form.cleaned_data['controlunicocredenciales']
                        institucion.actualizarfotoadministrativos = form.cleaned_data['actualizarfotoadministrativos']
                        institucion.actualizarfotoalumnos = form.cleaned_data['actualizarfotoalumnos']
                        institucion.nombreusuariocedula = form.cleaned_data['nombreusuariocedula']
                        institucion.correoobligatorio = form.cleaned_data['correoobligatorio']
                        institucion.preguntasinscripcion = form.cleaned_data['preguntasinscripcion']
                        institucion.save(request)
                        log(u'Modifico parametros de aplicacion: %s' % institucion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editdatoscostos':
                try:
                    form = DatosCostosAplicacionForm(request.POST)
                    if form.is_valid():
                        institucion.contribuyenteespecial = form.cleaned_data['contribuyenteespecial']
                        institucion.obligadocontabilidad = form.cleaned_data['obligadocontabilidad']
                        institucion.estudiantevefecharubro = form.cleaned_data['estudiantevefecharubro']
                        institucion.costoperiodo = form.cleaned_data['costoperiodo']
                        institucion.costoenmalla = form.cleaned_data['costoenmalla']
                        institucion.matriculacondeuda = form.cleaned_data['matriculacondeuda']
                        institucion.pagoestrictoasistencia = form.cleaned_data['pagoestrictoasistencia']
                        institucion.pagoestrictonotas = form.cleaned_data['pagoestrictonotas']
                        institucion.cuotaspagoestricto = form.cleaned_data['cuotaspagoestricto']
                        institucion.formalizarxporcentaje = form.cleaned_data['formalizarxporcentaje']
                        institucion.formalizarxmatricula = form.cleaned_data['formalizarxmatricula']
                        institucion.porcentajeformalizar = form.cleaned_data['porcentajeformalizar']
                        institucion.vencematriculaspordias = form.cleaned_data['vencematriculaspordias']
                        institucion.diashabiles = form.cleaned_data['diashabiles']
                        institucion.diasmatriculaexpirapresencial = form.cleaned_data['diasmatriculaexpirapresencial']
                        institucion.diasmatriculaexpirasemipresencial = form.cleaned_data['diasmatriculaexpirasemipresencial']
                        institucion.diasmatriculaexpiradistancia = form.cleaned_data['diasmatriculaexpiradistancia']
                        institucion.diasmatriculaexpiraonline = form.cleaned_data['diasmatriculaexpiraonline']
                        institucion.diasmatriculaexpirahibrida = form.cleaned_data['diasmatriculaexpirahibrida']
                        institucion.fechaexpiramatriculagrado = form.cleaned_data['fechaexpiramatriculagrado']
                        institucion.fechaexpiramatriculaposgrado = form.cleaned_data['fechaexpiramatriculaposgrado']
                        institucion.save(request)
                        log(u'Modifico parametros de aplicacion: %s' % institucion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editdatosbloqueo':
                try:
                    form = DatosBloqueoAplicacionForm(request.POST)
                    if form.is_valid():
                        institucion.deudabloqueaasistencia = form.cleaned_data['deudabloqueaasistencia']
                        institucion.deudabloqueamimalla = form.cleaned_data['deudabloqueamimalla']
                        institucion.deudabloqueamishorarios = form.cleaned_data['deudabloqueamishorarios']
                        institucion.deudabloqueadocumentos = form.cleaned_data['deudabloqueadocumentos']
                        institucion.deudabloqueacronograma = form.cleaned_data['deudabloqueacronograma']
                        institucion.deudabloqueamatriculacion = form.cleaned_data['deudabloqueamatriculacion']
                        institucion.deudabloqueasolicitud = form.cleaned_data['deudabloqueasolicitud']
                        institucion.deudabloqueanotas = form.cleaned_data['deudabloqueanotas']
                        institucion.save(request)
                        log(u'Modifico parametros de aplicacion: %s' % institucion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editdatosgeneralessolicitudes':
                try:
                    form = DatosGeneralesForm(request.POST)
                    if form.is_valid():
                        institucion.solicitudnumeracion = form.cleaned_data['solicitudnumeracion']
                        institucion.solicitudnumeroautomatico = form.cleaned_data['solicitudnumeroautomatico']
                        institucion.permitealumnoregistrar = form.cleaned_data['permitealumnoregistrar']
                        institucion.especificarcantidadsolicitud = form.cleaned_data['especificarcantidadsolicitud']
                        institucion.diasvencimientosolicitud = form.cleaned_data['diasvencimientosolicitud']
                        institucion.permitealumnoelegirresponsable = form.cleaned_data['permitealumnoelegirresponsable']
                        institucion.save(request)
                        log(u'Modifico parametros de aplicacion: %s' % institucion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editdatosfactura':
                try:
                    form = DatosFacturacionAplicacionForm(request.POST)
                    if form.is_valid():
                        institucion.facturacionelectronicaexterna = form.cleaned_data['facturacionelectronicaexterna']
                        institucion.urlfacturacion = form.cleaned_data['urlfacturacion']
                        institucion.apikey = form.cleaned_data['apikey']
                        institucion.pfx = form.cleaned_data['pfx']
                        institucion.codigoporcentajeiva = form.cleaned_data['codigoporcentajeiva']
                        institucion.proveedorfacturacion = form.cleaned_data['proveedorfacturacion']
                        institucion.save(request)
                        log(u'Modifico parametros de aplicacion: %s' % institucion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editdatosurlapp':
                try:
                    form = DatosUrlAplicacionForm(request.POST)
                    if form.is_valid():
                        institucion.urlaplicacionandroid = form.cleaned_data['urlaplicacionandroid']
                        institucion.urlaplicacionios = form.cleaned_data['urlaplicacionios']
                        institucion.urlaplicacionwindows = form.cleaned_data['urlaplicacionwindows']
                        institucion.save(request)
                        log(u'Modifico parametros de aplicacion: %s' % institucion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editdatosbiblioteca':
                try:
                    form = DatosBibliotecaForm(request.POST)
                    if form.is_valid():
                        institucion.usabiblioteca = form.cleaned_data['usabiblioteca']
                        institucion.documentoscoleccion = form.cleaned_data['documentoscoleccion']
                        institucion.documentosautonumeracion = form.cleaned_data['documentosautonumeracion']
                        institucion.documentoscoleccionautonumeracion = form.cleaned_data['documentoscoleccionautonumeracion']
                        institucion.save(request)
                        log(u'Modifico parametros de biblioteca: %s' % institucion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addpuntoventa':
                try:
                    form = PuntoVentaForm(request.POST)
                    sede = data['coordinacionseleccionada'].sede
                    if form.is_valid():
                        if PuntoVenta.objects.filter(puntoventa=form.cleaned_data['puntoventa'], establecimiento=form.cleaned_data['establecimiento']).exists():
                            return bad_json(mensaje=u'Ya existe un Punto de Venta con esas especificaciones')
                        pv = PuntoVenta(puntoventa=form.cleaned_data['puntoventa'],
                                        sede=sede,
                                        tipoemision=form.cleaned_data['tipoemision'],
                                        secuenciafactura=form.cleaned_data['secuenciafactura'],
                                        secuenciarecibopago=form.cleaned_data['secuenciarecibopago'],
                                        imprimirrecibo=form.cleaned_data['imprimirrecibopago'],
                                        modeloimpresionfactura=form.cleaned_data['modeloimpresionfactura'],
                                        modeloimpresionrecibopago=form.cleaned_data['modeloimpresionrecibopago'],
                                        modeloimpresionnotacredito=form.cleaned_data['modeloimpresionnotacredito'],
                                        ambientefacturacion=form.cleaned_data['ambientefacturacion'],
                                        facturaelectronica=form.cleaned_data['facturaelectronica'],
                                        numeracionemitida=form.cleaned_data['numeracionemitida'],
                                        imprimirfactura=form.cleaned_data['imprimirfactura'],
                                        establecimiento=form.cleaned_data['establecimiento'])
                        pv.save(request)
                        log(u'Adiciono punto de venta: %s' % pv, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editpuntoventa':
                try:
                    form = PuntoVentaForm(request.POST)
                    puntoventa = PuntoVenta.objects.get(pk=int(request.POST['id']))
                    if form.is_valid():
                        if PuntoVenta.objects.filter(puntoventa=form.cleaned_data['puntoventa'], establecimiento=form.cleaned_data['establecimiento']).exclude(id=puntoventa.id).exists():
                            return bad_json(mensaje=u'Ya existe un Punto de Venta con esas especificaciones')
                        puntoventa.ambientefacturacion = form.cleaned_data['ambientefacturacion']
                        puntoventa.tipoemision = form.cleaned_data['tipoemision']
                        puntoventa.numeracionemitida = form.cleaned_data['numeracionemitida']
                        puntoventa.modeloimpresionfactura = form.cleaned_data['modeloimpresionfactura']
                        puntoventa.modeloimpresionrecibopago = form.cleaned_data['modeloimpresionrecibopago']
                        puntoventa.modeloimpresionnotacredito = form.cleaned_data['modeloimpresionnotacredito']
                        puntoventa.secuenciafactura = form.cleaned_data['secuenciafactura']
                        puntoventa.secuencianotacredito = form.cleaned_data['secuencianotacredito']
                        puntoventa.secuenciarecibopago = form.cleaned_data['secuenciarecibopago']
                        if not puntoventa.mis_cajeros():
                            puntoventa.puntoventa = form.cleaned_data['puntoventa']
                            puntoventa.facturaelectronica = form.cleaned_data['facturaelectronica']
                            puntoventa.imprimirfactura = form.cleaned_data['imprimirfactura']
                            puntoventa.imprimirrecibo = form.cleaned_data['imprimirrecibopago']
                            puntoventa.imprimirnotacredito = form.cleaned_data['imprimirnotacredito']
                            puntoventa.establecimiento = form.cleaned_data['establecimiento']
                        puntoventa.save(request)
                        log(u'Modificó punto de venta: %s' % puntoventa, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delpunto':
                try:
                    puntoventa = PuntoVenta.objects.get(pk=int(request.POST['id']))
                    if puntoventa.en_uso():
                        puntoventa.activo = False
                        puntoventa.save()
                        log(u'Desactivo punto venta: %s' % puntoventa, request, "del")
                    else:
                        log(u'Elimino punto venta: %s' % puntoventa, request, "del")
                        puntoventa.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addiva':
                try:
                    form = IvaForm(request.POST)
                    if form.is_valid():
                        iva = IvaAplicado(descripcion=form.cleaned_data['descripcion'],
                                          porcientoiva=form.cleaned_data['porcientoiva'],
                                          codigo=form.cleaned_data['codigo'])
                        iva.save(request)
                        log(u'Adiciono iva: %s' % iva, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editiva':
                try:
                    form = IvaForm(request.POST)
                    if form.is_valid():
                        iva = IvaAplicado.objects.get(pk=request.POST['id'])
                        iva.descripcion = form.cleaned_data['descripcion']
                        iva.porcientoiva = form.cleaned_data['porcientoiva']
                        iva.codigo = form.cleaned_data['codigo']
                        iva.save(request)
                        log(u'Modifico iva: %s' % iva, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'deliva':
                try:
                    iva = IvaAplicado.objects.get(pk=request.POST['id'])
                    log(u'Elimino iva: %s' % iva, request, "del")
                    iva.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'activariva':
                try:
                    iva = IvaAplicado.objects.get(pk=request.POST['id'])
                    iva.activo = True
                    iva.save()
                    log(u'Activo iva: %s' % iva, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'desactivariva':
                try:
                    iva = IvaAplicado.objects.get(pk=request.POST['id'])
                    iva.activo = False
                    iva.save()
                    log(u'Desactivo iva: %s' % iva, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addcuenta':
                try:
                    form = CuentaForm(request.POST)
                    if form.is_valid():
                        cuenta = CuentaBanco(banco=form.cleaned_data['banco'],
                                             tipocuenta=form.cleaned_data['tipocuenta'],
                                             representante=form.cleaned_data['representante'],
                                             numero=form.cleaned_data['numero'])
                        cuenta.save(request)
                        log(u'Adiciono cuenta: %s' % cuenta, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editcuenta':
                try:
                    form = CuentaForm(request.POST)
                    if form.is_valid():
                        cuenta = CuentaBanco.objects.get(pk=request.POST['id'])
                        cuenta.banco = form.cleaned_data['banco']
                        cuenta.tipocuenta = form.cleaned_data['tipocuenta']
                        cuenta.numero = form.cleaned_data['numero']
                        cuenta.representante = form.cleaned_data['representante']
                        cuenta.save(request)
                        log(u'Modifico cuenta: %s' % cuenta, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delcuenta':
                try:
                    cuenta = CuentaBanco.objects.get(pk=request.POST['id'])
                    log(u'Elimino cuenta: %s' % cuenta, request, "del")
                    cuenta.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'activarcuenta':
                try:
                    cuenta = CuentaBanco.objects.get(pk=request.POST['id'])
                    cuenta.activo = True
                    cuenta.save()
                    log(u'Activo cuenta: %s' % cuenta, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'desactivarcuenta':
                try:
                    cuenta = CuentaBanco.objects.get(pk=request.POST['id'])
                    cuenta.activo = False
                    cuenta.save()
                    log(u'Desactivo cuenta: %s' % cuenta, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'editsolicitud':
                try:
                    form = TipoSolicitudForm(request.POST)
                    if form.is_valid():
                        solicitud = TipoSolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                        solicitud.nombre = form.cleaned_data['nombre']
                        solicitud.valor = form.cleaned_data['valor']
                        solicitud.descripcion = form.cleaned_data['descripcion']
                        solicitud.costo_unico = form.cleaned_data['costo_unico']
                        solicitud.costo_base = form.cleaned_data['costo_base']
                        solicitud.gratismatricula = form.cleaned_data['gratismatricula']
                        solicitud.grupos = form.cleaned_data['grupos']
                        solicitud.save(request)
                        log(u'Modifico solicitud: %s' % solicitud, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addsolicitud':
                try:
                    form = TipoSolicitudForm(request.POST)
                    if form.is_valid():
                        solicitud = TipoSolicitudSecretariaDocente(nombre=form.cleaned_data['nombre'],
                                                                   valor=form.cleaned_data['valor'],
                                                                   descripcion=form.cleaned_data['descripcion'],
                                                                   costo_unico=form.cleaned_data['costo_unico'],
                                                                   costo_base=form.cleaned_data['costo_base'],
                                                                   gratismatricula=form.cleaned_data['gratismatricula'])
                        solicitud.save(request)
                        solicitud.grupos.set(form.cleaned_data['grupos'])
                        solicitud.save(request)
                        log(u'Modifico solicitud: %s' % solicitud, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delsolicitud':
                try:
                    solicitud = TipoSolicitudSecretariaDocente.objects.get(pk=request.POST['id'])
                    log(u'Elimino solicitud: %s' % solicitud, request, "del")
                    solicitud.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addreferenciaweb':
                try:
                    form = ReferenciaWebForm(request.POST, request.FILES)
                    if form.is_valid():
                        from bib.models import ReferenciaWeb
                        newfile = None
                        if 'logo' in request.FILES:
                            newfile = request.FILES['logo']
                            newfile._name = generar_nombre("logo", newfile._name)
                        rf = ReferenciaWeb(url=form.cleaned_data['url'],
                                           nombre=form.cleaned_data['nombre'],
                                           logo=newfile)
                        rf.save(request)
                        log(u'Adiciono referencia web: %s' % rf, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editreferenciaweb':
                try:
                    form = ReferenciaWebForm(request.POST, request.FILES)
                    if form.is_valid():
                        from bib.models import ReferenciaWeb
                        rf = ReferenciaWeb.objects.get(pk=int(request.POST['id']))
                        newfile = rf.logo
                        if 'logo' in request.FILES:
                            newfile = request.FILES['logo']
                            newfile._name = generar_nombre("logo", newfile._name)
                        rf.url=form.cleaned_data['url']
                        rf.nombre=form.cleaned_data['nombre']
                        rf.logo=newfile
                        rf.save(request)
                        log(u'Modifico referencia web: %s' % rf, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delreferenciaweb':
                try:
                    from bib.models import ReferenciaWeb
                    rf = ReferenciaWeb.objects.get(pk=request.POST['id'])
                    log(u'Elimino Referencia Web: %s' % rf, request, "del")
                    rf.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'tipourl':
                try:
                    form = ReferenciaWebForm(request.POST, request.FILES)
                    if form.is_valid():
                        from bib.models import OtraBibliotecaVirtual
                        otrabibliotecavirtual = OtraBibliotecaVirtual.objects.filter(id=request.POST['id'])[0]
                        otrabibliotecavirtual.externa = True if request.POST['valor'] == 'true' else False
                        otrabibliotecavirtual.save()
                        log(u'Modifico estado Tipo de URL: %s' % otrabibliotecavirtual, request, "edit")
                        return ok_json()
                except Exception as ex:
                    return bad_json(error=3)

            if action == 'addbibvirtual':
                try:
                    form = ReferenciaWebForm(request.POST, request.FILES)
                    if form.is_valid():
                        from bib.models import OtraBibliotecaVirtual
                        newfile = None
                        if 'logo' in request.FILES:
                            newfile = request.FILES['logo']
                            newfile._name = generar_nombre("logo", newfile._name)
                        rf = OtraBibliotecaVirtual(url=form.cleaned_data['url'],
                                                   nombre=form.cleaned_data['nombre'],
                                                   descripcion=form.cleaned_data['descripcion'],
                                                   logo=newfile)
                        rf.save(request)
                        log(u'Adiciono biblioteca virtual: %s' % rf, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editbibvirtual':
                try:
                    form = ReferenciaWebForm(request.POST, request.FILES)
                    if form.is_valid():
                        from bib.models import OtraBibliotecaVirtual
                        rf = OtraBibliotecaVirtual.objects.get(pk=int(request.POST['id']))
                        newfile = rf.logo
                        if 'logo' in request.FILES:
                            newfile = request.FILES['logo']
                            newfile._name = generar_nombre("logo", newfile._name)
                        rf.url = form.cleaned_data['url']
                        rf.nombre = form.cleaned_data['nombre']
                        rf.descripcion = form.cleaned_data['descripcion']
                        rf.logo = newfile
                        rf.save(request)
                        log(u'Modifico biblioteca virtual: %s' % rf, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delbibvirtual':
                try:
                    from bib.models import OtraBibliotecaVirtual
                    rf = OtraBibliotecaVirtual.objects.get(pk=request.POST['id'])
                    log(u'Elimino Biblioteca virtual: %s' % rf, request, "del")
                    rf.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addcompetenciagenerica':
                try:
                    form = CompetenciaGenericaForm(request.POST)
                    if form.is_valid():
                        competencia = CompetenciaGenerica(nombre = form.cleaned_data['nombre'])
                        competencia.save(request)
                        log(u'Adiciono competencia genérica: %s' % competencia, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addtipotrabajotitulacion':
                try:
                    form = TipoTrabajoTitulacionForm(request.POST)
                    if form.is_valid():
                        tipotrabajo = TipoTrabajoTitulacion(nombre = form.cleaned_data['nombre'],
                                                            codigosniese = form.cleaned_data['codigosniese'])
                        tipotrabajo.save(request)
                        log(u'Adiciono competencia genérica: %s' % tipotrabajo, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delcompetencia':
                try:
                    competencia = CompetenciaGenerica.objects.get(pk=request.POST['id'])
                    competencia.delete()
                    log(u'Elimino competencia genérica: %s' % competencia, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'deltipotrabajotitulacion':
                try:
                    tipotrabajo = TipoTrabajoTitulacion.objects.get(pk=request.POST['id'])
                    tipotrabajo.delete()
                    log(u'Elimino Tipo de Trabajo de Titulación: %s' % tipotrabajo, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addsesion':
                try:
                    form = SesionForm(request.POST)
                    if form.is_valid():
                        sesion = Sesion(nombre=form.cleaned_data['nombre'],
                                        termina=form.cleaned_data['termina'],
                                        codigo=form.cleaned_data['codigo'],
                                        lunes=form.cleaned_data['lunes'],
                                        martes=form.cleaned_data['martes'],
                                        miercoles=form.cleaned_data['miercoles'],
                                        jueves=form.cleaned_data['jueves'],
                                        viernes=form.cleaned_data['viernes'],
                                        sabado=form.cleaned_data['sabado'],
                                        domingo=form.cleaned_data['domingo'],
                                        comienza=form.cleaned_data['comienza'])
                        sesion.save(request)
                        log(u'Adiciono sesion: %s' % sesion, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delsesion':
                try:
                    sesion = Sesion.objects.get(pk=request.POST['id'])
                    sesion.delete()
                    log(u'Elimino sesion: %s' % sesion, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addturno':
                try:
                    form = TurnoForm(request.POST)
                    if form.is_valid():
                        turno = Turno(sesion=form.cleaned_data['sesion'],
                                      termina=form.cleaned_data['termina'],
                                      horas=form.cleaned_data['horas'],
                                      comienza=form.cleaned_data['comienza'])
                        turno.save(request)
                        log(u'Adiciono turno: %s' % turno, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delturno':
                try:
                    turno = Turno.objects.get(pk=request.POST['id'])
                    turno.delete()
                    log(u'Elimino turno: %s' % turno, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addapi':
                try:
                    form = ApiForm(request.POST)
                    if form.is_valid():
                        api = Api(tipo=form.cleaned_data['tipo'],
                                  nombrecorto=form.cleaned_data['nombrecorto'],
                                  descripcion=form.cleaned_data['descripcion'],
                                  key=form.cleaned_data['key'],
                                  logicaapi=form.cleaned_data['logicaapi'])
                        api.save()
                        log(u'Adiciono api: %s' % api.nombrecorto, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editapi':
                try:
                    form = ApiForm(request.POST)
                    if form.is_valid():
                        api = Api.objects.get(pk=request.POST['id'])
                        api.nombrecorto = form.cleaned_data['nombrecorto']
                        api.descripcion = form.cleaned_data['descripcion']
                        api.key = form.cleaned_data['key']
                        api.tipo = form.cleaned_data['tipo']
                        api.logicaapi = form.cleaned_data['logicaapi']
                        api.save(request)
                        log(u'Edito informacion de API: %s' % api, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delapi':
                try:
                    api = Api.objects.get(pk=request.POST['id'])
                    api.delete()
                    log(u'Elimino API: %s' % api, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addgrupo':
                try:
                    form = GrupoSistemaForm(request.POST)
                    if form.is_valid():
                        grupo = Group(name=null_to_text(form.cleaned_data['nombre']))
                        grupo.save()
                        log(u'Adiciono grupo: %s' % grupo, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editgrupo':
                try:
                    form = GrupoSistemaForm(request.POST)
                    if form.is_valid():
                        grupo = Group.objects.get(pk=request.POST['id'])
                        grupo.name = null_to_text(form.cleaned_data['nombre'])
                        grupo.save()
                        log(u'Modifico grupo: %s' % grupo, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delgrupo':
                try:
                    grupo = Group.objects.get(pk=request.POST['id'])
                    log(u'Elimino grupo: %s' % grupo, request, "del")
                    grupo.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addpermisogrupo':
                try:
                    grupo = Group.objects.get(pk=int(request.POST['id']))
                    datos = json.loads(request.POST['lista'])
                    for dato in datos:
                        permiso = Permission.objects.get(pk=int(dato['id']))
                        grupo.permissions.add(permiso)
                    log(u'Agregó permiso : %s' % grupo, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delpermisogrupo':
                try:
                    grupo = Group.objects.get(pk=int(request.POST['id']))
                    datos = json.loads(request.POST['lista'])
                    for dato in datos:
                        permiso = Permission.objects.get(pk=int(dato['id']))
                        grupo.permissions.remove(permiso)
                    log(u'Eliminó permiso : %s' % grupo, request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addmodulogrupo':
                try:
                    grupo = Group.objects.get(pk=int(request.POST['id']))
                    datos = json.loads(request.POST['lista'])
                    for dato in datos:
                        modulo = Modulo.objects.get(pk=int(dato['id']))
                        if not GruposModulos.objects.filter(grupo=grupo):
                            mg = GruposModulos(grupo=grupo)
                            mg.save(request)
                        else:
                            mg = GruposModulos.objects.filter(grupo=grupo)[0]
                        mg.modulos.add(modulo)
                    log(u'Agregó módulo a grupo : %s' % grupo, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delmodulogrupo':
                try:
                    grupo = Group.objects.get(pk=int(request.POST['id']))
                    datos = json.loads(request.POST['lista'])
                    for dato in datos:
                        modulo = Modulo.objects.get(pk=int(dato['id']))
                        if not GruposModulos.objects.filter(grupo=grupo):
                            mg = GruposModulos(grupo=grupo)
                            mg.save(request)
                        else:
                            mg = GruposModulos.objects.filter(grupo=grupo)[0]
                        mg.modulos.remove(modulo)
                    log(u'Eliminó módulo a grupo : %s' % grupo, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addreporte':
                try:
                    grupo = Group.objects.get(pk=int(request.POST['id']))
                    datos = json.loads(request.POST['lista'])
                    for dato in datos:
                        reporte = Reporte.objects.get(pk=int(dato['id']))
                        reporte.grupos.add(grupo)
                    log(u'Agregó reporte a grupo : %s' % grupo, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delreporte':
                try:
                    grupo = Group.objects.get(pk=int(request.POST['id']))
                    datos = json.loads(request.POST['lista'])
                    for dato in datos:
                        reporte = Reporte.objects.get(pk=int(dato['id']))
                        reporte.grupos.remove(grupo)
                    log(u'Agregó reporte a grupo : %s' % grupo, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'importar':
                try:
                    form = ImportarArchivoXLSForm(request.POST, request.FILES)
                    if form.is_valid():
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("importacioncorreos_", nfile._name)
                        archivo = Archivo(nombre='IMPORTACION_CORREOS',
                                          fecha=datetime.now(),
                                          archivo=nfile,
                                          tipo_id=ARCHIVO_TIPO_GENERAL)
                        archivo.save(request)
                        workbook = xlrd.open_workbook(archivo.archivo.file.name)
                        sheet = workbook.sheet_by_index(0)
                        linea = 1
                        hoy = datetime.now().date()
                        for rowx in range(sheet.nrows):
                            if linea:
                                cols = sheet.row_values(rowx)
                                identificacion = cols[0].strip()
                                if Persona.objects.filter(Q(cedula=identificacion)| Q(pasaporte=identificacion)).exists():
                                    persona = Persona.objects.filter(Q(cedula=identificacion)| Q(pasaporte=identificacion))[0]
                                    persona.emailinst = cols[1]
                                    persona.save()
                            linea += 1
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editcorreo':
                try:
                    form = InfoCorreoForm(request.POST)
                    if form.is_valid():
                        institucion.emailhost = form.cleaned_data['emailhost']
                        institucion.emaildomain = form.cleaned_data['emaildomain']
                        institucion.emailport = form.cleaned_data['emailport']
                        institucion.emailhostuser = form.cleaned_data['emailhostuser']
                        institucion.emailpassword = form.cleaned_data['emailpassword']
                        institucion.domainapp = form.cleaned_data['domainapp']
                        institucion.usatls = form.cleaned_data['usatls']
                        institucion.save(request)
                        log(u'Modifico datos correo: %s' % institucion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editarlogicamodelo':
                try:
                    form = EditarLogicaModeloForm(request.POST)
                    if form.is_valid():
                        logica = LmsModeloEvaluativo.objects.get(pk=int(request.POST['id']))
                        logica.logica = form.cleaned_data['logica']
                        logica.save(request)
                        log(u'Modifico logica de importacion de modelo desde lms: %s - %s' % (logica.modeloevaluativo, logica.lms), request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'importarplantillas':
                try:
                    lms = Lms.objects.get(pk=int(request.POST['id']))
                    local_scope = {}
                    exec(lms.logica_plantillas, globals(), local_scope)
                    logica_plantillas = local_scope['logica_plantillas']
                    logica_plantillas(lms)

                    log(u'Actualizo plantilla: %s' % lms, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'deleteplantilla':
                try:
                    plantilla = PlantillasLms.objects.get(pk=request.POST['id'])
                    if plantilla.en_uso():
                        return bad_json(error=8)
                    log(u'Elimino plantilla lms: %s' % plantilla, request, "del")
                    plantilla.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'deletebloqueolms':
                try:
                    bloqueado = BloqueoLms.objects.get(pk=request.POST['id'])
                    log(u'Elimino bloqueado lms: %s' % bloqueado, request, "del")
                    bloqueado.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'activarapi':
                try:
                    api = Api.objects.get(pk=request.POST['id'])
                    api.activo = request.POST['valor'] == 'true'
                    api.save()
                    if api.activo:
                        log(u'Desactivo Api: %s' % api, request, "edit")
                    else:
                        log(u'Activo Api: %s' % api, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'activarlms':
                try:
                    lms = Lms.objects.get(pk=request.POST['id'])
                    lms.activo = request.POST['valor'] == 'true'
                    lms.save()
                    if lms.activo:
                        log(u'Desactivo lms: %s' % lms, request, "edit")
                    else:
                        log(u'Activo lms: %s' % lms, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'activarplantilla':
                try:
                    plantillalms = PlantillasLms.objects.get(pk=request.POST['id'])
                    plantillalms.activo = request.POST['valor'] == 'true'
                    plantillalms.save()
                    if plantillalms.activo:
                        log(u'Desactivo plantilla lms: %s' % plantillalms, request, "edit")
                    else:
                        log(u'Activo plantilla lms: %s' % plantillalms, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar sede'
                    form = SedeForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "adm_institucion/add.html", data)
                except Exception as ex:
                    pass

            if action == 'addpuntoventa':
                try:
                    data['title'] = u'Adicionar punto de venta'
                    data['form'] = PuntoVentaForm()
                    return render(request, "adm_institucion/addpv.html", data)
                except Exception as ex:
                    pass

            if action == 'editpunto':
                try:
                    data['title'] = u'Editar punto de venta'
                    data['puntoventa'] = puntoventa = PuntoVenta.objects.get(pk=request.GET['id'])
                    form = PuntoVentaForm(initial={'establecimiento': puntoventa.establecimiento,
                                                   'tipoemision': puntoventa.tipoemision,
                                                   'ambientefacturacion': puntoventa.ambientefacturacion,
                                                   'puntoventa': puntoventa.puntoventa,
                                                   'secuenciafactura': puntoventa.secuenciafactura,
                                                   'secuenciarecibopago': puntoventa.secuenciarecibopago,
                                                   'facturaelectronica': puntoventa.facturaelectronica,
                                                   'numeracionemitida': puntoventa.numeracionemitida,
                                                   'modeloimpresionnotacredito': puntoventa.modeloimpresionnotacredito,
                                                   'modeloimpresionrecibopago': puntoventa.modeloimpresionrecibopago,
                                                   'modeloimpresionfactura': puntoventa.modeloimpresionfactura,
                                                   'imprimirrecibopago': puntoventa.imprimirrecibo,
                                                   'imprimirfactura': puntoventa.imprimirfactura})
                    form.editar(puntoventa)
                    data['form'] = form
                    return render(request, "adm_institucion/editpv.html", data)
                except Exception as ex:
                    pass

            if action == 'delpunto':
                try:
                    data['title'] = u'Eliminar punto de venta'
                    data['puntoventa'] = puntoventa = PuntoVenta.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/delpunto.html", data)
                except Exception as ex:
                    pass

            if action == 'addaula':
                try:
                    data['title'] = u'Adicionar Aula'
                    data['sede'] = sede = Sede.objects.get(id=int(request.GET['id']))
                    form = AulaForm(initial={'capacidad': CAPACIDAD_MATERIA_INICIAL})
                    form.adicionar(sede)
                    data['form'] = form
                    return render(request, "adm_institucion/addaula.html", data)
                except Exception as ex:
                    pass

            if action == 'editaula':
                try:
                    data['title'] = u'Editar Aula'
                    data['aula'] = aula = Aula.objects.get(id=int(request.GET['id']))
                    form = AulaForm(initial={'nombre': aula.nombre,
                                             'tipo': aula.tipo,
                                             'capacidad': aula.capacidad,
                                             'coordinacion': aula.coordinaciones()})
                    form.editar(aula)
                    data['form'] = form
                    return render(request, "adm_institucion/editaula.html", data)
                except Exception as ex:
                    pass

            if action == 'delaula':
                try:
                    data['title'] = u'Eliminar Aula'
                    data['aula'] = Aula.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/delaula.html", data)
                except Exception as ex:
                    pass

            if action == 'addlms':
                try:
                    data['title'] = u'Adicionar LMS'
                    form = LmsForm()
                    data['form'] = form
                    return render(request, "adm_institucion/addlms.html", data)
                except Exception as ex:
                    pass

            if action == 'editlms':
                try:
                    data['title'] = u'Editar LMS'
                    data['lms'] = lms = Lms.objects.get(id=int(request.GET['id']))
                    form = LmsForm(initial={'nombre': lms.nombre,
                                            'host': lms.host,
                                            'puerto': lms.port,
                                            'tipo': lms.tipolms,
                                            'key': lms.key,
                                            'activo': lms.activo,
                                            'logica_creacion_materia': lms.logica_creacion_materia,
                                            'logica_creacion_usuario': lms.logica_creacion_usuario,
                                            'logica_matricular_usuario_materia': lms.logica_matricular_usuario_materia,
                                            'logica_asignar_profesor_materia': lms.logica_asignar_profesor_materia,
                                            'logica_general': lms.logica_general,
                                            'logica_bloqueo_usuario': lms.logica_bloqueo_usuario,
                                            'logica_desbloqueo_usuario': lms.logica_desbloqueo_usuario,
                                            'logica_plantillas': lms.logica_plantillas})
                    data['form'] = form
                    return render(request, "adm_institucion/editlms.html", data)
                except Exception as ex:
                    pass

            if action == 'dellms':
                try:
                    data['title'] = u'Eliminar LMS'
                    data['lms'] = Lms.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/dellms.html", data)
                except Exception as ex:
                    pass

            if action == 'addcoordinacion':
                try:
                    data['title'] = u'Adicionar coordinacion'
                    data['sede'] = sede = Sede.objects.get(pk=request.GET['id'])
                    data['form'] = CoordinacionForm()
                    return render(request, "adm_institucion/addcoordinacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editcoordinacion':
                try:
                    data['title'] = u'Editar de coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    form = CoordinacionForm(initial={'nombre': coordinacion.nombre,
                                                     'sede': coordinacion.sede,
                                                     'carrera': coordinacion.carrera.all(),
                                                     'alias': coordinacion.alias})
                    data['form'] = form
                    data['h'] = request.GET['h']
                    return render(request, "adm_institucion/editcoordinacion.html", data)
                except Exception as ex:
                    pass

            if action == 'delcoordinacion':
                try:
                    data['title'] = u'Eliminar coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    data['h'] = request.GET['h']
                    return render(request, "adm_institucion/delcoordinacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editar':
                try:
                    data['title'] = u'Editar sede'
                    data['sede'] = sede = Sede.objects.get(pk=request.GET['id'])
                    form = SedeForm(initial={'nombre': sede.nombre,
                                             'provincia': sede.provincia,
                                             'canton': sede.canton,
                                             'parroquia': sede.parroquia,
                                             'alias': sede.alias,
                                             'sector': sede.sector,
                                             'ciudad': sede.ciudad,
                                             'direccion': sede.direccion,
                                             'telefono': sede.telefono})
                    form.editar(sede)
                    data['form'] = form
                    return render(request, "adm_institucion/editar.html", data)
                except Exception as ex:
                    pass

            if action == 'addbibliotecario':
                try:
                    data['title'] = u'Adicionar bibliotecario de sede'
                    data['biblioteca'] = biblioteca = Biblioteca.objects.get(pk=request.GET['id'])
                    data['form'] = ResponsableBibliotecaForm()
                    return render(request, "adm_institucion/addbibliotecario.html", data)
                except Exception as ex:
                    pass

            if action == 'addbiblioteca':
                try:
                    data['title'] = u'Adicionar biblioteca a la sede'
                    data['sede'] = sede = Sede.objects.get(pk=request.GET['id'])
                    data['form'] = BibliotecaForm()
                    return render(request, "adm_institucion/addbiblioteca.html", data)
                except Exception as ex:
                    pass

            if action == 'addcajero':
                try:
                    data['title'] = u'Adicionar cajero de sede'
                    data['puntoventa'] = puntoventa = PuntoVenta.objects.get(pk=request.GET['id'])
                    data['form'] = CajeroForm()
                    return render(request, "adm_institucion/addcajero.html", data)
                except Exception as ex:
                    pass

            if action == 'delbibliotecario':
                try:
                    data['title'] = u'Eliminar bibliotecario'
                    data['bibliotecario'] = ResponsableBiblioteca.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/delbibliotecario.html", data)
                except Exception as ex:
                    pass

            if action == 'delcajero':
                try:
                    data['title'] = u'Eliminar cajero'
                    data['cajero'] = LugarRecaudacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/delcajero.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabilitarcajero':
                try:
                    data['title'] = u'Deshabilitar cajero'
                    data['cajero'] = LugarRecaudacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/deshabilitarcajero.html", data)
                except Exception as ex:
                    pass

            if action == 'habilitarcajero':
                try:
                    data['title'] = u'Deshabilitar cajero'
                    data['cajero'] = LugarRecaudacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/habilitarcajero.html", data)
                except Exception as ex:
                    pass

            if action == 'addpersonacargo':
                try:
                    data['title'] = u'Adicionar cargo'
                    data['form'] = CargoPersonaForm()
                    return render(request, "adm_institucion/addpersonacargo.html", data)
                except Exception as ex:
                    pass

            if action == 'addcargo':
                try:
                    data['title'] = u'Adicionar Cargo'
                    data['form'] = CargoForm()
                    return render(request, "adm_institucion/addcargo.html", data)
                except Exception as ex:
                    pass

            if action == 'addpersonacargosede':
                try:
                    data['title'] = u'Adicionar cargo'
                    data['sede'] = Sede.objects.get(id=int(request.GET['id']))
                    data['form'] = CargoPersonaForm()
                    return render(request, "adm_institucion/addpersonacargoconsede.html", data)
                except Exception as ex:
                    pass

            if action == 'delpersonacargo':
                try:
                    data['title'] = u'Eliminar cargo'
                    data['cargo'] = CargoInstitucion.objects.get(pk=request.GET['id'])
                    h = 100
                    if 'h' in request.GET:
                        h = int(request.GET['h'])
                    if 't' in request.GET:
                        data['t'] = int(request.GET['t'])
                    else:
                        data['t'] = 2
                    data['h'] = h
                    return render(request, "adm_institucion/delpersonacargo.html", data)
                except Exception as ex:
                    pass

            if action == 'editparametrosclases':
                try:
                    data['title'] = u'Editar'
                    form = ParametrosClaseForm(initial={'horarioestricto': institucion.horarioestricto,
                                                        'clasescierreautomatico': institucion.clasescierreautomatico,
                                                        'abrirmateriasenfecha': institucion.abrirmateriasenfecha,
                                                        'minutosapeturaantes': institucion.minutosapeturaantes,
                                                        'minutosapeturadespues': institucion.minutosapeturadespues,
                                                        'minutoscierreantes': institucion.minutoscierreantes,
                                                        'egresamallacompleta': institucion.egresamallacompleta})
                    data['form'] = form
                    return render(request, "adm_institucion/editparametrosclase.html", data)
                except Exception as ex:
                    pass

            if action == 'editdatosaplicacion':
                try:
                    data['title'] = u'Editar'
                    form = ParametrosAplicacionForm(initial={'defaultpassword': institucion.defaultpassword,
                                                             'claveusuariocedula': institucion.claveusuariocedula,
                                                             'actualizarfotoalumnos': institucion.actualizarfotoalumnos,
                                                             'actualizarfotoadministrativos': institucion.actualizarfotoadministrativos,
                                                             'controlunicocredenciales': institucion.controlunicocredenciales,
                                                             'correoobligatorio': institucion.correoobligatorio,
                                                             'nombreusuariocedula': institucion.nombreusuariocedula,
                                                             'preguntasinscripcion': institucion.preguntasinscripcion})
                    data['form'] = form
                    return render(request, "adm_institucion/editdatosaplicacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editdatoscostos':
                try:
                    data['title'] = u'Editar'
                    form = DatosCostosAplicacionForm(initial={'contribuyenteespecial': institucion.contribuyenteespecial,
                                                              'obligadocontabilidad': institucion.obligadocontabilidad,
                                                              'estudiantevefecharubro': institucion.estudiantevefecharubro,
                                                              'costoperiodo': institucion.costoperiodo,
                                                              'matricularcondeuda': institucion.matricularcondeuda,
                                                              'cuotaspagoestricto': institucion.cuotaspagoestricto,
                                                              'pagoestrictonotas': institucion.pagoestrictonotas,
                                                              'pagoestrictoasistencia': institucion.pagoestrictoasistencia,
                                                              'costoenmalla': institucion.costoenmalla,
                                                              'formalizarxporcentaje': institucion.formalizarxporcentaje,
                                                              'formalizarxmatricula': institucion.formalizarxmatricula,
                                                              'porcentajeformalizar': institucion.porcentajeformalizar,
                                                              'vencematriculaspordias': institucion.vencematriculaspordias,
                                                              'diashabiles': institucion.diashabiles,
                                                              'diasmatriculaexpirapresencial': institucion.diasmatriculaexpirapresencial,
                                                              'diasmatriculaexpirasemipresencial': institucion.diasmatriculaexpirasemipresencial,
                                                              'diasmatriculaexpiradistancia': institucion.diasmatriculaexpiradistancia,
                                                              'diasmatriculaexpiraonline': institucion.diasmatriculaexpiraonline,
                                                              'diasmatriculaexpirahibrida': institucion.diasmatriculaexpirahibrida,
                                                              'fechaexpiramatriculagrado': institucion.fechaexpiramatriculagrado,
                                                              'fechaexpiramatriculaposgrado': institucion.fechaexpiramatriculaposgrado})
                    data['form'] = form
                    return render(request, "adm_institucion/editdatoscostos.html", data)
                except Exception as ex:
                    pass

            if action == 'editdatosbloqueo':
                try:
                    data['title'] = u'Editar Bloqueo de módulos'
                    form = DatosBloqueoAplicacionForm(initial={'deudabloqueaasistencia': institucion.deudabloqueaasistencia,
                                                               'deudabloqueamimalla': institucion.deudabloqueamimalla,
                                                               'deudabloqueamishorarios': institucion.deudabloqueamishorarios,
                                                               'deudabloqueacronograma': institucion.deudabloqueacronograma,
                                                               'deudabloqueamatriculacion': institucion.deudabloqueamatriculacion,
                                                               'deudabloqueasolicitud': institucion.deudabloqueasolicitud,
                                                               'deudabloqueanotas': institucion.deudabloqueanotas,
                                                               'deudabloqueadocumentos': institucion.deudabloqueadocumentos})
                    data['form'] = form
                    return render(request, "adm_institucion/editdatosbloqueo.html", data)
                except Exception as ex:
                    pass

            if action == 'editdatosgeneralessolicitudes':
                try:
                    data['title'] = u'Editar datos generales'
                    form = DatosGeneralesForm(initial={'solicitudnumeracion': institucion.solicitudnumeracion,
                                                       'solicitudnumeroautomatico': institucion.solicitudnumeroautomatico,
                                                       'permitealumnoregistrar': institucion.permitealumnoregistrar,
                                                       'diasvencimientosolicitud': institucion.diasvencimientosolicitud,
                                                       'permitealumnoelegirresponsable': institucion.permitealumnoelegirresponsable,
                                                       'especificarcantidadsolicitud': institucion.especificarcantidadsolicitud})
                    data['form'] = form
                    return render(request, "adm_institucion/editdatosgeneralessolicitudes.html", data)
                except Exception as ex:
                    pass

            if action == 'editdatosfactura':
                try:
                    data['title'] = u'Editar datos de facturación'
                    form = DatosFacturacionAplicacionForm(initial={'facturacionelectronicaexterna': institucion.facturacionelectronicaexterna,
                                                                   'codigoporcentajeiva': institucion.codigoporcentajeiva,
                                                                   'pfx': institucion.pfx,
                                                                   'apikey': institucion.apikey,
                                                                   'urlfacturacion': institucion.urlfacturacion})
                    data['form'] = form
                    return render(request, "adm_institucion/editdatosfactura.html", data)
                except Exception as ex:
                    pass

            if action == 'editdatosurlapp':
                try:
                    data['title'] = u'Editar datos de URL de aplicaciones'
                    form = DatosUrlAplicacionForm(initial={'urlaplicacionandroid': institucion.urlaplicacionandroid,
                                                           'urlaplicacionios': institucion.urlaplicacionios,
                                                           'urlaplicacionwindows': institucion.urlaplicacionwindows})
                    data['form'] = form
                    return render(request, "adm_institucion/editdatosurlapp.html", data)
                except Exception as ex:
                    pass

            if action == 'editdatosbiblioteca':
                try:
                    data['title'] = u'Editar datos de Biblioteca'
                    form = DatosBibliotecaForm(initial={'usabiblioteca': institucion.usabiblioteca,
                                                        'documentoscoleccion': institucion.documentoscoleccion,
                                                        'documentoscoleccionautonumeracion': institucion.documentoscoleccionautonumeracion,
                                                        'documentosautonumeracion': institucion.documentosautonumeracion})
                    data['form'] = form
                    return render(request, "adm_institucion/editdatosbiblioteca.html", data)
                except Exception as ex:
                    pass

            if action == 'addiva':
                try:
                    data['title'] = u'Adicionar IVA'
                    data['form'] = IvaForm()
                    return render(request, "adm_institucion/addiva.html", data)
                except Exception as ex:
                    pass

            if action == 'editiva':
                try:
                    data['title'] = u'Editar IVA'
                    data['iva'] = iva = IvaAplicado.objects.get(id=int(request.GET['id']))
                    data['form'] = IvaForm(initial={'descripcion': iva.descripcion,
                                                    'codigo': iva.codigo,
                                                    'porcientoiva': iva.porcientoiva})
                    return render(request, "adm_institucion/editiva.html", data)
                except Exception as ex:
                    pass

            if action == 'deliva':
                try:
                    data['title'] = u'Eliminar IVA'
                    data['iva'] = iva = IvaAplicado.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/deliva.html", data)
                except Exception as ex:
                    pass

            if action == 'activariva':
                try:
                    data['title'] = u'Activar IVA'
                    data['iva'] = IvaAplicado.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/activariva.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivariva':
                try:
                    data['title'] = u'Desactivar IVA'
                    data['iva'] = iva = IvaAplicado.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/desactivariva.html", data)
                except Exception as ex:
                    pass

            if action == 'addcuenta':
                try:
                    data['title'] = u'Adicionar Cuenta bancaria'
                    data['form'] = CuentaForm()
                    return render(request, "adm_institucion/addcuenta.html", data)
                except Exception as ex:
                    pass

            if action == 'editcuenta':
                try:
                    data['title'] = u'Editar Cuenta bancaria'
                    data['cuenta'] = cuenta = CuentaBanco.objects.get(id=int(request.GET['id']))
                    data['form'] = CuentaForm(initial={'banco': cuenta.banco,
                                                       'representante': cuenta.representante,
                                                       'numero': cuenta.numero,
                                                       'tipocuenta': cuenta.tipocuenta})
                    return render(request, "adm_institucion/editcuenta.html", data)
                except Exception as ex:
                    pass

            if action == 'delcuenta':
                try:
                    data['title'] = u'Eliminar Cuenta bancaria'
                    data['cuenta'] = CuentaBanco.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/delcuenta.html", data)
                except Exception as ex:
                    pass

            if action == 'activarcuenta':
                try:
                    data['title'] = u'Activar Cuenta'
                    data['cuenta'] = CuentaBanco.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/activarcuenta.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivarcuenta':
                try:
                    data['title'] = u'Desactivar Cuenta'
                    data['cuenta'] = CuentaBanco.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/desactivarcuenta.html", data)
                except Exception as ex:
                    pass

            if action == 'editsolicitud':
                try:
                    data['title'] = u'Editar Tipo Solicitud'
                    data['solicitud'] = solicitud = TipoSolicitudSecretariaDocente.objects.get(
                        id=int(request.GET['id']))
                    data['form'] = TipoSolicitudForm(initial={'nombre': solicitud.nombre,
                                                              'descripcion': solicitud.descripcion,
                                                              'valor': solicitud.valor,
                                                              'costo_base': solicitud.costo_base,
                                                              'grupos': solicitud.grupos.all(),
                                                              'gratismatricula': solicitud.gratismatricula})
                    return render(request, "adm_institucion/editsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'addsolicitud':
                try:
                    data['title'] = u'Editar Tipo Solicitud'
                    data['form'] = TipoSolicitudForm()
                    return render(request, "adm_institucion/addsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar tipo solicitud'
                    data['solicitud'] = TipoSolicitudSecretariaDocente.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/delsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'addreferenciaweb':
                try:
                    data['title'] = u'Adicionar Referencia web'
                    form = ReferenciaWebForm()
                    form.referencia()
                    data['form'] = form
                    return render(request, "adm_institucion/addreferenciaweb.html", data)
                except Exception as ex:
                    pass

            if action == 'editreferenciaweb':
                try:
                    data['title'] = u'Editar Referencia web'
                    from bib.models import ReferenciaWeb
                    data['rf'] = rf = ReferenciaWeb.objects.get(id=int(request.GET['id']))
                    form = ReferenciaWebForm(initial={'nombre': rf.nombre,
                                                      'url': rf.url})
                    form.referencia()
                    data['form'] = form
                    return render(request, "adm_institucion/editreferenciaweb.html", data)
                except Exception as ex:
                    pass

            if action == 'delreferenciaweb':
                try:
                    data['title'] = u'Eliminar Referencia'
                    from bib.models import ReferenciaWeb
                    data['rf'] = ReferenciaWeb.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/delreferencia.html", data)
                except Exception as ex:
                    pass

            if action == 'addbibvirtual':
                try:
                    data['title'] = u'Adicionar Biblioteca virtual'
                    data['form'] = ReferenciaWebForm()
                    return render(request, "adm_institucion/addbibvirtual.html", data)
                except Exception as ex:
                    pass

            if action == 'editbibvirtual':
                try:
                    data['title'] = u'Editar biblioteca virtual'
                    from bib.models import OtraBibliotecaVirtual
                    data['rf'] = rf = OtraBibliotecaVirtual.objects.get(id=int(request.GET['id']))
                    data['form'] = ReferenciaWebForm(initial={'nombre': rf.nombre,
                                                              'descripcion': rf.descripcion,
                                                              'url': rf.url})
                    return render(request, "adm_institucion/editbibvirtual.html", data)
                except Exception as ex:
                    pass

            if action == 'delbibvirtual':
                try:
                    data['title'] = u'Eliminar biblioteca virtual'
                    from bib.models import OtraBibliotecaVirtual
                    data['rf'] = OtraBibliotecaVirtual.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/delbibvirtual.html", data)
                except Exception as ex:
                    pass

            if action == 'addcompetenciagenerica':
                try:
                    data['title'] = u'Adicionar Competencia Genérica'
                    data['form'] = CompetenciaGenericaForm()
                    return render(request, "adm_institucion/addcompetenciagenerica.html", data)
                except Exception as ex:
                    pass

            if action == 'addtipotrabajotitulacion':
                try:
                    data['title'] = u'Adicionar un Tipo de Trabajo de Titulación'
                    data['form'] = TipoTrabajoTitulacionForm()
                    return render(request, "adm_institucion/addtipotrabajotitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'delcompetencia':
                try:
                    data['title'] = u'Eliminar Competencia'
                    data['competencia'] = CompetenciaGenerica.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/delcompetencia.html", data)
                except Exception as ex:
                    pass

            if action == 'deltipotrabajotitulacion':
                try:
                    data['title'] = u'Eliminar Tipo de Trabajo de Titulación'
                    data['tipotrabajo'] = TipoTrabajoTitulacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/deltipotrabajotitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addsesion':
                try:
                    data['title'] = u'Adicionar Sesión'
                    data['form'] = SesionForm(initial={'comienza': datetime.now().time().strftime("%I:%M %p"),
                                                       'termina': datetime.now().time().strftime("%I:%M %p")})
                    return render(request, "adm_institucion/addsesion.html", data)
                except Exception as ex:
                    pass

            if action == 'delsesion':
                try:
                    data['title'] = u'Eliminar Sesión'
                    data['sesion'] = Sesion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/delsesion.html", data)
                except Exception as ex:
                    pass

            if action == 'addturno':
                try:
                    data['title'] = u'Adicionar Turno'
                    data['form'] = TurnoForm(initial={'comienza': '12:00', 'termina': '12:00'})
                    return render(request, "adm_institucion/addturno.html", data)
                except Exception as ex:
                    pass

            if action == 'delturno':
                try:
                    data['title'] = u'Eliminar Turno'
                    data['turno'] = Turno.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/delturno.html", data)
                except Exception as ex:
                    pass

            if action == 'addgrupo':
                try:
                    data['title'] = u'Adicionar Grupo'
                    data['form'] = GrupoSistemaForm()
                    return render(request, "adm_institucion/addgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'editgrupo':
                try:
                    data['title'] = u'Editar Grupo'
                    data['grupo'] = grupo = Group.objects.get(id=int(request.GET['id']))
                    data['form'] = GrupoSistemaForm(initial={'nombre': grupo.name})
                    return render(request, "adm_institucion/editgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'delgrupo':
                try:
                    data['title'] = u'Eliminar Grupo'
                    data['grupo'] = grupo = Group.objects.get(id=int(request.GET['id']))
                    return render(request, "adm_institucion/delgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'permisosgrupo':
                try:
                    data['title'] = u'Permisos'
                    data['grupo'] = grupo = Group.objects.get(pk=int(request.GET['id']))
                    data['permisos_grupo'] = perm = grupo.permissions.all()
                    data['permisos'] = Permission.objects.all().exclude(id__in=[x.id for x in perm]).exclude(name__startswith='Can ')
                    data['modulos_grupo'] = modulos = Modulo.objects.filter(gruposmodulos__grupo=grupo).distinct()
                    data['modulos'] = Modulo.objects.all().exclude(id__in=modulos.values_list('id', flat=True))
                    return render(request, "adm_institucion/permisosgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'reportesgrupo':
                try:
                    data['title'] = u'Reportes'
                    data['grupo'] = grupo = Group.objects.get(pk=int(request.GET['id']))
                    data['reportes_grupo'] = rep = grupo.reporte_set.all()
                    data['reportes'] = Reporte.objects.all().exclude(id__in=[x.id for x in rep]).exclude(interface=True)
                    return render(request, "adm_institucion/reportesgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar notas'
                    data['form'] = ImportarArchivoXLSForm()
                    return render(request, "adm_institucion/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'addapi':
                try:
                    data['title'] = u'Adicionar Api'
                    data['form'] = ApiForm()
                    return render(request, "adm_institucion/addapi.html", data)
                except Exception as ex:
                    pass

            if action == 'editapi':
                try:
                    data['title'] = u'Editar API'
                    data['api'] = api = Api.objects.get(id=int(request.GET['id']))
                    form = ApiForm(initial={'nombrecorto': api.nombrecorto,
                                            'descripcion': api.descripcion,
                                            'key': api.key,
                                            'tipo': api.tipo,
                                            'logicaapi': api.logicaapi})
                    data['form'] = form
                    return render(request, "adm_institucion/editapi.html", data)
                except Exception as ex:
                    pass

            if action == 'delapi':
                try:
                    data['title'] = u'Eliminar API'
                    data['api'] = Api.objects.get(pk=request.GET['id'])
                    return render(request, "adm_institucion/delapi.html", data)
                except Exception as ex:
                    pass


            if action == 'editcorreo':
                try:
                    data['title'] = u'Editar información de correo'
                    form = InfoCorreoForm(initial={'emaildomain': institucion.emaildomain,
                                                   'emailhost': institucion.emailhost,
                                                   'emailport': institucion.emailport,
                                                   'emailpassword': institucion.emailpassword,
                                                   'usatls': institucion.usatls,
                                                   'domainapp': institucion.domainapp,
                                                   'emailhostuser': institucion.emailhostuser})
                    data['form'] = form
                    return render(request, "adm_institucion/editcorreo.html", data)
                except Exception as ex:
                    pass

            if action == 'plantillaslms':
                try:
                    data['title'] = u'Plantillas LMS'
                    data['lms'] = lms = Lms.objects.get(pk=int(request.GET['id']))
                    plantillas = PlantillasLms.objects.filter(lms=lms)
                    search = ''
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        plantillas = PlantillasLms.objects.filter(nombre__icontains=search).distinct()
                    paging = MiPaginador(plantillas, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'adm_institucion_plantillaslms_page' in request.session:
                            p = int(request.session['adm_institucion_plantillaslms_page'])
                        if 'page' in request.GET:
                            request.session['adm_institucion_plantillaslms_page'] = p = int(request.GET['page'])
                        page = paging.page(p)
                    except:
                        p = 1
                        page = paging.page(p)
                    data['pagenumber'] = request.session['adm_institucion_plantillaslms_page'] = p
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search
                    data['ids'] = ids
                    data['plantillas'] = page.object_list
                    return render(request, "adm_institucion/plantillaslms.html", data)
                except Exception as ex:
                    pass

            if action == 'modeloslms':
                try:
                    data['title'] = u'Modelos LMS'
                    data['lms'] = Lms.objects.get(pk=int(request.GET['id']))
                    data['modelos'] = ModeloEvaluativo.objects.all()
                    return render(request, "adm_institucion/modeloslms.html", data)
                except Exception as ex:
                    pass

            if action == 'bloqueadoslms':
                try:
                    data['title'] = u'Bloqueos LMS'
                    data['lms'] = lms = Lms.objects.get(pk=int(request.GET['id']))
                    bloqueados = BloqueoLms.objects.filter(lms=lms)
                    search = ''
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            bloqueados = BloqueoLms.objects.filter(Q(persona__nombre1__icontains=search) |
                                                                   Q(persona__nombre2__icontains=search) |
                                                                   Q(persona__apellido1__icontains=search) |
                                                                   Q(persona__apellido2__icontains=search) |
                                                                   Q(persona__cedula__icontains=search) |
                                                                   Q(persona__pasaporte__icontains=search) |
                                                                   Q(identificador__icontains=search) |
                                                                   Q(carrera__nombre__icontains=search) |
                                                                   Q(persona__usuario__username__icontains=search)).distinct()
                        else:
                            bloqueados = BloqueoLms.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                                   Q(persona__apellido2__icontains=ss[1])).distinct()
                    paging = MiPaginador(bloqueados, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'adm_institucion_bloqueadoslms_page' in request.session:
                            p = int(request.session['adm_institucion_bloqueadoslms_page'])
                        if 'page' in request.GET:
                            request.session['adm_institucion_bloqueadoslms_page'] = p = int(request.GET['page'])
                        page = paging.page(p)
                    except:
                        p = 1
                        page = paging.page(p)
                    data['pagenumber'] = request.session['adm_institucion_bloqueadoslms_page'] = p
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search
                    data['ids'] = ids
                    data['bloqueados'] = page.object_list
                    return render(request, "adm_institucion/bloqueadoslms.html", data)
                except Exception as ex:
                    pass

            if action == 'editarlogicamodelo':
                try:
                    data['title'] = u'Editar logica modelo'
                    data['logica'] = logica = LmsModeloEvaluativo.objects.get(pk=int(request.GET['id']))
                    form = EditarLogicaModeloForm(initial={'logica': logica.logica})
                    data['form'] = form
                    return render(request, "adm_institucion/editlogicamodelo.html", data)
                except Exception as ex:
                    pass

            if action == 'importarplantillas':
                try:
                    data['title'] = u'Importar plantilla'
                    data['lms'] = lms = Lms.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_institucion/importarplantillas.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteplantilla':
                try:
                    data['title'] = u'Eliminar plantilla'
                    data['plantilla'] = PlantillasLms.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_institucion/deleteplantilla.html", data)
                except Exception as ex:
                    pass

            if action == 'deletebloqueolms':
                try:
                    data['title'] = u'Eliminar bloqueado lms'
                    data['bloqueado'] = BloqueoLms.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_institucion/deletebloqueolms.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                if 'seccion' in request.GET:
                    request.session['adm_institucion_seccion'] = seccion = int(request.GET['seccion'])
                    request.session['adm_institucion_subseccion'] = subseccion = 0
                else:
                    if 'adm_institucion_seccion' not in request.session:
                        request.session['adm_institucion_seccion'] = 0
                    seccion = request.session['adm_institucion_seccion']
                if 'subseccion' in request.GET:
                    request.session['adm_institucion_subseccion'] = subseccion = int(request.GET['subseccion'])
                else:
                    if 'adm_institucion_subseccion' not in request.session:
                        request.session['adm_institucion_subseccion'] = 0
                    subseccion = request.session['adm_institucion_subseccion']
                data['subseccion'] = subseccion
                data['seccion'] = seccion
                data['title'] = u'Parametros institución'

                if seccion == 0:
                    data['coordinacion'] = coordinacion = request.session['coordinacionseleccionada']
                    data['sedes'] = sedes = Sede.objects.all()
                    return render(request, "adm_institucion/0.html", data)

                if seccion == 1:

                    if subseccion == 0:
                        data['cargos'] = Cargo.objects.all()
                        return render(request, "adm_institucion/1_0.html", data)

                    if subseccion == 1:
                        data['cargos'] = Cargo.objects.all()
                        data['sedes'] = sedes = Sede.objects.all()
                        data['cargosinstitucion'] = CargoInstitucion.objects.filter(sede__isnull=True)
                        return render(request, "adm_institucion/1_1.html", data)

                if seccion == 2:
                    if subseccion == 0:
                        data['solicitudes'] = TipoSolicitudSecretariaDocente.objects.all()
                        return render(request, "adm_institucion/2_0.html", data)
                    if subseccion == 1:
                        data['puntoventa'] = PuntoVenta.objects.all()
                        data['solicitudes_generadas'] = SolicitudSecretariaDocente.objects.count()
                        return render(request, "adm_institucion/2_1.html", data)
                    if subseccion == 2:
                        data['ivas'] = IvaAplicado.objects.all()
                        return render(request, "adm_institucion/2_2.html", data)
                    if subseccion == 3:
                        data['cuentas'] = CuentaBanco.objects.all()
                        return render(request, "adm_institucion/2_3.html", data)
                    if subseccion == 4:
                        data['solicitudes'] = TipoSolicitudSecretariaDocente.objects.all()
                        return render(request, "adm_institucion/2_4.html", data)

                if seccion == 3:
                    if subseccion == 0:
                        from bib.models import ReferenciaWeb, OtraBibliotecaVirtual
                        data['referenciasweb'] = ReferenciaWeb.objects.all()
                        data['otrasbib'] = OtraBibliotecaVirtual.objects.all()
                        return render(request, "adm_institucion/3_0.html", data)
                    if subseccion == 1:
                        data['sedes'] = sedes = Sede.objects.all()
                        return render(request, "adm_institucion/3_1.html", data)

                if seccion == 4:
                    if subseccion == 0:
                        return render(request, "adm_institucion/4_0.html", data)
                    if subseccion == 1:
                        data['competenciagenericas'] = CompetenciaGenerica.objects.all()
                        return render(request, "adm_institucion/4_1.html", data)
                    if subseccion == 2:
                        data['sesiones'] = Sesion.objects.all()
                        return render(request, "adm_institucion/4_2.html", data)
                    if subseccion == 3:
                        data['turnos'] = Turno.objects.all()
                        return render(request, "adm_institucion/4_3.html", data)
                    if subseccion == 4:
                        data['tipotrabajotitulacion'] = TipoTrabajoTitulacion.objects.all()
                        return render(request, "adm_institucion/4_4.html", data)
                    if subseccion == 5:
                        data['sedes'] = sedes = Sede.objects.all()
                        data['aulas'] = Aula.objects.all()
                        return render(request, "adm_institucion/4_5.html", data)
                    if subseccion == 6:
                        data['lmsall'] = Lms.objects.all()
                        return render(request, "adm_institucion/4_6.html", data)

                if seccion == 5:
                    if subseccion == 0:
                        data['PERM_DIRECTOR_SIS'] = False
                        persona = request.session['persona']
                        if persona.id in PERM_DIRECTOR_SIS:
                            data['PERM_DIRECTOR_SIS'] = True
                        data['grupos'] = Group.objects.all().order_by('name')
                        return render(request, "adm_institucion/5_0.html", data)
                    if subseccion == 1:
                        return render(request, "adm_institucion/5_1.html", data)
                    if subseccion == 2:
                        return render(request, "adm_institucion/5_2.html", data)
                    if subseccion == 3:
                        return render(request, "adm_institucion/5_3.html", data)

                if seccion == 6:
                    if subseccion == 0:
                        return render(request, "adm_institucion/6_0.html", data)
                    if subseccion == 1:
                        data['apis'] = Api.objects.all().order_by('nombrecorto')
                        return render(request, "adm_institucion/6_1.html", data)

                request.session['adm_institucion_seccion'] = 0
                request.session['adm_institucion_subseccion'] = 0
                return HttpResponseRedirect('/adm_institucion')
            except Exception as ex:
                return HttpResponseRedirect('/')
