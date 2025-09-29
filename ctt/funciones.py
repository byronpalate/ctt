 # coding=utf-8
from __future__ import division

import json
import os
import random
import unicodedata
from datetime import datetime, timedelta, date
from unicodedata import normalize

from django.contrib.admin.models import LogEntry, ADDITION, DELETION, CHANGE
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.encoding import smart_str

from settings import MEDIA_ROOT, MEDIA_URL, EMAIL_DOMAIN, EMAIL_DOMAIN_ESTUDIANTES, \
    MODALIDAD_DISTANCIA, DIAS_MATRICULA_EXPIRA_CURSOS_ESCUELAS, VENCE_MATRICULA_POR_DIAS_CURSOS_ESCUELAS, \
    FECHA_EXPIRA_MATRICULA_CURSOS_ESCUELAS, DIAS_MATRICULA_EXPIRA_EXAMEN_UBICACION, \
    VENCE_MATRICULA_POR_DIAS_EXAMEN_UBICACION, FECHA_EXPIRA_MATRICULA_EXAMEN_UBICACION, VENCE_PARQUEADERO_POR_DIAS, \
    DIAS_PARQUEO_EXPIRA, FECHA_EXPIRA_PARQUEO, MODALIDAD_PRECENCIAL, MODALIDAD_SEMIPRECENCIAL, MODALIDAD_ONLINE, \
     MODALIDAD_HIBRIDA

MENSAJES_ERROR = (
    'Error en la accion.',
    'No tiene permisos para realizar esta accion.'
)


class MiPaginador(Paginator):
    def __init__(self, object_list, per_page, orphans=0, allow_empty_first_page=True, rango=5):
        super(MiPaginador, self).__init__(object_list, per_page, orphans=orphans,
                                          allow_empty_first_page=allow_empty_first_page)
        self.rango = rango
        self.paginas = []
        self.primera_pagina = False
        self.ultima_pagina = False

    def rangos_paginado(self, pagina):
        left = pagina - self.rango
        right = pagina + self.rango
        if left < 1:
            left = 1
        if right > self.num_pages:
            right = self.num_pages
        self.paginas = range(left, right + 1)
        self.primera_pagina = True if left > 1 else False
        self.ultima_pagina = True if right < self.num_pages else False
        self.ellipsis_izquierda = left - 1
        self.ellipsis_derecha = right + 1


def proximafecha(fecha, periocidad):
    day = fecha.day
    month = fecha.month
    year = fecha.year
    if (month + periocidad) > 12:
        sobrante = (month + periocidad) - 12
        nextmonth = sobrante
        nextyear = year + 1
    elif month == 12 and periocidad == 1:
        nextmonth = 1
        nextyear = year + 1
    else:
        nextmonth = month + periocidad
        nextyear = year
    dia = fecha.day
    while dia >= 0:
        try:
            return datetime(nextyear, nextmonth, dia)
        except:
            dia -= 1

import re

def validar_correo(correo):
    # Expresión regular para validar el formato del correo electrónico
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'

    if re.match(patron, correo):
        return True
    # El correo es válido
    # Guarda el correo en tu modelo o realiza cualquier otra operación necesaria
    else:
        # El correo no es válido, puedes manejarlo de la manera que prefieras
        return False

def validar_placa_ecuador(placa):
    """
    Valida una placa de Ecuador para autos y motos.
    - Autos: Formato ABC-1234
    - Motos: Formato ABC-123
    """
    regex_auto = r'^[A-Z]{3}-\d{4}$'  # Formato para autos: ABC-1234
    regex_moto = r'^[A-Z]{3}-\d{3}$'  # Formato para motos: ABC-123
    placa = placa.upper()  # Convertir a mayúsculas para consistencia
    if not re.match(regex_auto, placa) and not re.match(regex_moto, placa):
        return False
    return True
def siguientemes(fecha):
    day = 1
    month = fecha.month
    year = fecha.year
    if (month + 1) > 12:
        month = 1
        year += 1
    else:
        month += 1
    return datetime(year, month, day)


def generar_email(persona, variant=1, estudiante=None):
    from ctt.models import Persona
    if estudiante:
        dominio = EMAIL_DOMAIN_ESTUDIANTES
    else:
        dominio = EMAIL_DOMAIN
    if variant > 1:
        email = remover_caracteres_especiales_unicode(u"%s%s@%s" % (persona.usuario.username, variant, dominio))
        if not Persona.objects.filter(emailinst=email).exists():
            return email
    else:
        email = remover_caracteres_especiales_unicode(u"%s@%s" % (persona.usuario.username, dominio))
        if not Persona.objects.filter(emailinst=email).exists():
            return email
    return generar_email(persona, variant=(variant + 1), estudiante=estudiante)


def resetear_clave(persona):
    password = persona.cedula if persona.cedula else persona.pasaporte
    user = persona.usuario
    user.set_password(password)
    user.save()
    persona.cambiar_clave()


def calculate_username(persona, variant=0):
    usernamevariant = (remover_caracteres_especiales_unicode(smart_str(persona.nombre1[0]+ persona.apellido1.replace(' ','')))).lower()
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.']
    usernamevariantfinal = ''
    for letra in usernamevariant:
        if letra in alfabeto:
            usernamevariantfinal += letra
    if variant > 1:
        usernamevariantfinal += str(variant)
    if not User.objects.filter(username=usernamevariantfinal).exists():
        return usernamevariantfinal
    return calculate_username(persona, variant + 1)


