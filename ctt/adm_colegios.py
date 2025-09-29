# coding=utf-8

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import ColegioForm, EspecialidadForm
from ctt.funciones import log, url_back, bad_json, ok_json, MiPaginador
from ctt.models import Colegio, Especialidad


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                try:
                    form = ColegioForm(request.POST)
                    if form.is_valid():
                        colegio = Colegio(nombre=form.cleaned_data['nombre'],
                                          tipocolegio=form.cleaned_data['tipocolegio'],
                                          codigo=form.cleaned_data['codigo'],
                                          provincia=form.cleaned_data['provincia'],
                                          canton=form.cleaned_data['canton'],
                                          estado=form.cleaned_data['estado'])
                        colegio.save(request)
                        log(u'Adiciono colegio: %s' % colegio, request, "add")
                        return ok_json(data={'id': colegio.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'edit':
                try:
                    form = ColegioForm(request.POST)
                    if form.is_valid():
                        colegio = Colegio.objects.get(pk=request.POST['id'])
                        colegio.nombre = form.cleaned_data['nombre']
                        colegio.tipocolegio = form.cleaned_data['tipocolegio']
                        colegio.codigo = form.cleaned_data['codigo']
                        colegio.provincia = form.cleaned_data['provincia']
                        colegio.canton = form.cleaned_data['canton']
                        colegio.estado = form.cleaned_data['estado']
                        colegio.save(request)
                        log(u'Modifico colegio: %s' % colegio, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'del':
                try:
                    colegio = Colegio.objects.get(pk=request.POST['id'])
                    if colegio.estudiopersona_set.exists():
                        return bad_json(mensaje=u'Este colegio se encuentra en uso')
                    log(u'Elimino colegio: %s' % colegio, request, "del")
                    colegio.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'addespecialidades':
                try:
                    form = EspecialidadForm(request.POST)
                    if form.is_valid():
                        especialidad = Especialidad(nombre=form.cleaned_data['nombre'])
                        especialidad.save(request)
                        log(u'Adiciono titulo: %s' % especialidad, request, "add")
                        return ok_json(data={'id': especialidad.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editespecialidades':
                try:
                    form = EspecialidadForm(request.POST)
                    if form.is_valid():
                        especialidad = Especialidad.objects.get(pk=request.POST['id'])
                        especialidad.nombre = form.cleaned_data['nombre']
                        especialidad.save(request)
                        log(u'Modifico titulo: %s' % especialidad, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delespecialidades':
                try:
                    especialidad = Especialidad.objects.get(pk=request.POST['id'])
                    if especialidad.estudiopersona_set.exists():
                        return bad_json(mensaje=u'Este titulo se encuentra en uso')
                    log(u'Elimino titulo: %s' % especialidad, request, "del")
                    especialidad.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'activa_desactiva_col':
                try:
                    colegio = Colegio.objects.get(pk=request.POST['id'])
                    if request.POST['estado'] == 'true':
                        colegio.estado=True
                        colegio.save()
                    else:
                        colegio.estado=False
                        colegio.save()
                    log(u"Se edito el colegio %s a estado  %s" % (colegio, colegio.estado), request, "edit")
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
                    data['title'] = u'Adicionar Colegio'
                    form = ColegioForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "adm_colegios/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar Colegio'
                    data['colegio'] = colegio = Colegio.objects.get(pk=request.GET['id'])
                    form = ColegioForm(initial={'nombre': colegio.nombre,
                                                'tipocolegio': colegio.tipocolegio,
                                                'codigo': colegio.codigo,
                                                'provincia': colegio.provincia,
                                                'canton': colegio.canton,
                                                'estado': colegio.estado})
                    form.editar(colegio)
                    data['form'] = form
                    return render(request, "adm_colegios/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'del':
                try:
                    data['title'] = u'Eliminar colegio'
                    data['colegio'] = Colegio.objects.get(pk=request.GET['id'])
                    return render(request, "adm_colegios/del.html", data)
                except Exception as ex:
                    pass

            if action == 'especialidades':
                try:
                    data['title'] = u'Títulos de bachillerato'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        if len(search.split(' ')) == 2:
                            ss = search.split(' ')
                            especialidades = Especialidad.objects.filter(Q(nombre__contains=ss[0]) & Q(nombre__contains=ss[1])).distinct()
                        else:
                            especialidades = Especialidad.objects.filter(nombre__contains=search).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        especialidades = Especialidad.objects.filter(id=ids)
                    else:
                        especialidades = Especialidad.objects.all()
                    paging = MiPaginador(especialidades, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session and 'paginador_url' in request.session:
                            if request.session['paginador_url'] == 'adm_colegios_titulos':
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
                    request.session['paginador_url'] = 'adm_colegios_titulos'
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['especialidades'] = page.object_list
                    return render(request, "adm_colegios/especialidades.html", data)
                except Exception as ex:
                    pass

            if action == 'addespecialidades':
                try:
                    data['title'] = u'Adicionar título'
                    data['form'] = EspecialidadForm()
                    return render(request, "adm_colegios/addespecialidades.html", data)
                except Exception as ex:
                    pass

            if action == 'editespecialidades':
                try:
                    data['title'] = u'Editar titulo'
                    data['especialidad'] = especialidad = Especialidad.objects.get(pk=request.GET['id'])
                    data['form'] = EspecialidadForm(initial={'nombre': especialidad.nombre})
                    return render(request, "adm_colegios/editespecialidades.html", data)
                except Exception as ex:
                    pass

            if action == 'delespecialidades':
                try:
                    data['title'] = u'Eliminar titulo'
                    data['especialidad'] = Especialidad.objects.get(pk=request.GET['id'])
                    return render(request, "adm_colegios/delespecialidades.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Colegios e instituciones educativas'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    if len(search.split(' ')) == 2:
                        ss = search.split(' ')
                        colegios = Colegio.objects.filter(Q(nombre__contains=ss[0]) & Q(nombre__contains=ss[1])).distinct()
                    else:
                        colegios = Colegio.objects.filter(nombre__contains=search).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    colegios = Colegio.objects.filter(id=ids)
                else:
                    colegios = Colegio.objects.all()
                paging = MiPaginador(colegios, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_colegios':
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
                request.session['paginador_url'] = 'adm_colegios'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['colegios'] = page.object_list
                return render(request, "adm_colegios/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
