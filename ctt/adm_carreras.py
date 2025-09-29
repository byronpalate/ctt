# coding=utf-8
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import CUARTO_NIVEL_TITULACION_ID
from ctt.commonviews import adduserdata
from ctt.forms import CarreraForm, CompetenciaEspecificaForm, TituloCarreraForm, TituloForm
from ctt.funciones import MiPaginador, log, ok_json, bad_json, url_back, remover_tildes
from ctt.models import Carrera, CompetenciaEspecifica, TituloObtenido, \
    TituloObtenidoCarrera


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
                form = CarreraForm(request.POST)
                if form.is_valid():
                    if Carrera.objects.filter(nombre=form.cleaned_data['nombre'].upper(), mencion=form.cleaned_data['mencion'].upper()).exists():
                        return bad_json(error=7)
                    carrera = Carrera(nombre=remover_tildes(form.cleaned_data['nombre']),
                                      nombreingles=remover_tildes(form.cleaned_data['nombreingles']).upper(),
                                      mencion=remover_tildes(form.cleaned_data['mencion']),
                                      tipogrado=form.cleaned_data['tipogrado'],
                                      tiposubgrado=form.cleaned_data['tiposubgrado'],
                                      alias=form.cleaned_data['alias'])
                    carrera.save(request)
                    if form.cleaned_data['tipogrado'].id == CUARTO_NIVEL_TITULACION_ID:
                        carrera.posgrado = True
                    else:
                        carrera.posgrado = False
                    carrera.save()
                    log(u'Adiciono carrera: %s' % carrera, request, "add")
                    return ok_json({"id": carrera.id})
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edit':
            try:
                carrera = Carrera.objects.get(pk=request.POST['id'])
                form = CarreraForm(request.POST)
                if form.is_valid():
                    if Carrera.objects.filter(nombre=form.cleaned_data['nombre'].upper(), mencion=form.cleaned_data['mencion'].upper()).exclude(id=carrera.id).exists():
                        return bad_json(error=7)
                    carrera.nombre = remover_tildes(form.cleaned_data['nombre'])
                    carrera.nombreingles = remover_tildes(form.cleaned_data['nombreingles'])
                    carrera.mencion = remover_tildes(form.cleaned_data['mencion'])
                    carrera.tipogrado = form.cleaned_data['tipogrado']
                    carrera.tiposubgrado= form.cleaned_data['tiposubgrado']
                    carrera.alias = form.cleaned_data['alias']
                    carrera.save(request)
                    log(u'Modifico carrera: %s' % carrera, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delete':
            try:
                carrera = Carrera.objects.get(pk=request.POST['id'])
                log(u'Elimino carrera: %s' % carrera, request, "del")
                carrera.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'habilitar':
            try:
                carrera = Carrera.objects.get(pk=request.POST['id'])
                log(u'Habilito carrera: %s' % carrera, request, "del")
                carrera.activa = True
                carrera.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'deshabilitar':
            try:
                carrera = Carrera.objects.get(pk=request.POST['id'])
                log(u'Deshabilito carrera: %s' % carrera, request, "del")
                carrera.activa = False
                carrera.save(request)
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'addcompetencias':
            try:
                form = CompetenciaEspecificaForm(request.POST)
                carrera = Carrera.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if CompetenciaEspecifica.objects.filter(carrera=carrera, nombre=form.cleaned_data['nombre'].upper()).exists():
                        return bad_json(error=7)
                    competencia = CompetenciaEspecifica(carrera=carrera,
                                                        nombre=form.cleaned_data['nombre'])
                    competencia.save(request)
                    log(u'Adiciono competencia: %s' % competencia, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addtitulos':
            try:
                form = TituloForm(request.POST)
                if form.is_valid():
                    if TituloObtenido.objects.filter(nombre=form.cleaned_data['nombre'].upper()).exists():
                        return bad_json(error=7)
                    titulo = TituloObtenido(nombre=form.cleaned_data['nombre'])
                    titulo.save(request)
                    log(u'Adiciono titulo: %s' % titulo, request, "add")
                    return ok_json(data={'id': titulo.id})
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addtituloscarrera':
            try:
                form = TituloCarreraForm(request.POST)
                carrera = Carrera.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if TituloObtenidoCarrera.objects.filter(carrera=carrera, tituloobtenido=form.cleaned_data['titulo']).exists():
                        return bad_json(error=7)
                    titulo = TituloObtenidoCarrera(carrera=carrera,
                                                   tituloobtenido=form.cleaned_data['titulo'])
                    titulo.save(request)
                    log(u'Adiciono titulo a carrera: %s' % titulo, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edittitulo':
            try:
                form = TituloForm(request.POST)
                titulo = TituloObtenido.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if TituloObtenido.objects.filter(nombre=form.cleaned_data['nombre'].upper()).exclude(id=titulo.id).exists():
                        return bad_json(error=7)
                    titulo.nombre = form.cleaned_data['nombre']
                    titulo.save(request)
                    log(u'Modifico titulo: %s' % titulo, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editcompetencia':
            try:
                form = CompetenciaEspecificaForm(request.POST)
                competencia = CompetenciaEspecifica.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if CompetenciaEspecifica.objects.filter(carrera=competencia.carrera, nombre=form.cleaned_data['nombre'].upper()).exclude(id=competencia.id).exists():
                        return bad_json(error=7)
                    competencia.nombre = form.cleaned_data['nombre']
                    competencia.save(request)
                    log(u'Modifico competencia: %s' % competencia, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delcompetencia':
            try:
                competencia = CompetenciaEspecifica.objects.get(pk=request.POST['id'])
                if not competencia.puede_eliminarse():
                    return bad_json(mensaje=u'No se puede eliminar la comptencia, se encuenta en uso.')
                log(u'Elimino competencia: %s' % competencia, request, "del")
                competencia.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'deltitulo':
            try:
                titulo = TituloObtenido.objects.get(pk=request.POST['id'])
                log(u'Elimino titulo: %s' % titulo, request, "del")
                if not titulo.puede_eliminarse():
                    return bad_json(mensaje=u'No se puede eliminar el titulo, se encuenta en uso.')
                titulo.delete()
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=2, ex=ex)

        if action == 'deltitulocarrera':
            try:
                titulo = TituloObtenidoCarrera.objects.get(pk=request.POST['id'])
                log(u'Elimino titulo de carrera: %s' % titulo, request, "del")
                if not titulo.puede_eliminarse():
                    return bad_json(mensaje=u'No se puede eliminar el titulo, se encuenta en uso.')
                titulo.delete()
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
                    data['title'] = u'Nueva carrera'
                    form = CarreraForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "adm_carreras/add.html", data)
                except Exception as ex:
                    pass

            if action == 'addcompetencias':
                try:
                    data['title'] = u'Adicionar competencia específica'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['form'] = CompetenciaEspecificaForm()
                    return render(request, "adm_carreras/addcompetencias.html", data)
                except Exception as ex:
                    pass

            if action == 'titulos':
                try:
                    data['title'] = u'Títulos obtenidos'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['titulos'] = carrera.tituloobtenidocarrera_set.all()
                    return render(request, "adm_carreras/titulos.html", data)
                except Exception as ex:
                    pass

            if action == 'addtitulos':
                try:
                    data['title'] = u'Adicionar título'
                    data['form'] = TituloForm()
                    return render(request, "adm_carreras/addtitulos.html", data)
                except Exception as ex:
                    pass

            if action == 'addtituloscarrera':
                try:
                    data['title'] = u'Adicionar título'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['form'] = TituloCarreraForm()
                    return render(request, "adm_carreras/addtituloscarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'edittitulo':
                try:
                    data['title'] = u'Editar titulo'
                    data['titulo'] = titulo = TituloObtenido.objects.get(pk=request.GET['id'])
                    data['form'] = TituloForm(initial={'nombre': titulo.nombre},
                                              )
                    return render(request, "adm_carreras/edittitulo.html", data)
                except Exception as ex:
                    pass

            if action == 'deltitulo':
                try:
                    data['title'] = u'Eliminar titulo'
                    data['titulo'] = titulo = TituloObtenido.objects.get(pk=request.GET['id'])
                    return render(request, "adm_carreras/deltitulo.html", data)
                except Exception as ex:
                    pass

            if action == 'deltitulocarrera':
                try:
                    data['title'] = u'Eliminar titulo de carrera'
                    data['titulo'] = titulo = TituloObtenidoCarrera.objects.get(pk=request.GET['id'])
                    return render(request, "adm_carreras/deltitulocarrera.html", data)
                except Exception as ex:
                    pass

            if action == 'competencias':
                try:
                    data['title'] = u'Competencias específicas'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    data['competencias'] = CompetenciaEspecifica.objects.filter(carrera=carrera)
                    return render(request, "adm_carreras/competencias.html", data)
                except Exception as ex:
                    pass

            if action == 'editcompetencia':
                try:
                    data['title'] = u'Editar competencia especifica'
                    data['competencia'] = competencia = CompetenciaEspecifica.objects.get(pk=request.GET['id'])
                    data['form'] = CompetenciaEspecificaForm(initial={'nombre': competencia.nombre})
                    return render(request, "adm_carreras/editcompetencia.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar carrera'
                    data['carrera'] = carrera = Carrera.objects.get(pk=request.GET['id'])
                    form = CarreraForm(initial={'nombre': carrera.nombre,
                                                'nombreingles':carrera.nombreingles,
                                                'mencion': carrera.mencion,
                                                'tipogrado': carrera.tipogrado,
                                                'tiposubgrado': carrera.tiposubgrado,
                                                'alias': carrera.alias})
                    form.editar(carrera)
                    data['form'] = form
                    data['permite_modificar'] = carrera.permite_modificar()
                    return render(request, "adm_carreras/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar carrera'
                    data['carrera'] = Carrera.objects.get(pk=request.GET['id'])
                    return render(request, "adm_carreras/delete.html", data)
                except Exception as ex:
                    pass

            if action == 'delcompetencia':
                try:
                    data['title'] = u'Eliminar Competencia'
                    data['competencia'] = competencia = CompetenciaEspecifica.objects.get(pk=request.GET['id'])
                    return render(request, "adm_carreras/delcompetencia.html", data)
                except Exception as ex:
                    pass

            if action == 'habilitar':
                try:
                    data['title'] = u'Habilitar'
                    data['carrera'] = Carrera.objects.get(pk=request.GET['id'])
                    return render(request, "adm_carreras/habilitar.html", data)
                except Exception as ex:
                    pass

            if action == 'deshabilitar':
                try:
                    data['title'] = u'Deshabilitar'
                    data['carrera'] = Carrera.objects.get(pk=request.GET['id'])
                    return render(request, "adm_carreras/deshabilitar.html", data)
                except Exception as ex:
                    pass

            if action == 'titulosobtenidos':
                try:
                    data['title'] = u'Títulos obtenidos'
                    search = None
                    ids = None
                    titulos = TituloObtenido.objects.all()
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        titulos = titulos.filter(id=ids)
                    elif 's' in request.GET:
                        search = request.GET['s'].strip()
                        titulos = titulos.filter(nombre__icontains=search).distinct()
                    paging = MiPaginador(titulos, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session and 'paginador_url' in request.session:
                            if request.session['paginador_url'] == 'adm_carreras_titulos':
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
                    request.session['paginador_url'] = 'adm_carreras_titulos'
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['titulos'] = page.object_list
                    return render(request, "adm_carreras/titulosobtenidos.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Carreras'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    carreras = Carrera.objects.filter(Q(nombre__icontains=search)).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    carreras = Carrera.objects.filter(id=ids)
                else:
                    carreras = Carrera.objects.all()
                paging = MiPaginador(carreras, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_carreras':
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
                request.session['paginador_url'] = 'adm_carreras'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['carreras'] = page.object_list
                return render(request, "adm_carreras/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