def log(mensaje, request, accion):
    if accion == "del":
        logaction = DELETION
    elif accion == "add":
        logaction = ADDITION
    else:
        logaction = CHANGE
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=None,
        object_id=None,
        object_repr='',
        action_flag=logaction,
        change_message=u"%s" % mensaje)


def convertir_fecha(s):
    if ':' in s:
        sep = ':'
    elif '-' in s:
        sep = '-'
    else:
        sep = '/'
    return date(int(s.split(sep)[2]), int(s.split(sep)[1]), int(s.split(sep)[0]))


def convertir_fecha_invertida(s):
    if ':' in s:
        sep = ':'
    elif '-' in s:
        sep = '-'
    else:
        sep = '/'
    return date(int(s.split(sep)[0]), int(s.split(sep)[1]), int(s.split(sep)[2]))


def extraeVideoIdYoutube(urlYoutube=''):
    data = urlYoutube.split('/')
    if len(data) > 1:
        return data[len(data) - 1]
    else:
        return None


def first_day_of_month(d):
    return date(d.year, d.month, 1)


def last_day_of_month(d):
    if d.month == 12:
        return d.replace(day=31)
    return d.replace(month=d.month + 1, day=1) - timedelta(days=1)


def fechatope(fecha, inscripcion):
    from ctt.models import mi_institucion
    institucion = mi_institucion()
    contador = 0
    nuevafecha = fecha
    dias = 0
    vencepordias = institucion.vencematriculaspordias
    if vencepordias:
        if inscripcion.modalidad.id == MODALIDAD_PRECENCIAL:
            dias = institucion.diasmatriculaexpirapresencial
        elif inscripcion.modalidad.id == MODALIDAD_SEMIPRECENCIAL:
            dias = institucion.diasmatriculaexpirasemipresencial
        elif inscripcion.modalidad.id == MODALIDAD_DISTANCIA:
            dias = institucion.diasmatriculaexpiradistancia
        elif inscripcion.modalidad.id == MODALIDAD_ONLINE:
            dias = institucion.diasmatriculaexpiraonline
        elif inscripcion.modalidad.id == MODALIDAD_HIBRIDA:
            dias = institucion.diasmatriculaexpirahibrida
        while contador < dias:
            nuevafecha = nuevafecha + timedelta(1)
            if institucion.diashabiles:
                if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
                    contador += 1
            else:
                contador += 1
    else:
        if not inscripcion.carrera.posgrado:
            nuevafecha = datetime.strptime(str(institucion.fechaexpiramatriculagrado), '%Y-%m-%d')
        else:
            nuevafecha = datetime.strptime(str(institucion.fechaexpiramatriculaposgrado), '%Y-%m-%d')
    return nuevafecha


def fechatope_cursos(fecha, inscripcion):
    contador = 0
    nuevafecha = fecha
    dias = DIAS_MATRICULA_EXPIRA_CURSOS_ESCUELAS
    vencepordias = VENCE_MATRICULA_POR_DIAS_CURSOS_ESCUELAS
    if vencepordias:
        while contador < dias:
            nuevafecha = nuevafecha + timedelta(1)
            if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
                contador += 1
    else:
        nuevafecha = datetime.strptime(FECHA_EXPIRA_MATRICULA_CURSOS_ESCUELAS, '%Y-%m-%d')
    return nuevafecha


def fechatope_examenubicacion_ingles(fecha, inscripcion):
    contador=0
    nuevafecha = fecha
    dias = DIAS_MATRICULA_EXPIRA_EXAMEN_UBICACION
    vencepordias = VENCE_MATRICULA_POR_DIAS_EXAMEN_UBICACION
    if vencepordias:
        while contador < dias:
            nuevafecha = nuevafecha + timedelta(1)
            if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
                contador += 1
    else:
        nuevafecha = datetime.strptime(FECHA_EXPIRA_MATRICULA_EXAMEN_UBICACION, '%Y-%m-%d')
    return nuevafecha


def fechatope_parqueo(fecha):
    contador=0
    nuevafecha = fecha
    dias = DIAS_PARQUEO_EXPIRA
    vencepordias = VENCE_PARQUEADERO_POR_DIAS
    if vencepordias:
        while contador < dias:
            nuevafecha = nuevafecha + timedelta(1)
            if nuevafecha.weekday() != 5 and nuevafecha.weekday() != 6:
                contador += 1
    else:
        nuevafecha = datetime.strptime(FECHA_EXPIRA_PARQUEO, '%Y-%m-%d')
    return nuevafecha


def formato24h(hora):
    horas = hora.partition(":")[0]
    minutos = hora.partition(":")[2].partition(" ")[0]
    meridiano = hora.partition(":")[2].partition(" ")[2]
    if meridiano == "AM":
        if horas == "12":
            return "00" + ":" + minutos + ":00"
        else:
            return horas + ":" + minutos + ":00"
    else:
        if horas == "12":
            return horas + ":" + minutos + ":00"
        else:
            return str(int(horas) + 12) + ":" + minutos + ":00"


def formato12h(hora):
    horas = hora.partition(":")[0]
    minutos = hora.partition(":")[2].partition(" ")[0]
    if horas >= "12":
        if horas == "12":
            return horas + ":" + minutos + " PM"
        else:
            return str(int(horas) - 12) + ":" + minutos + " PM"
    else:
        if horas == "0":
            return "12:" + minutos + " AM"
        else:
            return horas + ":" + minutos + " AM"


