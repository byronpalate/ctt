# coding=utf-8
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from decorators import last_access
from settings import ARCHIVO_TIPO_GENERAL
from ctt.commonviews import adduserdata
from ctt.funciones import log, url_back, bad_json, ok_json, generar_nombre, MiPaginador
from ctt.models import Mensaje, MensajeDestinatario, Persona, Archivo


@login_required(login_url='/login')
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add':
                try:
                    destinatarioanterior = None
                    if 'reenvio' in request.POST:
                        destinatarioanterior = MensajeDestinatario.objects.get(pk=request.POST['reenvio'])
                    nuevo = Mensaje(asunto=request.POST['asunto'],
                                    contenido=request.POST['mensaje'],
                                    fecha=datetime.now().date(),
                                    hora=datetime.now().time(),
                                    origen=request.session['persona'],
                                    borrador=False)
                    nuevo.save()
                    if 'reenvio' not in request.POST:
                        if request.FILES:
                            for name, filename in request.FILES.iteritems():
                                nfile = request.FILES[name]
                                nfile._name = generar_nombre('adjunto', nfile._name)
                                archivo = Archivo(nombre=filename._name,
                                                  fecha=datetime.now(),
                                                  archivo=nfile,
                                                  tipo_id=ARCHIVO_TIPO_GENERAL)
                                archivo.save()
                                nuevo.archivo.add(archivo)
                    else:
                        for archivo in destinatarioanterior.mensaje.archivo.all():
                            archivo = Archivo(nombre=archivo.nombre,
                                              fecha=datetime.now(),
                                              archivo=archivo.archivo,
                                              tipo_id=ARCHIVO_TIPO_GENERAL)
                            archivo.save()
                            nuevo.archivo.add(archivo)
                    destinatarios = request.POST['seleccion'].split(",")
                    for destinatario in destinatarios:
                        nuevodestinatario = MensajeDestinatario(mensaje=nuevo,
                                                                destinatario=Persona.objects.get(pk=int(destinatario)),
                                                                leido=False)
                        nuevodestinatario.save()
                        if 'reenvio' in request.POST:
                            nuevodestinatario.reenvio = destinatarioanterior.mensaje
                            nuevodestinatario.save()
                    log(u'Adiciono mensaje: %s' % nuevo, request, "add")
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(mensaje=u'%s' % ex.message)

            if action == 'vermensajein':
                try:
                    mensaje = Mensaje.objects.get(pk=request.POST['id'])
                    if mensaje.mensajedestinatario_set.filter(destinatario__id=request.POST['destinatario']).exists():
                        dest = mensaje.mensajedestinatario_set.filter(destinatario__id=request.POST['destinatario'])[0]
                        dest.leido = True
                        dest.fecha = datetime.now().date()
                        dest.hora = datetime.now().time()
                        dest.save()
                        lista = []
                        for archivo in mensaje.archivo.all():
                            lista.append({'nombre': archivo.nombre, 'url': archivo.download_link()})
                        return ok_json({'archivos': lista, 'id': mensaje.id, 'contenido': mensaje.contenido, 'asunto': mensaje.asunto, 'datosenvio': mensaje.origen.nombre_completo() + ' - ' + mensaje.fecha.strftime("%d-%m-%Y") + ' a las ' + mensaje.hora.strftime("%I:%M %p")})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delin':
                try:
                    mensajes = json.loads(request.POST['lista'])
                    for idm in mensajes:
                        inbox = MensajeDestinatario.objects.filter(mensaje__id=int(idm['id']), destinatario=persona)[0]
                        inbox.leido = True
                        inbox.visible = False
                        inbox.save()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'delout':
                try:
                    mensajes = json.loads(request.POST['lista'])
                    for idm in mensajes:
                        inbox = Mensaje.objects.get(pk=int(idm['id']))
                        inbox.visible = False
                        inbox.save()
                    return ok_json()
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == 'vermensajeout':
                try:
                    mensaje = Mensaje.objects.get(pk=request.POST['id'])
                    if mensaje.mensajedestinatario_set.filter(destinatario__id=request.POST['destinatario']).exists():
                        dest = mensaje.mensajedestinatario_set.filter(destinatario__id=request.POST['destinatario'])[0]
                        dest.leido = True
                        dest.fecha = datetime.now().date()
                        dest.hora = datetime.now().time()
                        dest.save()
                        lista = []
                        for archivo in mensaje.archivo.all():
                            lista.append({'nombre': archivo.nombre, 'url': archivo.download_link()})
                        return ok_json({'archivos': lista, 'id': mensaje.id, 'contenido': mensaje.contenido, 'asunto': mensaje.asunto, 'datosenvio': mensaje.origen.nombre_completo() + ' - ' + mensaje.fecha.strftime("%d-%m-%Y") + ' a las ' + mensaje.hora.strftime("%I:%M %p")})
                    else:
                        return bad_json(error=6)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=1, ex=ex)

            if action == "vin":
                try:
                    persona = request.session['persona']
                    mensaje = Mensaje.objects.get(pk=request.POST['id'])
                    destinatario = mensaje.mensajedestinatario_set.filter(destinatario=persona)[0]
                    destinatario.leido = True
                    destinatario.save()
                    data['mensaje'] = mensaje
                    data['destinatario'] = destinatario
                    pendientes = MensajeDestinatario.objects.filter(destinatario=persona, leido=False).count()
                    template = get_template("mailbox/vermensajein.html")
                    json_content = template.render(data)
                    # return HttpResponse(json.dumps({"result": "ok", 'html': json_content, 'pendientes': pendientes}), mimetype="application/json")
                    return HttpResponse(json.dumps({"result": "ok", 'html': json_content, 'pendientes': pendientes}))
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

            if action == "vout":
                try:
                    mensaje = Mensaje.objects.get(pk=request.POST['id'])
                    data['mensaje'] = mensaje
                    template = get_template("mailbox/vermensajeout.html")
                    json_content = template.render(data)
                    # return HttpResponse(json.dumps({"result": "ok", 'html': json_content}), mimetype="application/json")
                    return HttpResponse(json.dumps({"result": "ok", 'html': json_content}))
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(error=3, ex=ex)

        return bad_json(error=0)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'enviados':
                try:
                    data['title'] = u'Mensajes enviados'
                    persona = request.session['persona']
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        mensajes = Mensaje.objects.filter(Q(asunto__icontains=search) |
                                                          Q(contenido__icontains=search) |
                                                          Q(mensajedestinatario__destinatario__apellido1__icontains=search) |
                                                          Q(mensajedestinatario__destinatario__apellido2__icontains=search) |
                                                          Q(mensajedestinatario__destinatario__nombres__icontains=search), origen=persona, visible=True)
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        mensajes = Mensaje.objects.filter(origen=persona, visible=True, id=ids)
                    else:
                        mensajes = Mensaje.objects.filter(origen=persona, visible=True)
                    paging = MiPaginador(mensajes, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session and 'paginador_url' in request.session:
                            if request.session['paginador_url'] == 'mensajes_in':
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
                    request.session['paginador_url'] = 'mensajes_in'
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['mensajes'] = page.object_list
                    return render(request, "mailbox/enviados.html", data)
                except Exception as ex:
                    pass

            return url_back(request, ex=ex if 'ex' in locals() else None)
        else:
            try:
                data['title'] = u'Mensajes entrantes'
                persona = request.session['persona']
                search = None
                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    mensajes = Mensaje.objects.filter(Q(asunto__icontains=search) |
                                                      Q(contenido__icontains=search) |
                                                      Q(mensajedestinatario__destinatario__apellido1__icontains=search) |
                                                      Q(mensajedestinatario__destinatario__apellido2__icontains=search) |
                                                      Q(mensajedestinatario__destinatario__nombre2__icontains=search) |
                                                      Q(mensajedestinatario__destinatario__nombre1__icontains=search), mensajedestinatario__destinatario=persona, mensajedestinatario__visible=True)
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    mensajes = Mensaje.objects.filter(mensajedestinatario__destinatario=persona, mensajedestinatario__visible=True, id=ids)
                else:
                    mensajes = Mensaje.objects.filter(mensajedestinatario__destinatario=persona, mensajedestinatario__visible=True)
                paging = MiPaginador(mensajes, 25)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session and 'paginador_url' in request.session:
                        if request.session['paginador_url'] == 'mensajes_in':
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
                request.session['paginador_url'] = 'mensajes_in'
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['mensajes'] = page.object_list
                return render(request, "mailbox/inbox.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/')
