"""Envoie les e-mails en attente.

  python manage.py process_email_queue           -> traite la file une fois puis s'arrete
  python manage.py process_email_queue --loop    -> tourne en permanence (tache "always-on")
"""
import time

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand
from datetime import timedelta

from django.db import close_old_connections, transaction
from django.db.models import Q
from django.utils import timezone

from patients.models import QueuedEmail


class Command(BaseCommand):
    help = "Envoie les e-mails en attente (file d'attente en base de donnees)."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Tourner en permanence.")
        parser.add_argument("--interval", type=int, default=5, help="Secondes entre deux passages (defaut 5).")
        parser.add_argument("--batch", type=int, default=50, help="E-mails maximum par passage.")

    def handle(self, *args, **opts):
        backend = getattr(settings, "REAL_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
        self.stdout.write("Facteur demarre (backend : %s)" % backend)
        while True:
            close_old_connections()  # evite "MySQL server has gone away" sur une tache longue
            try:
                sent = self.process_batch(backend, opts["batch"])
                if sent:
                    self.stdout.write("%s - %d e-mail(s) traite(s)" % (timezone.localtime().strftime("%H:%M:%S"), sent))
            except Exception as exc:  # la boucle ne doit jamais mourir
                # serveur e-mail injoignable : les e-mails restent en attente, on reessaie dans 1 minute
                self.stderr.write("Erreur : %s (nouvel essai dans 60 s)" % exc)
                if not opts["loop"]:
                    break
                time.sleep(60)
                continue
            if not opts["loop"]:
                break
            time.sleep(opts["interval"])

    def process_batch(self, backend, batch_size):
        with transaction.atomic():
            ids = list(
                QueuedEmail.objects.select_for_update(skip_locked=True)
                .filter(status=QueuedEmail.STATUS_PENDING)
                .filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=timezone.now()))
                .values_list("id", flat=True)[:batch_size]
            )
        if not ids:
            return 0

        connection = get_connection(backend, fail_silently=False)
        done = 0
        try:
            connection.open()
            for item in QueuedEmail.objects.filter(id__in=ids, status=QueuedEmail.STATUS_PENDING):
                msg = EmailMultiAlternatives(
                    subject=item.subject, body=item.body,
                    from_email=item.from_email or settings.DEFAULT_FROM_EMAIL,
                    to=item.to, cc=item.cc, bcc=item.bcc, reply_to=item.reply_to,
                    headers=item.headers or None, connection=connection,
                )
                if item.html_body:
                    msg.attach_alternative(item.html_body, "text/html")
                item.attempts += 1
                try:
                    msg.send()
                    item.mark_sent()  # efface aussi le contenu des e-mails de compte (codes)
                except Exception as exc:
                    item.last_error = str(exc)[:2000]
                    if item.attempts >= QueuedEmail.MAX_ATTEMPTS:
                        item.status = QueuedEmail.STATUS_FAILED
                    else:
                        # nouvel essai de plus en plus tard : 1, 4, 9, 16 minutes
                        item.next_attempt_at = timezone.now() + timedelta(minutes=item.attempts ** 2)
                item.save(update_fields=["status", "attempts", "last_error", "sent_at", "next_attempt_at",
                                        "body", "html_body", "body_erased"])
                done += 1
        finally:
            try:
                connection.close()
            except Exception:
                pass
        return done
