# coding=utf-8
from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import PROFESORES_GROUP_ID, EMAIL_DOMAIN, PAIS_ECUADOR_ID,PERM_ENTRAR_COMO_USUARIO, \
    ALUMNOS_GROUP_ID, ADMINISTRATIVOS_GROUP_ID, DOCENTES_REGISTRAN_ESTUDIOS, \
    DOCENTES_REGISTRAN_CURSOS, DOCENTES_REGISTRAN_PUBLICACIONES, DOCENTES_REGISTRAN_CV, \
    EMAIL_DOMAIN_ESTUDIANTES, NACIONALIDAD_INDIGENA_ID, CODIGO_IES, EMAIL_INSTITUCIONAL_AUTOMATICO_DOCENTES
from ctt.commonviews import adduserdata, obtener_reporte
from ctt.forms import ProfesorForm, EstudioEducacionSuperiorForm, NuevaInscripcionForm

from ctt.funciones import MiPaginador, generar_nombre, log, generar_usuario, url_back, resetear_clave, generar_email, \
    remover_tildes, consultar_titulos
from ctt.funciones import bad_json, ok_json
from ctt.models import Profesor, Persona, Clase, \
    Administrativo, Materia, Turno, EstudioPersona, CursoPersona, Inscripcion,\
    Carrera, Periodo, InscripcionMalla


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    coordinacion = request.session['coordinacionseleccionada']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                if 'documentoidentificacion' not in request.FILES:
                    return bad_json(mensaje=u"Debe subir el documento de identificación en formato PNG o JPG.")
                form = ProfesorForm(request.POST, request.FILES)
                if not form.is_valid():
                    mensaje_error = form.errors.get('documentoidentificacion', [u"Hay errores en el formulario. Por favor, revise todos los campos."])[0]
                    return bad_json(mensaje=mensaje_error)
                if form.is_valid():
                    cedula = remover_tildes(form.cleaned_data['cedula'].strip())
                    pasaporte = form.cleaned_data['pasaporte'].strip()
                    fechanac = form.cleaned_data['nacimiento']
                    edad = relativedelta(datetime.now(), fechanac)
                    if edad.years < 18:
                        return bad_json(mensaje=u"Debe ser mayor de edad.")
                    if not cedula and not pasaporte:
                        return bad_json(mensaje=u"Debe ingresar una identificación.")
                    if cedula:
                        if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if pasaporte:
                        if Persona.objects.filter(Q(cedula=pasaporte) | Q(pasaporte=pasaporte)).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    personaprofesor = Persona(nombre1=remover_tildes(form.cleaned_data['nombre1']),
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
                                              sangre=form.cleaned_data['sangre'])
                    personaprofesor.save(request)
                    generar_usuario(persona=personaprofesor, group_id=PROFESORES_GROUP_ID)
                    if EMAIL_INSTITUCIONAL_AUTOMATICO_DOCENTES:
                        personaprofesor.emailinst = generar_email(personaprofesor)
                    else:
                        personaprofesor.emailinst = form.cleaned_data['emailinst']
                    personaprofesor.save(request)
                    profesor = Profesor(persona=personaprofesor,
                                        activo=True,
                                        fechainiciodocente=form.cleaned_data['fechainiciodocente'],
                                        dedicacion=form.cleaned_data['dedicacion'],
                                        nivelescalafon=form.cleaned_data['nivelescalafon'],
                                        coordinacion=data['coordinacionseleccionada'])
                    profesor.save(request)
                    cedula = persona.cedula_doc()
                    if request.FILES["documentoidentificacion"]:
                        newfile = request.FILES["documentoidentificacion"]
                        newfile._name = generar_nombre("documentoidentificacion", newfile._name)
                        if cedula:
                            cedula.cedula = newfile
                            cedula.save(request)
                        else:
                            cedula = CedulaPersona(persona=persona, cedula=newfile)
                            cedula.save(request)
                    personaprofesor.crear_perfil(profesor=profesor)
                    personaprofesor.mi_ficha()
                    perfil = personaprofesor.mi_perfil()
                    perfil.raza = form.cleaned_data['etnia']
                    perfil.nacionalidadindigena = form.cleaned_data['nacionalidadindigena']
                    perfil.save(request)
                    personaprofesor.datos_extension()
                    log(u'Adiciono Docente: %s' % profesor, request, "add")
                    return ok_json({"id": profesor.id})
                else:
                    return bad_json(error=6,form=form)
            except Exception as d:
                transaction.set_rollback(True)
                return bad_json(error=1)

        if action == 'edit':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                form = ProfesorForm(request.POST, request.FILES)
                persona = profesor.persona
                if form.is_valid():
                    cedula = remover_tildes(form.cleaned_data['cedula'].strip())
                    pasaporte = form.cleaned_data['pasaporte'].strip()
                    if not cedula and not pasaporte:
                        return bad_json(mensaje=u"Debe ingresar una identificación.")
                    if cedula:
                        if Persona.objects.filter(cedula=cedula).exclude(id=persona.id).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if pasaporte:
                        if Persona.objects.filter(pasaporte=pasaporte).exclude(id=persona.id).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    persona.nombre1 = remover_tildes(form.cleaned_data['nombre1'])
                    persona.nombre2 = remover_tildes(form.cleaned_data['nombre2'])
                    persona.apellido1 = remover_tildes(form.cleaned_data['apellido1'])
                    persona.apellido2 = remover_tildes(form.cleaned_data['apellido2'])
                    persona.cedula = remover_tildes(form.cleaned_data['cedula'])
                    persona.pasaporte = form.cleaned_data['pasaporte']
                    persona.nacimiento = form.cleaned_data['nacimiento']
                    persona.sexo = form.cleaned_data['sexo']
                    persona.nacionalidad = form.cleaned_data['nacionalidad']
                    persona.paisnac = form.cleaned_data['paisnac']
                    persona.provincianac = form.cleaned_data['provincianac']
                    persona.cantonnac = form.cleaned_data['cantonnac']
                    persona.parroquianac = form.cleaned_data['parroquianac']
                    persona.pais = form.cleaned_data['pais']
                    persona.provincia = form.cleaned_data['provincia']
                    persona.canton = form.cleaned_data['canton']
                    persona.parroquia = form.cleaned_data['parroquia']
                    persona.sector = remover_tildes(form.cleaned_data['sector'])
                    persona.direccion = remover_tildes(form.cleaned_data['direccion'])
                    persona.direccion2 = remover_tildes(form.cleaned_data['direccion2'])
                    persona.num_direccion = remover_tildes(form.cleaned_data['num_direccion'])
                    persona.telefono = remover_tildes(form.cleaned_data['telefono'])
                    persona.telefono_conv = remover_tildes(form.cleaned_data['telefono_conv'])
                    persona.email = form.cleaned_data['email']
                    persona.emailinst = form.cleaned_data['emailinst']
                    persona.sangre = form.cleaned_data['sangre']
                    persona.save(request)

                    perfil = profesor.persona.mi_perfil()
                    perfil.raza = form.cleaned_data['etnia']
                    perfil.nacionalidadindigena = form.cleaned_data['nacionalidadindigena']
                    perfil.save(request)
                    profesor.fechainiciodocente = form.cleaned_data['fechainiciodocente']
                    profesor.coordinacion = form.cleaned_data['coordinacion']
                    profesor.nivelescalafon = form.cleaned_data['nivelescalafon']
                    profesor.save(request)
                    cedula = persona.cedula_doc()
                    if request.FILES["documentoidentificacion"]:
                        newfile = request.FILES["documentoidentificacion"]
                        newfile._name = generar_nombre("cedula_", newfile._name)
                        if cedula:
                            cedula.cedula = newfile
                            cedula.save(request)
                        else:
                            cedula = CedulaPersona(persona=persona, cedula=newfile)
                            cedula.save(request)
                    log(u'Edito informacion del docente:%s - coordinacion: %s' % (profesor.persona, profesor.coordinacion), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6,form=form)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addtitulacion':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                form = EstudioEducacionSuperiorForm(request.POST)
                if form.is_valid():
                    estudio = EstudioPersona(persona=profesor.persona,
                                             superior=True,
                                             institucioneducacionsuperior_id=form.cleaned_data['institucion'],
                                             carrera=form.cleaned_data['carrera'],
                                             niveltitulacion=form.cleaned_data['niveltitulacion'],
                                             detalleniveltitulacion=form.cleaned_data['detalleniveltitulacion'],
                                             titulo=form.cleaned_data['titulo'],
                                             aliastitulo=form.cleaned_data['aliastitulo'],
                                             fechainicio=form.cleaned_data['fechainicio'],
                                             fechafin=form.cleaned_data['fechafin'],
                                             fecharegistro=form.cleaned_data['fecharegistro'],
                                             fechagraduacion=form.cleaned_data['fechagraduacion'],
                                             registro=form.cleaned_data['registro'],
                                             cursando=form.cleaned_data['cursando'],
                                             aplicabeca=form.cleaned_data['aplicabeca'],
                                             tipobeca=form.cleaned_data['tipobeca'],
                                             montobeca=form.cleaned_data['montobeca'],
                                             tipofinanciamientobeca=form.cleaned_data['tipofinanciamientobeca'],
                                             cicloactual=form.cleaned_data['cicloactual'])
                    estudio.save(request)
                    log(u'Adiciono estudio de:%s - %s' % (profesor.persona,estudio), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addcurso':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                form = CursoPersonaForm(request.POST)
                if form.is_valid():
                    curso = CursoPersona(persona=profesor.persona,
                                         nombre=form.cleaned_data['nombre'],
                                         institucion_id=form.cleaned_data['institucion'],
                                         educacionsuperior=form.cleaned_data['esinstitucion'],
                                         institucionformacion=form.cleaned_data['institucionformacion'],
                                         tipocurso=form.cleaned_data['tipocurso'],
                                         fecha_inicio=form.cleaned_data['fecha_inicio'],
                                         apolloinstitucion=form.cleaned_data['apolloinstitucion'],
                                         fecha_fin=form.cleaned_data['fecha_fin'],
                                         horas=form.cleaned_data['horas'])
                    curso.save(request)
                    log(u'Adiciono curso para : %s -%s' % (profesor.persona,curso), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edittitulacion':
            try:
                titulacion = EstudioPersona.objects.get(pk=request.POST['id'])
                form = EstudioEducacionSuperiorForm(request.POST)
                if form.is_valid():
                    titulacion.institucioneducacionsuperior_id = form.cleaned_data['institucion']
                    titulacion.niveltitulacion = form.cleaned_data['niveltitulacion']
                    titulacion.detalleniveltitulacion = form.cleaned_data['detalleniveltitulacion']
                    titulacion.carrera = form.cleaned_data['carrera']
                    titulacion.titulo = form.cleaned_data['titulo']
                    titulacion.aliastitulo = form.cleaned_data['aliastitulo']
                    titulacion.fechainicio = form.cleaned_data['fechainicio']
                    titulacion.fechafin = form.cleaned_data['fechafin']
                    titulacion.fecharegistro = form.cleaned_data['fecharegistro']
                    titulacion.fechagraduacion = form.cleaned_data['fechagraduacion']
                    titulacion.cursando = form.cleaned_data['cursando']
                    titulacion.cicloactual = form.cleaned_data['cicloactual']
                    titulacion.registro = form.cleaned_data['registro']
                    titulacion.aplicabeca = form.cleaned_data['aplicabeca']
                    titulacion.tipobeca = form.cleaned_data['tipobeca']
                    titulacion.montobeca = form.cleaned_data['montobeca']
                    titulacion.tipofinanciamientobeca = form.cleaned_data['tipofinanciamientobeca']
                    titulacion.save(request)
                    log(u'Modifico estudio de: %s - %s' % (titulacion.persona, titulacion), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editcurso':
            try:
                curso = CursoPersona.objects.get(pk=request.POST['id'])
                form = CursoPersonaForm(request.POST)
                if form.is_valid():
                    esinstitucion = form.cleaned_data['esinstitucion']
                    curso.nombre = form.cleaned_data['nombre']
                    curso.institucion_id = form.cleaned_data['institucion'] if esinstitucion else None
                    curso.institucionformacion=form.cleaned_data['institucionformacion'] if not esinstitucion else ''
                    curso.tipocurso = form.cleaned_data['tipocurso']
                    curso.fecha_inicio = form.cleaned_data['fecha_inicio']
                    curso.fecha_fin = form.cleaned_data['fecha_fin']
                    curso.apolloinstitucion = form.cleaned_data['apolloinstitucion']
                    curso.horas = form.cleaned_data['horas']
                    curso.save(request)
                    log(u'modifico curso de: %s - %s' % (curso.persona,curso), request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deltitulacion':
            try:
                titulacion = EstudioPersona.objects.get(pk=request.POST['id'])
                log(u'Elimino estudio de: %s - %s' % (titulacion.persona, titulacion), request, "del")
                titulacion.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'delcurso':
            try:
                curso = CursoPersona.objects.get(pk=request.POST['id'])
                log(u'Elimino curso de: %s - %s' % (curso.persona,curso), request, "del")
                curso.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'cargarcv':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                form = CargarCVForm(request.POST, request.FILES)
                if form.is_valid():
                    personaprofesor = profesor.persona
                    cv = personaprofesor.cv()
                    newfile = request.FILES['cv']
                    newfile._name = generar_nombre("cv_", newfile._name)
                    if cv:
                        cv.cv = newfile
                        cv.save(request)
                    else:
                        cv = CVPersona(persona=personaprofesor,
                                       cv=newfile)
                        cv.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'resetear':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                resetear_clave(profesor.persona)
                profesor.persona.cambiar_clave()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'borrarcv':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                personaprofesor = profesor.persona
                personaprofesor.borrar_cv()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'activar':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                ui = profesor.persona.usuario
                ui.is_active = True
                ui.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desactivar':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                ui = profesor.persona.usuario
                ui.is_active = False
                ui.save()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addadministrativo':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                if profesor.persona.administrativo_set.exists():
                    return bad_json(mensaje=u"El usuario ya tiene un perfil como administrativo.")
                administrativo = Administrativo(persona=profesor.persona,
                                                sede=profesor.coordinacion.sede)
                administrativo.save(request)
                grupo = Group.objects.get(pk=ADMINISTRATIVOS_GROUP_ID)
                grupo.user_set.add(profesor.persona.usuario)
                grupo.save()
                profesor.persona.crear_perfil(administrativo=administrativo)
                log(u'Adiciono administrativo: %s' % administrativo, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'periodoscarrera':
            try:
                carrera = Carrera.objects.get(pk=int(request.POST['idcarrera']))
                lista = []
                for periodo in Periodo.objects.filter():
                    lista.append([periodo.id, periodo.__str__()])
                return ok_json({'lista': lista})
            except:
                return bad_json(error=3)

        if action == 'addestudiante':
            try:
                form = NuevaInscripcionForm(request.POST)
                if form.is_valid():
                    profesor = Profesor.objects.get(pk=request.POST['id'])
                    carrera = form.cleaned_data['carrera']
                    sesion = form.cleaned_data['sesion']
                    modalidad = form.cleaned_data['modalidad']
                    sede = form.cleaned_data['sede']
                    coordinacion = form.cleaned_data['coordinacion']
                    malla = form.cleaned_data['malla']
                    if Inscripcion.objects.filter(persona=profesor.persona, carrera=carrera).exists():
                        return bad_json(mensaje=u"Ya se encuentra registrado en esa carrera.")
                    nuevainscripcion = Inscripcion(persona=profesor.persona,
                                                   fecha=datetime.now().date(),
                                                   hora=datetime.now().time(),
                                                   fechainiciocarrera=form.cleaned_data['fechainiciocarrera'],
                                                   carrera=carrera,
                                                   modalidad=modalidad,
                                                   sesion=sesion,
                                                   sede=sede,
                                                   coordinacion=coordinacion,
                                                   condicionado=True)
                    nuevainscripcion.save(request)
                    malla = InscripcionMalla(inscripcion=nuevainscripcion,
                                           malla=malla)
                    malla.save()
                    nuevainscripcion.actualiza_fecha_inicio_carrera()
                    grupo = Group.objects.get(pk=ALUMNOS_GROUP_ID)
                    grupo.user_set.add(profesor.persona.usuario)
                    grupo.save()
                    personaadmin = profesor.persona
                    personaadmin.crear_perfil(inscripcion=nuevainscripcion)
                    personaadmin.save(request)
                    minivel = nuevainscripcion.mi_nivel()
                    if form.cleaned_data['prenivelacion']:
                        nuevainscripcion.nivelhomologado = form.cleaned_data['nivelmalla']
                        nuevainscripcion.save(request)
                    nuevainscripcion.mi_malla(form.cleaned_data['malla'])
                    nuevainscripcion.actualizar_nivel()
                    nuevainscripcion.actualiza_tipo_inscripcion()
                    nuevainscripcion.generar_rubro_inscripcion(form.cleaned_data['malla'])
                    log(u'Adiciono como estudiante a docente: %s' % nuevainscripcion, request, "add")
                    documentos = nuevainscripcion.documentos_entregados()
                    documentos.pre = form.cleaned_data['prenivelacion']
                    documentos.observaciones_pre = form.cleaned_data['observacionespre']
                    documentos.save(request)
                    # SNNA
                    snna = profesor.persona.datos_snna()
                    snna.rindioexamen = form.cleaned_data['rindioexamen']
                    snna.fechaexamen = form.cleaned_data['fechaexamensnna']
                    snna.puntaje = form.cleaned_data['puntajesnna']
                    snna.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desactivarperfil':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                profesor.activo = False
                profesor.save(request)
                log(u'Desactivo perfil de usuario: %s' % profesor, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'activarperfil':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                profesor.activo = True
                profesor.save(request)
                log(u'Activo perfil de usuario: %s' % profesor, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'verificartitulo':
            try:
                estudio = EstudioPersona.objects.get(pk=request.POST['id'])
                estudio.verificado = (request.POST['valor'] == 'true')
                estudio.save(request)
                log(u"Verifico datos de estudio de : %s - %s" % (estudio.persona,estudio), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'verificarcurso':
            try:
                estudio = CursoPersona.objects.get(pk=request.POST['id'])
                estudio.verificado = (request.POST['valor'] == 'true')
                estudio.save(request)
                log(u"Verifico datos de curso para: %s - %s" % (estudio.persona,estudio), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'verificarpublicacion':
            try:
                publicacion = Publicaciones.objects.get(pk=request.POST['id'])
                publicacion.verificado = (request.POST['valor'] == 'true')
                publicacion.save(request)
                log(u"Verifico datos de publicacion de: %s - %s" % (publicacion.persona,publicacion), request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addarchivo':
            try:
                form = ArchivoEvidenciaEstudiosForm(request.POST, request.FILES)
                if form.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("estudiopersona_", newfile._name)
                    estudio = EstudioPersona.objects.get(pk=request.POST['id'])
                    estudio.archivo = newfile
                    estudio.save(request)
                    log(u'Adiciono archivo: %s' % estudio, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addarchivocurso':
            try:
                form = ArchivoEvidenciaEstudiosForm(request.POST, request.FILES)
                if form.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("cursopersona", newfile._name)
                    curso = CursoPersona.objects.get(pk=request.POST['id'])
                    curso.archivo = newfile
                    curso.save(request)
                    log(u'Adiciono archivo: %s' % curso, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addarchivopublicacion':
            try:
                form = ArchivoEvidenciaEstudiosForm(request.POST, request.FILES)
                if form.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("cursopersona", newfile._name)
                    publicacion = Publicaciones.objects.get(pk=request.POST['id'])
                    publicacion.archivo = newfile
                    publicacion.save(request)
                    log(u'Adiciono archivo: %s' % publicacion, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addpublicacion':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                form = PublicacionesPersonaForm(request.POST)
                if form.is_valid():
                    titulo = form.cleaned_data['titulo']
                    for p in Publicaciones.objects.all():
                        if p.titulo == titulo:
                            return bad_json(error=7, mensaje='La publicación ya fue registrada por: ' + str(p.autor))
                    publicacion = Publicaciones(autor=profesor,
                                                titulo=form.cleaned_data['titulo'],
                                                codigoies=CODIGO_IES,
                                                tipopublicacion_id=9,
                                                tipoarticulo=form.cleaned_data['tipoarticulo'],
                                                codigodoi=form.cleaned_data['codigodoi'],
                                                basedatosindexada=form.cleaned_data['bdindexada'],
                                                catalogo_id=form.cleaned_data['revista'],
                                                issn=form.cleaned_data['issn'],
                                                numerorevista=form.cleaned_data['numerorevista'],
                                                cuatril=form.cleaned_data['cuatril'],
                                                sjr=form.cleaned_data['sjr'],
                                                fechapublicacion=form.cleaned_data['fecha'],
                                                carrera=form.cleaned_data['carrera'],
                                                centroinvestigacion=form.cleaned_data['centro'],
                                                estado=form.cleaned_data['estado'],
                                                linkpublicacion=form.cleaned_data['linkpublicacion'],
                                                linkrevista=form.cleaned_data['linkrevista'],
                                                filiacion=form.cleaned_data['filiacion'],
                                                volumenrevista=form.cleaned_data['volumenrevista'])
                    publicacion.save(request)
                    log(u'Adiciono curso: %s' % publicacion, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editpublicacion':
            try:
                publicacion = PublicacionPersona.objects.get(pk=request.POST['id'])
                form = PublicacionesPersonaForm(request.POST)
                if form.is_valid():
                    publicacion.titulo = form.cleaned_data['titulo']
                    publicacion.tipoarticulo = form.cleaned_data['tipoarticulo']
                    publicacion.codigodoi = form.cleaned_data['codigodoi']
                    publicacion.basedatosindexada = form.cleaned_data['bdindexada']
                    publicacion.catalogo_id = form.cleaned_data['revista'] if form.cleaned_data['revista'] > 0 else None
                    publicacion.issn = form.cleaned_data['issn']
                    publicacion.numerorevista = form.cleaned_data['numerorevista']
                    publicacion.cuatril = form.cleaned_data['cuatril']
                    publicacion.sjr = form.cleaned_data['sjr']
                    publicacion.fechapublicacion = form.cleaned_data['fecha']
                    publicacion.centroinvestigacion = form.cleaned_data['centro']
                    publicacion.estado = form.cleaned_data['estado']
                    publicacion.carrera = form.cleaned_data['carrera']
                    publicacion.linkpublicacion = form.cleaned_data['linkpublicacion']
                    publicacion.linkrevista = form.cleaned_data['linkrevista']
                    publicacion.filiacion = form.cleaned_data['filiacion']
                    publicacion.volumenrevista = form.cleaned_data['volumenrevista']
                    publicacion.save(request)
                    log(u'modifico curso: %s' % publicacion, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delpublicacion':
            try:
                publicacion = Publicaciones.objects.get(pk=request.POST['id'])
                log(u'Elimino publicacion: %s' % publicacion, request, "del")
                publicacion.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'actualizartitulos':
            try:
                profesor = Profesor.objects.get(pk=request.POST['id'])
                consultar_titulos(profesor.persona)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'resetear':
                try:
                    data['title'] = u'Resetear clave del usuario'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/resetear.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivar':
                try:
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/desactivar.html", data)
                except Exception as ex:
                    pass

            if action == 'activar':
                try:
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/activar.html", data)
                except Exception as ex:
                    pass

            if action == 'titulacion':
                try:
                    data['title'] = u'Titulos y cursos del profesor'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['titulos'] = profesor.persona.estudiopersona_set.all()
                    data['cursos'] = profesor.persona.cursopersona_set.all()
                    data['distributivos'] = ProfesorDistributivoHoras.objects.filter(profesor=profesor,periodo__extendido=False).order_by('-periodo__inicio')[0:6]
                    data['publicaciones'] = profesor.publicaciones_set.filter(tipopublicacion_id=9).order_by('-fechapublicacion')
                    data['docentes_registran_estudios'] = DOCENTES_REGISTRAN_ESTUDIOS
                    data['docentes_registran_cursos'] = DOCENTES_REGISTRAN_CURSOS
                    data['docentes_registran_publicaciones'] = DOCENTES_REGISTRAN_PUBLICACIONES
                    data['docentes_registran_cv'] = DOCENTES_REGISTRAN_CV
                    data['puede_modificar_distributivo'] = True if (Group.objects.get(pk=26) in persona.grupos()) else False
                    return render(request, "docentes/titulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addtitulacion':
                try:
                    data['title'] = u'Adicionar titulación del profesor'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    form = EstudioEducacionSuperiorForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "docentes/addtitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addcurso':
                try:
                    data['title'] = u'Adicionar curso'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['form'] = CursoPersonaForm()
                    return render(request, "docentes/addcurso.html", data)
                except Exception as ex:
                    pass

            if action == 'edittitulacion':
                try:
                    data['title'] = u'Editar titulación del profesor'
                    data['titulacion'] = titulacion = EstudioPersona.objects.get(pk=request.GET['id'])
                    data['profesor'] = titulacion.persona.profesor()
                    form = EstudioEducacionSuperiorForm(initial={'institucion': titulacion.institucioneducacionsuperior_id,
                                                                 'niveltitulacion': titulacion.niveltitulacion,
                                                                 'detalleniveltitulacion': titulacion.detalleniveltitulacion,
                                                                 'carrera': titulacion.carrera,
                                                                 'fechainicio': titulacion.fechainicio,
                                                                 'fechafin': titulacion.fechafin,
                                                                 'fecharegistro': titulacion.fecharegistro,
                                                                 'cursando': titulacion.cursando,
                                                                 'cicloactual': titulacion.cicloactual,
                                                                 'titulo': titulacion.titulo,
                                                                 'aliastitulo': titulacion.aliastitulo,
                                                                 'fechagraduacion': titulacion.fechagraduacion,
                                                                 'aplicabeca': titulacion.aplicabeca,
                                                                 'montobeca': titulacion.montobeca,
                                                                 'tipobeca': titulacion.tipobeca,
                                                                 'tipofinanciamientobeca': titulacion.tipofinanciamientobeca,
                                                                 'registro': titulacion.registro})
                    form.editar(titulacion)
                    data['form'] = form
                    return render(request, "docentes/edittitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editcurso':
                try:
                    data['title'] = u'Editar curso'
                    data['curso'] = curso = CursoPersona.objects.get(pk=request.GET['id'])
                    data['profesor'] = curso.persona.profesor()
                    form = CursoPersonaForm(initial={"institucion": curso.institucion.id if curso.institucion else None,
                                                     "esinstitucion": curso.educacionsuperior,
                                                     "institucionformacion": curso.institucionformacion,
                                                     "nombre": curso.nombre,
                                                     "tipocurso": curso.tipocurso,
                                                     "apolloinstitucion": curso.apolloinstitucion,
                                                     "fecha_inicio": curso.fecha_inicio,
                                                     "fecha_fin": curso.fecha_fin,
                                                     "horas": curso.horas})
                    form.editar(curso)
                    data['form'] = form
                    return render(request, "docentes/editcurso.html", data)
                except Exception as ex:
                    pass

            if action == 'deltitulacion':
                try:
                    data['title'] = u'Eliminar titulación del profesor'
                    data['titulacion'] = titulacion = EstudioPersona.objects.get(pk=request.GET['id'])
                    data['profesor'] = titulacion.persona.profesor()
                    return render(request, "docentes/deltitulacion.html", data)
                except Exception as ex:
                    pass

            if action == 'delcurso':
                try:
                    data['title'] = u'Eliminr curso'
                    data['curso'] = curso = CursoPersona.objects.get(pk=request.GET['id'])
                    data['profesor'] = curso.persona.profesor()
                    return render(request, "docentes/delcurso.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Adicionar profesor'
                    form = ProfesorForm()
                    form.adicionar()
                    data['form'] = form
                    data['email_domain'] = EMAIL_DOMAIN
                    data['email_domain_estudiante'] = EMAIL_DOMAIN_ESTUDIANTES
                    data['pais_ecuador_id'] = PAIS_ECUADOR_ID
                    data['email_institucional_automatico'] = EMAIL_INSTITUCIONAL_AUTOMATICO_DOCENTES
                    data['nacionalidad_indigena_id'] = NACIONALIDAD_INDIGENA_ID
                    return render(request, "docentes/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar profesor'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    perfil = profesor.persona.mi_perfil()
                    form = ProfesorForm(initial={'nombre1': profesor.persona.nombre1,
                                                 'nombre2': profesor.persona.nombre2,
                                                 'apellido1': profesor.persona.apellido1,
                                                 'apellido2': profesor.persona.apellido2,
                                                 'nivelescalafon': profesor.nivelescalafon,
                                                 'cedula': profesor.persona.cedula,
                                                 'pasaporte': profesor.persona.pasaporte,
                                                 'nacionalidad': profesor.persona.nacionalidad,
                                                 'paisnac': profesor.persona.paisnac,
                                                 'provincianac': profesor.persona.provincianac,
                                                 'cantonnac': profesor.persona.cantonnac,
                                                 'parroquianac': profesor.persona.parroquianac,
                                                 'nacimiento': profesor.persona.nacimiento,
                                                 'sexo': profesor.persona.sexo,
                                                 'etnia': perfil.raza,
                                                 'nacionalidadindigena': perfil.nacionalidadindigena,
                                                 'sangre': profesor.persona.sangre,
                                                 'pais': profesor.persona.pais,
                                                 'provincia': profesor.persona.provincia,
                                                 'canton': profesor.persona.canton,
                                                 'parroquia': profesor.persona.parroquia,
                                                 'sector': profesor.persona.sector,
                                                 'direccion': profesor.persona.direccion,
                                                 'direccion2': profesor.persona.direccion2,
                                                 'num_direccion': profesor.persona.num_direccion,
                                                 'telefono': profesor.persona.telefono,
                                                 'telefono_conv': profesor.persona.telefono_conv,
                                                 'email': profesor.persona.email,
                                                 'emailinst': profesor.persona.emailinst,
                                                 'coordinacion': profesor.coordinacion,
                                                 'dedicacion': profesor.dedicacion,
                                                 'fechainiciodocente': profesor.fechainiciodocente})
                    form.editar(profesor)
                    data['form'] = form
                    data['email_domain'] = EMAIL_DOMAIN
                    data['email_domain_estudiante'] = EMAIL_DOMAIN_ESTUDIANTES
                    data['pais_ecuador_id'] = PAIS_ECUADOR_ID
                    data['email_institucional_automatico'] = EMAIL_INSTITUCIONAL_AUTOMATICO_DOCENTES
                    data['nacionalidad_indigena_id'] = NACIONALIDAD_INDIGENA_ID
                    return render(request, "docentes/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'cargarcv':
                try:
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    data['form'] = CargarCVForm()
                    return render(request, "docentes/cargarcv.html", data)
                except Exception as ex:
                    pass

            if action == 'borrarcv':
                try:
                    data['title'] = u'Borrar CV'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/borrarcv.html", data)
                except Exception as ex:
                    pass

            if action == 'horario':
                try:
                    data['title'] = u'Horario del profesor'
                    periodo = request.session['periodo']
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],[6, 'Sabado'], [7, 'Domingo']]
                    data['materiasregulares'] = materiasregulares = Materia.objects.filter(profesormateria__profesor=profesor, nivel__periodo=periodo).distinct()
                    data['clases'] = clases = Clase.objects.filter(materia__in=materiasregulares, activo=True).distinct()
                    data['turnos'] = Turno.objects.filter(clase__in=clases).distinct().order_by('comienza')
                    data['reporte_0'] = obtener_reporte('horario_docente_periodo')
                    return render(request, "docentes/horario.html", data)
                except Exception as ex:
                    pass

            if action == 'addadministrativo':
                try:
                    data['title'] = u'Crear cuenta de administrativo'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/addadministrativo.html", data)
                except Exception as ex:
                    pass

            if action == 'addestudiante':
                try:
                    data['title'] = u'Crear cuenta de estudiante'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    form = NuevaInscripcionForm()
                    form.adicionar(persona,coordinacion)
                    data['form'] = form
                    return render(request, "docentes/addestudiante.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivarperfil':
                try:
                    data['title'] = u'Desactivar perfil de usuario'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/desactivarperfil.html", data)
                except Exception as ex:
                    pass

            if action == 'activarperfil':
                try:
                    data['title'] = u'Activar perfil de usuario'
                    data['profesor'] = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/activarperfil.html", data)
                except Exception as ex:
                    pass

            if action == 'materias':
                try:
                    data['title'] = u'Materias del profesor'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    periodo = request.session['periodo']
                    data['materias'] = profesor.mis_materias(periodo).order_by('materia__asignatura__nombre')
                    data['reporte_0'] = obtener_reporte('listado_asistencia_dias')
                    data['reporte_1'] = obtener_reporte('lista_alumnos_matriculados_materia')
                    data['reporte_2'] = obtener_reporte("control_academico")
                    return render(request, "docentes/materias.html", data)
                except Exception as ex:
                    pass

            if action == 'tutorias':
                try:
                    data['title'] = u'Tutorías activas'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['tutorias'] = profesor.tutor_proyectogrado_activos()
                    return render(request, "docentes/tutorias.html", data)
                except Exception as ex:
                    pass

            if action == 'addpublicacion':
                try:
                    data['title'] = u'Adicionar publicación'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    data['form'] = PublicacionesPersonaForm()
                    return render(request, "docentes/addpublicacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addarchivo':
                try:
                    data['title'] = u'Adicionar archivo'
                    data['titulacion'] = titulacion = EstudioPersona.objects.get(pk=request.GET['id'])
                    data['profesor'] = titulacion.persona.profesor()
                    data['form'] = ArchivoEvidenciaEstudiosForm()
                    return render(request, "docentes/addarchivo.html", data)
                except Exception as ex:
                    pass

            if action == 'addarchivopublicacion':
                try:
                    data['title'] = u'Adicionar archivo'
                    data['publicacion'] = publicacion = Publicaciones.objects.get(pk=request.GET['id'])
                    data['profesor'] = publicacion.autor.profesor()
                    data['form'] = ArchivoEvidenciaEstudiosForm()
                    return render(request, "docentes/addarchivopublicacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addarchivocurso':
                try:
                    data['title'] = u'Adicionar archivo'
                    data['curso'] = curso = CursoPersona.objects.get(pk=request.GET['id'])
                    data['profesor'] = curso.persona.profesor()
                    data['form'] = ArchivoEvidenciaEstudiosForm()
                    return render(request, "docentes/addarchivocurso.html", data)
                except Exception as ex:
                    pass

            if action == 'editpublicacion':
                try:
                    data['title'] = u'Editar publicación'
                    data['publicacion'] = publicacion = PublicacionPersona.objects.get(pk=request.GET['id'])
                    data['profesor'] = publicacion.persona.profesor()
                    form = PublicacionesPersonaForm(initial={"titulo": publicacion.titulo,
                                                             "tipoarticulo": publicacion.tipoarticulo,
                                                             "codigodoi": publicacion.codigodoi,
                                                             "bdindexada": publicacion.basedatosindexada,
                                                             "revista": publicacion.catalogo.id if publicacion.catalogo else 0,
                                                             "issn": publicacion.issn,
                                                             "numerorevista": publicacion.numerorevista,
                                                             "cuatril": publicacion.cuatril,
                                                             "sjr": publicacion.sjr,
                                                             "fecha": publicacion.fechapublicacion,
                                                             "centro": publicacion.centroinvestigacion,
                                                             "carrera": publicacion.carrera,
                                                             "estado": publicacion.estado,
                                                             "linkpublicacion": publicacion.linkpublicacion,
                                                             "linkrevista": publicacion.linkrevista,
                                                             "volumenrevista": publicacion.volumenrevista,
                                                             "filiacion": publicacion.filiacion})
                    form.editar(publicacion)
                    data['form'] = form
                    return render(request, "docentes/editpublicacion.html", data)
                except Exception as ex:
                    pass

            if action == 'delpublicacion':
                try:
                    data['title'] = u'Eliminar publicación'
                    data['publicacion'] = publicacion = Publicaciones.objects.get(pk=request.GET['id'])
                    data['profesor'] = publicacion.autor.profesor()
                    return render(request, "docentes/delpublicacion.html", data)
                except Exception as ex:
                    pass

            if action == 'actualizartitulos':
                try:
                    data['title'] = u'Actualizar títulos'
                    data['profesor'] = profesor = Profesor.objects.get(pk=request.GET['id'])
                    return render(request, "docentes/actualizartitulos.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de profesores'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        profesores = Profesor.objects.filter(Q(persona__nombre1__icontains=search) |
                                                             Q(persona__nombre2__icontains=search) |
                                                             Q(persona__apellido1__icontains=search) |
                                                             Q(persona__apellido2__icontains=search) |
                                                             Q(persona__cedula__icontains=search) |
                                                             Q(persona__pasaporte__icontains=search)).distinct()
                    else:
                        profesores = Profesor.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                             Q(persona__apellido2__icontains=ss[1])).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    profesores = Profesor.objects.filter(id=ids)
                else:
                    profesores = Profesor.objects.all()
                paging = MiPaginador(profesores, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'docentes':
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
                request.session['paginador_url'] = 'docentes'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['profesores'] = page.object_list
                data['reporte_0'] = obtener_reporte('listado_clases_abiertas')
                data['reporte_1'] = obtener_reporte('ficha_docente')
                data['reporte_2'] = obtener_reporte('resultado_evaluacion')
                if persona.id in PERM_ENTRAR_COMO_USUARIO:
                    data['entrar_como_usuario'] = True
                return render(request, "docentes/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/")
