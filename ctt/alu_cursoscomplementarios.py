# coding=utf-8
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import TIPO_ESTUDIANTE_CURSO_UTI_ID, NOTA_ESTADO_EN_CURSO
from ctt.commonviews import adduserdata
from ctt.forms import ActividadInscripcionForm
from ctt.funciones import url_back, bad_json, ok_json, MiPaginador, log, fechatope_cursos
from ctt.models import CursoEscuelaComplementaria, MatriculaCursoEscuelaComplementaria


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':

        action = request.POST['action']

        if action == 'registrar':
            try:
                curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                fechamatricula = datetime.now().date()
                if not curso.aprobacionfinanciero:
                    return bad_json(mensaje=u'El curso no ha sido aprobado por financiero.')
                if curso.cerrado:
                    return bad_json(mensaje=u'El curso ya esta cerrado.')
                if MatriculaCursoEscuelaComplementaria.objects.filter(curso=curso, inscripcion__persona=inscripcion.persona).exists():
                    return bad_json(mensaje=u'Ya se encuentra registrado en el curso.')
                if curso.prerequisitos:
                    for materia in curso.materiacursoescuelacomplementaria_set.all():
                        if not inscripcion.puede_tomar_materia(materia.asignatura):
                            return bad_json(mensaje=u'No puede tomar materias en este curso.')
                if inscripcion.tiene_deuda():
                    return bad_json(mensaje=u'No puede tomar este curso porque mantiene una deuda con la institución.')
                matricula = MatriculaCursoEscuelaComplementaria(curso=curso,
                                                                tipoestudiantecurso_id=TIPO_ESTUDIANTE_CURSO_UTI_ID,
                                                                inscripcion=inscripcion,
                                                                estado_id=NOTA_ESTADO_EN_CURSO,
                                                                fecha=fechamatricula,
                                                                hora=datetime.now().time(),
                                                                fechatope=fechatope_cursos(fechamatricula, inscripcion))
                matricula.save()
                for materia in curso.materiacursoescuelacomplementaria_set.all():
                    asignatura = MateriaAsignadaCurso(matricula=matricula,
                                                      materia=materia,
                                                      estado_id=NOTA_ESTADO_EN_CURSO)
                    asignatura.save()
                matricula.generar_rubro()
                log(u"Adiciono registro de curso: %s" % matricula, request, "add")
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'registrarlocaciones':
            try:
                form = ActividadInscripcionForm(request.POST)
                if form.is_valid():
                    curso = CursoEscuelaComplementaria.objects.get(pk=request.POST['id'])
                    if not curso.aprobacionfinanciero:
                        return bad_json(mensaje=u'El curso no ha sido aprobado por financiero')
                    inscripcion = inscripcion
                    if curso.cerrado:
                        return bad_json(mensaje=u'El curso ya esta cerrado')
                    matricula = MatriculaCursoEscuelaComplementaria(curso=curso,
                                                                    tipoestudiantecurso_id=TIPO_ESTUDIANTE_CURSO_UTI_ID,
                                                                    inscripcion=inscripcion,
                                                                    locacion=form.cleaned_data['locacion'],
                                                                    estado_id=NOTA_ESTADO_EN_CURSO)
                    matricula.save()
                    for materia in curso.materiacursoescuelacomplementaria_set.all():
                        asignatura = MateriaAsignadaCurso(matricula=matricula,
                                                          materia=materia,
                                                          estado_id=NOTA_ESTADO_EN_CURSO)
                        asignatura.save()
                    matricula.generar_rubro()
                    log(u"Adiciono registro de curso: %s" % matricula, request, "add")
                    return ok_json()
                else:
                    return bad_json(error=6)
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'registrar':
                try:
                    data['title'] = u'Registrarse en curso'
                    data['curso'] = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    return render(request, "alu_cursoscomplementarios/registrar.html", data)
                except Exception as ex:
                    pass

            if action == 'registrarlocaciones':
                try:
                    data['title'] = u'Registrarse en curso'
                    data['actividad'] = curso = CursoEscuelaComplementaria.objects.get(pk=request.GET['id'])
                    form = ActividadInscripcionForm()
                    form.autoregistro(curso)
                    data['form'] = form
                    return render(request, "alu_cursoscomplementarios/registrarlocaciones.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Cursos y escuelas complementarias'
                search = None
                ids = None
                actividades = CursoEscuelaComplementaria.objects.filter(Q(costodiferenciado=False) | Q(costodiferenciado=True), Q(coordinacion__sede=inscripcion.sede, registrootrasede=False) | Q(registrootrasede=True), Q(modalidad=inscripcion.modalidad, permiteregistrootramodalidad=False) | Q(permiteregistrootramodalidad=True), fecha_inicio__gte=datetime.now().date(), registrointerno=True, aprobacionfinanciero=True, actualizacionconocimiento=False).exclude(matriculacursoescuelacomplementaria__inscripcion=inscripcion).distinct().order_by('-fecha_fin')
                registrados = CursoEscuelaComplementaria.objects.filter(matriculacursoescuelacomplementaria__inscripcion=inscripcion).distinct().order_by('-fecha_fin')
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    actividades = actividades.filter(nombre__icontains=search).distinct().order_by('-fecha_fin')
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    actividades = actividades.filter(id=ids).order_by('-fecha_fin')
                paging = MiPaginador(actividades, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'alu_cursoscomplementarios':
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
                request.session['paginador_url'] = 'alu_cursoscomplementarios'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['actividades'] = page.object_list
                data['registrados'] = registrados
                return render(request, "alu_cursoscomplementarios/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
