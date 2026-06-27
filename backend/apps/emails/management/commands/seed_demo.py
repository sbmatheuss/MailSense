"""Management command to seed the database with realistic demo emails.

Generates 150 emails over the last 30 days following the distributions defined
in the MailSense architecture prompt (Agente 5). Safe to run multiple times —
existing demo emails are cleared before seeding.
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.emails.models import ActionLog, Email, EmailClassification

# ── Distribution weights ────────────────────────────────────────────────────

CATEGORY_WEIGHTS = [
    ("support", 30),
    ("billing", 15),
    ("bug", 10),
    ("feature", 10),
    ("sales", 10),
    ("internal", 10),
    ("newsletter", 10),
    ("spam", 5),
]

PRIORITY_WEIGHTS = [
    ("critical", 10),
    ("high", 20),
    ("medium", 40),
    ("low", 30),
]

SENTIMENT_WEIGHTS = [
    ("negative", 25),
    ("neutral", 50),
    ("positive", 20),
    ("urgent", 5),
]

# ── Realistic email corpus ──────────────────────────────────────────────────

SENDERS = [
    ("Carlos Silva", "carlos.silva@empresa.com"),
    ("Ana Costa", "ana.costa@clienteimportante.com"),
    ("Pedro Oliveira", "p.oliveira@startup.io"),
    ("Maria Santos", "maria@consultoria.com.br"),
    ("Tech Digest", "noreply@techdigest.com"),
    ("João Ferreira", "joao.f@parceiro.net"),
    ("Suporte Cliente", "suporte@clientevip.com"),
    ("Financeiro Corp", "financeiro@corp.com.br"),
    ("Lucas Mendes", "lmendes@dev.io"),
    ("Rafaela Lima", "r.lima@agencia.com"),
    ("Sistema", "noreply@sistema.internal"),
    ("DevOps Alert", "alerts@monitoring.io"),
]

TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "support": [
        (
            "Problema ao acessar o painel de controle",
            "Olá, estou com dificuldades para acessar meu painel desde ontem. Já tentei limpar o cache e usar outro navegador, mas o problema persiste. Vocês conseguem me ajudar?",
        ),
        (
            "Erro ao exportar relatório em PDF",
            "Boa tarde. Toda vez que tento exportar o relatório mensal em PDF, o sistema retorna um erro genérico. Isso está atrasando meu trabalho. Preciso de uma solução urgente.",
        ),
        (
            "Integração com ERP não está funcionando",
            "A integração com nosso ERP parou de funcionar após a atualização de sexta-feira. Os dados não estão sincronizando. Já registrei o ticket #4521 mas não tive resposta.",
        ),
        (
            "Dúvida sobre configuração de permissões",
            "Como faço para dar acesso de leitura a um colaborador sem que ele possa editar os dados? Tentei pelo painel de usuários mas não encontrei essa opção.",
        ),
    ],
    "billing": [
        (
            "Cobrança duplicada na fatura de dezembro",
            "Recebi duas cobranças no cartão referentes ao plano Pro de dezembro. O valor cobrado foi R$ 299,00 duas vezes. Precisamos de um estorno urgente.",
        ),
        (
            "Solicitação de nota fiscal - NF #8821",
            "Por favor, precisamos da nota fiscal referente ao pagamento realizado em 05/01. O CNPJ para emissão é 12.345.678/0001-90. Prazo: até sexta-feira.",
        ),
        (
            "Upgrade para plano Enterprise",
            "Gostaríamos de fazer upgrade para o plano Enterprise a partir do próximo ciclo de faturamento. Podem me enviar uma proposta comercial com os valores?",
        ),
        (
            "Cancellation request - account #7743",
            "I would like to cancel my subscription effective immediately. Please confirm the cancellation and ensure I am not charged for the next cycle.",
        ),
    ],
    "bug": [
        (
            "URGENTE: Sistema fora do ar há 2 horas",
            "O sistema principal está completamente inacessível desde as 14h. Já temos 3 clientes enterprise reclamando e perdemos vendas. Precisamos de uma resolução imediata.",
        ),
        (
            "Bug crítico: dados de produção corrompidos",
            "Após o deploy de ontem, alguns registros de usuários aparecem com dados trocados. Identificamos pelo menos 15 contas afetadas. Isso é um problema sério de integridade.",
        ),
        (
            "Loop infinito no processo de checkout",
            "Usuários estão reportando que o checkout fica em loop após inserir os dados do cartão. Taxa de conversão caiu 40% nas últimas 3 horas.",
        ),
        (
            "Notificações por e-mail não estão sendo enviadas",
            "Desde ontem nenhum e-mail de confirmação de pedido está saindo. Os usuários estão confusos achando que as compras não foram processadas.",
        ),
    ],
    "feature": [
        (
            "Sugestão: modo escuro no dashboard",
            "Passamos várias horas por dia usando o dashboard e um modo escuro seria muito bem-vindo para reduzir o cansaço visual. Há previsão de implementação?",
        ),
        (
            "Feature request: exportação para Excel",
            "Seria muito útil poder exportar as listas de dados direto para .xlsx além do CSV atual. Nosso time financeiro usa Excel exclusivamente.",
        ),
        (
            "API pública para integração com Zapier",
            "Temos interesse em criar automações via Zapier. Vocês têm planos de disponibilizar uma API pública ou webhooks para eventos do sistema?",
        ),
        (
            "Filtros avançados na listagem de pedidos",
            "Precisamos filtrar pedidos por múltiplos critérios ao mesmo tempo (data + status + valor). O filtro atual só permite um critério por vez.",
        ),
    ],
    "sales": [
        (
            "Re: Proposta comercial - Plano Enterprise",
            "Boa tarde, analisamos a proposta e gostaríamos de agendar uma reunião para discutir os termos. Temos interesse no plano anual com desconto de 20%.",
        ),
        (
            "Interesse em licença para 50 usuários",
            "Nossa empresa está avaliando sua plataforma para um time de 50 pessoas. Podem nos enviar uma proposta? Precisamos de resposta até o final do mês.",
        ),
        (
            "Parceria estratégica - proposta de co-marketing",
            "Somos uma agência com 200 clientes em comum com o seu ICP. Gostaríamos de propor uma parceria de co-marketing. Quando podemos conversar?",
        ),
        (
            "Trial corporativo - 30 dias",
            "Estamos interessados em um trial corporativo de 30 dias para 10 usuários antes de fechar contrato. É possível? Precisaríamos de acesso esta semana.",
        ),
    ],
    "internal": [
        (
            "Reunião de sprint planning - segunda 9h",
            "Lembrando que o sprint planning da próxima sprint será segunda-feira às 9h na sala de reuniões 3. Por favor confirmem presença.",
        ),
        (
            "Atualização do roadmap Q1 2025",
            "Compartilho o roadmap atualizado para o Q1. Os principais itens são: refatoração do módulo de pagamentos, nova API de integração e melhorias de performance.",
        ),
        (
            "Política de home office - novo regimento",
            "A partir de fevereiro, o home office será de até 3 dias por semana mediante alinhamento com o gestor. O novo regimento completo está no Notion.",
        ),
        (
            "Deploy de emergência - janela amanhã 2h",
            "Precisamos fazer um deploy de emergência amanhã às 2h da manhã para corrigir o bug de segurança identificado hoje. Alguém do time de infra pode acompanhar?",
        ),
    ],
    "newsletter": [
        (
            "Newsletter semanal - Tech Digest #142",
            "As principais notícias da semana em tecnologia: 1. Nova versão do Python 3.13 lançada. 2. OpenAI anuncia GPT-5. 3. GitHub Copilot chega ao terminal.",
        ),
        (
            "Seu resumo mensal de janeiro está pronto",
            "Olá! Seu relatório de atividades de janeiro está disponível. Você processou 1.243 e-mails, respondeu 89% em menos de 24h e sua taxa de resolução foi 94%.",
        ),
        (
            "5 dicas para aumentar sua produtividade em 2025",
            "Newsletter de produtividade: 1. Use blocos de tempo focado. 2. Limite verificações de e-mail a 3x por dia. 3. Automatize tarefas repetitivas com IA.",
        ),
    ],
    "spam": [
        (
            "Você ganhou um prêmio! Clique aqui",
            "Parabéns! Você foi selecionado para receber R$ 5.000 em prêmios. Clique no link abaixo para resgatar seu prêmio antes que expire em 24 horas!",
        ),
        (
            "Oferta imperdível - 90% OFF hoje",
            "Aproveite nossa mega promoção relâmpago! Produtos com até 90% de desconto por tempo limitado. Não perca essa oportunidade única!",
        ),
    ],
    "other": [
        (
            "Confirmação de agendamento",
            "Seu agendamento para 15/01/2025 às 14h foi confirmado. Endereço: Av. Paulista, 1000, São Paulo. Qualquer dúvida, entre em contato.",
        ),
        (
            "Pesquisa de satisfação - 2 minutos",
            "Olá! Gostaríamos de saber sua opinião sobre nosso atendimento. A pesquisa leva apenas 2 minutos. Sua resposta é muito importante para nós.",
        ),
    ],
}

SUGGESTED_REPLIES: dict[str, str] = {
    "support": "Olá! Recebemos sua solicitação e nossa equipe de suporte já está analisando o caso. Em breve entraremos em contato com mais informações. Caso precise de atendimento urgente, acesse nosso chat online.",
    "billing": "Olá! Recebemos sua solicitação financeira e vamos processá-la em até 2 dias úteis. Em caso de estorno, o prazo de crédito depende da operadora do cartão.",
    "bug": "Recebemos seu reporte de bug e nossa equipe técnica já está investigando. Você receberá atualizações sobre o progresso. Pedimos desculpas pelo inconveniente.",
    "feature": "Obrigado pela sugestão! Registramos sua solicitação em nosso backlog de produto. Nossa equipe avaliará a viabilidade e impacto nas próximas sprints.",
    "sales": "Obrigado pelo seu interesse! Um de nossos consultores comerciais entrará em contato em até 1 dia útil para agendar uma demonstração personalizada.",
    "internal": "Confirmado! Estarei presente na reunião.",
    "newsletter": "",
    "spam": "",
    "other": "Recebemos sua mensagem e retornaremos em breve. Obrigado pelo contato.",
}

KEY_TOPICS_MAP: dict[str, list[str]] = {
    "support": ["suporte técnico", "acesso", "erro", "problema"],
    "billing": ["faturamento", "pagamento", "nota fiscal", "cobrança"],
    "bug": ["bug", "erro crítico", "produção", "urgente"],
    "feature": ["feature request", "produto", "melhoria", "integração"],
    "sales": ["venda", "proposta comercial", "enterprise", "contrato"],
    "internal": ["interno", "reunião", "equipe", "processo"],
    "newsletter": ["newsletter", "notícias", "relatório"],
    "spam": ["spam", "promoção"],
    "other": ["geral", "agendamento"],
}


def _weighted_choice(weights: list[tuple[str, int]]) -> str:
    population = [item for item, w in weights for _ in range(w)]
    return random.choice(population)


def _confidence_for_category(category: str, priority: str) -> float:
    base = {"spam": 0.97, "newsletter": 0.95, "internal": 0.90}.get(category, 0.75)
    if priority == "critical":
        base = min(base + 0.05, 0.99)
    return round(random.uniform(max(0.65, base - 0.15), min(0.99, base + 0.05)), 2)


class Command(BaseCommand):
    """Seeds the database with 150 realistic demo emails for a given user.

    Clears existing emails for the user before inserting to ensure a clean state.
    Designed to be idempotent — safe to run multiple times.
    """

    help = "Popula o banco com 150 e-mails fictícios para modo demo"

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, help="ID do usuário (default: usuário demo)")
        parser.add_argument("--count", type=int, default=150, help="Número de e-mails a gerar")
        parser.add_argument("--days", type=int, default=30, help="Período em dias para distribuir os e-mails")

    def handle(self, *args, **options):
        user = self._get_or_create_demo_user(options.get("user_id"))
        count = options["count"]
        days = options["days"]

        # Clear existing data for this user
        deleted_count, _ = Email.objects.filter(user=user).delete()
        if deleted_count:
            self.stdout.write(f"  Removidos {deleted_count} e-mails existentes.")

        self.stdout.write(f"Gerando {count} e-mails para @{user.username}...")

        emails = self._generate_emails(user, count, days)
        Email.objects.bulk_create(emails, ignore_conflicts=True)

        created_emails = list(Email.objects.filter(user=user).order_by("id"))
        classifications = self._generate_classifications(created_emails)
        EmailClassification.objects.bulk_create(classifications)

        action_logs = self._generate_action_logs(created_emails, user)
        ActionLog.objects.bulk_create(action_logs)

        self.stdout.write(self.style.SUCCESS(
            f"✓ {len(created_emails)} e-mails, {len(classifications)} classificações, "
            f"{len(action_logs)} action logs criados para @{user.username}."
        ))

    def _get_or_create_demo_user(self, user_id: int | None) -> User:
        if user_id:
            try:
                return User.objects.get(pk=user_id)
            except User.DoesNotExist:
                raise CommandError(f"Usuário com id={user_id} não encontrado.")
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@mailsense.app", "is_active": True},
        )
        if created:
            user.set_password("demo123")
            user.save()
            self.stdout.write(f"  Usuário demo criado: demo / demo123")
        return user

    def _generate_emails(self, user: User, count: int, days: int) -> list[Email]:
        emails = []
        now = timezone.now()
        for i in range(count):
            category = _weighted_choice(CATEGORY_WEIGHTS)
            templates = TEMPLATES.get(category, TEMPLATES["other"])
            subject, body = random.choice(templates)
            sender_name, sender_email = random.choice(SENDERS)
            received_at = now - timedelta(
                days=random.uniform(0, days),
                hours=random.uniform(0, 23),
                minutes=random.uniform(0, 59),
            )
            # Create thread groups: ~30% of emails are part of a thread
            thread_id = f"thread_{random.randint(1, count // 3)}" if random.random() < 0.3 else f"thread_solo_{i}"
            emails.append(Email(
                user=user,
                gmail_id=f"demo_{user.id}_{i:04d}",
                thread_id=thread_id,
                from_address=sender_email,
                from_name=sender_name,
                to_address=[user.email or "demo@mailsense.app"],
                cc_address=[],
                subject=subject,
                body_text=body,
                body_html=f"<p>{body}</p>",
                received_at=received_at,
                is_read=random.random() > 0.4,
                is_archived=random.random() < 0.15,
                has_attachments=random.random() < 0.1,
                status=Email.Status.CLASSIFIED,
                raw_headers={},
            ))
        return emails

    def _generate_classifications(self, emails: list[Email]) -> list[EmailClassification]:
        classifications = []
        for email in emails:
            category = _weighted_choice(CATEGORY_WEIGHTS)
            priority = _weighted_choice(PRIORITY_WEIGHTS)
            sentiment = _weighted_choice(SENTIMENT_WEIGHTS)

            # Derive sentiment/priority from category for realism
            if category == "bug" and priority == "critical":
                sentiment = "urgent"
            elif category in ("newsletter", "spam"):
                priority = "low"
                sentiment = "neutral"

            confidence = _confidence_for_category(category, priority)
            key_topics = random.sample(KEY_TOPICS_MAP.get(category, ["geral"]), k=min(3, len(KEY_TOPICS_MAP.get(category, ["geral"]))))
            suggested_reply = SUGGESTED_REPLIES.get(category, "")
            urgency_reason = (
                f"E-mail classificado como {priority} em categoria {category}."
                if priority in ("critical", "high")
                else ""
            )

            classifications.append(EmailClassification(
                email=email,
                category=category,
                priority=priority,
                sentiment=sentiment,
                confidence_score=confidence,
                summary=f"{email.subject[:80]}. {email.body_text[:100]}".strip(),
                key_topics=key_topics,
                suggested_reply=suggested_reply,
                urgency_reason=urgency_reason,
                requires_action=priority in ("critical", "high") or category in ("support", "billing", "bug"),
                user_corrected=False,
                processing_time_ms=random.randint(800, 4500),
            ))
        return classifications

    def _generate_action_logs(self, emails: list[Email], user: User) -> list[ActionLog]:
        """Generates realistic action logs for ~40% of emails."""
        logs = []
        for email in random.sample(emails, k=int(len(emails) * 0.4)):
            action = random.choice([
                ActionLog.ActionType.REPLIED,
                ActionLog.ActionType.ARCHIVED,
                ActionLog.ActionType.STARRED,
            ])
            logs.append(ActionLog(
                email=email,
                action=action,
                details={"body": "Resposta enviada via modo demo."} if action == ActionLog.ActionType.REPLIED else {},
                performed_by=user,
            ))
        return logs
