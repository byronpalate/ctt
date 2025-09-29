# coding=utf-8
from django.db import transaction
from django.template import Context
from django.template.loader import get_template

from ctt.funciones import ok_json, bad_json
from ctt.models import *


def imprimir_contenido(request, referencia, iden):
    if ModeloImpresion.objects.filter(referencia=referencia).exists():
        modeloimpresion = ModeloImpresion.objects.get(referencia=referencia)
        modelo = eval(modeloimpresion.modelo)
        dato = modelo.objects.get(pk=iden)
        impresion = Impresion(usuario=request.user,
                              impresa=False,
                              contenido='')
        impresion.save(request)
        template = get_template("print/%s" % modeloimpresion.plantilla)
        d = {'dato': dato, "id": impresion.id}
        json_content = template.render(d)
        impresion.contenido = json_content
        impresion.save(request)


@transaction.atomic()
def view(request, referencia, idd):
    try:
        if not ModeloImpresion.objects.filter(referencia=referencia).exists():
            return bad_json(mensaje=u"No existe modelo de impresión.")
        imprimir_contenido(request, referencia, idd)
        return ok_json()
    except Exception as ex:
        transaction.set_rollback(True)
        return bad_json(mensaje=u'Error al imprimir el documento.')
