# Rotas da área do Paciente

Especificação das rotas do Paciente: o que cada tela mostra, por onde se chega
nela e como está implementada. Segue o mesmo formato de `rotas-aluno.md` e
`rotas-coordenador.md`, e detalha a linha do Paciente de
`mapa_rota_permisao.md`.

A área tem uma diferença de fundo em relação às outras: o Paciente é o dono dos
dados, não um operador do serviço. Nenhuma tela dele escreve em prontuário,
triagem ou agenda — a única escrita é pedir um horário. Por isso o recorte de
visibilidade é mais estreito que em qualquer outra área, e as telas de leitura
mostram o resultado do trabalho da equipe, não o trabalho em andamento.

---

## 1. Mapa das rotas

Prefixo `/patient/`, `app_name = "patient"`, arquivo `patient/urls.py`.

| Rota | Nome | View | Template | Acesso |
|---|---|---|---|---|
| `/patient/` | `patient:home` | `PatientHomeView` | `patient/home_patient.html` | `PatientOnly` |
| `/patient/agendamentos/` | `patient:agendamentos` | `PatientAppointmentsView` | `patient/agendamentos.html` | `PatientOnly` + `visible_to` |
| `/patient/agendamentos/solicitar/` | `patient:solicitar_horario` | `AppointmentRequestView` | `patient/solicitar_horario.html` | `PatientOnly` + `can_be_created_by` |
| `/patient/historico/` | `patient:historico` | `PatientHistoryView` | `patient/historico.html` | `PatientOnly` + `visible_to` |
| `/patient/historico/<pk>/` | `patient:historico_detalhe` | `PatientSessionDetailView` | `patient/historico_detalhe.html` | `PatientOnly` + `visible_to` |
| `/patient/triagens/` | `patient:triagens` | `PatientTriagesView` | `patient/triagens.html` | `PatientOnly` + `visible_to` |
| `/patient/triagens/<pk>/` | `patient:triagem_detalhe` | `PatientTriageDetailView` | `patient/triagem_detalhe.html` | `PatientOnly` + `visible_to` |
| `/patient/contato/` | `patient:contato` | `PatientContactView` | `patient/contato.html` | `PatientOnly` |

As views ficam no pacote `patient/views/`, um módulo por assunto: `home.py`,
`appointments.py`, `history.py`, `triages.py`, `contact.py`, mais `access.py` (o
mixin) e `sessions.py`, que concentra o vocabulário de sessão compartilhado pelas
telas — rótulos de status, selo de presença, "Hoje/Amanhã/Ontem" e a consulta das
próximas sessões.

O cadastro do Paciente **não** fica nesta área: é o assistente do Administrativo,
em `/administration/cadastrar-paciente/`. O Paciente não cria a própria conta.

## 2. Como o acesso funciona

`PatientOnly` (`patient/views/access.py`) é `LoginRequiredMixin` +
`UserPassesTestMixin` com um `test_func` que confere a role:

```python
class PatientOnly(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == CustomUser.Role.PACIENTE
```

Quem não está autenticado cai no `/login/` com `next`. Quem está autenticado em
outra role recebe 403, e o `handler403` redireciona para a home da própria role
com a mensagem de aviso — não existe tela de erro visível.

O mixin confere a role; o recorte por pessoa é o `visible_to`, e para o Paciente
ele é sempre o próprio registro:

| Model | Recorte do Paciente |
|---|---|
| `Patient` | `pk = eu` |
| `Appointment` | `patient_id = eu` |
| `AppointmentRequest` | `patient_id = eu` |
| `TriageRecord` | `patient_id = eu` **e** status em `VISIBLE_TO_PATIENT` |
| `RoomBooking` | `patient_id = eu` |

`VISIBLE_TO_PATIENT` é `(CLOSED, REFERRED)`: o Paciente só enxerga a triagem
depois de encerrada ou encaminhada. Ficha aberta, enviada ou com edição
finalizada é trabalho em andamento da equipe e não aparece — é o que permite às
telas de triagem não terem nenhum filtro de status próprio, como se vê em 3.4.

Nenhum model dá ao Paciente `EDITABLE_FIELDS`. A única escrita da área é
`AppointmentRequest`, com `CREATABLE_BY = (Role.PACIENTE,)`.

## 3. Rota por rota

### 3.1 `/patient/` — Página inicial

`PatientHomeView` (`patient/views/home.py`), um `TemplateView`. Monta tudo em
`overview()`, dentro de um `try/except DatabaseError` que troca o conteúdo por
`home_error`.

Quatro indicadores, escritos direto no contexto (esta home ainda não usa o
`summary_list.html`):

| Indicador | Consulta |
|---|---|
| `sessions_done` | sessões com status `ATTENDED` |
| `triage_status` | rótulo derivado do `flow_status` do paciente |
| `next_session` | próxima sessão agendada, como "Hoje", "Amanhã" ou a data |
| `absences` | sessões com status `PATIENT_NO_SHOW` |

