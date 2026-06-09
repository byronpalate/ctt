# coding=utf-8

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import render

from decorators import last_access, secure_module
from ctt.commonviews import adduserdata
from ctt.funciones import bad_json, log, ok_json, url_back
from ctt.utils.etools import certificacionb1ingles as b1


@login_required(login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['costob1'] = b1.VALOR_EXAMEN_CERTIFICACION_B1

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                ok, resultado = b1.guardar_proceso_b1(request)

                if not ok:
                    return resultado

                log(u'Adiciono convocatoria certificacion B1 Ingles: %s' % resultado, request, 'add')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'edit':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.guardar_proceso_b1(request, proceso)

                if not ok:
                    return resultado

                log(u'Edito convocatoria certificacion B1 Ingles: %s' % resultado, request, 'edit')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editfechaexamen':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.guardar_fecha_examen_b1(request, proceso)

                if not ok:
                    return resultado

                log(u'Edito fecha examen certificacion B1 Ingles: %s' % resultado, request, 'edit')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'habilitar':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                proceso.activo = True
                proceso.save(request)

                log(u'Habilito convocatoria certificacion B1 Ingles: %s' % proceso, request, 'edit')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deshabilitar':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                proceso.activo = False
                proceso.save(request)

                log(u'Deshabilito convocatoria certificacion B1 Ingles: %s' % proceso, request, 'edit')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'cerrar':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                proceso.activo = False
                proceso.cerrado = True
                proceso.save(request)

                log(u'Cerro convocatoria certificacion B1 Ingles: %s' % proceso, request, 'edit')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'abrir':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['id'])

                if not proceso.cerrado:
                    return bad_json(mensaje=u'La convocatoria ya se encuentra abierta.')

                proceso.cerrado = False
                proceso.activo = False
                proceso.save(request)

                log(u'Abrio convocatoria certificacion B1 Ingles: %s' % proceso, request, 'edit')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'del':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                log(u'Elimino convocatoria certificacion B1 Ingles: %s' % proceso, request, 'del')
                proceso.delete()

                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'adddetalle':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.guardar_detalle_b1(request, proceso=proceso)

                if not ok:
                    return resultado

                log(u'Adiciono cronograma certificacion B1 Ingles: %s' % resultado, request, 'add')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editdetalle':
            try:
                detalle = b1.get_detalle_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(detalle.convocatoriaconsultorio)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.guardar_detalle_b1(request, detalle=detalle)

                if not ok:
                    return resultado

                log(u'Edito cronograma certificacion B1 Ingles: %s' % resultado, request, 'edit')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'deldetalle':
            try:
                detalle = b1.get_detalle_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(detalle.convocatoriaconsultorio)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                log(u'Elimino cronograma certificacion B1 Ingles: %s' % detalle, request, 'del')
                detalle.delete()

                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addrequisitoexamen':
            try:
                detalle = b1.get_detalle_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(detalle.convocatoriaconsultorio)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.guardar_requisito_b1(request, detalle=detalle)

                if not ok:
                    return resultado

                log(u'Adiciono requisito certificacion B1 Ingles: %s' % resultado, request, 'add')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'editrequisitoexamen':
            try:
                requisito = b1.get_requisito_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(
                    requisito.detalleproceso.convocatoriaconsultorio
                )
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.guardar_requisito_b1(request, requisito=requisito)

                if not ok:
                    return resultado

                log(u'Edito requisito certificacion B1 Ingles: %s' % resultado, request, 'edit')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delrequisitoexamen':
            try:
                requisito = b1.get_requisito_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(
                    requisito.detalleproceso.convocatoriaconsultorio
                )
                if mensaje:
                    return bad_json(mensaje=mensaje)

                log(u'Elimino requisito certificacion B1 Ingles: %s' % requisito, request, 'del')
                requisito.delete()

                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'addregistro':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['convocatoria'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.registrar_estudiante_b1(request, proceso)

                if not ok:
                    return resultado

                log(u'Registro por secretaria a certificacion B1 Ingles: %s' % resultado, request, 'add')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delregistro':
            try:
                registro = b1.get_registro_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(registro.convocatoria)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                log(u'Elimino registro certificacion B1 Ingles: %s' % registro, request, 'del')
                registro.delete()

                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'calificar':
            try:
                registro = b1.get_registro_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(registro.convocatoria)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.calificar_registro_b1(request, registro)

                if not ok:
                    return resultado

                log(
                    u'Califico certificacion B1 Ingles: %s nota final %s' %
                    (resultado, resultado.notafinal),
                    request,
                    'edit'
                )
                return ok_json()
            except ValueError as ex:
                transaction.set_rollback(True)
                return bad_json(mensaje=str(ex))
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'subirnotas':
            try:
                proceso = b1.get_convocatoria_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.procesar_subida_notas_b1(request, proceso)

                if not ok:
                    return resultado

                log(
                    u'Carga masiva notas B1 Ingles proceso %s, actualizados %s, omitidos sin pago %s' %
                    (proceso, resultado['actualizados'], resultado['omitidos']),
                    request,
                    'edit'
                )
                return ok_json()
            except ValueError as ex:
                transaction.set_rollback(True)
                return bad_json(mensaje=str(ex))
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'subircertificado':
            try:
                registro = b1.get_registro_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(registro.convocatoria)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                ok, resultado = b1.procesar_certificado_b1(request, registro)

                if not ok:
                    return resultado

                log(u'Subio certificado B1 Ingles: %s' % resultado, request, 'edit')
                return ok_json()
            except ValueError as ex:
                transaction.set_rollback(True)
                return bad_json(mensaje=str(ex))
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        if action == 'delcertificado':
            try:
                registro = b1.get_registro_b1(request.POST['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(registro.convocatoria)
                if mensaje:
                    return bad_json(mensaje=mensaje)

                b1.eliminar_certificado_b1(registro, request)

                log(u'Elimino certificado B1 Ingles: %s' % registro, request, 'del')
                return ok_json()
            except Exception as ex:
                transaction.set_rollback(True)
                return bad_json(error=1, ex=ex)

        return bad_json(error=0)

    if 'action' in request.GET:
        action = request.GET['action']

        if action == 'add':
            try:
                data['title'] = u'Agregar convocatoria certificacion institucional B1'
                data['form'] = b1.proceso_form_inicial_b1()
                return render(request, 'adm_certificacionb1ingles/add.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)

        if action == 'edit':
            try:
                data['title'] = u'Editar convocatoria certificacion institucional B1'
                data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

                mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
                if mensaje:
                    return url_back(request, ex=mensaje)

                data['form'] = b1.proceso_form_inicial_b1(proceso)
                return render(request, 'adm_certificacionb1ingles/edit.html', data)
            except Exception as ex:
                return url_back(request, ex=ex)

        if action == 'habilitar':
            data['title'] = u'Habilitar convocatoria'
            data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
            if mensaje:
                return url_back(request, ex=mensaje)

            return render(request, 'adm_certificacionb1ingles/habilitar.html', data)

        if action == 'deshabilitar':
            data['title'] = u'Deshabilitar convocatoria'
            data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
            if mensaje:
                return url_back(request, ex=mensaje)

            return render(request, 'adm_certificacionb1ingles/deshabilitar.html', data)

        if action == 'cerrar':
            data['title'] = u'Cerrar convocatoria'
            data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
            if mensaje:
                return url_back(request, ex=mensaje)

            return render(request, 'adm_certificacionb1ingles/cerrar.html', data)

        if action == 'abrir':
            data['title'] = u'Abrir convocatoria'
            data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

            if not proceso.cerrado:
                return url_back(request, ex=u'La convocatoria ya se encuentra abierta.')

            return render(request, 'adm_certificacionb1ingles/abrir.html', data)

        if action == 'del':
            data['title'] = u'Eliminar convocatoria'
            data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
            if mensaje:
                return url_back(request, ex=mensaje)

            return render(request, 'adm_certificacionb1ingles/delconvocatoria.html', data)

        if action == 'detalles':
            data['title'] = u'Cronograma y requisitos B1'
            data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])
            data['detalles'] = proceso.detalleconvocatoriaexamensuficiencia_set.all().order_by('inicio', 'fin')

            return render(request, 'adm_certificacionb1ingles/detalles.html', data)

        if action == 'registrados':
            data['title'] = u'Registrados certificacion institucional B1'
            data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])
            search = request.GET.get('s', '').strip()

            registrados = proceso.procesoaplicanteexamensuficiencia_set.select_related(
                'inscripcion__persona',
                'inscripcion__carrera',
                'inscripcion__modalidad'
            ).order_by('inscripcion__persona__apellido1')

            if search:
                registrados = registrados.filter(
                    Q(inscripcion__persona__cedula__icontains=search) |
                    Q(inscripcion__persona__apellido1__icontains=search) |
                    Q(inscripcion__persona__apellido2__icontains=search) |
                    Q(inscripcion__persona__nombres__icontains=search)
                )

            paging, page, p = b1.paginar(
                request,
                registrados,
                'adm_certificacionb1ingles_registrados',
                30
            )

            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search
            data['registrados'] = page.object_list
            data['transparencia'] = {
                registro.id: b1.detalle_calculo_b1(registro)
                for registro in page.object_list
            }

            return render(request, 'adm_certificacionb1ingles/registrados.html', data)

        if action == 'adddetalle':
            data['title'] = u'Adicionar cronograma'
            data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
            if mensaje:
                return url_back(request, ex=mensaje)

            data['form'] = b1.detalle_form_inicial_b1()
            return render(request, 'adm_certificacionb1ingles/adddetalle.html', data)

        if action == 'editdetalle':
            data['title'] = u'Editar cronograma'
            data['detalle'] = detalle = b1.get_detalle_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(detalle.convocatoriaconsultorio)
            if mensaje:
                return url_back(request, ex=mensaje)

            data['form'] = b1.detalle_form_inicial_b1(detalle)
            return render(request, 'adm_certificacionb1ingles/editdetalle.html', data)

        if action == 'deldetalle':
            data['title'] = u'Eliminar cronograma'
            data['detalle'] = detalle = b1.get_detalle_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(detalle.convocatoriaconsultorio)
            if mensaje:
                return url_back(request, ex=mensaje)

            return render(request, 'adm_certificacionb1ingles/deldetalle.html', data)

        if action == 'requisitosexamensuficiencia':
            data['title'] = u'Requisitos certificacion institucional B1'
            data['detalle'] = detalle = b1.get_detalle_b1(request.GET['id'])
            data['proceso'] = detalle.convocatoriaconsultorio
            data['requisitos'] = detalle.requisitosdetalleconvocatoriaexamensuficiencia_set.all()

            return render(request, 'adm_certificacionb1ingles/requisitosexamen.html', data)

        if action == 'addrequisitoexamen':
            data['title'] = u'Adicionar requisito certificacion B1'
            data['detalle'] = detalle = b1.get_detalle_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(detalle.convocatoriaconsultorio)
            if mensaje:
                return url_back(request, ex=mensaje)

            data['form'] = b1.requisito_form_inicial_b1()
            return render(request, 'adm_certificacionb1ingles/addrequisitoexamen.html', data)

        if action == 'editrequisitoexamen':
            data['title'] = u'Editar requisito certificacion B1'
            data['requisito'] = requisito = b1.get_requisito_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(
                requisito.detalleproceso.convocatoriaconsultorio
            )
            if mensaje:
                return url_back(request, ex=mensaje)

            data['form'] = b1.requisito_form_inicial_b1(requisito)
            return render(request, 'adm_certificacionb1ingles/editrequisitoexamen.html', data)

        if action == 'delrequisitoexamen':
            data['title'] = u'Eliminar requisito certificacion B1'
            data['requisito'] = requisito = b1.get_requisito_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(
                requisito.detalleproceso.convocatoriaconsultorio
            )
            if mensaje:
                return url_back(request, ex=mensaje)

            return render(request, 'adm_certificacionb1ingles/delrequisitoexamen.html', data)

        if action == 'addregistro':
            data['title'] = u'Adicionar estudiante'
            data['convocatoria'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
            if mensaje:
                return url_back(request, ex=mensaje)

            data['form'] = b1.registro_estudiante_form_b1()
            return render(request, 'adm_certificacionb1ingles/addregistro.html', data)

        if action == 'delregistro':
            data['title'] = u'Eliminar registro'
            data['registro'] = registro = b1.get_registro_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(registro.convocatoria)
            if mensaje:
                return url_back(request, ex=mensaje)

            return render(request, 'adm_certificacionb1ingles/delregistro.html', data)

        if action == 'calificar':
            data['title'] = u'Calificar certificacion B1'
            data['registro'] = registro = b1.get_registro_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(registro.convocatoria)
            if mensaje:
                return url_back(request, ex=mensaje)

            data['form'] = b1.nota_certificacion_form_b1(registro)
            return render(request, 'adm_certificacionb1ingles/calificar.html', data)

        if action == 'transparencia':
            data['title'] = u'Transparencia calculo certificacion B1'
            data['registro'] = registro = b1.get_registro_b1(request.GET['id'])
            data['proceso'] = registro.convocatoria
            data['calculo'] = b1.detalle_calculo_b1(registro)

            return render(request, 'adm_certificacionb1ingles/transparencia.html', data)

        if action == 'subirnotas':
            data['title'] = u'Subir archivo de notas certificacion B1'
            data['convocatoria'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
            if mensaje:
                return url_back(request, ex=mensaje)

            data['form'] = b1.importar_notas_form_b1()
            return render(request, 'adm_certificacionb1ingles/subirnotas.html', data)

        if action == 'subircertificado':
            data['title'] = u'Subir certificado B1'
            data['registro'] = registro = b1.get_registro_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(registro.convocatoria)
            if mensaje:
                return url_back(request, ex=mensaje)

            data['form'] = b1.certificado_form_b1()
            return render(request, 'adm_certificacionb1ingles/subircertificado.html', data)

        if action == 'delcertificado':
            data['title'] = u'Eliminar certificado B1'
            data['registro'] = registro = b1.get_registro_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(registro.convocatoria)
            if mensaje:
                return url_back(request, ex=mensaje)

            return render(request, 'adm_certificacionb1ingles/delcertificado.html', data)

        if action == 'descargarregistrados':
            proceso = b1.get_convocatoria_b1(request.GET['id'])
            return b1.descargar_registrados_b1(proceso)

        if action == 'editfechaexamen':
            data['title'] = u'Editar fecha de examen B1'
            data['proceso'] = proceso = b1.get_convocatoria_b1(request.GET['id'])

            mensaje = b1.bloqueo_convocatoria_cerrada(proceso)
            if mensaje:
                return url_back(request, ex=mensaje)

            data['form'] = b1.fecha_examen_form_b1(proceso)
            return render(request, 'adm_certificacionb1ingles/editfechaexamen.html', data)

        return url_back(request)

    try:
        data['title'] = u'Certificacion institucional B1 Ingles'
        search = request.GET.get('s', '').strip()

        procesos = b1.convocatorias_b1().filter(
            periodo=request.session['periodo']
        )

        if search:
            procesos = procesos.filter(
                Q(nombre__icontains=search) |
                Q(id=search if search.isdigit() else 0)
            )

        procesos = procesos.order_by('-fechainicio')

        paging, page, p = b1.paginar(
            request,
            procesos,
            'adm_certificacionb1ingles',
            25
        )

        data['paging'] = paging
        data['rangospaging'] = paging.rangos_paginado(p)
        data['page'] = page
        data['search'] = search
        data['procesos'] = page.object_list

        return render(request, 'adm_certificacionb1ingles/view.html', data)
    except Exception:
        return HttpResponseRedirect('/')
