# SEP — Plataforma de Gestão de Estágios em Psicologia

Sistema web em Django para digitalizar e gerenciar a rotina clínica e acadêmica do **Serviço-Escola de Psicologia (SEP)** da **Universidade de Vassouras — Campus Maricá**.

## Sobre o projeto

O SEP substitui o fluxo hoje baseado em papel e planilhas por uma plataforma única que cobre toda a jornada do estágio em Psicologia: triagem e avaliação de risco do paciente, encaminhamento a professores responsáveis, atendimentos e evoluções clínicas, controle de carga horária dos estagiários e emissão de documentos oficiais — com conformidade à LGPD desde o design, por lidar com dados sensíveis de saúde.

## Perfis de acesso

Seis níveis hierárquicos de acesso, para preservar o sigilo clínico e organizar os processos:

| Perfil | Responsabilidade principal |
|---|---|
| **Superadmin** | Infraestrutura, logs de segurança e manutenção — sem interferir na rotina clínica |
| **Supervisor Geral** | Cadastra professores e alunos, analisa e encaminha as fichas de triagem, dá feedback |
| **Professor Responsável** | Orienta os alunos da sua abordagem teórica; acesso restrito aos prontuários dos seus orientandos |
| **Administrativo** | Agenda de atendimentos e salas; emite declarações e atestados |
| **Aluno (Estagiário)** | Realiza triagem e atendimento; acesso a um caso é revogado assim que ele é encaminhado ou fechado |
| **Paciente** | Entidade central do sistema — dados protegidos e rastreados em toda a jornada |

## Segurança e conformidade

- Conformidade com a **LGPD** no tratamento de dados de saúde
- Criptografia de dados sensíveis (dados pessoais, queixas, prontuários) no banco
- Assinatura digital de documentos com validade jurídica (integração **DocuSeal**)
- Log de auditoria para qualquer impressão — quem, o quê, quando, IP e localização aproximada — com mascaramento automático de dados sensíveis no material impresso

## Funcionalidades

- Controle automático de carga horária dos estagiários (atendimento, triagem, prontuários)
- Agendamento de atendimentos e salas, com registro de presenças, faltas e cancelamentos
- Dashboard com estatísticas de atendimentos, fluxo de pacientes e desempenho dos alunos
- Ficha de triagem digital ampliada (dados sociodemográficos, nome social, histórico de tratamentos, rede de suporte)
- **IARV-SEP** — instrumento de avaliação de risco e vulnerabilidade psicossocial, com cálculo automático de índice de prioridade, em versões para adultos, adolescentes (13–17) e crianças (6–12)

## Stack

- **Backend:** Django
- **Qualidade e segurança:** pytest + pytest-django + coverage, Bandit (análise estática de segurança), Ruff (lint), Radon (métricas de complexidade)

## Como executar (ambiente de desenvolvimento)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Fluxo de contribuição

- `main` é protegida — merge apenas pelo mantenedor do projeto
- Colaboradores abrem PR para `dev`; merge condicionado à aprovação do mantenedor

## Status

Em desenvolvimento ativo.