def remover_caracteres_especiales(cadena):
    return ''.join((c for c in unicodedata.normalize('NFD', u"%s" % cadena) if unicodedata.category(c) != 'Mn'))


def remover_tildes(cadena):
    trans_tab = dict.fromkeys(map(ord, u'\u0301\u0308'), None)
    cadena = normalize('NFKC', normalize('NFKD', cadena).translate(trans_tab))
    return cadena.replace('.', '').replace('!', '').replace('"', '').replace('*', '').replace('-', '').replace('+', '').replace('/', '').replace(',', '').replace(';', '').replace(':', '').replace('_', '').replace('|', '')


def remover_caracteres_especiales_unicode(cadena):
    cadena = smart_str(cadena)
    return cadena.replace('ñ', 'n').replace('Ñ', 'N').replace('Á', 'A').replace('á', 'a').replace('É', 'E').replace('é', 'e').replace('Í', 'I').replace('í', 'i').replace('Ó', 'O').replace('ó', 'o').replace('Ú', '').replace('ú', '')


def generar_nombre(nombre, original):
    ext = ""
    if original.find(".") > 0:
        ext = original[original.rfind("."):]
    fecha = datetime.now().date()
    hora = datetime.now().time()
    return nombre + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__() + ext


def generar_nombre_guayaquil(nombre, original):
    ext = ""
    if original.find(".") > 0:
        ext = original[original.rfind("."):]
    fecha = datetime.now().date()
    hora = datetime.now().time()
    return nombre + fecha.year.__str__() + '%02d' % fecha.month + fecha.day.__str__() + '_EOD' + ext


def generar_nombre_western(nombre, original):
    ext = ""
    if original.find(".") > 0:
        ext = original[original.rfind("."):]
    fecha = datetime.now().date()
    # hora = datetime.now().time()
    return nombre + fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + ext


def validarcedula(numero):
    nat = False
    numeroprovincias = 24
    modulo = 11
    if numero.__len__() != 10:
        return 'El numero de cedula no es valido, tiene mas de 10 digitos'
    prov = numero[0:2]
    if int(prov) > numeroprovincias or int(prov) <= 0:
        return 'El codigo de la provincia (dos primeros digitos) es invalido'
    d1 = numero[0:1]
    d2 = numero[1:2]
    d3 = numero[2:3]
    d4 = numero[3:4]
    d5 = numero[4:5]
    d6 = numero[5:6]
    d7 = numero[6:7]
    d8 = numero[7:8]
    d9 = numero[8:9]
    d10 = numero[9:10]
    p1 = 0
    p2 = 0
    p3 = 0
    p4 = 0
    p5 = 0
    p6 = 0
    p7 = 0
    p8 = 0
    p9 = 0
    if int(d3) == 7 or int(d3) == 8:
        return 'El tercer digito ingresado es invalido'
    if int(d3) < 6:
        nat = True
        p1 = int(d1) * 2
        if p1 >= 10:
            p1 -= 9
        p2 = int(d2) * 1
        if p2 >= 10:
            p2 -= 9
        p3 = int(d3) * 2
        if p3 >= 10:
            p3 -= 9
        p4 = int(d4) * 1
        if p4 >= 10:
            p4 -= 9
        p5 = int(d5) * 2
        if p5 >= 10:
            p5 -= 9
        p6 = int(d6) * 1
        if p6 >= 10:
            p6 -= 9
        p7 = int(d7) * 2
        if p7 >= 10:
            p7 -= 9
        p8 = int(d8) * 1
        if p8 >= 10:
            p8 -= 9
        p9 = int(d9) * 2
        if p9 >= 10:
            p9 -= 9
        modulo = 10
    elif int(d3) == 6:
        p1 = int(d1) * 3
        p2 = int(d2) * 2
        p3 = int(d3) * 7
        p4 = int(d4) * 6
        p5 = int(d5) * 5
        p6 = int(d6) * 4
        p7 = int(d7) * 3
        p8 = int(d8) * 2
        p9 = 0
    elif int(d3) == 9:
        p1 = int(d1) * 4
        p2 = int(d2) * 3
        p3 = int(d3) * 2
        p4 = int(d4) * 7
        p5 = int(d5) * 6
        p6 = int(d6) * 5
        p7 = int(d7) * 4
        p8 = int(d8) * 3
        p9 = int(d9) * 2
    suma = p1 + p2 + p3 + p4 + p5 + p6 + p7 + p8 + p9
    residuo = suma % modulo
    if residuo == 0:
        digitoverificador = 0
    else:
        digitoverificador = modulo - residuo
    if nat:
        if digitoverificador != int(d10):
            return 'El numero de cedula de la persona natural es incorrecto'
        else:
            return 'Ok'
    else:
        return 'El numero de cedula introducido es incorrecto'


def puede_modificar_inscripcion_get(request, inscripcion):
    persona = request.session['persona']
    if not inscripcion.coordinacion in persona.lista_coordinaciones():
        raise Exception(MENSAJES_ERROR[1])
    if not inscripcion.carrera in persona.lista_carreras_coordinacion(inscripcion.coordinacion):
        raise Exception(MENSAJES_ERROR[1])


def puede_modificar_inscripcion_post(request, inscripcion):
    persona = request.session['persona']
    if not inscripcion.coordinacion in persona.lista_coordinaciones():
        return False
    if not inscripcion.carrera in persona.lista_carreras_coordinacion(inscripcion.coordinacion):
        return False
    return True


