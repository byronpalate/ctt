# coding=utf-8
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import CoordinacionForm, SecretariaCoordinacionForm, \
    ResponsableCarreraForm, CarreraCoordinacionForm, ResponsableCoordinacionForm
from ctt.funciones import log, bad_json, ok_json, url_back, MiPaginador
from ctt.models import Coordinacion, ResponsableCoordinacion, CoordinadorCarrera, Carrera, PerfilAccesoUsuario, \
    SecretariaCoordinacion, Modalidad, DirectorCoordinacion


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                try:
                    form = CoordinacionForm(request.POST)
                    if form.is_valid():
                        if Coordinacion.objects.filter(nombre=form.cleaned_data['nombre'].upper(), sede=form.cleaned_data['sede']).exists():
                            return bad_json(error=7)
                        coordinacion = Coordinacion(nombre=form.cleaned_data['nombre'],
                                                    nombreingles=form.cleaned_data['nombreingles'].upper(),
                                                    sede=form.cleaned_data['sede'],
                                                    alias=form.cleaned_data['alias'],
                                                    estado=form.cleaned_data['estado'])
                        coordinacion.save(request)
                        log(u'Adicionada coordinacion: %s' % coordinacion, request, "add")
                        return ok_json(data={'id': coordinacion.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editar':
                try:
                    form = CoordinacionForm(request.POST)
                    if form.is_valid():
                        coordinacion = Coordinacion.objects.get(pk=int(request.POST['id']))
                        if Coordinacion.objects.filter(nombre=form.cleaned_data['nombre'].upper(), sede=form.cleaned_data['sede']).exclude(id=coordinacion.id).exists():
                            return bad_json(error=7)
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

            if action == 'editresponsablecoordinacion':
                try:
                    form = ResponsableCoordinacionForm(request.POST)
                    if form.is_valid():
                        coordinacion = Coordinacion.objects.get(pk=int(request.POST['id']))
                        responsable = coordinacion.responsable()
                        if responsable:
                            responsable.delete()
                        if form.cleaned_data['responsable']:
                            responsable = ResponsableCoordinacion(coordinacion=coordinacion,
                                                                  persona_id=int(form.cleaned_data['responsable']))
                            responsable.save(request)
                        log(u'Modifico responsable coordinacion: %s' % coordinacion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editresponsabledirector':
                try:
                    form = ResponsableCoordinacionForm(request.POST)
                    if form.is_valid():
                        coordinacion = Coordinacion.objects.get(pk=int(request.POST['id']))
                        responsable = coordinacion.director()
                        if responsable:
                            responsable.delete()
                        if form.cleaned_data['responsable']:
                            responsable = DirectorCoordinacion(coordinacion=coordinacion,
                                                                  persona_id=int(form.cleaned_data['responsable']),
                                                                  firmadignidad=form.cleaned_data['firmadignidad'])
                            responsable.save(request)
                        log(u'Modifico director coordinacion: %s' % coordinacion, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delsecretaria':
                try:
                    secretaria = SecretariaCoordinacion.objects.get(pk=request.POST['id'])
                    log(u'Elimino secretaria de coordinacion: %s' % secretaria, request, "del")
                    secretaria.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'deltecnico':
                try:
                    tecnico = TecnicoCoordinacion.objects.get(pk=request.POST['id'])
                    log(u'Elimino tecnico de coordinacion: %s' % tecnico, request, "del")
                    tecnico.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delcarrera':
                try:
                    carrera = Carrera.objects.get(pk=request.POST['id'])
                    coordinacion = Coordinacion.objects.get(pk=request.POST['idc'])
                    coordinacion.carrera.remove(carrera)
                    log(u'Elimino carrera %s de coordinacion: %s' % (carrera, coordinacion), request, "del")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'editresponsablecarrera':
                try:
                    form = ResponsableCarreraForm(request.POST)
                    if form.is_valid():
                        carrera = Carrera.objects.get(pk=request.POST['id'])
                        coordinacion = Coordinacion.objects.get(pk=request.POST['idc'])
                        modalidad = Modalidad.objects.get(pk=request.POST['idm'])
                        CoordinadorCarrera.objects.filter(coordinacion=coordinacion, carrera=carrera, modalidad=modalidad).delete()
                        if form.cleaned_data['responsable']:
                            responsable = CoordinadorCarrera(persona_id=form.cleaned_data['responsable'],
                                                             firmadignidad=form.cleaned_data['firmadignidad'],
                                                             coordinacion=coordinacion,
                                                             modalidad=modalidad,
                                                             carrera=carrera)
                            responsable.save(request)
                        log(u'Modifico responsable de carrera: %s' % carrera, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addaccesopersona':
                try:
                    form = ResponsableCarreraForm(request.POST)
                    if form.is_valid():
                        carrera = Carrera.objects.get(pk=request.POST['id'])
                        coordinacion = Coordinacion.objects.get(pk=request.POST['idc'])
                        modalidad = Modalidad.objects.get(pk=request.POST['idm'])
                        if PerfilAccesoUsuario.objects.filter(coordinacion=coordinacion, carrera=carrera, modalidad=modalidad, persona_id=form.cleaned_data['responsable']).exists():
                            return bad_json(mensaje=u'Ya existe un registro para esta persona.')
                        responsable = PerfilAccesoUsuario(coordinacion=coordinacion,
                                                          carrera=carrera,
                                                          modalidad=modalidad,
                                                          persona_id=form.cleaned_data['responsable'])
                        responsable.save(request)
                        log(u'Adiciono permiso a %s acceso a la carrera: %s de la modalidad: %s' % (responsable.persona, responsable.carrera, responsable.modalidad), request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addcarrera':
                try:
                    form = CarreraCoordinacionForm(request.POST)
                    if form.is_valid():
                        coordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                        if Carrera.objects.filter(id=form.cleaned_data['carrera'].id, coordinacion__sede=coordinacion.sede).exists():
                            return bad_json(mensaje=u'Esta carrera ya se encuetra registrada en otra coodinación de esta sede')
                        decano=CoordinadorCarrera(carrera=form.cleaned_data['carrera'],
                                                  modalidad=form.cleaned_data['modalidad'],
                                                  persona_id=form.cleaned_data['responsable'],
                                                  coordinacion=coordinacion)
                        decano.save()
                        coordinacion.carrera.add(form.cleaned_data['carrera'])
                        log(u'Adiciono carrera %s a coordinacion: %s' % (form.cleaned_data['carrera'], coordinacion) , request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delaccesopersona':
                try:
                    coordinador = PerfilAccesoUsuario.objects.get(pk=request.POST['id'])
                    log(u'Elimino responsable de carrera: %s' % coordinador, request, "del")
                    coordinador.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addsecretaria':
                try:
                    coordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                    form = SecretariaCoordinacionForm(request.POST)
                    if form.is_valid():
                        if SecretariaCoordinacion.objects.filter(coordinacion=coordinacion, carrera=form.cleaned_data['carrera'], modalidad=form.cleaned_data['modalidad'], persona_id=form.cleaned_data['responsable']).exists():
                            return bad_json(mensaje=u'Ya existe un regisro de esta persona.')
                        secretaria = SecretariaCoordinacion(coordinacion=coordinacion,
                                                            carrera=form.cleaned_data['carrera'],
                                                            modalidad=form.cleaned_data['modalidad'],
                                                            persona_id=form.cleaned_data['responsable'])
                        secretaria.save(request)
                        log(u'Adiciono secretaria de coordinacion: %s' % secretaria, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addtecnico':
                try:
                    coordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                    form = SecretariaCoordinacionForm(request.POST)
                    if form.is_valid():
                        if TecnicoCoordinacion.objects.filter(coordinacion=coordinacion, carrera=form.cleaned_data['carrera'], modalidad=form.cleaned_data['modalidad'], persona_id=form.cleaned_data['responsable']).exists():
                            return bad_json(mensaje=u'Ya existe un regisro de esta persona.')
                        secretaria = TecnicoCoordinacion(coordinacion=coordinacion,
                                                         carrera=form.cleaned_data['carrera'],
                                                         modalidad=form.cleaned_data['modalidad'],
                                                         persona_id=form.cleaned_data['responsable'])
                        secretaria.save(request)
                        log(u'Adiciono secretaria de coordinacion: %s' % secretaria, request, "add")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'verificarsecretaria':
                try:
                    secretaria = SecretariaCoordinacion.objects.get(pk=request.POST['id'])
                    if request.POST['valor'] == 'true':
                        if secretaria.coordinacion.secretariacoordinacion_set.filter(principal=True, carrera=secretaria.carrera, modalidad=secretaria.modalidad).exists():
                            return bad_json(mensaje=u'Ya existe una secretaria principal asignada.')
                        secretaria.principal = True
                    else:
                        secretaria.principal = False
                    secretaria.save(request)
                    log(u"Agrego secretaria principal: %s" % secretaria, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delcoordinacion':
                try:
                    coordinacion = Coordinacion.objects.get(pk=request.POST['id'])
                    coordinacion.delete()
                    log(u'Elimino coordinación: %s' % coordinacion, request, "del")
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
                    data['title'] = u'Adicionar de coordinación'
                    data['form'] = CoordinacionForm()
                    return render(request, "adm_coordinaciones/add.html", data)
                except Exception as ex:
                    pass

            if action == 'editar':
                try:
                    data['title'] = u'Editar de coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    responsable = coordinacion.responsable()
                    form = CoordinacionForm(initial={'nombre': coordinacion.nombre,
                                                     'nombreingles': coordinacion.nombreingles,
                                                     'sede': coordinacion.sede,
                                                     'alias': coordinacion.alias,
                                                     'estado': coordinacion.estado})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_coordinaciones/editar.html", data)
                except Exception as ex:
                    pass
                    pass

            if action == 'editresponsablecarrera':
                try:
                    data['title'] = u'Editar responsable de carrera'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['idc'])
                    data['modalidad'] = modalidad= Modalidad.objects.get(pk=request.GET['idm'])
                    form = ResponsableCarreraForm()
                    form.editar(coordinacion, carrera, modalidad)
                    data['form'] = form
                    return render(request, "adm_coordinaciones/editresponsablecarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'editresponsablecoordinacion':
                try:
                    data['title'] = u'Editar responsable de coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    form = ResponsableCoordinacionForm()
                    form.editar(coordinacion)
                    data['form'] = form
                    return render(request, "adm_coordinaciones/editresponsablecoordinacion.html", data)
                except Exception as ex:
                    pass

            if action == 'editresponsabledirector':
                try:
                    data['title'] = u'Editar responsable director'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    form = ResponsableCoordinacionForm()
                    form.editar(coordinacion)
                    data['form'] = form
                    return render(request, "adm_coordinaciones/editresponsabledirector.html", data)
                except Exception as ex:
                    pass

            if action == 'accesocarreras':
                try:
                    data['title'] = u'Permisos de acceso a carreras'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['idc'])
                    data['modalidad'] = modalidad= Modalidad.objects.get(pk=request.GET['idm'])
                    data['responsables'] = PerfilAccesoUsuario.objects.filter(coordinacion=coordinacion, carrera=carrera, modalidad=modalidad)
                    return render(request, "adm_coordinaciones/accesocarreras.html", data)
                except Exception as ex:
                    pass

            if action == 'carreras':
                try:
                    data['title'] = u'Carreras de la coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    data['carreras'] = coordinacion.carrera.all()
                    return render(request, "adm_coordinaciones/carreras.html", data)
                except Exception as ex:
                    pass

            if action == 'personalsecretaria':
                try:
                    data['title'] = u'Personal secretaria docente de la coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    data['secretarias'] = coordinacion.mis_secretarias()
                    return render(request, "adm_coordinaciones/personalsecretaria.html", data)
                except Exception as ex:
                    pass

            if action == 'directorcoordinacion':
                try:
                    data['title'] = u'Director de coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    data['secretarias'] = coordinacion.mis_secretarias()
                    return render(request, "adm_coordinaciones/personalsecretaria.html", data)
                except Exception as ex:
                    pass

            if action == 'personaltecnico':
                try:
                    data['title'] = u'Personal secretaria docente de la coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    data['secretarias'] = coordinacion.mis_tecnicos()
                    return render(request, "adm_coordinaciones/personaltecnico.html", data)
                except Exception as ex:
                    pass

            if action == 'addaccesopersona':
                try:
                    data['title'] = u'Adicionar personal de carrera'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['idc'])
                    data['modalidad'] = modalidad= Modalidad.objects.get(pk=request.GET['idm'])
                    data['form'] = ResponsableCarreraForm()
                    return render(request, "adm_coordinaciones/addaccesopersona.html", data)
                except Exception as ex:
                    pass

            if action == 'addcarrera':
                try:
                    data['title'] = u'Adicionar carrera'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    form = CarreraCoordinacionForm()
                    form.adicionar(coordinacion)
                    data['form'] = form
                    return render(request, "adm_coordinaciones/addcarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'delaccesopersona':
                try:
                    data['title'] = u'Eliminar personal'
                    data['responsable'] = PerfilAccesoUsuario.objects.get(pk=request.GET['id'])
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['idc'])
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['idco'])
                    data['modalidad'] = modalidad = Modalidad.objects.get(pk=request.GET['idm'])
                    return render(request, "adm_coordinaciones/delaccesopersona.html", data)
                except Exception as ex:
                    pass

            if action == 'delcarrera':
                try:
                    data['title'] = u'Eliminar carrera'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['idc'])
                    return render(request, "adm_coordinaciones/delcarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'delsecretaria':
                try:
                    data['title'] = u'Eliminar personal de secretaria'
                    data['secretaria'] = SecretariaCoordinacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_coordinaciones/delsecretaria.html", data)
                except Exception as ex:
                    pass

            if action == 'deltecnico':
                try:
                    data['title'] = u'Eliminar personal de secretaria'
                    data['tecnico'] = TecnicoCoordinacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_coordinaciones/deltecnico.html", data)
                except Exception as ex:
                    pass

            if action == 'addsecretaria':
                try:
                    data['title'] = u'Adicionar secretaria de coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    form = SecretariaCoordinacionForm()
                    form.adicionar(coordinacion)
                    data['form'] = form
                    return render(request, "adm_coordinaciones/addsecretaria.html", data)
                except Exception as ex:
                    pass

            if action == 'addtecnico':
                try:
                    data['title'] = u'Adicionar tecnico de coordinación'
                    data['coordinacion'] = coordinacion = Coordinacion.objects.get(pk=request.GET['id'])
                    form = SecretariaCoordinacionForm()
                    form.adicionar(coordinacion)
                    data['form'] = form
                    return render(request, "adm_coordinaciones/addtecnico.html", data)
                except Exception as ex:
                    pass

            if action == 'delcoordinacion':
                try:
                    data['title'] = u'Eliminar coordinacion'
                    data['coordinacion'] = Coordinacion.objects.get(pk=request.GET['id'])
                    return render(request, "adm_coordinaciones/delcoordinacion.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Coordinaciones'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    coordinaciones = Coordinacion.objects.filter(nombre__icontains=search).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    coordinaciones = Coordinacion.objects.filter(id=ids)
                else:
                    coordinaciones = Coordinacion.objects.all()
                paging = MiPaginador(coordinaciones, 30)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_coordinaciones':
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
                request.session['paginador_url'] = 'adm_coordinaciones'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['coordinaciones'] = page.object_list
                return render(request, "adm_coordinaciones/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
