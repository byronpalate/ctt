# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import PROFESORES_GROUP_ID, ADMINISTRATIVOS_GROUP_ID, ALUMNOS_GROUP_ID, EMAIL_DOMAIN, \
    EMPLEADORES_GRUPO_ID, PAIS_ECUADOR_ID, EMAIL_DOMAIN_ESTUDIANTES, NACIONALIDAD_INDIGENA_ID, TIEMPO_DEDICACION_TIEMPO_COMPLETO_ID, ESCALAFON_TITULAR_PRINCIPAL_ID, \
    CLIENTES_GROUP_ID
from ctt.commonviews import adduserdata
from ctt.forms import AdministrativosForm, GrupoUsuarioForm, NuevaInscripcionForm, SedeAdministrativoForm, ClientesForm
from ctt.funciones import MiPaginador, log, generar_usuario, resetear_clave, url_back, bad_json, ok_json, remover_tildes
from ctt.models import Persona, Profesor, Administrativo, Inscripcion, Carrera, Periodo, Cliente, EmpresaEmpleadora


def actualizar_empresa_cliente(cliente, form, request):
    if not form.cleaned_data.get('empresa'):
        cliente.empresa = None
        cliente.save(request)
        return None

    ruc = form.cleaned_data['ruc'].strip()
    nombreempresa = form.cleaned_data['nombreempresa'].strip()
    if not ruc or not nombreempresa:
        return u"Debe ingresar RUC y nombre de la empresa."

    empresa, _ = EmpresaEmpleadora.objects.get_or_create(ruc=ruc)
    empresa.nombre = remover_tildes(nombreempresa)
    empresa.direccion = remover_tildes(form.cleaned_data['direccionempresa'].strip())
    empresa.celular = remover_tildes(form.cleaned_data['telefonoempresa'].strip())
    empresa.telefonos = empresa.celular
    empresa.save(request)

    cliente.empresa = empresa
    cliente.save(request)
    return None


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
                form = ClientesForm(request.POST)
                if form.is_valid():
                    cedula = form.cleaned_data['cedula'].strip()
                    pasaporte = form.cleaned_data['pasaporte'].strip()
                    if not cedula and not pasaporte:
                        return bad_json(mensaje=u"Debe ingresar una identificación.")
                    if cedula:
                        if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if pasaporte:
                        if Persona.objects.filter(Q(cedula=pasaporte) | Q(pasaporte=pasaporte)).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if form.cleaned_data['empresa'] and (not form.cleaned_data['ruc'].strip() or not form.cleaned_data['nombreempresa'].strip()):
                        return bad_json(mensaje=u"Debe ingresar RUC y nombre de la empresa.")
                    personacliente = Persona(nombre1=remover_tildes(form.cleaned_data['nombre1']),
                                           nombre2=remover_tildes(form.cleaned_data['nombre2']),
                                           apellido1=remover_tildes(form.cleaned_data['apellido1']),
                                           apellido2=remover_tildes(form.cleaned_data['apellido2']),
                                           cedula=remover_tildes(cedula),
                                           pasaporte=pasaporte,
                                           sexo=form.cleaned_data['sexo'],
                                           direccion=remover_tildes(form.cleaned_data['direccion']),
                                           telefono=remover_tildes(form.cleaned_data['telefono']),
                                           email=form.cleaned_data['email'])
                    personacliente.save(request)
                    cliente = Cliente(persona=personacliente,
                                                    activo=True)
                    cliente.save(request)
                    generar_usuario(persona=personacliente, group_id=CLIENTES_GROUP_ID)
                    personacliente.crear_perfil(cliente=cliente)
                    error_empresa = actualizar_empresa_cliente(cliente, form, request)
                    if error_empresa:
                        return bad_json(mensaje=error_empresa)
                    log(u'Adiciono un nuevo cliente : %s' % cliente, request, "add")
                    return ok_json({"id": cliente.id})
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edit':
            try:
                cliente = Cliente.objects.get(pk=request.POST['id'])
                personacliente = cliente.persona
                form = ClientesForm(request.POST)
                if form.is_valid():
                    cedula = remover_tildes(form.cleaned_data['cedula'].strip())
                    pasaporte = form.cleaned_data['pasaporte'].strip()
                    if not cedula and not pasaporte:
                        return bad_json(mensaje=u"Debe ingresar una identificación.")
                    if cedula:
                        if Persona.objects.filter(Q(cedula=cedula) | Q(pasaporte=cedula)).exclude(id=personacliente.id).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if pasaporte:
                        if Persona.objects.filter(Q(cedula=pasaporte) | Q(pasaporte=pasaporte)).exclude(id=personacliente.id).exists():
                            return bad_json(mensaje=u"Existe una persona registrada con esta identificación.")
                    if form.cleaned_data['empresa'] and (not form.cleaned_data['ruc'].strip() or not form.cleaned_data['nombreempresa'].strip()):
                        return bad_json(mensaje=u"Debe ingresar RUC y nombre de la empresa.")
                    personacliente.nombre1 = remover_tildes(form.cleaned_data['nombre1'])
                    personacliente.nombre2 = remover_tildes(form.cleaned_data['nombre2'])
                    personacliente.apellido1 = remover_tildes(form.cleaned_data['apellido1'])
                    personacliente.apellido2 = remover_tildes(form.cleaned_data['apellido2'])
                    personacliente.cedula = cedula
                    personacliente.pasaporte = pasaporte
                    personacliente.sexo = form.cleaned_data['sexo']
                    personacliente.direccion = remover_tildes(form.cleaned_data['direccion'])
                    personacliente.telefono = remover_tildes(form.cleaned_data['telefono'])
                    personacliente.email = form.cleaned_data['email']
                    personacliente.save(request)

                    error_empresa = actualizar_empresa_cliente(cliente, form, request)
                    if error_empresa:
                        return bad_json(mensaje=error_empresa)

                    log(u'Modifico cliente: %s' % cliente, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'resetear':
            try:
                cliente = Cliente.objects.get(pk=request.POST['id'])
                if not cliente.persona.usuario:
                    return bad_json(mensaje=u"El cliente no tiene usuario.")
                resetear_clave(cliente.persona)
                cliente.persona.cambiar_clave()
                log(u'Reseteo clave de usuario cliente: %s' % cliente, request, "edit")
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
                cliente = Cliente.objects.get(pk=request.POST['id'])
                usuario = cliente.persona.usuario
                if not usuario:
                    return bad_json(mensaje=u"El cliente no tiene usuario.")
                usuario.is_active = True
                usuario.save()
                log(u'Activo usuario cliente: %s' % cliente, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'activarperfil':
            try:
                cliente = Cliente.objects.get(pk=request.POST['id'])
                cliente.activo = True
                cliente.save(request)
                log(u'Activo perfil de cliente: %s' % cliente, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desactivar':
            try:
                cliente = Cliente.objects.get(pk=request.POST['id'])
                ui = cliente.persona.usuario
                if not ui:
                    return bad_json(mensaje=u"El cliente no tiene usuario.")
                ui.is_active = False
                ui.save()
                log(u'Desactivo usuario cliente: %s' % cliente, request, "edit")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'desactivarperfil':
            try:
                cliente = Cliente.objects.get(pk=request.POST['id'])
                cliente.activo = False
                cliente.save(request)
                log(u'Desactivo perfil de cliente: %s' % cliente, request, "edit")
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
                    data['title'] = u'Adicionar Nuevo Cliente'
                    form = ClientesForm()
                    data['form'] = form
                    return render(request, "adm_cliente/add.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivar':
                try:
                    data['title'] = u'Desactivar usuario'
                    data['cliente'] = Cliente.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cliente/desactivar.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivarperfil':
                try:
                    data['title'] = u'Desactivar perfil de cliente'
                    data['cliente'] = Cliente.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cliente/desactivarperfil.html", data)
                except Exception as ex:
                    pass

            if action == 'activar':
                try:
                    data['title'] = u'Activar usuario'
                    data['cliente'] = Cliente.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cliente/activar.html", data)
                except Exception as ex:
                    pass

            if action == 'activarperfil':
                try:
                    data['title'] = u'Activar perfil de cliente'
                    data['cliente'] = Cliente.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cliente/activarperfil.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar cliente'
                    data['cliente'] = cliente = Cliente.objects.select_related('persona', 'empresa').get(pk=request.GET['id'])
                    personacliente = cliente.persona
                    empresa = cliente.empresa
                    form = ClientesForm(initial={'nombre1': personacliente.nombre1,
                                                 'nombre2': personacliente.nombre2,
                                                 'apellido1': personacliente.apellido1,
                                                 'apellido2': personacliente.apellido2,
                                                 'cedula': personacliente.cedula,
                                                 'pasaporte': personacliente.pasaporte,
                                                 'sexo': personacliente.sexo,
                                                 'direccion': personacliente.direccion,
                                                 'telefono': personacliente.telefono,
                                                 'email': personacliente.email,
                                                 'empresa': bool(empresa),
                                                 'ruc': empresa.ruc if empresa else '',
                                                 'nombreempresa': empresa.nombre if empresa else '',
                                                 'direccionempresa': empresa.direccion if empresa else '',
                                                 'telefonoempresa': empresa.celular if empresa else ''},)
                    data['form'] = form
                    return render(request, "adm_cliente/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'addgrupo':
                try:
                    data['title'] = u'Adicionar grupo'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    form = GrupoUsuarioForm()
                    form.grupos(Group.objects.all().exclude(id__in=[PROFESORES_GROUP_ID, ALUMNOS_GROUP_ID, EMPLEADORES_GRUPO_ID]).order_by('name'))
                    data['form'] = form
                    return render(request, "adm_cliente/addgrupo.html", data)
                except Exception as ex:
                    pass

            if action == 'asignarsede':
                try:
                    data['title'] = u'Asignar sede'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    data['form'] = SedeAdministrativoForm()
                    return render(request, "adm_cliente/asignarsede.html", data)
                except Exception as ex:
                    pass

            if action == 'resetear':
                try:
                    data['title'] = u'Resetear clave del usuario'
                    data['cliente'] = Cliente.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cliente/resetear.html", data)
                except Exception as ex:
                    pass

            if action == 'delgrupo':
                try:
                    data['title'] = u'Eliminar de grupo'
                    data['administrativo'] = Administrativo.objects.get(pk=request.GET['id'])
                    data['grupo'] = Group.objects.get(pk=request.GET['idg'])
                    return render(request, "adm_cliente/delgrupo.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado Clientes'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        clientes = Cliente.objects.filter(Q(persona__nombre1__icontains=search) |
                                                          Q(persona__nombre2__icontains=search) |
                                                          Q(persona__apellido1__icontains=search) |
                                                          Q(persona__apellido2__icontains=search) |
                                                          Q(persona__cedula__icontains=search) |
                                                          Q(persona__pasaporte__icontains=search) |
                                                          Q(empresa__nombre__icontains=search) |
                                                          Q(empresa__ruc__icontains=search)).distinct()
                    else:
                        clientes = Cliente.objects.filter(Q(persona__apellido1__icontains=ss[0]) &
                                                          Q(persona__apellido2__icontains=ss[1])).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    clientes = Cliente.objects.filter(id=ids).distinct()
                else:
                    clientes = Cliente.objects.all()
                clientes = clientes.select_related('persona', 'persona__usuario', 'empresa').order_by('persona__apellido1', 'persona__apellido2', 'persona__nombre1')
                paging = MiPaginador(clientes, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'clientes':
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
                request.session['paginador_url'] = 'clientes'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['clientes'] = page.object_list

                data['entrar_como_usuario']=True
                return render(request, "adm_cliente/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
