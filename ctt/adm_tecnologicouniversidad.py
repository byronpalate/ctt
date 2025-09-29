# coding=utf-8

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import last_access, secure_module
from ctt.commonviews import adduserdata
from ctt.forms import TecnologicoUniversidadForm
from ctt.funciones import log, url_back, bad_json, ok_json, MiPaginador
from ctt.models import TecnologicoUniversidad


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
                    form = TecnologicoUniversidadForm(request.POST)
                    if form.is_valid():
                        tecnologicouniversidad = TecnologicoUniversidad(nombre=form.cleaned_data['nombre'],
                                                                        tipotecnologicouniversidad=form.cleaned_data['tipotecnologicouniversidad'],
                                                                        universidad=form.cleaned_data['universidad'],
                                                                        pais=form.cleaned_data['pais'],
                                                                        codigosniese=form.cleaned_data['codigosniese'])
                        tecnologicouniversidad.save(request)
                        log(u'Adiciono institución: %s' % tecnologicouniversidad, request, "add")
                        return ok_json(data={'id': tecnologicouniversidad.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'edit':
                try:
                    form = TecnologicoUniversidadForm(request.POST)
                    if form.is_valid():
                        tecnologicouniversidad = TecnologicoUniversidad.objects.get(pk=request.POST['id'])
                        tecnologicouniversidad.nombre = form.cleaned_data['nombre']
                        tecnologicouniversidad.tipotecnologicouniversidad = form.cleaned_data['tipotecnologicouniversidad']
                        tecnologicouniversidad.universidad = form.cleaned_data['universidad']
                        tecnologicouniversidad.pais = form.cleaned_data['pais']
                        tecnologicouniversidad.codigosniese = form.cleaned_data['codigosniese']
                        tecnologicouniversidad.save(request)
                        log(u'Modifico institución: %s' % tecnologicouniversidad, request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'del':
                try:
                    tecnologicouniversidad = TecnologicoUniversidad.objects.get(pk=request.POST['id'])
                    if tecnologicouniversidad.estudiopersona_set.exists():
                        return bad_json(mensaje=u'Este institución se encuentra en uso')
                    log(u'Elimino institución: %s' % tecnologicouniversidad, request, "del")
                    tecnologicouniversidad.delete()
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
                    data['title'] = u'Adicionar institución'
                    data['form'] = TecnologicoUniversidadForm()
                    return render(request, "adm_tecnologicouniversidad/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar institución'
                    data['tecnologicouniversidad'] = tecnologicouniversidad = TecnologicoUniversidad.objects.get(pk=request.GET['id'])
                    data['form'] = TecnologicoUniversidadForm(initial={'nombre': tecnologicouniversidad.nombre,
                                                                       'tipotecnologicouniversidad': tecnologicouniversidad.tipotecnologicouniversidad,
                                                                       'univerdidad': tecnologicouniversidad.universidad,
                                                                       'pais': tecnologicouniversidad.pais,
                                                                       'codigosniese': tecnologicouniversidad.codigosniese})
                    return render(request, "adm_tecnologicouniversidad/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'del':
                try:
                    data['title'] = u'Eliminar institución'
                    data['tecnologicouniversidad'] = TecnologicoUniversidad.objects.get(pk=request.GET['id'])
                    return render(request, "adm_tecnologicouniversidad/del.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Instituciones de educación superior'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    if len(search.split(' ')) == 2:
                        ss = search.split(' ')
                        tecnologicouniversidad = TecnologicoUniversidad.objects.filter(Q(nombre__contains=ss[0]) & Q(nombre__contains=ss[1])).distinct()
                    else:
                        tecnologicouniversidad = TecnologicoUniversidad.objects.filter(nombre__contains=search).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    tecnologicouniversidad = TecnologicoUniversidad.objects.filter(id=ids)
                else:
                    tecnologicouniversidad = TecnologicoUniversidad.objects.all()
                paging = MiPaginador(tecnologicouniversidad, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_tecnologicouniversidad':
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
                request.session['paginador_url'] = 'intitucion_educativa'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['tecnologicouniversidades'] = page.object_list
                return render(request, "adm_tecnologicouniversidad/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
