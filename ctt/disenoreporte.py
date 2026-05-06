# coding=utf-8
from django.http import HttpResponse


def diseno(request):
    """
    Placeholder de diseno de reportes.

    En el proyecto original esta vista suele abrir una interfaz para disenar/editar
    reportes. En esta copia faltaba el modulo y la opcion quedaba sin respuesta.
    """
    return HttpResponse("Diseno de reporte no disponible en esta copia.", content_type="text/plain; charset=utf-8")

