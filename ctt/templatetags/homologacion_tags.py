# apps/sga/templatetags/homologacion_tags.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

PASO_LABELS = {
    1: ("Documentos",               "D"),
    2: ("Solicitud",                "S"),
    3: ("Info Pre-Homolog.",        "P"),
    4: ("Materias Pre-Homolog.",    "M"),
    5: ("Record",                   "R"),
}

@register.simple_tag
def barra_homologacion(paso) -> str:
    try:
        paso = int(paso)
    except (TypeError, ValueError):
        return ""

    if paso == 0:
        return ""

    ancho = 100 // 5        # 5 pasos
    barras = []
    for i in range(1, 6):
        nombre, sigla = PASO_LABELS[i]

        if i < paso:
            cls = "bg-success"
        elif i == paso:
            cls = "bg-primary"
        else:
            cls = "bg-light text-muted"

        barras.append(
            f'<div class="progress-bar {cls}" '
            f'style="width:{ancho}%;font-size:9px;height:16px;line-height:16px" '
            f'data-bs-toggle="tooltip" data-bs-placement="top" title="{nombre}">{sigla}</div>'
        )

    html = (
        '<div class="progress" style="height:16px;">'
        f'{"".join(barras)}'
        '</div>'
        '<script>var tt=document.querySelectorAll(\'[data-bs-toggle="tooltip"]\');'
        'tt.forEach(t=>new bootstrap.Tooltip(t));</script>'
    )
    return mark_safe(html)

@register.filter
def paso_label(paso):
    return PASO_LABELS.get(int(paso), ("—", ""))[0]