def puede_realizar_accion_post(request, permiso):
    return request.user.has_perm(permiso)


def puede_realizar_accion_get(request, permiso):
    return request.user.has_perm(permiso)


def url_back(request, ex=None):
    message = ''
    try:
        if ex and ex.message in MENSAJES_ERROR:
            message = "?info=%s" % ex.message
        elif ex and ex.message not in MENSAJES_ERROR:
            message = "?info=%s" % MENSAJES_ERROR[0]
    except:
        pass
    return HttpResponseRedirect("%s%s" % (request.path, message))


def lista_correo(listagrupos):
    from ctt.models import Persona
    lista = []
    for persona in Persona.objects.filter(usuario__groups__id__in=listagrupos, usuario__is_active=True).distinct():
        lista.extend(persona.lista_emails_correo())
    return lista


def solo_letas(texto):
    textofinal = ''
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.', ' ']
    for letra in texto:
        if letra in alfabeto:
            textofinal += letra
    return textofinal.strip()


def solo_caracteres(texto):
    acentos = [u'á', u'é', u'í', u'ó', u'ú', u'Á', u'É', u'Í', u'Ó', u'Ú', u'ñ', u'Ñ']
    alfabeto = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '.', '/', '#', ',', ' ', ':', '-', '_']
    resultado = ''
    for letra in texto:
        if letra in alfabeto:
            resultado += letra
        elif letra in acentos:
            if letra == u'á':
                resultado += 'a'
            elif letra == u'é':
                resultado += 'e'
            elif letra == u'í':
                resultado += 'i'
            elif letra == u'ó':
                resultado += 'o'
            elif letra == u'ú':
                resultado += 'u'
            elif letra == u'Á':
                resultado += 'A'
            elif letra == u'É':
                resultado += 'E'
            elif letra == u'Í':
                resultado += 'I'
            elif letra == u'Ó':
                resultado += 'O'
            elif letra == u'Ú':
                resultado += 'U'
            elif letra == u'Ñ':
                resultado += 'N'
            elif letra == u'ñ':
                resultado += 'n'
        else:
            resultado += '?'
    return resultado


def fetch_resources(uri):
    return os.path.join(MEDIA_ROOT, uri.replace(MEDIA_URL, ""))


def bad_json(mensaje=None, error=None, extradata=None, ex=None, form=None):
    data = {'result': 'bad'}
    if mensaje:
        data.update({"icono": "warning", "titulo": "Advertencia",'mensaje': mensaje})
    elif error:
        if error == 0:
            data.update({"icono": "warning", "titulo": "Advertencia", "mensaje": "Solicitud incorrecta."})
        elif error == 1:
            data.update({"icono": "warning", "titulo": "Advertencia", "mensaje": "Error al guardar los datos.","excepcion":'No envia excepción' if ex == None else ex.args[0]})
        elif error == 2:
            data.update({"icono": "warning", "titulo": "Advertencia", "mensaje": "Error al eliminar los datos.","excepcion":'No envia excepción' if ex == None else ex.args[0]})
        elif error == 3:
            data.update({"errors": None if form == None else form.errors, "icono": "warning", "titulo": "Advertencia", "mensaje": "Error al obtener los datos.","excepcion":'No envia excepción' if ex == None else ex.args[0]})
        elif error == 4:
            data.update({"icono": "info", "titulo": "Advertencia", "mensaje": "No tiene permisos para realizar esta acción."})
        elif error == 5:
            data.update({"icono": "warning", "titulo": "Advertencia", "mensaje": "Error al generar la información."})
        elif error == 6:
            data.update({"errors": None if form == None else form.errors,"icono": "warning", "titulo": "Advertencia", "mensaje": "Los datos no son validos, revise la información.","excepcion": ex })
        elif error == 7:
            data.update({"icono": "info", "titulo": "Advertencia", "mensaje": "Registro duplicado."})
        elif error == 8:
            data.update({"icono": "info", "titulo": "Advertencia", "mensaje": "No se puede eliminar existen registros relacionados."})
        elif error == 9:
            data.update({"icono": "warning", "titulo": "Advertencia", "mensaje": "No tiene permiso para modificar la ficha del estudiante."})
    else:
        data.update({"icono": "error", "titulo": "Advertencia", "mensaje": "Error en el sistema."})
    if extradata:
        data.update(extradata)
    return JsonResponse(data)


def ok_json(data=None, simple=None, safe=True):
    if data:
        if not simple:
            if 'result' not in data.keys():
                data.update({"result": "ok"})
    else:
        data = {"result": "ok"}
    return JsonResponse(data) if safe else JsonResponse(data, safe=False)


def empty_json(data):
    if 'result' not in data.keys():
        data.update({"result": "ok"})
    return JsonResponse(data)


def generar_cambio_clave():
    clave = ''
    for i in range(15):
        clave += random.choice('0123456789ABCDEF')
    return clave


UNIDADES = (
    '',
    'UN ',
    'DOS ',
    'TRES ',
    'CUATRO ',
    'CINCO ',
    'SEIS ',
    'SIETE ',
    'OCHO ',
    'NUEVE ',
    'DIEZ ',
    'ONCE ',
    'DOCE ',
    'TRECE ',
    'CATORCE ',
    'QUINCE ',
    'DIECISEIS ',
    'DIECISIETE ',
    'DIECIOCHO ',
    'DIECINUEVE ',
    'VEINTE '
)

