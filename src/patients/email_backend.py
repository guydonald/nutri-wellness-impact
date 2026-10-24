"""Backends e-mail du site : chaque e-mail envoye est enregistre dans la table QueuedEmail
(historique visible dans l'admin Django : a qui, quand, envoye ou en echec).

- QueuedEmailBackend (EMAIL_QUEUE=True) : l'e-mail est seulement range dans la file ; la page
  repond tout de suite et la tache "process_email_queue --loop" l'envoie en arriere-plan.
- LoggedEmailBackend (EMAIL_QUEUE=False) : l'e-mail part tout de suite (comme avant) et le
  resultat est note dans l'historique.

Le contenu des e-mails de compte (codes de connexion, mot de passe oublie) est efface une fois
l'e-mail envoye : seuls le sujet, le destinataire et la date sont gardes.
"""
from django.conf import settings
from django.core.mail import get_connection
from django.core.mail.backends.base import BaseEmailBackend


def _record(msg, status=None):
    from .models import QueuedEmail

    headers = dict(msg.extra_headers or {})
    category = headers.pop(QueuedEmail.HEADER_CATEGORY, QueuedEmail.CATEGORY_ACCOUNT)
    if category not in dict(QueuedEmail.CATEGORY_CHOICES):
        category = 'other'
    html = ""
    for content, mimetype in getattr(msg, "alternatives", []) or []:
        if mimetype == "text/html":
            html = content
            break
    return QueuedEmail.objects.create(
        subject=str(msg.subject)[:255],
        body=msg.body or "",
        html_body=html,
        from_email=msg.from_email or "",
        to=list(msg.to or []),
        cc=list(msg.cc or []),
        bcc=list(msg.bcc or []),
        reply_to=list(msg.reply_to or []),
        headers={k: str(v) for k, v in headers.items()},
        category=category,
        status=status or QueuedEmail.STATUS_PENDING,
    )


class QueuedEmailBackend(BaseEmailBackend):
    """Range les e-mails dans la file d'attente (envoi en arriere-plan)."""

    def send_messages(self, email_messages):
        count = 0
        for msg in email_messages or []:
            _record(msg)
            count += 1
        return count


class LoggedEmailBackend(BaseEmailBackend):
    """Envoie tout de suite avec le vrai backend, et garde une trace dans l'historique."""

    def send_messages(self, email_messages):
        from .models import QueuedEmail

        sent = 0
        real = getattr(settings, "REAL_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
        connection = get_connection(real, fail_silently=self.fail_silently)
        for msg in email_messages or []:
            item = _record(msg)
            # l'en-tete interne ne doit pas partir chez le destinataire
            (msg.extra_headers or {}).pop(QueuedEmail.HEADER_CATEGORY, None)
            msg.connection = connection
            item.attempts = 1
            try:
                if connection.send_messages([msg]):
                    item.mark_sent()
                    sent += 1
                else:
                    item.status = QueuedEmail.STATUS_FAILED
            except Exception as exc:
                item.status = QueuedEmail.STATUS_FAILED
                item.last_error = str(exc)[:2000]
                item.save()
                if not self.fail_silently:
                    raise
                continue
            item.save()
        return sent
