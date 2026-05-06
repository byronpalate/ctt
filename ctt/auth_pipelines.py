# coding=utf-8
"""
Pipelines de autenticacion social (python-social-auth).

Este proyecto referencia:
    - ctt.auth_pipelines.only_students
    - ctt.auth_pipelines.set_student_principal

En la copia actual faltaba este modulo y el login social terminaba en ImportError.
Estas implementaciones son conservadoras (no bloquean) y solo evitan que el flujo
se rompa. Si se requiere una validacion estricta, aqui es donde se debe ajustar.
"""


def only_students(strategy, details, backend, user=None, *args, **kwargs):
    """
    Hook para permitir/rechazar autenticacion segun reglas del proyecto.

    Retornamos kwargs para que el pipeline continue. En esta copia no aplicamos
    bloqueo para no dejar el acceso inutilizable por falta de reglas completas.
    """
    return kwargs


def set_student_principal(strategy, details, backend, user=None, *args, **kwargs):
    """
    Hook opcional para fijar perfil principal (si aplica).

    En esta copia se deja como no-op para mantener el flujo estable.
    """
    return kwargs

