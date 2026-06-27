from celery import shared_task


@shared_task(bind=True, max_retries=2)
def classify_email_task(self, email_id: int) -> None:
    """Classifica um e-mail individual via LLMService."""
    raise NotImplementedError


@shared_task
def classify_pending_batch() -> None:
    """Pega até 5 e-mails PENDING e classifica em batch."""
    raise NotImplementedError
