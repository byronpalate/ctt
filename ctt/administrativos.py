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
from settings import PROFESORES_GROUP_ID, ADMINISTRATIVOS_GROUP_ID, ALUMNOS_GROUP_ID, EMAIL_DOMAIN, \
    EMPLEADORES_GRUPO_ID, PAIS_ECUADOR_ID, EMAIL_DOMAIN_ESTUDIANTES,PERM_ENTRAR_COMO_USUARIO, \
    NACIONALIDAD_INDIGENA_ID, TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID, ESCALAFON_TITULAR_PRINCIPAL_ID, \
    EMAIL_INSTITUCIONAL_AUTOMATICO_ADMINISTRATIVOS, PERM_DIRECTOR_SIS
from ctt.commonviews import adduserdata
from ctt.forms import AdministrativosForm, GrupoUsuarioForm, NuevaInscripcionForm, SedeAdministrativoForm
from ctt.funciones import MiPaginador, log, generar_usuario, resetear_clave, url_back, bad_json, ok_json, generar_email, \
    remover_tildes, validarcedula
from ctt.models import Persona, Profesor, Administrativo, Inscripcion, Carrera, Periodo, Nacionalidad, Coordinacion


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                form = AdministrativosForm(request.POST)
                if form.is_valid():
                    cedula = form.cleaned_data['cedula'].strip()
                    pasaporte = form.cleaned_data['pasaporte'].strip()
                    fechanac = form.cleaned_data['nacimiento']
                    edad = relativedelta(datetime.now(), fechanac)
                    nacionalidad = form.cleaned_data['nacionalidad']
                    pais = Nacionalidad.objects.get(nombre=nacionalidad)
                    if pais.id == 18:
                        if validarcedula(cedula) != 'Ok':
                            return bad_json(mensaje=u"El número de pasaporte ingresado esta incorrecto.")
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
                    personaadmin = Persona(nombre1=remover_tildes(form.cleaned_data['nombre1']),
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
                                           sangre=form.cleaned_data['sangre'],
                                           email=form.cleaned_data['email'])
                    personaadmin.save(request)
                    administrativo = Administrativo(persona=personaadmin,
                                                    sede=form.cleaned_data['sede'],
                                                    activo=True)
                    administrativo.save(request)
                    generar_usuario(persona=personaadmin, group_id=ADMINISTRATIVOS_GROUP_ID)
                    if EMAIL_INSTITUCIONAL_AUTOMATICO_ADMINISTRATIVOS:
                        personaadmin.emailinst = generar_email(personaadmin)
                    else:
                        personaadmin.emailinst = form.cleaned_data['emailinst']
                    personaadmin.save(request)
                    personaadmin.crear_perfil(administrativo=administrativo)
                    personaadmin.mi_ficha()
                    perfil = personaadmin.mi_perfil()
                    perfil.raza = form.cleaned_data['etnia']
                    perfil.nacionalidadindigena = form.cleaned_data['nacionalidadindigena']
                    perfil.save(request)
                    personaadmin.datos_extension()
                    log(u'Adiciono personal administrativo: %s' % administrativo, request, "add")
                    return ok_json({"id": administrativo.id})
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edit':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                personaadmin = administrativo.persona
                form = AdministrativosForm(request.POST)
                if form.is_valid():
                    cedula = remover_tildes(form.cleaned_data['cedula'].strip())
                    pasaporte = form.cleaned_data['pasaporte'].strip()
                    if not cedula and not pasaporte:
                        return bad_json(mensaje=u"Debe ingresar una identificación.")
                    if cedula:
                        if Persona.objects.filter(cedula=cedula).exclude(id=personaadmin.id).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if pasaporte:
                        if Persona.objects.filter(pasaporte=pasaporte).exclude(id=personaadmin.id).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    perfil = personaadmin.mi_perfil()
                    personaadmin.nombre1 = remover_tildes(form.cleaned_data['nombre1'])
                    personaadmin.nombre2 = remover_tildes(form.cleaned_data['nombre2'])
                    personaadmin.apellido1 = remover_tildes(form.cleaned_data['apellido1'])
                    personaadmin.apellido2 = remover_tildes(form.cleaned_data['apellido2'])
                    personaadmin.cedula = remover_tildes(form.cleaned_data['cedula'])
                    personaadmin.pasaporte = form.cleaned_data['pasaporte']
                    personaadmin.nacimiento = form.cleaned_data['nacimiento']
                    personaadmin.sexo = form.cleaned_data['sexo']
                    personaadmin.nacionalidad = form.cleaned_data['nacionalidad']
                    personaadmin.paisnac = form.cleaned_data['paisnac']
                    personaadmin.provincianac = form.cleaned_data['provincianac']
                    personaadmin.cantonnac = form.cleaned_data['cantonnac']
                    personaadmin.parroquianac = form.cleaned_data['parroquianac']
                    personaadmin.pais = form.cleaned_data['pais']
                    personaadmin.provincia = form.cleaned_data['provincia']
                    personaadmin.canton = form.cleaned_data['canton']
                    personaadmin.parroquia = form.cleaned_data['parroquia']
                    personaadmin.sector = remover_tildes(form.cleaned_data['sector'])
                    personaadmin.direccion = remover_tildes(form.cleaned_data['direccion'])
                    personaadmin.direccion2 = remover_tildes(form.cleaned_data['direccion2'])
                    personaadmin.num_direccion = remover_tildes(form.cleaned_data['num_direccion'])
                    personaadmin.telefono = remover_tildes(form.cleaned_data['telefono'])
                    personaadmin.telefono_conv = remover_tildes(form.cleaned_data['telefono_conv'])
                    personaadmin.email = form.cleaned_data['email']
                    personaadmin.emailinst = form.cleaned_data['emailinst']
                    personaadmin.sangre = form.cleaned_data['sangre']
                    personaadmin.save(request)
                    administrativo.sede = form.cleaned_data['sede']
                    administrativo.save()
                    perfil.raza = form.cleaned_data['etnia']
                    perfil.nacionalidadindigena = form.cleaned_data['nacionalidadindigena']
                    perfil.save(request)
                    log(u'Modifico administrativo: %s' % administrativo, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'resetear':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                resetear_clave(administrativo.persona)
                administrativo.persona.cambiar_clave()
                log(u'Reseteo clave de usuario: %s' % administrativo, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addprofesor':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                if administrativo.persona.profesor_set.exists():
                    return bad_json(mensaje=u"El usuario ya tiene un perfil como profesor.")
                profesor = Profesor(persona=administrativo.persona,
                                    activo=True,
                                    coordinacion=request.session['coordinacionseleccionada'],
                                    fechainiciodocente=datetime.now().date(),
                                    dedicacion_id=TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID,
                                    nivelescalafon_id=ESCALAFON_TITULAR_PRINCIPAL_ID)
                profesor.save(request)
                grupo = Group.objects.get(pk=PROFESORES_GROUP_ID)
                grupo.user_set.add(administrativo.persona.usuario)
                grupo.save()
                administrativo.persona.crear_perfil(profesor=profesor)
                log(u'Adiciono profesor: %s' % profesor, request, "add")
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
            except Exception as ex:
                return bad_json(error=3, ex=ex)

        if action == 'addestudiante':
            try:
                form = NuevaInscripcionForm(request.POST)
                if form.is_valid():
                    administrativo = Administrativo.objects.get(pk=int(request.POST['id']))
                    carrera = form.cleaned_data['carrera']
                    sesion = form.cleaned_data['sesion']
                    modalidad = form.cleaned_data['modalidad']
                    sede = form.cleaned_data['sede']
                    coordinacion = form.cleaned_data['coordinacion']
                    if Inscripcion.objects.filter(persona=administrativo.persona, coordinacion=form.cleaned_data['coordinacion'], carrera=form.cleaned_data['carrera'], modalidad=form.cleaned_data['modalidad']).exists():
                        return bad_json(mensaje=u'El estudiante ya se encuentra registrado en esta carrera con esta modalidad.')
                    nuevainscripcion = Inscripcion(persona=administrativo.persona,
                                                   fecha=datetime.now().date(),
                                                   hora=datetime.now().time(),
                                                   fechainiciocarrera=form.cleaned_data['fechainiciocarrera'],
                                                   periodo=form.cleaned_data['periodo'],
                                                   carrera=carrera,
                                                   modalidad=modalidad,
                                                   sesion=sesion,
                                                   sede=sede,
                                                   coordinacion=coordinacion,
                                                   condicionado=True)
                    nuevainscripcion.save(request)
                    nuevainscripcion.actualiza_fecha_inicio_carrera()
                    grupo = Group.objects.get(pk=ALUMNOS_GROUP_ID)
                    grupo.user_set.add(administrativo.persona.usuario)
                    grupo.save()
                    personaadmin = administrativo.persona
                    personaadmin.crear_perfil(inscripcion=nuevainscripcion)
                    personaadmin.save(request)
                    minivel = nuevainscripcion.mi_nivel()
                    nuevainscripcion.mi_malla(form.cleaned_data['malla'])
                    nuevainscripcion.actualizar_nivel()
                    nuevainscripcion.actualiza_tipo_inscripcion()
                    # nuevainscripcion.generar_rubro_inscripcion(form.cleaned_data['malla'])
                    log(u'Adiciono como estudiante al administrativo: %s' % nuevainscripcion, request, "add")
                    # documentos = nuevainscripcion.documentos_entregados()
                    # documentos.pre = form.cleaned_data['prenivelacion']
                    # documentos.observaciones_pre = form.cleaned_data['observacionespre']
                    # documentos.save(request)
                    # SNNA
                    # snna = administrativo.persona.datos_snna()
                    # snna.rindioexamen = form.cleaned_data['rindioexamen']
                    # snna.fechaexamen = form.cleaned_data['fechaexamensnna']
                    # snna.puntaje = form.cleaned_data['puntajesnna']
                    # snna.save(request)
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'activar':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                usuario = administrativo.persona.usuario
                usuario.is_active = True
                usuario.save()
                log(u'Activo usuario: %s' % administrativo, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'activarperfil':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                administrativo.activo = True
                administrativo.save(request)
                log(u'Activo perfil de usuario: %s' % administrativo, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desactivar':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                ui = administrativo.persona.usuario
                ui.is_active = False
                ui.save()
                log(u'Desactivo usuario: %s' % administrativo, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desactivarperfil':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                administrativo.activo = False
                administrativo.save(request)
                log(u'Desactivo perfil de usuario: %s' % administrativo, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addgrupo':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                form = GrupoUsuarioForm(request.POST)
                if form.is_valid():
                    grupo = form.cleaned_data['grupo']
                    grupo.user_set.add(administrativo.persona.usuario)
                    grupo.save()
                    log(u'Adiciono a grupo : %s a usuario: %s ' % (grupo, administrativo), request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'asignarsede':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                form = SedeAdministrativoForm(request.POST)
                if form.is_valid():
                    administrativo.sede = form.cleaned_data['sede']
                    administrativo.save(request)
                    log(u'Modifico sede de administrativo: %s' % administrativo, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delgrupo':
            try:
                administrativo = Administrativo.objects.get(pk=request.POST['id'])
                grupo = Group.objects.get(pk=request.POST['idg'])
                if grupo.id in [PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]:
                    return bad_json(mensaje=u"No puede eliminar del grupo seleccionado.")
                if administrativo.persona.usuario.groups.exclude(id__in=[PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]).count() <= 1:
                    return bad_json(mensaje=u"El usuario debe de pertenecer a un grupo.")
                grupo.user_set.remove(administrativo.persona.usuario)
                grupo.save()
                log(u'Elimino del grupo de usuarios: %s a usuario: %s' % (grupo, administrativo), request, "del")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar personal administrativo'
                    form = AdministrativosForm()
                    form.adicionar()
                    form.adicionar_provincia()
                    data['email_domain'] = EMAIL_DOMAIN
                    data['email_domain_estudiante'] = EMAIL_DOMAIN_ESTUDIANTES
                    data['pais_ecuador_id'] = PAIS_ECUADOR_ID
                    data['nacionalidad_indigena_id'] = NACIONALIDAD_INDIGENA_ID
                    data['form'] = form
                    return render(request, "administrativos/add.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivar':
                try:
                    data['title'] = u'Desactivar usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/desactivar.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivarperfil':
                try:
                    data['title'] = u'Desactivar perfil de usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/desactivarperfil.html", data)
                except Exception as ex:
                    pass

            if action == 'activar':
                try:
                    data['title'] = u'Activar usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/activar.html", data)
                except Exception as ex:
                    pass

            if action == 'activarperfil':
                try:
                    data['title'] = u'Activar perfil de usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/activarperfil.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar personal administrativo'
                    data['administrativo'] = administrativo = Administrativo.objects.get(pk=request.GET['id'])
                    personaadmin = administrativo.persona
                    perfil = personaadmin.mi_perfil()
                    form = AdministrativosForm(initial={'nombre1': personaadmin.nombre1,
                                                        'nombre2': personaadmin.nombre2,
                                                        'apellido1': personaadmin.apellido1,
                                                        'apellido2': personaadmin.apellido2,
                                                        'cedula': personaadmin.cedula,
                                                        'pasaporte': personaadmin.pasaporte,
                                                        'nacionalidad': personaadmin.nacionalidad,
                                                        'paisnac': personaadmin.paisnac,
                                                        'provincianac': personaadmin.provincianac,
                                                        'cantonnac': personaadmin.cantonnac,
                                                        'parroquianac': personaadmin.parroquianac,
                                                        'nacimiento': personaadmin.nacimiento,
                                                        'etnia': perfil.raza,
                                                        'nacionalidadindigena': perfil.nacionalidadindigena,
                                                        'sexo': personaadmin.sexo,
                                                        'pais': personaadmin.pais,
                                                        'provincia': personaadmin.provincia,
                                                        'canton': personaadmin.canton,
                                                        'parroquia': personaadmin.parroquia,
                                                        'sector': personaadmin.sector,
                                                        'direccion': personaadmin.direccion,
                                                        'direccion2': personaadmin.direccion2,
                                                        'sede': administrativo.sede,
                                                        'num_direccion': personaadmin.num_direccion,
                                                        'telefono': personaadmin.telefono,
                                                        'telefono_conv': personaadmin.telefono_conv,
                                                        'email': personaadmin.email,
                                                        'emailinst': personaadmin.emailinst},)
                    form.editar(administrativo)
                    data['form'] = form
                    data['email_domain'] = EMAIL_DOMAIN
                    data['email_domain_estudiante'] = EMAIL_DOMAIN_ESTUDIANTES
                    data['pais_ecuador_id'] = PAIS_ECUADOR_ID
                    data['nacionalidad_indigena_id'] = NACIONALIDAD_INDIGENA_ID
                    return render(request, "administrativos/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'addgrupo':
                try:
                    data['title'] = u'Adicionar grupo'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    form = GrupoUsuarioForm()
                    form.grupos(Group.objects.all().exclude(id__in=[PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]).order_by('name'))
                    data['form'] = form
                    return render(request, "administrativos/addgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'asignarsede':
                try:
                    data['title'] = u'Asignar sede'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    data['form'] = SedeAdministrativoForm()
                    return render(request, "administrativos/asignarsede.html", data)
                except Exception as ex:
                    pass

            if action == 'resetear':
                try:
                    data['title'] = u'Resetear clave del usuario'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/resetear.html", data)
                except Exception as ex:
                    pass

            if action == 'addprofesor':
                try:
                    data['title'] = u'Crear cuenta de profesor'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    return render(request, "administrativos/addprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'addestudiante':
                try:
                    data['title'] = u'Crear cuenta de estudiante'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    form = NuevaInscripcionForm(formbase='ajaxformdinamicbs.html')
                    coordinacion = Coordinacion.objects.all().first()
                    form.adicionar(persona, coordinacion)
                    data['form'] = form
                    return render(request, "administrativos/addestudiante.html", data)
                except Exception as ex:
                    pass

            if action == 'delgrupo':
                try:
                    data['title'] = u'Eliminar de grupo'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    data['grupo'] = Group.objects.get(pk=request.GET['idg'])
                    return render(request, "administrativos/delgrupo.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de personal administrativo'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        administrativos = Administrativo.objects.filter(Q(persona__nombre1__icontains=search) |
                                                                        Q(persona__nombre2__icontains=search) |
                                                                        Q(persona__apellido1__icontains=search) |
                                                                        Q(persona__apellido2__icontains=search) |
                                                                        Q(persona__cedula__icontains=search) |
                                                                        Q(persona__usuario__groups__name__icontains=search) |
                                                                        Q(persona__pasaporte__icontains=search)).distinct()
                    else:
                        administrativos = Administrativo.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                                        Q(persona__apellido2__icontains=ss[1])).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    administrativos = Administrativo.objects.filter(id=ids).distinct()
                else:
                    administrativos = Administrativo.objects.all()
                paging = MiPaginador(administrativos, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'administrativos':
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
                request.session['paginador_url'] = 'administrativos'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['administrativos'] = page.object_list
                data['grupo_docentes'] = PROFESORES_GROUP_ID
                data['grupo_empleadores'] = EMPLEADORES_GRUPO_ID
                data['grupo_administrativo'] = ADMINISTRATIVOS_GROUP_ID
                data['grupo_estudiantes'] = ALUMNOS_GROUP_ID

                data['entrar_como_usuario']=True
                return render(request, "administrativos/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