O `triage_status` sai do dicionário `TRIAGE_STATUS`, que traduz o fluxo do
paciente para o que ele lê na tela:

| `flow_status` | Rótulo | Explicação na tela |
|---|---|---|
| `AWAITING_TRIAGE` | Não iniciada | "Sua triagem ainda não começou." |
| `IN_TRIAGE` | Em andamento | "Sua triagem está sendo feita pela equipe." |
| `AWAITING_REVIEW` | Em análise | "Sua triagem está em análise pela coordenação." |
| `REFERRED` | Concluída | "Triagem encaminhada para acompanhamento." |
| `IN_TREATMENT` | Concluída | "Triagem concluída e acompanhamento em andamento." |
| `DISCHARGED` | Concluída | "Triagem concluída." |

O fluxo vazio (`""`), do cadastro legado, cai no mesmo rótulo de "Não iniciada".

Três atividades: a última sessão já registrada, a próxima agendada e a situação
da triagem. O calendário vem de `core/month_calendar.py` e marca as sessões do
mês, exceto as canceladas.

### 3.2 `/patient/agendamentos/` — Meus agendamentos

`PatientAppointmentsView` (`patient/views/appointments.py`). Duas listas:

- `appointments`: as próximas sessões, de `sessions.upcoming_appointments` —
  status `SCHEDULED` e data de hoje em diante, em ordem crescente;
- `schedule_requests`: as cinco solicitações mais recentes, com selo pela
  situação (`Pendente`/`warning`, `Aceita`/`success`, `Recusada`/`danger`) e a
  resposta do Administrativo quando houver.

O selo da sessão vem de `sessions.session_badge`, que consulta
`appointment.presence_status(now)`: sessão agendada e já confirmada aparece como
confirmada, sessão perto da data aparece como aguardando confirmação, e as demais
caem nos rótulos de `SESSION_STATUS`. Quem confirma presença é o professor
responsável, não o Paciente.

Falha de banco troca as duas listas por vazio e preenche `appointments_error`.

### 3.3 `/patient/agendamentos/solicitar/` — Solicitar horário

`AppointmentRequestView`, um `FormView` com `AppointmentRequestForm`
(`patient/forms.py`). É a única escrita da área, e tem três camadas de proteção
para a mesma regra — uma solicitação pendente por vez:

1. `test_func` estende o do mixin com
   `AppointmentRequest.can_be_created_by(user)`;
2. `post()` consulta `pending_request()` antes de validar e, se houver pendente,
   recusa com `messages.error` e manda para os agendamentos;
3. o banco tem `UniqueConstraint(fields=["patient"], condition=Q(status="PE"))`,
   e o `IntegrityError` é tratado em `form_valid` com a mesma mensagem.

A terceira camada é a que vale em corrida: duas abas abertas passam pela segunda
e param na constraint. O formulário limita as observações a 500 caracteres e o
campo de data nasce com `min` no dia de hoje.

`form_valid` busca o `Patient` pelo `visible_to` e grava dentro de
`transaction.atomic()`. Cadastro de paciente não encontrado vira erro no
formulário, não exceção.

### 3.4 `/patient/historico/` e `/patient/historico/<pk>/`

`PatientHistoryView` (`patient/views/history.py`) lista o que já passou:
`history_appointments()` traz as sessões que não estão mais agendadas **ou** cuja
data já passou, da mais recente para a mais antiga. Sessão agendada de data
passada e ainda sem registro aparece como "Aguardando registro"/`secondary` — é
como a tela mostra que a equipe ainda não fechou o registro.

A paginação é `Paginator` com dez por página, pelo parâmetro `?pagina=`.

`PatientSessionDetailView` usa a mesma consulta filtrada pelo `pk`, e levanta
`Http404` quando não encontra. Como a consulta já nasce recortada pelo
`visible_to`, sessão de outro paciente e sessão futura ainda agendada respondem
404 sem checagem extra. O detalhe traz tipo, duração, quem atendeu, o professor e
uma frase explicando a situação, de `HISTORY_MESSAGES`.

### 3.5 `/patient/triagens/` e `/patient/triagens/<pk>/`

`PatientTriagesView` (`patient/views/triages.py`) lista as triagens concluídas.
`concluded_triages()` não filtra status: quem filtra é o `visible_to`, pelo
`VISIBLE_TO_PATIENT`. A consulta usa `.only(...)` para não trazer os campos
criptografados da ficha — o Paciente vê que a triagem existiu e como terminou,
não o conteúdo clínico.

Cada linha traz a data e o desfecho, de `TRIAGE_OUTCOMES`:

| Status | Rótulo | Nível |
|---|---|---|
| `REFERRED` | Encaminhada | `success` |
| `CLOSED` | Encerrada | `secondary` |