DECENAS = (
    'VENTI',
    'TREINTA ',
    'CUARENTA ',
    'CINCUENTA ',
    'SESENTA ',
    'SETENTA ',
    'OCHENTA ',
    'NOVENTA ',
    'CIEN '
)

CENTENAS = (
    'CIENTO ',
    'DOSCIENTOS ',
    'TRESCIENTOS ',
    'CUATROCIENTOS ',
    'QUINIENTOS ',
    'SEISCIENTOS ',
    'SETECIENTOS ',
    'OCHOCIENTOS ',
    'NOVECIENTOS '
)

MONEDAS = (
    {'country': u'Colombia', 'currency': 'COP', 'singular': u'PESO COLOMBIANO', 'plural': u'PESOS COLOMBIANOS', 'symbol': u'$'},
    {'country': u'Estados Unidos', 'currency': 'USD', 'singular': u'DÓLAR', 'plural': u'DÓLARES', 'symbol': u'US$'},
    {'country': u'Europa', 'currency': 'EUR', 'singular': u'EURO', 'plural': u'EUROS', 'symbol': u'€'},
    {'country': u'México', 'currency': 'MXN', 'singular': u'PESO MEXICANO', 'plural': u'PESOS MEXICANOS', 'symbol': u'$'},
    {'country': u'Perú', 'currency': 'PEN', 'singular': u'NUEVO SOL', 'plural': u'NUEVOS SOLES', 'symbol': u'S/.'},
    {'country': u'Reino Unido', 'currency': 'GBP', 'singular': u'LIBRA', 'plural': u'LIBRAS', 'symbol': u'£'}
)


def to_word(number, mi_moneda=None):
    if mi_moneda:
        try:
            moneda = filter(lambda x: x['currency'] == mi_moneda, MONEDAS).next()
            if number < 2:
                moneda = moneda['singular']
            else:
                moneda = moneda['plural']
        except Exception as ex:
            return "Tipo de moneda inválida"
    else:
        moneda = ""
    converted = ''

    if not (0 < number < 999999999):
        return 'No es posible convertir el numero a letras'

    number_str = str(number).zfill(9)
    millones = number_str[:3]
    miles = number_str[3:6]
    cientos = number_str[6:]

    if millones:
        if millones == '001':
            converted += 'UN MILLON '
        elif int(millones) > 0:
            converted += '%sMILLONES ' % __convert_group(millones)

    if miles:
        if miles == '001':
            converted += 'MIL '
        elif int(miles) > 0:
            converted += '%sMIL ' % __convert_group(miles)

    if cientos:
        if cientos == '001':
            converted += 'UN '
        elif int(cientos) > 0:
            converted += '%s ' % __convert_group(cientos)

    converted += moneda
    return converted.title()


def __convert_group(n):
    output = ''

    if n == '100':
        output = "CIEN "
    elif n[0] != '0':
        output = CENTENAS[int(n[0]) - 1]

    k = int(n[1:])
    if k <= 20:
        output += UNIDADES[k]
    else:
        if k > 30 and n[2] != '0':
            output += '%sY %s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
        else:
            output += '%s%s' % (DECENAS[int(n[1]) - 2], UNIDADES[int(n[2])])
    return output


def enletras(x):
    entera = str(x).split('.')[0]
    fraccion = str(x).split('.')[1]
    return (to_word(int(entera)) + "con " + fraccion.ljust(2, '0') + "/100").upper()


def ruta_en_media(fichero):
    path = ''
    incluir = False
    if '/' in fichero:
        separador = '/'
    else:
        separador = '\\'
    for elemento in fichero.split(separador):
        if not incluir:
            if elemento == 'media':
                incluir = True
        if incluir:
            path += '/' + elemento
    return path


def generar_clave(largo):
    clave = ''
    for i in range(largo):
        clave += random.choice('0123456789ABCDEF')
    return clave


def calcular_edad(nacimiento):
    today = date.today()
    try:
        birthday = nacimiento.replace(year=today.year)
    except ValueError:
        birthday = nacimiento.replace(year=today.year, month=nacimiento.month+1, day=1)
    if birthday > today:
        return today.year - nacimiento.year - 1
    else:
        return today.year - nacimiento.year


def fields_model(classname, app):
    try:
        exec('from %s.models import %s' % (app, classname))
        fields = eval(classname + '._meta.get_fields()')
        return fields
    except:
        return []


def field_default_value_model(field):
    try:
        value = str(field)
        return value if 'django.db.models.fields.NOT_PROVIDED' not in value else ''
    except:
        return ''


def generar_usuario(persona, group_id=None):
    password = persona.cedula if persona.cedula else persona.pasaporte
    user = User.objects.create_user(calculate_username(persona), '', password)
    user.save()
    persona.usuario = user
    persona.save()
    persona.cambiar_clave()
    if group_id:
        g = Group.objects.get(pk=group_id)
        g.user_set.add(user)
        g.save()
    return user


def rango_fecha(horario):
    from datetime import timedelta
    lista = []
    for x in range((horario.fin - horario.inicio).days + 1):
        fecha = horario.inicio + timedelta(days=x)
        if fecha.isoweekday() == horario.dia:
            lista.append(fecha)
    return lista


def valores_asignados(periodo, sede, carrera, modalidad, malla):
    from ctt.models import PreciosPeriodoModulosInscripcion
    if PreciosPeriodoModulosInscripcion.objects.filter(periodo=periodo, sede=sede, carrera=carrera, modalidad=modalidad, malla=malla).exists():
        return PreciosPeriodoModulosInscripcion.objects.filter(periodo=periodo, sede=sede, carrera=carrera, modalidad=modalidad, malla=malla).first()
    return False


