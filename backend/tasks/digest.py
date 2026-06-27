from celery import shared_task


@shared_task
def generate_daily_digest(user_id: int) -> None:
    """Gera resumo diário: e-mails recebidos, urgentes, pendentes de ação."""
    raise NotImplementedError


@shared_task
def generate_daily_digest_all() -> None:
    """Dispara digest para todos os usuários ativos."""
    raise NotImplementedError
