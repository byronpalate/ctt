# coding=utf-8

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from ctt.commonviews import adduserdata
from ctt.forms import AsignaturaForm, UnificarAsignaturaForm
from ctt.funciones import log, MiPaginador, ok_json, bad_json, url_back, remover_tildes
from ctt.models import Asignatura, Inscripcion, Group


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
                form = AsignaturaForm(request.POST)
                if form.is_valid():
                    if Asignatura.objects.filter(nombre=form.cleaned_data['nombre'].upper()).exists():
                        return bad_json(error=7)
                    asignatura = Asignatura(nombre=remover_tildes(form.cleaned_data['nombre']),
                                            codigo=remover_tildes(form.cleaned_data['codigo']))
                    asignatura.save(request)
                    log(u'Adiciono asignatura: %s' % asignatura, request, "add")
                    return ok_json({"id": asignatura.id})
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edit':
            try:
                asignatura = Asignatura.objects.get(pk=request.POST['id'])
                form = AsignaturaForm(request.POST)
                if form.is_valid():
                    if Asignatura.objects.filter(nombre=form.cleaned_data['nombre'].upper()).exclude(id=asignatura.id).exists():
                        return bad_json(error=7)
                    asignatura.codigo = remover_tildes(form.cleaned_data['codigo'])
                    if not asignatura.en_uso():
                        asignatura.nombre = remover_tildes(form.cleaned_data['nombre'])
                    asignatura.save(request)
                    log(u'Modifico asignatura: %s' % asignatura, request, "edit")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'unificar':
            try:
                asignatura = Asignatura.objects.get(pk=request.POST['id'])
                form = UnificarAsignaturaForm(request.POST)
                if form.is_valid():
                    nuevaasignatura = form.cleaned_data['asignatura']
                    existentes = Inscripcion.objects.filter(recordacademico__asignatura=asignatura)
                    if existentes.filter(recordacademico__asignatura=nuevaasignatura).exists():
                        return bad_json(mensaje=u'Error existen ambas en el record de un estudiante.')
                    log(u'Unifico asignatura: %s con %s' % (asignatura, nuevaasignatura), request, "del")
                    asignatura.historicorecordacademico_set.all().update(asignatura=nuevaasignatura)
                    asignatura.recordacademico_set.all().update(asignatura=nuevaasignatura)
                    asignatura.agregacioneliminacionmaterias_set.all().update(asignatura=nuevaasignatura)
                    asignatura.asignaturamalla_set.all().update(asignatura=nuevaasignatura)
                    asignatura.homologacioninscripcion_set.all().update(asignatura=nuevaasignatura)
                    asignatura.materia_set.all().update(asignatura=nuevaasignatura)
                    asignatura.materiaotracarrera_set.all().update(asignatura=nuevaasignatura)
                    asignatura.materiaasignada_set.all().update(asignaturareal=nuevaasignatura)
                    asignatura.materiacursoescuelacomplementaria_set.all().update(asignatura=nuevaasignatura)
                    asignatura.asignaturacurso_set.all().update(asignatura=nuevaasignatura)
                    asignatura.materiacursounidadtitulacion_set.all().update(asignatura=nuevaasignatura)
                    asignatura.prehomologacioninscripcion_set.all().update(asignatura=nuevaasignatura)
                    for prematricula in asignatura.prematricula_set.all():
                        prematricula.asignaturas.remove(asignatura)
                        prematricula.asignaturas.add(nuevaasignatura)
                    asignatura.trabajotitulacionmalla_set.all().update(asignatura=nuevaasignatura)
                    asignatura.retirofinanciero_set.all().update(asignatura=nuevaasignatura)
                    if asignatura.en_uso():
                        return bad_json(mensaje=u'La asignatura se encuentra en uso en una tabla no definida en esta acción')
                    asignatura.delete()
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delete':
            try:
                asignatura = Asignatura.objects.get(pk=request.POST['id'])
                if asignatura.en_uso():
                    return bad_json(error=8)
                log(u'Elimino asignatura: %s' % asignatura, request, "del")
                asignatura.delete()
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
                    data['title'] = u'Adicionar asignatura'
                    data['form'] = AsignaturaForm()
                    return render(request, "adm_asignaturas/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar asignaturas'
                    data['asignatura'] = asignatura = Asignatura.objects.get(pk=request.GET['id'])
                    form = AsignaturaForm(initial={'nombre': asignatura.nombre,
                                                   'codigo': asignatura.codigo},
                                          )
                    form.editar(asignatura)
                    data['form'] = form
                    data['permite_modificar'] = asignatura.permite_modificar()
                    return render(request, "adm_asignaturas/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'unificar':
                try:
                    data['title'] = u'Unificar asignaturas'
                    data['asignatura'] = asignatura = Asignatura.objects.get(pk=request.GET['id'])
                    form = UnificarAsignaturaForm(initial={'origen': asignatura})
                    form.editar(asignatura)
                    data['form'] = form
                    return render(request, "adm_asignaturas/unificar.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar asignatura'
                    data['asignatura'] = Asignatura.objects.get(pk=request.GET['id'])
                    return render(request, "adm_asignaturas/delete.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Listado de asignaturas'
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    asignaturas = Asignatura.objects.filter(Q(nombre__icontains=search) | Q(codigo__icontains=search)).distinct()
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    asignaturas = Asignatura.objects.filter(id=ids)
                else:
                    asignaturas = Asignatura.objects.all()
                paging = MiPaginador(asignaturas, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'adm_asignaturas':
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
                request.session['paginador_url'] = 'adm_asignaturas'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['asignaturas'] = page.object_list
                data['sololectura'] = True
                ids_grupos = [11, 28]
                listagrupo = Group.objects.filter(id__in=ids_grupos)
                if persona.en_grupos(listagrupo):
                    data['sololectura'] = False
                return render(request, "adm_asignaturas/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
