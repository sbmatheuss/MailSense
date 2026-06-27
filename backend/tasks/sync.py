from celery import shared_task


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_gmail_inbox(self, user_id: int) -> None:
    """Sincroniza inbox do Gmail para um usuário. Disparado via API ou beat."""
    raise NotImplementedError


@shared_task
def sync_gmail_inbox_all_users() -> None:
    """Itera sobre usuários com Gmail conectado e despacha sync individual."""
    raise NotImplementedError
