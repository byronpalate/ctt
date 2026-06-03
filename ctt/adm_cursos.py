# coding=utf-8

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.funciones import MiPaginador
from ctt.commonviews import adduserdata
from ctt.forms import CursoForm, MallaCursoForm, AsignaturaMallaCursoForm
from ctt.funciones import log, bad_json, url_back, ok_json
from ctt.models import Curso, MallaCurso, AsignaturaCurso, null_to_numeric


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
                    form = CursoForm(request.POST)
                    if form.is_valid():
                        curso = Curso(nombre=form.cleaned_data['nombre'],
                                      certificadoobtenido=form.cleaned_data['certificadoobtenido'],
                                      alias=form.cleaned_data['alias'])
                        curso.save(request)
                        log(u'Adiciono curso: %s' % curso, request, "add")
                        return ok_json({"id": curso.id})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'edit':
                try:
                    curso = Curso.objects.get(pk=request.POST['id'])
                    form = CursoForm(request.POST)
                    if form.is_valid():
                        curso.nombre = form.cleaned_data['nombre']
                        curso.certificadoobtenido = form.cleaned_data['certificadoobtenido']
                        curso.alias = form.cleaned_data['alias']
                        curso.save(request)
                        log(u'Edito curso: %s - %s' % (curso.nombre, curso.certificadoobtenido), request, "edit")
                        return ok_json()
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addmalla':
                try:
                    form = MallaCursoForm(request.POST)
                    if form.is_valid():
                        curso = Curso.objects.get(pk=request.POST['id'])
                        mallacurso = MallaCurso(curso=curso,
                                                inicio=form.cleaned_data['inicio'])
                        mallacurso.save(request)
                        log(u'Adicionada malla curso: %s' % mallacurso, request, "add")
                        return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'addasignaturasmalla':
                try:
                    form = AsignaturaMallaCursoForm(request.POST)
                    if form.is_valid():
                        mallacurso = MallaCurso.objects.get(pk=request.POST['id'])
                        if mallacurso.asignaturacurso_set.filter(asignatura=form.cleaned_data['asignatura']).exists():
                            return bad_json(mensaje=u'Ya la asignatura se encuentra registrada')
                        asignaturamalla = AsignaturaCurso(mallacurso=mallacurso,
                                                          asignatura=form.cleaned_data['asignatura'],
                                                          nivelmalla=form.cleaned_data['nivelmalla'],
                                                          validacreditos=form.cleaned_data['validacreditos'],
                                                          validapromedio=form.cleaned_data['validapromedio'],
                                                          horas=form.cleaned_data['horas'],
                                                          creditos=form.cleaned_data['creditos'],
                                                          requiereaprobar=form.cleaned_data['requiereaprobar'],
                                                          calificar=form.cleaned_data['calificar'],
                                                          notamaxima=null_to_numeric(form.cleaned_data['notamaxima'], 0),
                                                          notaaprobar=null_to_numeric(form.cleaned_data['notaaprobar'], 0),
                                                          asistenciaaprobar=form.cleaned_data['asistenciaaprobar'])
                        asignaturamalla.save(request)
                        log(u'Adiciono asignatura de malla de curso: %s' % asignaturamalla, request, "add")
                        return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'editasignaturamalla':
                try:
                    form = AsignaturaMallaCursoForm(request.POST)
                    asignaturamalla = AsignaturaCurso.objects.get(pk=request.POST['id'])
                    if form.is_valid():
                        asignaturamalla.asignatura = form.cleaned_data['asignatura']
                        asignaturamalla.nivelmalla = form.cleaned_data['nivelmalla']
                        asignaturamalla.horas = form.cleaned_data['horas']
                        asignaturamalla.creditos = form.cleaned_data['creditos']
                        asignaturamalla.validacreditos = form.cleaned_data['validacreditos']
                        asignaturamalla.validapromedio = form.cleaned_data['validapromedio']
                        asignaturamalla.requiereaprobar = form.cleaned_data['requiereaprobar']
                        asignaturamalla.calificar = form.cleaned_data['calificar']
                        asignaturamalla.notamaxima = null_to_numeric(form.cleaned_data['notamaxima'], 0)
                        asignaturamalla.notaaprobar = null_to_numeric(form.cleaned_data['notaaprobar'], 0)
                        asignaturamalla.asistenciaaprobar = form.cleaned_data['asistenciaaprobar']
                        asignaturamalla.save(request)
                        log(u"Modifico asignatura de malla de curso: %s" % asignaturamalla, request, "edit")
                        return ok_json()
                    else:
                        pass
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'activarmalla':
                try:
                    mallacurso = MallaCurso.objects.get(pk=request.POST['id'])
                    mallacurso.activa = True
                    mallacurso.save(request)
                    log(u"habilito malla curso: %s" % mallacurso, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'desactivarmalla':
                try:
                    mallacurso = MallaCurso.objects.get(pk=request.POST['id'])
                    mallacurso.activa = False
                    mallacurso.save(request)
                    log(u"Deshabilito malla curso: %s" % mallacurso, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'activarcurso':
                try:
                    curso = Curso.objects.get(pk=request.POST['id'])
                    curso.activa = True
                    curso.save(request)
                    log(u"Habilito curso: %s" % curso, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'desactivarcurso':
                try:
                    curso = Curso.objects.get(pk=request.POST['id'])
                    curso.activa = False
                    curso.save(request)
                    log(u"Deshabilito curso: %s" % curso, request, "edit")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delasignaturamalla':
                try:
                    asignaturacurso = AsignaturaCurso.objects.get(pk=request.POST['id'])
                    log(u"Elimino asignatura de malla de curso: %s" % asignaturacurso, request, "del")
                    asignaturacurso.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'eliminar':
                try:
                    curso = Curso.objects.get(pk=request.POST['id'])
                    log(u"Elimino curso: %s" % curso, request, "del")
                    curso.delete()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=2, ex=ex)

            if action == 'delmalla':
                try:
                    malla = MallaCurso.objects.get(pk=request.POST['id'])
                    log(u"Elimino malla de curso: %s" % malla, request, "del")
                    malla.delete()
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
                    data['title'] = u'Adicionar nuevo curso'
                    data['form'] = CursoForm()
                    return render(request, "adm_cursos/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar curso'
                    data['curso'] = curso = Curso.objects.get(pk=request.GET['id'])
                    data['form'] = CursoForm(initial={'nombre': curso.nombre,
                                                      'certificadoobtenido': curso.certificadoobtenido,
                                                      'alias': curso.alias})
                    return render(request, "adm_cursos/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'addmalla':
                try:
                    data['title'] = u'Adicionar malla de curso'
                    data['curso'] = Curso.objects.get(pk=request.GET['id'])
                    data['form'] = MallaCursoForm()
                    return render(request, "adm_cursos/addmallacurso.html", data)
                except Exception as ex:
                    pass

            if action == 'addasignaturasmalla':
                try:
                    data['title'] = u'Adicionar asignatura a malla de curso'
                    data['malla'] = MallaCurso.objects.get(pk=request.GET['id'])
                    data['form'] = AsignaturaMallaCursoForm()
                    return render(request, "adm_cursos/addasignaturamallacurso.html", data)
                except Exception as ex:
                    pass

            if action == 'editasignaturamalla':
                try:
                    data['title'] = u'Modificar asignatura de malla de curso'
                    data['asignaturacurso'] = asignaturacurso = AsignaturaCurso.objects.get(pk=request.GET['id'])
                    data['malla'] = asignaturacurso.mallacurso
                    data['form'] = AsignaturaMallaCursoForm(initial={'asignatura': asignaturacurso.asignatura,
                                                                     'nivelmalla': asignaturacurso.nivelmalla,
                                                                     'horas': asignaturacurso.horas,
                                                                     'calificar': asignaturacurso.calificar,
                                                                     'requiereaprobar': asignaturacurso.requiereaprobar,
                                                                     'validacreditos': asignaturacurso.validacreditos,
                                                                     'validapromedio': asignaturacurso.validapromedio,
                                                                     'creditos': asignaturacurso.creditos,
                                                                     'notamaxima': asignaturacurso.notamaxima,
                                                                     'notaaprobar': asignaturacurso.notaaprobar,
                                                                     'asistenciaaprobar': asignaturacurso.asistenciaaprobar})
                    return render(request, "adm_cursos/editasignaturamalla.html", data)
                except Exception as ex:
                    pass

            if action == 'activarmalla':
                try:
                    data['title'] = u'Habilitar malla'
                    data['malla'] = MallaCurso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursos/activarmalla.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivarmalla':
                try:
                    data['title'] = u'Deshabilitar malla'
                    data['malla'] = MallaCurso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursos/desactivarmalla.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminar':
                try:
                    data['title'] = u'Eliminar asignatura de curso'
                    data['curso'] = Curso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursos/eliminar.html", data)
                except Exception as ex:
                    pass

            if action == 'delmalla':
                try:
                    data['title'] = u'Eliminar malla de curso'
                    data['malla'] = MallaCurso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursos/delmalla.html", data)
                except Exception as ex:
                    pass

            if action == 'activarcurso':
                try:
                    data['title'] = u'Activar curso'
                    data['curso'] = Curso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursos/activarcurso.html", data)
                except Exception as ex:
                    pass

            if action == 'desactivarcurso':
                try:
                    data['title'] = u'Desactivar curso'
                    data['curso'] = Curso.objects.get(pk=request.GET['id'])
                    return render(request, "adm_cursos/desactivarcurso.html", data)
                except Exception as ex:
                    pass

            if action == 'asignaturasmalla':
                try:
                    data['title'] = u'Asignaturas de la malla del curso'
                    data['malla'] = malla = MallaCurso.objects.get(pk=request.GET['id'])
                    data['asignaturas'] = AsignaturaCurso.objects.filter(mallacurso=malla)
                    return render(request, "adm_cursos/asignaturasmalla.html", data)
                except Exception as ex:
                    pass

            if action == 'mallas':
                try:
                    data['title'] = u'Mallas de cursos'
                    data['curso'] = curso = Curso.objects.get(pk=request.GET['id'])
                    data['mallas'] = curso.mallacurso_set.all()
                    return render(request, "adm_cursos/mallas.html", data)
                except Exception as ex:
                    pass

            if action == 'delasignaturamalla':
                try:
                    data['title'] = u'Eliminar asignatura de curso'
                    data['asignaturacurso'] = asignaturacurso = AsignaturaCurso.objects.get(pk=request.GET['id'])
                    data['malla'] = asignaturacurso.mallacurso
                    return render(request, "adm_cursos/delasignaturamalla.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            data['title'] = u'Configuración de cursos y escuelas complementarias'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s'].strip()
                actividades = Curso.objects.filter(nombre__icontains=search)
            elif 'id' in request.GET:
                ids = request.GET['id']
                actividades = Curso.objects.filter(id=ids)
            else:
                actividades = Curso.objects.all()

            paging = MiPaginador(actividades, 20)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session and 'paginador_url' in request.session:
                    if request.session['paginador_url'] == 'adm_cursos':
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
            request.session['paginador_url'] = 'adm_cursos'
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['actividades'] = page.object_list
            data['actividades'] = actividades
            return render(request, "adm_cursos/view.html", data)