O vazio tem duas versões, e é a única parte da tela que olha o `flow_status`:
quando o paciente está em triagem ou aguardando parecer, a mensagem é "Há uma
triagem em andamento. Quando ela for concluída, aparece aqui."; nos demais casos,
"Você ainda não tem triagem concluída.". Sem isso, quem estava justamente em
triagem veria a tela dizendo que não tem nenhuma.

`PatientTriageDetailView` mostra quando foi criada, quando e por quem foi
encerrada, e — só quando encaminhada — os professores responsáveis pelo caso.
Triagem não encontrada levanta `Http404`.

### 3.6 `/patient/contato/` — Contato

`PatientContactView` (`patient/views/contact.py`) junta duas coisas: quem cuida
do atendimento e como falar com o serviço.

`caregivers` são os alunos com caso aberto do paciente, com as iniciais para o
avatar. `channels` são montados a partir de `settings.SEP_CONTACT`
(`config/settings/base.py`), e cada canal só entra se o dado existir: localização
vira link do Google Maps, telefone vira `tel:+55` com os dígitos, e-mail vira
`mailto:`. Não há nada configurável por paciente nesta tela.

## 4. Ordem dos fluxos

**Agendamento.** Página inicial (indicador "Próxima sessão" ou a atividade de
agendamento) → Meus agendamentos → "Solicitar horário" → escolher data e período
→ enviar → volta para Meus agendamentos com a solicitação em "Pendente". A
resposta apareceria na mesma lista, mas o fluxo para por aí: o
`AppointmentRequest` dá ao Administrativo os campos de resposta em
`EDITABLE_FIELDS` e nenhuma tela usa esses campos hoje — é a pendência técnica 2.

**Histórico.** Página inicial (atividade da última sessão) → Histórico de sessões
→ abrir uma sessão.

**Triagem.** Página inicial (atividade "Triagem") → Minhas triagens → abrir a
triagem concluída. Enquanto a equipe trabalha, a lista fica vazia e a home
explica em que etapa o processo está.

**Contato.** Direto pelo menu.

## 5. Origem dos dados

| Informação | Origem | Situação |
|---|---|---|
| Sessões realizadas, faltas, próxima sessão | `Appointment` | Real |
| Situação da triagem na home | `Patient.flow_status` | Real |
| Calendário | `Appointment` do paciente | Real |
| Agendamentos e selo de presença | `Appointment.presence_status` | Real |
| Solicitações de horário e resposta | `AppointmentRequest` | Real |
| Histórico e detalhe da sessão | `Appointment` | Real |
| Triagens concluídas e desfecho | `TriageRecord` | Real |
| Professores responsáveis | `Patient.responsible_teachers` | Real |
| Quem cuida do atendimento | `CaseAssignment` aberto | Real |
| Telefone, e-mail e endereço do serviço | `settings.SEP_CONTACT` | Real, fixo em settings |

A área não tem mock de dado: tudo que aparece existe no banco. O que tem `TODO`
são os três ícones do header em `patient/base_patient.html`, com
`{# TODO: botões sem lógica; ficam para fazer #}`.

## 6. Templates e componentes

Todas as telas estendem `patient/base_patient.html`, que estende `base.html` e
preenche `brand`, `main_nav` (Página inicial, Agendamentos, Histórico, Triagens,
Contato), `user_links` e `footer`. A base do Paciente é a única que declara um
bloco próprio, `page_header`.

As listagens usam `{% data_table %}`; os selos, `components/badge.html`; vazio e
erro, `empty_state.html` e `error_state.html`; a solicitação de horário usa
`components/form.html`, que é `method="post"` com `form.as_p`. A home ainda
escreve os indicadores à mão, em vez de usar `summary_list.html`; a migração está
registrada em `componentes.md`.

## 7. Pendências técnicas

1. **Indicadores da home.** São os únicos que não passam por
   `summary_list.html`. Migram quando alguma tarefa tocar nessa view, porque
   exige montar a lista na view em vez de campo a campo no template.
2. **Solicitação sem resposta.** A solicitação de horário nasce "Pendente" e não
   há tela em lugar nenhum que a responda — o Administrativo tem os campos
   (`status`, `response`, `answered_by`, `answered_at`) em `EDITABLE_FIELDS`, mas
   nenhuma view os edita. Enquanto isso, o Paciente vê o pedido parado e a
   `UniqueConstraint` o impede de mandar outro.
3. **Cancelar ou remarcar.** O Paciente pede horário, mas não tem como desmarcar
   nem pedir remarcação. Falta definir se cancela pelo sistema ou pelo contato.
4. **Confirmação de presença.** O selo "Aguardando confirmação" aparece para o
   Paciente, mas quem confirma é o professor. Falta definir se o Paciente também
   confirma.
5. **Fim do acompanhamento.** "Alta" existe no `flow_status` e aparece como
   triagem "Concluída", sem tela que explique o encerramento do acompanhamento.
6. **`patient/views/profile.py`.** Tem uma `enviar_email` vazia, sem rota. Ou
   ganha função, ou sai.
