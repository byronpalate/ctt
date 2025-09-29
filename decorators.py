# coding=utf-8
from django.http import HttpResponseRedirect

from settings import ALLOWED_IPS_FOR_INHOUSE, ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID, EMPLEADORES_GRUPO_ID
from ctt.models import Modulo
from datetime import datetime


def secure_module(f):

    def new_f(*args, **kwargs):
        request = args[0]
        # if request.user.is_superuser:
        #     request.user.is_superuser = False
        #     request.user.is_staff = True
        if request.user.is_authenticated:
            try:
                p = request.session['perfilprincipal']
                from ctt.commonviews import primera_url_obligatoria
                url = primera_url_obligatoria(request)
                if url and request.path[1:] != url:
                    return HttpResponseRedirect("/%s" % url)
                if len(request.path[1:]) > 1:
                    if p.es_empleador() or p.es_estudiante():
                        if request.path == '/reportes' and 'action' in request.GET:
                            return f(request)
                    if p.es_estudiante():
                        g = [ALUMNOS_GROUP_ID]
                    elif p.es_profesor():
                        g = [PROFESORES_GROUP_ID]
                    elif p.es_empleador():
                        g = [EMPLEADORES_GRUPO_ID]
                    else:
                       g = [x.id for x in p.persona.usuario.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])]
                    if Modulo.objects.filter(gruposmodulos__grupo__id__in=g, url=request.path[1:], activo=True).exists():
                        return f(request)
                    else:
                        return HttpResponseRedirect("/")
                else:
                    return f(request)
            except Exception as ex:
                return HttpResponseRedirect("/")
        else:
            return HttpResponseRedirect("/")
    return new_f


def last_access(f):

    def new_f(*args, **kwargs):
        request = args[0]
        if 'ultimo_acceso' in request.session:
            request.session['ultimo_acceso'] = datetime.now()
        return f(request)

    return new_f


def inhouse_only(f):
    from ctt.commonviews import get_client_ip

    def new_f(*args, **kargs):
        request = args[0]
        ip = get_client_ip(request)
        if '*' in ALLOWED_IPS_FOR_INHOUSE:
            return f(request)
        else:
            for iprage in ALLOWED_IPS_FOR_INHOUSE:
                if iprage in ip:
                    return f(request)
        return HttpResponseRedirect('/')

    return new_f


def inhouse_check(request):
    from ctt.commonviews import get_client_ip
    ip = get_client_ip(request)
    if '*' in ALLOWED_IPS_FOR_INHOUSE:
        return True
    else:
        for iprage in ALLOWED_IPS_FOR_INHOUSE:
            if iprage in ip:
                return True
    return False


def db_selector(f):

    def new_f(*args, **kwargs):
        from settings import DATABASES

        request = args[0]
        router = 0
        if len(DATABASES) > 1:
            if 'bd_selector' not in request.session:
                request.session['bd_selector'] = router = 1
            else:
                router = request.session['bd_selector']
            router += 1
            if router > len(DATABASES) - 1:
                router = 1
            request.session['bd_name'] = 'consultas%s' % router
        else:
            if 'bd_selector' not in request.session:
                request.session['bd_selector'] = router = 0
            request.session['bd_name'] = 'default'
        request.session['bd_selector'] = router
        return f(request)

    return new_f