def EncryptString(txtClaro):
    import base64
    import Crypto.Cipher.AES as AES
    clearTextBytes = txtClaro.encode('utf-8')
    rijn = AES.new('hcxilkqbbhczfeultgbskdmaunivmfuo', AES.MODE_CBC, 'ryojvlzmdalyglrj')
    blockSize = 16
    paddingLength = blockSize - (len(clearTextBytes) % blockSize)
    padding = chr(paddingLength) * paddingLength
    paddedClearTextBytes = clearTextBytes + padding
    cipherTextBytes = rijn.encrypt(paddedClearTextBytes)
    return base64.b64encode(cipherTextBytes)


def DecryptString(txtEncriptado):
    import base64
    import StringIO
    import Crypto.Cipher.AES as AES
    encryptedTextBytes = base64.b64decode(txtEncriptado)
    ms = StringIO.StringIO()
    rijn = AES.new('hcxilkqbbhczfeultgbskdmaunivmfuo', AES.MODE_CBC, 'ryojvlzmdalyglrj')
    blockSize = 16
    paddingLength = ord(encryptedTextBytes[-1])
    paddedEncryptedTextBytes = encryptedTextBytes[:-paddingLength]
    clearTextBytes = rijn.decrypt(paddedEncryptedTextBytes)
    return clearTextBytes.decode('utf-8')


def crear_usuario_ad(persona):
    from suds.client import Client
    from suds.transport.https import HttpAuthenticated
    from ctt.models import TituloInstitucion
    titulo = TituloInstitucion.objects.get(pk=1)
    client = Client(titulo.urlwebservicead)
    username = 'UsuarioAd'
    password = 'U$uar102023'
    authentication = HttpAuthenticated(username=username, password=password)
    client.set_options(transport=authentication)
    departamento = ''
    if persona.es_estudiante():
        departamento = 'USUARIOS'
    else:
        if persona.es_administrativo():
            departamento = ''
            if persona.es_profesor():
                departamento = 'DOCENTES'
    response = client.service.CrearUsuario(Usuario=username,
                                           Clave=password,
                                           Nombre1=persona.nombre1,
                                           Nombre2=persona.nombre2,
                                           Apellido1=persona.apellido1,
                                           Apellido2=persona.apellido2,
                                           Identificacion=persona.cedula if persona.cedula else persona.pasaporte,
                                           NombreUsuario=persona.usuario.username,
                                           Email=persona.usuario.email,
                                           Telefono=persona.telefono,
                                           Compania='UTI',
                                           Departamento=departamento,
                                           Titulo='ESTUDIANTES',
                                           # Contrasenia=persona.cedula if persona.cedula else persona.pasaporte,
                                           # Contrasenia='U$uar102023',
                                           Contrasenia=EncryptString(persona.cedula),
                                           Portal='CTT;',
                                           Estado='1',
                                           EstadoProceso='1')
    return response


