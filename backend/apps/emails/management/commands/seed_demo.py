"""Management command to seed the database with realistic demo emails.

Generates 150 emails over the last 30 days with coherent category/classification
pairs — the classification category always matches the email's template category.
Safe to run multiple times (clears existing data first).
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

# Per-category priority distributions: realistic skews
PRIORITY_BY_CATEGORY: dict[str, list[tuple[str, int]]] = {
    "support":    [("critical", 10), ("high", 30), ("medium", 45), ("low", 15)],
    "billing":    [("critical", 5),  ("high", 35), ("medium", 45), ("low", 15)],
    "bug":        [("critical", 25), ("high", 40), ("medium", 30), ("low", 5)],
    "feature":    [("critical", 2),  ("high", 10), ("medium", 50), ("low", 38)],
    "sales":      [("critical", 5),  ("high", 35), ("medium", 45), ("low", 15)],
    "internal":   [("critical", 3),  ("high", 12), ("medium", 45), ("low", 40)],
    "newsletter": [("critical", 0),  ("high", 0),  ("medium", 15), ("low", 85)],
    "spam":       [("critical", 0),  ("high", 0),  ("medium", 5),  ("low", 95)],
    "other":      [("critical", 2),  ("high", 15), ("medium", 45), ("low", 38)],
}

SENTIMENT_BY_CATEGORY: dict[str, list[tuple[str, int]]] = {
    "support":    [("negative", 40), ("neutral", 30), ("positive", 10), ("urgent", 20)],
    "billing":    [("negative", 30), ("neutral", 40), ("positive", 15), ("urgent", 15)],
    "bug":        [("negative", 35), ("neutral", 20), ("positive", 5),  ("urgent", 40)],
    "feature":    [("negative", 5),  ("neutral", 40), ("positive", 50), ("urgent", 5)],
    "sales":      [("negative", 5),  ("neutral", 25), ("positive", 65), ("urgent", 5)],
    "internal":   [("negative", 10), ("neutral", 60), ("positive", 25), ("urgent", 5)],
    "newsletter": [("negative", 5),  ("neutral", 55), ("positive", 35), ("urgent", 5)],
    "spam":       [("negative", 10), ("neutral", 70), ("positive", 20), ("urgent", 0)],
    "other":      [("negative", 15), ("neutral", 55), ("positive", 25), ("urgent", 5)],
}

# ── Senders ─────────────────────────────────────────────────────────────────

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
    ("Beatriz Rocha", "b.rocha@enterprise.com"),
    ("Thiago Nunes", "thiago@saas.co"),
    ("Carla Pimentel", "cpimentel@bigcorp.com.br"),
    ("Felipe Azevedo", "f.azevedo@tech.io"),
    ("Isabela Martins", "isabela.m@agency.com"),
    ("Roberto Dias", "roberto.dias@holding.com.br"),
]

# ── Email templates (subject, body, summary, urgency_hint) ──────────────────
# Each entry: (subject, body, one_line_summary, urgency_hint_if_high_priority)

TEMPLATES: dict[str, list[tuple[str, str, str, str]]] = {
    "support": [
        (
            "Problema ao acessar o painel de controle",
            "Olá, estou com dificuldades para acessar meu painel desde ontem. Já tentei limpar o cache e usar outro navegador, mas o problema persiste. Vocês conseguem me ajudar? Isso está impactando meu trabalho diário.",
            "Usuário reporta impossibilidade de acessar o painel de controle há mais de 24 horas.",
            "Acesso bloqueado por mais de 24h impacta produtividade diária do cliente.",
        ),
        (
            "Erro ao exportar relatório em PDF",
            "Boa tarde. Toda vez que tento exportar o relatório mensal em PDF, o sistema retorna um erro genérico. Isso está atrasando meu trabalho. Preciso de uma solução urgente para apresentação amanhã.",
            "Exportação de PDF falha com erro genérico, bloqueando entrega de relatório.",
            "Prazo de apresentação amanhã torna este problema urgente para o cliente.",
        ),
        (
            "Integração com ERP não está funcionando",
            "A integração com nosso ERP parou de funcionar após a atualização de sexta-feira. Os dados não estão sincronizando entre os sistemas. Já registrei o ticket #4521 mas não tive resposta em 48 horas.",
            "Integração ERP quebrou após atualização; dados não sincronizam há 48 horas.",
            "Ausência de sincronização de dados com ERP afeta operações do cliente.",
        ),
        (
            "Dúvida sobre configuração de permissões de usuário",
            "Como faço para dar acesso de leitura a um colaborador sem que ele possa editar os dados? Tentei pelo painel de usuários mas não encontrei essa opção específica.",
            "Cliente busca orientação para configurar permissões de leitura para colaboradores.",
            "",
        ),
        (
            "Aplicativo mobile trava ao abrir notificações",
            "O app para iOS está travando toda vez que o usuário clica em uma notificação push. O problema começou após atualização para a versão 3.2.1. Afeta todos os usuários do meu time (12 pessoas).",
            "App iOS trava ao abrir notificações push desde atualização 3.2.1, afetando 12 usuários.",
            "Bug afeta toda equipe do cliente — 12 usuários impedidos de usar notificações.",
        ),
        (
            "Senha de acesso não aceita caracteres especiais",
            "Estou tentando criar uma senha com o símbolo @ e o sistema não aceita. A mensagem de erro é genérica. Minha política de segurança exige símbolos especiais.",
            "Sistema rejeita senha com caracteres especiais, violando política de segurança do cliente.",
            "",
        ),
        (
            "Dashboard não carrega dados históricos",
            "Os gráficos de dados históricos (mais de 90 dias) ficam em loading infinito. Dados recentes carregam normalmente. Preciso dos históricos para análise de tendências.",
            "Gráficos de histórico acima de 90 dias não carregam; dados recentes funcionam.",
            "",
        ),
        (
            "Erro 403 ao acessar relatórios de equipe",
            "Desde ontem recebo erro 403 ao tentar acessar os relatórios da minha equipe. Minha conta é admin e nunca tive esse problema antes. Outros admins também estão com o mesmo problema.",
            "Erro 403 impede admins de acessar relatórios de equipe desde ontem.",
            "Múltiplos admins afetados — possível problema de permissões em produção.",
        ),
    ],
    "billing": [
        (
            "Cobrança duplicada na fatura de dezembro",
            "Recebi duas cobranças no cartão referentes ao plano Pro de dezembro. O valor cobrado foi R$ 299,00 duas vezes. Precisamos de um estorno urgente. O CNPJ da empresa é 12.345.678/0001-90.",
            "Cliente reporta cobrança duplicada de R$ 299 no cartão — estorno solicitado.",
            "Cobrança indevida de R$ 299 exige estorno imediato para evitar chargeback.",
        ),
        (
            "Solicitação de nota fiscal - Pagamento #8821",
            "Por favor, precisamos da nota fiscal referente ao pagamento realizado em 05/01. O CNPJ para emissão é 12.345.678/0001-90. Prazo contábil até sexta-feira — é urgente.",
            "Cliente solicita nota fiscal de pagamento #8821 com prazo contábil na sexta.",
            "Prazo contábil iminente — nota fiscal deve ser emitida até sexta-feira.",
        ),
        (
            "Solicitação de upgrade para plano Enterprise",
            "Gostaríamos de fazer upgrade para o plano Enterprise a partir do próximo ciclo de faturamento. Podem me enviar uma proposta comercial com desconto para pagamento anual?",
            "Cliente solicita upgrade para Enterprise com interesse em desconto anual.",
            "",
        ),
        (
            "Cancelamento imediato de assinatura",
            "Solicito o cancelamento da minha assinatura com efeito imediato. Por favor confirme o cancelamento e garanta que não serei cobrado no próximo ciclo. Número da conta: #7743.",
            "Cliente solicita cancelamento imediato da conta #7743.",
            "Risco de churn — cliente solicitando cancelamento imediato da assinatura.",
        ),
        (
            "Discrepância no valor cobrado - Plano Business",
            "Fui cobrado R$ 899,00 em vez de R$ 799,00 conforme contrato assinado. Envio em anexo o contrato com o valor acordado. Por favor corrija e emita nova fatura.",
            "Valor cobrado R$100 acima do contratado — cliente solicita correção e nova fatura.",
            "Divergência contratual de R$ 100 — cliente com documentação do valor correto.",
        ),
        (
            "Pedido de reembolso - Produto não entregue",
            "Fiz o pagamento em 10/01 no valor de R$ 1.200,00 mas o acesso ao produto adicional contratado não foi liberado. Solicito reembolso ou liberação imediata do acesso.",
            "Pagamento de R$ 1.200 realizado mas acesso ao produto não foi liberado.",
            "Cliente pagou R$ 1.200 sem receber o produto — risco de disputa no cartão.",
        ),
        (
            "Atualização de dados de cobrança",
            "Preciso atualizar o cartão de crédito cadastrado para cobrança. O cartão atual vence no final do mês e não quero interrupção no serviço. Como faço essa atualização?",
            "Cliente precisa atualizar cartão de crédito antes do vencimento.",
            "",
        ),
    ],
    "bug": [
        (
            "URGENTE: Sistema fora do ar há 2 horas",
            "O sistema principal está completamente inacessível desde as 14h. Já temos 3 clientes enterprise reclamando e perdemos vendas. Status page não reflete o problema real. Precisamos de uma resolução imediata.",
            "Indisponibilidade total do sistema por 2h+ com impacto direto em clientes enterprise.",
            "Sistema principal offline por mais de 2 horas — clientes enterprise afetados.",
        ),
        (
            "Bug crítico: dados de usuários aparecem trocados",
            "Após o deploy de ontem, alguns registros de usuários aparecem com dados trocados entre contas. Identificamos pelo menos 15 contas afetadas. Isso é um problema grave de integridade e privacidade de dados.",
            "Deploy causou mistura de dados entre 15+ contas — problema de privacidade.",
            "Violação de privacidade: dados de usuários expostos entre contas distintas.",
        ),
        (
            "Loop infinito no processo de checkout",
            "Usuários estão reportando que o checkout fica em loop após inserir dados do cartão. Taxa de conversão caiu 40% nas últimas 3 horas. Reproduzido em Chrome e Firefox com diferentes cartões.",
            "Checkout em loop infinito após entrada de dados — conversão caiu 40% em 3h.",
            "Falha de checkout impactando receita diretamente — 40% de queda em conversões.",
        ),
        (
            "E-mails de confirmação não estão sendo enviados",
            "Desde ontem nenhum e-mail de confirmação de pedido está saindo. Os usuários estão abrindo tickets de suporte achando que as compras não foram processadas. São mais de 200 pedidos sem confirmação.",
            "200+ pedidos processados sem e-mail de confirmação — usuários abrindo tickets.",
            "Falha no envio de confirmações gera confusão massiva e sobrecarga no suporte.",
        ),
        (
            "API retornando 500 para todos os endpoints /v2/",
            "Todos os endpoints da versão /v2/ estão retornando HTTP 500 desde as 16h. A versão /v1/ funciona normalmente. Temos integrações de clientes que dependem exclusivamente do /v2/.",
            "Todos os endpoints /v2/ da API retornam 500 desde as 16h.",
            "API v2 completamente quebrada — integrações de clientes falhando.",
        ),
        (
            "Relatórios gerando com dados de data incorretos",
            "Os relatórios gerados nos últimos 2 dias estão com datas erradas — mostram dados de novembro em vez de janeiro. O problema parece ser de timezone. Afeta todos os relatórios exportados.",
            "Relatórios exibindo datas erradas (novembro em vez de janeiro) — possível bug de timezone.",
            "",
        ),
        (
            "Performance crítica: queries levando 30+ segundos",
            "As queries de listagem de pedidos estão levando entre 30-60 segundos para carregar. Antes eram instantâneas. O problema começou após a migration de ontem. CPU do banco está em 95%.",
            "Degradação crítica de performance — queries de listagem levando 30-60s após migration.",
            "CPU do banco em 95% — risco de indisponibilidade total iminente.",
        ),
        (
            "Upload de arquivos falhando silenciosamente",
            "Os uploads de arquivos PDF acima de 5MB falham sem mostrar mensagem de erro. O arquivo parece subir (barra de progresso completa) mas não aparece no sistema. Verificamos S3 e o arquivo não está lá.",
            "Upload de PDFs acima de 5MB falha silenciosamente — arquivo não salvo no S3.",
            "",
        ),
    ],
    "feature": [
        (
            "Sugestão: modo escuro no dashboard",
            "Passamos várias horas por dia usando o dashboard e um modo escuro seria muito bem-vindo para reduzir o cansaço visual. Nosso time inteiro pediria isso. Há previsão de implementação?",
            "Equipe solicita modo escuro no dashboard para reduzir cansaço visual.",
            "",
        ),
        (
            "Feature request: exportação para Excel (.xlsx)",
            "Seria muito útil poder exportar as listas de dados direto para .xlsx além do CSV atual. Nosso time financeiro usa Excel exclusivamente e converter de CSV gera erros de formatação.",
            "Solicitação de exportação nativa para Excel — equipe financeira usa exclusivamente.",
            "",
        ),
        (
            "API pública para integração com Zapier/Make",
            "Temos interesse em criar automações via Zapier e Make. Vocês têm planos de disponibilizar uma API pública com webhooks? Isso desbloquearia integrações com 20+ ferramentas que usamos.",
            "Cliente solicita API pública e webhooks para integração com ferramentas de automação.",
            "",
        ),
        (
            "Filtros avançados na listagem de pedidos",
            "Precisamos filtrar pedidos por múltiplos critérios simultaneamente (data + status + valor + cliente). O filtro atual só permite um critério por vez, tornando a análise muito lenta.",
            "Solicitação de filtros combinados na listagem — filtro atual suporta apenas um critério.",
            "",
        ),
        (
            "Relatórios customizados por período e equipe",
            "Gostaríamos de criar relatórios customizados selecionando métricas específicas, período e filtrando por equipe ou usuário. Os relatórios atuais são fixos e não atendem nossas necessidades de análise.",
            "Solicitação de builder de relatórios customizados com filtros por equipe e período.",
            "",
        ),
        (
            "Autenticação SSO com Google Workspace",
            "Nossa empresa usa Google Workspace e gostaríamos de fazer login único via SSO. Hoje todos os funcionários precisam criar senhas separadas, o que é um problema de segurança e UX.",
            "Solicitação de SSO com Google Workspace — empresa usa GSuite exclusivamente.",
            "",
        ),
        (
            "Notificações via Slack para eventos críticos",
            "Seria muito útil receber notificações no Slack quando houver novos tickets críticos ou SLAs próximos do vencimento. Passamos mais tempo no Slack do que em e-mail.",
            "Solicitação de integração com Slack para alertas de tickets críticos e SLA.",
            "",
        ),
    ],
    "sales": [
        (
            "Re: Proposta comercial - Plano Enterprise",
            "Boa tarde, analisamos a proposta enviada na semana passada e gostaríamos de agendar uma reunião para discutir os termos. Temos interesse no plano anual com desconto. Quando podemos conversar?",
            "Prospect interessado na proposta Enterprise quer reunião para discutir desconto anual.",
            "Oportunidade quente — prospect pedindo reunião para fechar Enterprise anual.",
        ),
        (
            "Interesse em licença corporativa para 50 usuários",
            "Nossa empresa está avaliando sua plataforma para todo o time de 50 pessoas. Precisamos de proposta com valores, SLA garantido e suporte dedicado. Prazo de decisão: final do mês.",
            "Empresa avaliando licença para 50 usuários com prazo de decisão no final do mês.",
            "Alta probabilidade de fechamento — prazo de decisão em dias, 50 licenças.",
        ),
        (
            "Proposta de parceria estratégica - co-marketing",
            "Somos uma agência com 200 clientes no mesmo segmento que vocês atendem. Gostaríamos de propor uma parceria de co-marketing e indicação. Quando podemos conversar sobre isso?",
            "Agência com 200 clientes propõe parceria de co-marketing e indicação mútua.",
            "",
        ),
        (
            "Solicitação de trial corporativo - 30 dias",
            "Estamos interessados em um trial corporativo de 30 dias para 10 usuários antes de fechar contrato anual. O valor estimado do contrato seria R$ 48.000/ano. Podem agilizar o setup?",
            "Trial de 30 dias solicitado antes de contrato anual de R$ 48k.",
            "Oportunidade de R$ 48k anual — trial como pré-requisito para fechamento.",
        ),
        (
            "Renovação de contrato - prazo vencendo em 15 dias",
            "O contrato atual vence em 15 dias e gostaríamos de renovar por mais 2 anos. Pedimos análise de upgrade para o plano acima com os benefícios para clientes antigos.",
            "Renovação de contrato em 15 dias com interesse em upgrade de plano.",
            "Risco de churn — contrato vence em 15 dias sem confirmação de renovação.",
        ),
        (
            "Inbound: conheci o produto no evento SaaStr",
            "Conheci o MailSense na palestra do SaaStr e fiquei muito interessado. Estamos buscando uma solução para nosso time de CS de 25 pessoas. Podem me enviar mais informações e agendar um demo?",
            "Lead inbound do SaaStr interessado em solução para time de CS de 25 pessoas.",
            "",
        ),
    ],
    "internal": [
        (
            "Sprint planning — segunda-feira 9h",
            "Lembrando que o sprint planning da próxima sprint será segunda-feira às 9h na sala de reuniões 3. Pauta: revisão do backlog, capacidade do time e metas da sprint. Por favor confirmem presença.",
            "Convocação para sprint planning na segunda às 9h — confirmação solicitada.",
            "",
        ),
        (
            "Atualização do roadmap Q1 2025",
            "Compartilho o roadmap atualizado para o Q1. Os principais itens são: refatoração do módulo de pagamentos (Jan), nova API de integração (Fev) e melhorias de performance (Mar). Feedback até sexta.",
            "Roadmap Q1 compartilhado: pagamentos em Jan, API em Fev, performance em Mar.",
            "",
        ),
        (
            "Nova política de home office - vigência imediata",
            "A partir de fevereiro o home office será de até 3 dias por semana mediante alinhamento com o gestor direto. O regimento completo foi publicado no Notion. Dúvidas falar com RH.",
            "Nova política de home office (máx 3 dias/semana) entra em vigor em fevereiro.",
            "",
        ),
        (
            "Deploy de emergência — janela amanhã às 2h",
            "Precisamos fazer um deploy de emergência amanhã às 2h para corrigir o bug de segurança identificado hoje. Alguém do time de infra precisa estar de plantão. Estimativa: 30 min de downtime.",
            "Deploy emergencial amanhã às 2h para correção de bug de segurança — infra de plantão.",
            "Janela de deploy de emergência requer equipe de plantão — downtime planejado de 30min.",
        ),
        (
            "Feedback da avaliação de performance — Q4",
            "As avaliações de performance do Q4 foram concluídas. Por favor verifiquem os feedbacks registrados no sistema de RH até dia 20. Alocações de bônus serão comunicadas até 31/01.",
            "Avaliações de performance Q4 disponíveis — bônus comunicados até 31/01.",
            "",
        ),
        (
            "All-hands meeting — resultado do Q4",
            "Confiram o convite para o all-hands de apresentação dos resultados do Q4 na próxima quinta às 15h. Presença de todos os times é obrigatória. Link do Zoom será enviado na manhã do evento.",
            "All-hands de resultados Q4 na quinta às 15h — presença obrigatória.",
            "",
        ),
        (
            "Incidente de segurança — ação necessária",
            "Identificamos acesso suspeito em 3 contas de colaboradores. É necessário que TODOS redefinam suas senhas até o final do dia de hoje. Por favor avisem suas equipes imediatamente.",
            "Incidente de segurança exige redefinição de senhas de todos os colaboradores hoje.",
            "Incidente de segurança ativo — redefinição de senhas requerida com urgência.",
        ),
    ],
    "newsletter": [
        (
            "Newsletter semanal — Tech Digest #142",
            "As principais notícias da semana: 1. Python 3.13 lançado com melhorias de GIL. 2. OpenAI anuncia GPT-5 para Q2. 3. GitHub Copilot chega ao terminal. 4. Rust supera C em projetos Linux.",
            "Newsletter semanal com novidades: Python 3.13, GPT-5, GitHub Copilot no terminal.",
            "",
        ),
        (
            "Seu resumo de atividades de janeiro está pronto",
            "Olá! Seu relatório de janeiro: você processou 1.243 e-mails, respondeu 89% em menos de 24h e sua taxa de resolução foi 94%. Seu tempo médio de resposta melhorou 12% vs dezembro.",
            "Relatório mensal: 1.243 emails processados, 89% respondidos em 24h, 94% resolvidos.",
            "",
        ),
        (
            "5 tendências de produto para 2025",
            "Nossa análise das principais tendências: 1. AI nativa em todas as ferramentas SaaS. 2. Consolidação de stacks para plataformas all-in-one. 3. Privacidade por design. 4. Automação de workflows. 5. Analytics preditivo.",
            "Newsletter analisa 5 tendências de produto para 2025: AI, consolidação e privacidade.",
            "",
        ),
        (
            "Novidades da plataforma — Release notes v2.8",
            "Confira as principais novidades da versão 2.8: novo dashboard de analytics, exportação para Excel, integração com Zapier e 47 correções de bugs. Changelog completo disponível na documentação.",
            "Release notes v2.8: novo dashboard, exportação Excel, integração Zapier, 47 bug fixes.",
            "",
        ),
        (
            "Convite: webinar 'IA em atendimento ao cliente'",
            "Junte-se a nós na quinta-feira às 14h para o webinar gratuito sobre como usar IA para transformar o atendimento ao cliente. Inscrições abertas — vagas limitadas.",
            "Convite para webinar gratuito sobre IA em atendimento ao cliente na quinta às 14h.",
            "",
        ),
    ],
    "spam": [
        (
            "Você ganhou um prêmio! Resgate agora",
            "Parabéns! Você foi selecionado para receber R$ 5.000 em prêmios. Clique no link abaixo para resgatar seu prêmio antes que expire em 24 horas! Oferta exclusiva não transferível.",
            "Possível spam: promessa de prêmio de R$ 5.000 com link suspeito.",
            "",
        ),
        (
            "Oferta relâmpago — 90% OFF hoje",
            "Mega promoção relâmpago! Produtos com até 90% de desconto por tempo absolutamente limitado. Oferta válida somente hoje. Não perca essa oportunidade única na vida!",
            "Spam: oferta de desconto de 90% com urgência artificial.",
            "",
        ),
        (
            "Sua conta será suspensa — ação necessária",
            "Detectamos atividade suspeita em sua conta. Para evitar suspensão permanente, acesse o link abaixo e confirme seus dados em até 2 horas. Ignore este e-mail por sua conta e risco.",
            "Phishing: ameaça falsa de suspensão de conta para obter dados.",
            "",
        ),
    ],
    "other": [
        (
            "Confirmação de agendamento — 15/01 às 14h",
            "Seu agendamento para 15/01/2025 às 14h foi confirmado. Local: Av. Paulista, 1000, sala 502, São Paulo. Leve documento com foto. Qualquer dúvida, responda este e-mail.",
            "Confirmação de agendamento para 15/01 às 14h na Av. Paulista.",
            "",
        ),
        (
            "Pesquisa de satisfação — 2 minutos",
            "Olá! Gostaríamos de saber sua opinião sobre nosso atendimento recente. A pesquisa leva apenas 2 minutos e nos ajuda a melhorar continuamente. Sua resposta é muito importante!",
            "Pesquisa de satisfação sobre atendimento recente — 2 minutos.",
            "",
        ),
        (
            "Documento para assinatura digital",
            "Segue documento para assinatura digital até sexta-feira. Por favor acesse o link de assinatura enviado separadamente. Qualquer dúvida sobre o conteúdo, entre em contato.",
            "Documento aguardando assinatura digital — prazo até sexta-feira.",
            "",
        ),
    ],
}

SUGGESTED_REPLIES: dict[str, str] = {
    "support": "Olá! Recebemos sua solicitação e nossa equipe de suporte já está analisando o caso. Em breve entraremos em contato com mais informações. Caso precise de atendimento urgente, acesse nosso chat online.",
    "billing": "Olá! Recebemos sua solicitação financeira e vamos processá-la em até 2 dias úteis. Para estornos, o prazo de crédito no cartão é de 5 a 10 dias úteis dependendo da operadora.",
    "bug": "Recebemos seu reporte e nossa equipe técnica já está investigando com prioridade. Você receberá atualizações de status a cada hora. Pedimos desculpas pelo inconveniente causado.",
    "feature": "Obrigado pela sugestão! Registramos sua solicitação em nosso backlog de produto. Nossa equipe de produto avaliará a viabilidade e impacto nas próximas sprints de planejamento.",
    "sales": "Obrigado pelo seu interesse! Um de nossos consultores comerciais entrará em contato em até 1 dia útil para agendar uma demonstração personalizada e discutir sua proposta.",
    "internal": "Confirmado! Estarei presente.",
    "newsletter": "",
    "spam": "",
    "other": "Recebemos sua mensagem e retornaremos em breve. Obrigado pelo contato.",
}

KEY_TOPICS_MAP: dict[str, list[str]] = {
    "support":    ["suporte técnico", "acesso", "erro de sistema", "integração", "configuração", "bug de UI"],
    "billing":    ["faturamento", "pagamento", "nota fiscal", "cobrança indevida", "cancelamento", "upgrade"],
    "bug":        ["bug crítico", "produção", "indisponibilidade", "erro 500", "performance", "dados corrompidos"],
    "feature":    ["feature request", "melhoria de produto", "integração", "API", "UX", "automação"],
    "sales":      ["proposta comercial", "enterprise", "contrato", "demo", "trial", "parceria"],
    "internal":   ["reunião", "processo interno", "segurança", "deploy", "roadmap", "RH"],
    "newsletter": ["newsletter", "novidades", "tendências", "relatório", "webinar"],
    "spam":       ["spam", "phishing", "promoção suspeita"],
    "other":      ["agendamento", "documento", "pesquisa", "geral"],
}


def _weighted_choice(weights: list[tuple[str, int]]) -> str:
    population = [item for item, w in weights for _ in range(w)]
    return random.choice(population)


def _confidence_for(category: str, priority: str) -> float:
    base = {
        "spam": 0.97,
        "newsletter": 0.95,
        "internal": 0.90,
        "bug": 0.88,
        "billing": 0.85,
    }.get(category, 0.75)
    if priority == "critical":
        base = min(base + 0.05, 0.99)
    elif priority == "low":
        base = max(base - 0.05, 0.60)
    return round(random.uniform(max(0.60, base - 0.12), min(0.99, base + 0.05)), 2)


class Command(BaseCommand):
    """Seeds the database with realistic demo emails.

    Uses coherent category/classification pairs — every email's classification
    matches its template category, ensuring the demo data tells a consistent story.
    Safe to run multiple times (clears existing data first).
    """

    help = "Popula o banco com e-mails fictícios realistas para modo demo"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id", dest="user_id", type=int,
            help="ID do usuário alvo (default: cria/usa usuário 'demo')",
        )
        parser.add_argument("--count", type=int, default=150, help="Número de e-mails")
        parser.add_argument("--days", type=int, default=30, help="Janela de tempo em dias")

    def handle(self, *args, **options):
        user = self._resolve_user(options.get("user_id"))
        count = options["count"]
        days = options["days"]

        deleted, _ = Email.objects.filter(user=user).delete()
        if deleted:
            self.stdout.write(f"  Removidos {deleted} e-mails existentes.")

        self.stdout.write(f"Gerando {count} e-mails para @{user.username}...")

        email_category_pairs = self._build_email_category_pairs(user, count, days)
        emails_to_create = [pair[0] for pair in email_category_pairs]
        Email.objects.bulk_create(emails_to_create, ignore_conflicts=True)

        created_emails = list(Email.objects.filter(user=user).order_by("id"))
        # Pair created emails with their intended categories by position
        categories = [pair[1] for pair in email_category_pairs]

        classifications = self._build_classifications(created_emails, categories)
        EmailClassification.objects.bulk_create(classifications)

        action_logs = self._build_action_logs(created_emails, user)
        ActionLog.objects.bulk_create(action_logs)

        self.stdout.write(self.style.SUCCESS(
            f"✓ {len(created_emails)} e-mails, {len(classifications)} classificações, "
            f"{len(action_logs)} action logs — @{user.username}"
        ))

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_user(self, user_id: int | None) -> User:
        if user_id:
            try:
                return User.objects.get(pk=user_id)
            except User.DoesNotExist:
                raise CommandError(f"Usuário id={user_id} não encontrado.")

        from apps.accounts.models import UserProfile

        user, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@mailsense.app", "is_active": True},
        )
        if created:
            user.set_password("demo123")
            user.save()
            self.stdout.write("  Usuário demo criado: demo / demo123")

        # Ensure a UserProfile exists so Settings page works without Gmail auth
        UserProfile.objects.get_or_create(user=user)
        return user

    def _build_email_category_pairs(
        self, user: User, count: int, days: int
    ) -> list[tuple[Email, str]]:
        pairs: list[tuple[Email, str]] = []
        now = timezone.now()

        for i in range(count):
            category = _weighted_choice(CATEGORY_WEIGHTS)
            template_list = TEMPLATES.get(category, TEMPLATES["other"])
            subject, body, _summary, _urgency = random.choice(template_list)
            sender_name, sender_email = random.choice(SENDERS)

            received_at = now - timedelta(
                days=random.uniform(0, days),
                hours=random.uniform(0, 23),
                minutes=random.uniform(0, 59),
            )
            # ~30% of emails share threads (realistic conversation grouping)
            if random.random() < 0.3:
                thread_id = f"thread_{random.randint(1, max(1, count // 5))}"
            else:
                thread_id = f"thread_solo_{user.id}_{i}"

            email = Email(
                user=user,
                gmail_id=f"demo_{user.id}_{i:04d}",
                thread_id=thread_id,
                from_address=sender_email,
                from_name=sender_name,
                to_address=[user.email or "demo@mailsense.app"],
                cc_address=[],
                subject=subject,
                body_text=body,
                body_html=f"<p>{body.replace(chr(10), '</p><p>')}</p>",
                received_at=received_at,
                is_read=random.random() > 0.35,
                is_archived=random.random() < 0.12,
                has_attachments=random.random() < 0.08,
                status=Email.Status.CLASSIFIED,
                raw_headers={},
            )
            pairs.append((email, category))
        return pairs

    def _build_classifications(
        self, emails: list[Email], categories: list[str]
    ) -> list[EmailClassification]:
        classifications: list[EmailClassification] = []

        for email, category in zip(emails, categories):
            priority_weights = PRIORITY_BY_CATEGORY.get(category, PRIORITY_BY_CATEGORY["other"])
            # Filter out zero-weight items before picking
            priority_weights = [(p, w) for p, w in priority_weights if w > 0]
            priority = _weighted_choice(priority_weights)

            sentiment_weights = SENTIMENT_BY_CATEGORY.get(category, SENTIMENT_BY_CATEGORY["other"])
            sentiment = _weighted_choice(sentiment_weights)

            # Override sentiment for coherence
            if category == "bug" and priority == "critical":
                sentiment = "urgent"
            elif category in ("newsletter", "spam"):
                sentiment = random.choice(["neutral", "neutral", "positive"])

            confidence = _confidence_for(category, priority)

            topic_pool = KEY_TOPICS_MAP.get(category, ["geral"])
            key_topics = random.sample(topic_pool, k=min(random.randint(2, 4), len(topic_pool)))

            # Find the matching template to get summary/urgency_hint
            template_match = next(
                (t for t in TEMPLATES.get(category, []) if t[0] == email.subject),
                None,
            )
            if template_match:
                _, _, summary, urgency_hint = template_match
            else:
                summary = f"{email.subject}. {email.body_text[:100]}".strip()
                urgency_hint = ""

            urgency_reason = urgency_hint if priority in ("critical", "high") else ""
            requires_action = (
                priority in ("critical", "high")
                or category in ("support", "billing", "bug", "sales")
            )

            classifications.append(EmailClassification(
                email=email,
                category=category,
                priority=priority,
                sentiment=sentiment,
                confidence_score=confidence,
                summary=summary,
                key_topics=key_topics,
                suggested_reply=SUGGESTED_REPLIES.get(category, ""),
                urgency_reason=urgency_reason,
                requires_action=requires_action,
                user_corrected=False,
                original_category="",
                original_priority="",
                original_sentiment="",
                processing_time_ms=random.randint(600, 3800),
            ))
        return classifications

    def _build_action_logs(self, emails: list[Email], user: User) -> list[ActionLog]:
        logs: list[ActionLog] = []
        sample_size = int(len(emails) * 0.38)
        for email in random.sample(emails, k=sample_size):
            action = random.choice([
                ActionLog.ActionType.REPLIED,
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
