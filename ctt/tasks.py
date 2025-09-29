# coding=utf-8
import cgi
import re
import threading
from datetime import datetime

from django.core.mail.message import EmailMessage
from django.template.loader import get_template

from settings import EMAIL_HOST_USER, ARCHIVO_TIPO_GENERAL


class EmailThread(threading.Thread):
    def __init__(self, subject, html_content, recipient_list, recipient_list_cc, attachtment):
        self.subject = subject
        self.recipient_list = recipient_list
        self.recipient_list_cc = recipient_list_cc
        self.html_content = html_content
        self.attachtment = attachtment
        threading.Thread.__init__(self)

    def run(self):
        msg = EmailMessage(self.subject, self.html_content, EMAIL_HOST_USER, self.recipient_list, bcc=self.recipient_list_cc)
        msg.content_subtype = "html"
        if self.attachtment:
            for attach in self.attachtment:
                if attach is not None:
                    if attach:
                        if attach.archivo:
                            file = attach.archivo
                            msg.attach(file.name, file.read(), 'application/octet-stream')
        msg.send()


def send_html_mail(subject, html_template, data, recipient_list, recipient_list_cc, attachtment=None, internalmail=None):
    try:
        if recipient_list.__len__() or recipient_list_cc.__len__():
            template = get_template(html_template)
            d = data
            html_content = template.render(d)
            if internalmail:
                internalmail.contenido = html_content
                internalmail.save()
            EmailThread(subject, html_content, recipient_list, recipient_list_cc, attachtment).start()
    except Exception as ex:
        pass


def send_mail(subject, recipient_list, contenido=None, recipient_list_cc=None, attachtment=None, html_template=None, data=None, persona=None, correos=None):
    from ctt.models import Mensaje, MensajeDestinatario, mi_institucion, Archivo
    fecha = datetime.now()
    nuevo = Mensaje(asunto=subject,
                    contenido=contenido,
                    fecha=fecha.date(),
                    hora=fecha.time(),
                    origen=persona,
                    borrador=False)
    nuevo.save()
    listaattachtment = []
    if attachtment:
        for adjunto in attachtment:
            if hasattr(adjunto, '__dict__'):
                nuevo.archivo.add(adjunto)
                listaattachtment.append([adjunto.nombre, adjunto.archivo])
            else:
                archivo = Archivo(nombre=adjunto[0],
                                  fecha=datetime.now(),
                                  archivo=adjunto[1],
                                  tipo_id=ARCHIVO_TIPO_GENERAL)
                archivo.save()
                nuevo.archivo.add(archivo)
                listaattachtment.append([archivo.nombre, archivo.archivo])
    for destinatario in recipient_list:
        nuevodestinatario = MensajeDestinatario(mensaje=nuevo,
                                                destinatario=destinatario)
        nuevodestinatario.save()
    destinatarios = []
    for p in recipient_list:
        destinatarios.extend(p.lista_emails_correo())
    destinatarios_cc = []
    for p in recipient_list:
        destinatarios_cc.extend(p.lista_emails_correo())
    if correos:
        for c in correos:
            destinatarios.append(c)
    if not html_template:
        html_template = 'emails/correobasico.html'
    if not data:
        if persona:
            data = {'personaenvia': persona, 'fechaenvio': datetime.now(), 't': mi_institucion(), 'attachtment': attachtment, 'mensaje': nuevo}
        else:
            data = {'fechaenvio': datetime.now(), 't': mi_institucion(), 'attachtment': attachtment, 'mensaje': nuevo}
    else:
        data['personaenvia'] = persona
        data['mensaje'] = nuevo
        data['fechaenvio'] = datetime.now()
        data['t'] = mi_institucion()
        data['attachtment'] = attachtment
    send_html_mail(subject=subject, html_template=html_template, data=data, recipient_list=destinatarios, recipient_list_cc=destinatarios_cc, attachtment=attachtment, internalmail=nuevo)
    # send_html_mail(subject=subject, html_template=html_template, data=data, recipient_list=destinatarios, recipient_list_cc=destinatarios_cc, attachtment=listaattachtment, internalmail=nuevo)

re_string = re.compile(r'(?P<htmlchars>[<&>])|(?P<space>^[ \t]+)|(?P<lineend>\r\n|\r|\n)|(?P<protocal>(^|\s)((http|ftp)://.*?))(\s|$)', re.S | re.M | re.I)


def plaintext2html(text, tabstop=4):
    def do_sub(m):
        c = m.groupdict()
        if c['htmlchars']:
            return cgi.escape(c['htmlchars'])
        if c['lineend']:
            return '<br>'
        elif c['space']:
            t = m.group().replace('\t', '&nbsp;' * tabstop)
            t = t.replace(' ', '&nbsp;')
            return t
        elif c['space'] == '\t':
            return ' ' * tabstop
        else:
            url = m.group('protocal')
            if url.startswith(' '):
                prefix = ' '
                url = url[1:]
            else:
                prefix = ''
            last = m.groups()[-1]
            if last in ['\n', '\r', '\r\n']:
                last = '<br>'
            return '%s<a href="%s">%s</a>%s' % (prefix, url, url, last)
    return re.sub(re_string, do_sub, text)