def generar_color_hexadecimal():
    while True:
        # Genera un número hexadecimal aleatorio para cada componente RGB
        color = "{:02X}{:02X}{:02X}".format(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        # Excluye el color blanco
        if color != "FFFFFF":
            return color


def consulta_datos(cedula):
    import requests
    from ctt.funciones import convertir_fecha
    from ctt.models import Provincia, Canton, Parroquia, Pais, Nacionalidad, Sexo, PersonaEstadoCivil
    from settings import PAIS_ECUADOR_ID
    from django.db.models import Q
    headers = {'AUTHORIZATION': u'RVNQQcORQTQ0'}
    try:
        url = 'https://datos.los4rios.com/api_basico_dp/' + cedula
        solicitud = requests.get(url, headers=headers, verify=False, timeout=7)
        r = solicitud.json()
        r = r['data'][0]
        idnacionalidad = 0
        idpais = 0
        idsexo = 0
        idestadocivil = 0
        idprovincianac = 0
        idcantonnac = 0
        idparroquianac = 0
        nombreprovnac = ''
        nombrecantonnac = ''
        nombreparroquianac = ''
        idprovinciadom = 0
        idcantondom = 0
        idparroquiadom = 0
        nombreprovdom = ''
        nombrecantondom = ''
        nombreparroquiadom = ''
        sector = ''
        nombrepais = ''
        if r['sexo'].strip() != '':
            try:
                idsexo = Sexo.objects.filter(nombre=r['sexo'].strip())[0].id
            except:
                idsexo = 0
        if r['estado_civil'].strip() != '':
            try:
                idestadocivil = PersonaEstadoCivil.objects.filter(nombre=r['estado_civil'].strip())[0].id
            except:
                idestadocivil = 0
        if r['nacionalidad'] == 'ECUATORIANA' or r['nacionalidad'] == "ECUATORIANO/ECUATORIANA":
            idnacionalidad = 18
            idpais = PAIS_ECUADOR_ID
            nombrepais = "ECUADOR"
            lugar = r['lugarnacimiento'].split("/")
            try:
                dato = Provincia.objects.filter(nombre=lugar[0])[0]
                idprovincianac = dato.id
                nombreprovnac = dato.nombre
            except:
                pass
            try:
                datoc = Canton.objects.filter(nombre=lugar[1], provincia_id=idprovincianac)[0]
                idcantonnac = datoc.id
                nombrecantonnac = datoc.nombre
            except:
                pass
            try:
                a = lugar[2].strip()
                datod = Parroquia.objects.filter(nombre=a, canton_id=idcantonnac)[0]
                idparroquianac = datod.id
                nombreparroquianac = datod.nombre
            except:
                idparroquianac = 0
            lugardomicilio = r['dirdomicilio'].split("/")
            try:
                datoe = Provincia.objects.filter(nombre=lugardomicilio[0])[0]
                idprovinciadom = datoe.id
                nombreprovdom = datoe.nombre
            except:
                pass
            try:
                datof = Canton.objects.filter(nombre=lugardomicilio[1], provincia__id=idprovinciadom)[0]
                idcantondom = datof.id
                nombrecantondom = datof.nombre
            except:
                pass
            try:
                a = lugardomicilio[2].strip()
                sector = a
                datog = Parroquia.objects.filter(nombre=a, canton__id=idcantondom)[0]
                idparroquiadom = datog.id
                nombreparroquiadom = datog.nombre
            except:
                idparroquiadom = 0
        else:
            if r['lugarnacimiento'].strip() != '':
                try:
                    idpais = Pais.objects.filter(nombre=r['lugarnacimiento'])[0].id
                    nombrepais = Pais.objects.filter(nombre=r['lugarnacimiento'])[0].nombre
                except:
                    idpais = 0
            try:
                idnacionlidad = Nacionalidad.objects.filter(Q(nombremasculino=r['nacionalidad']) | Q(nombrefemenino=r['nacionalidad']))[0].id
            except:
                idnacionlidad = 0
            lugardomicilio = r['dirdomicilio'].split("/")
            try:
                datoe = Provincia.objects.filter(nombre=lugardomicilio[0])[0]
                idprovinciadom = datoe.id
                nombreprovdom = datoe.nombre
            except:
                pass
            try:
                datof = Canton.objects.filter(nombre=lugardomicilio[1])[0]
                idcantondom = datof.id
                nombrecantondom = datof.nombre
            except:
                pass
            try:
                a = lugardomicilio[2].strip()
                datog = Parroquia.objects.filter(nombre=a)[0]
                idparroquiadom = datog.id
                nombreparroquiadom = datog.nombre
            except Exception as error:
                pass
        from datetime import datetime
        nombres = r['nombres'].strip().split(' ')
        return {'result': 'ok',
                'cedula': r['identificacion'],
                'existe': 'si' if len(r['nombres']) > 0 else 'no',
                'nombre1': nombres[0],
                'nombre2': nombres[1] if len(nombres) > 1 else '',
                'apellido1': r['apellido1'],
                'apellido2': r['apellido2'],
                'nacionalidad': r['nacionalidad'],
                'idnacionalidad': idnacionalidad,
                'idpaisnacimiento': idpais,
                'paisnacimiento': nombrepais,
                'nacimiento': convertir_fecha(r['nacimiento']).strftime("%d-%m-%Y"),
                'idsexo': idsexo,
                'idestadocivil': idestadocivil,
                'lugarnacimiento': r['lugarnacimiento'],
                'idprovicianacimiento': idprovincianac,
                'nombreprovnac': nombreprovnac,
                'idcantonnacimiento': idcantonnac,
                'nombrecantonnac': nombrecantonnac,
                'idparroquianacimiento': idparroquianac,
                'sector': sector,
                'celular': r['celular'],
                'telefono': r['telefono'],
                'direccion': r['direccion'],
                'email': r['correo'],
                'emailinst': r['correoinst'],
                'nombreparroquianac': nombreparroquianac,
                'domicilio': r['dirdomicilio'],
                'idprovinciadom': idprovinciadom,
                'nombreprovdom': nombreprovdom,
                'idcantondom': idcantondom,
                'nombrecantondom': nombrecantondom,
                'idparroquiadom': idparroquiadom,
                'nombreparroquiadom': nombreparroquiadom,
                'calledomicilio': r['calledomicilio'],
                'numerodomicilio': r['numerodomicilio'],
                'nombreconyuge': '',
                'apellido1conyuge': '',
                'apellido2conyuge': '',
                'instruccion': r['instruccion'],
                'profesion': r['profesion'],
                'nombrespadre': r['nombrespadre'],
                'nombresmadre': r['nombresmadre']}
    except Exception as ex:
        return {'existe': 'no', 'result': 'bad', 'mensaje': ex.message}


def consultar_titulos(persona):
    import requests
    from ctt.funciones import convertir_fecha
    from ctt.models import TecnologicoUniversidad, NivelTitulacion, Colegio, Especialidad, EstudioPersona, \
        null_to_text
    headers = {'AUTHORIZATION': u'SVNURVIgVElUVUxPUzUy'}
    try:
        # url = 'http://192.168.220.71:8085/api_titulo/' + persona.cedula
        url = 'https://datos.los4rios.com/api_titulo/' + persona.cedula
        solicitud = requests.get(url, headers=headers, verify=False, timeout=6)
        r = solicitud.json()
        r = r['data'][0]
        try:
            for e in r['superiores']:
                if TecnologicoUniversidad.objects.filter(nombre=null_to_text(e['institucion'])).exists():
                    ie = TecnologicoUniversidad.objects.filter(nombre=null_to_text(e['institucion']))[0]
                else:
                    ie = TecnologicoUniversidad(nombre=null_to_text(e['institucion']),
                                                universidad=True)
                    ie.save()
                niveltitulacion = e['nivel']
                nivel = NivelTitulacion.objects.filter(nombre__icontains='3')[0]
                if NivelTitulacion.objects.filter(nombre=niveltitulacion).exists():
                    nivel = NivelTitulacion.objects.filter(nombre=niveltitulacion)[0]
                if not EstudioPersona.objects.filter(persona=persona, registro=e['registro']).exists():
                    if e['fecharegistro'] != '':
                        fecharegistro = convertir_fecha(e['fecharegistro'])
                    else:
                        fecharegistro = None
                    if e['fechagraduacion'] != '':
                        fechagraduacion = convertir_fecha(e['fechagraduacion'])
                    else:
                        fechagraduacion = None
                    estudio = EstudioPersona(persona=persona,
                                             superior=True,
                                             cursando=False,
                                             registro=e['registro'],
                                             fecharegistro=fecharegistro,
                                             fechagraduacion=fechagraduacion,
                                             niveltitulacion=nivel,
                                             institucioneducacionsuperior=ie,
                                             titulo=e['titulo'],
                                             verificado=True)
                    estudio.save()
            for e in r['basicos']:
                if Colegio.objects.filter(nombre=null_to_text(e['institucion'])).exists():
                    ie = Colegio.objects.filter(nombre=null_to_text(e['institucion']))[0]
                else:
                    ie = Colegio(nombre=null_to_text(e['institucion']))
                    ie.save()
                if Especialidad.objects.filter(nombre=null_to_text(e['especialidad'])).exists():
                    esp = Especialidad.objects.filter(nombre=null_to_text(e['especialidad']))[0]
                else:
                    esp = Especialidad(nombre=null_to_text(e['especialidad']))
                    esp.save()
                if not EstudioPersona.objects.filter(persona=persona, superior=False, institucioneducacionbasica=ie).exists():
                    estudio = EstudioPersona(persona=persona,
                                             superior=False,
                                             institucioneducacionbasica=ie,
                                             especialidadeducacionbasica=esp,
                                             fechagraduacion=convertir_fecha(e['fechagraduacion']).year if e['fechagraduacion'] else None,
                                             cursando=False,
                                             verificado=True)
                    estudio.save()
        except Exception as ex:
            pass
    except Exception as ex:
        pass

def paisSGA(cod):
    from ctt.models import Pais
    if cod is None:
        return ''
    pais = Pais.objects.filter(codseven=cod).first()
    if pais is None or pais.id is None:
        return ''
    else:
        return pais.id

def provinciaSGA(cod):
    from ctt.models import Provincia
    if cod is None:
        return ''
    provincia = Provincia.objects.filter(codseven=cod).first()
    if provincia is None or provincia.id is None:
        return ''
    else:
        return provincia.id
def cantonSGA(cod):
    from ctt.models import Canton
    if cod is None:
        return ''
    canton = Canton.objects.filter(codseven=cod).first()
    if canton is None or canton.id is None:
        return ''
    else:
        return canton.id

def parroquiaSGA(canton,cod):
    from ctt.models import Parroquia
    if cod is None:
        return ''
    parroquia = Parroquia.objects.filter(canton_id=canton,codseven=cod).first()
    if parroquia is None or parroquia.id is None:
        return ''
    else:
        return parroquia.id

def detectar_cambios(objeto_original, cleaned_data, campos_mapeados):
    cambios = []
    for campo_form, campo_modelo in campos_mapeados.items():
        valor_original = getattr(objeto_original, campo_modelo, None)
        valor_nuevo = cleaned_data.get(campo_form, None)
        if valor_original != valor_nuevo:
            cambios.append(f"{campo_modelo}: '{str(valor_original)}' → '{str(valor_nuevo)}'")
    return cambios

def diff_log(old_obj, new_obj, *, extra_exclude=None, as_string=False, string_prefix='Cambios: '):
    from datetime import date, datetime
    from django.db.models.fields.files import FieldFile

    # ---- 1) lista de exclusiones ---- #
    exclude = {'id', 'usuario_modificacion_id', 'fecha_modificacion', 'updated_at',} | set(extra_exclude or ())

    # ---- 2) helper local para normalizar ---- #
    def _n(val):
        if val is None:
            return None
        if isinstance(val, datetime):
            return val.strftime('%d-%m-%Y %H:%M')
        if isinstance(val, date):
            return val.strftime('%d-%m-%Y')
        if isinstance(val, FieldFile):
            return val.name or ''
        return val

    # ---- 3) recorrer campos y armar diferencias ---- #
    cambios = []
    for field in new_obj._meta.concrete_fields:        # evita M2M/reverse
        name = field.attname
        if name in exclude:
            continue

        old_val = _n(getattr(old_obj, name, None))
        new_val = _n(getattr(new_obj, name, None))

        if old_val != new_val:
            cambios.append({
                'field': name,
                'old':   old_val,
                'new':   new_val,
                'type':  type(getattr(new_obj, name)).__name__,
            })

    # ---- 4) salida según lo que pidas ---- #
    if as_string:
        if not cambios:
            return ''  # sin cambios
        partes = [f"{c['field']}: '{c['old']}' → '{c['new']}'" for c in cambios]
        return string_prefix + "; ".join(partes)

    return cambios

def validarRGB(color):
    if color:
        try:
            s = color.split(',')
            if len(s) == 3:
                for i in range(0, 3):
                    if int(s[i]) < 0 or int(s[i]) > 255:
                        return '0,0,0'
                return str(s[0]) + ',' + str(s[1]) + ',' + str(s[2])
        except:
            return '0,0,0'
    return '0,0,0'
