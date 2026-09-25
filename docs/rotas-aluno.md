# Rotas da área do Aluno

Especificação das rotas do Aluno: o que cada tela mostra, por onde se chega nela
e como está implementada. Complementa `fluxos-aluno.md`, que registra o desenho
feito antes da implementação, e detalha a linha do Aluno de
`mapa_rota_permisao.md`, que é o mapa geral de permissões.

Onde o dado ainda não existe no banco, a tela entra com **dado mockado** e um
`TODO` no ponto exato em que a consulta real deve substituí-lo. A lista está na
seção 7.

---

## 1. Mapa das rotas

Prefixo `/students/`, `app_name = "students"`, arquivo `students/urls.py`.

| Rota | Nome | View | Template | Acesso |
|---|---|---|---|---|
| `/students/` | `students:home` | `HomeEstudanteView` | `student/home.html` | `StudentOnly` |
| `/students/prontuarios/` | `students:prontuarios` | `StudentRecordsView` | `student/prontuarios.html` | `StudentOnly` |
| `/students/triagens/` | `students:triagens` | `StudentTriagesView` | `student/triagens.html` | `StudentOnly` |
| `/students/triagens/<pk>/concluida/` | `students:triagem_concluida` | `TriageCompletedView` | `student/triagem_concluida.html` | `StudentOnly` + `visible_to` |
| `/students/encaminhamentos/` | `students:encaminhamentos` | `StudentReferralsView` | `student/encaminhamentos.html` | `StudentOnly` |
| `/students/feedbacks/` | `students:feedbacks` | `StudentFeedbacksView` | `student/feedbacks.html` | `StudentOnly` |
| `/students/meu-professor/` | `students:meu_professor` | `MeuProfessorView` | `student/meu_professor.html` | `StudentOnly` |
| `/students/painel/` | `students:painel` | `PainelEstudanteView` | `student/student_panel.html` | `StudentOnly`, tela antiga |
| `/students/perfil/` | `students:perfil` | `PerfilAlunoView` | `student/perfil.html` | `GroupRequiredMixin("Students")` |
| `/students/cadastrar/` | `students:cadastrar` | `cadastrar_aluno` | `student/cadastro.html` | `has_perm("students.add_student")` |

As views ficam no pacote `students/views/`, um módulo por assunto: `home.py`,
`records.py`, `triages.py`, `referrals.py`, `feedbacks.py`, `account.py`, mais
quatro módulos de apoio — `access.py` (o mixin), `queue.py` (a fila de espera),
`dates.py` (rótulos de data) e `mocks.py` (o que ainda não existe no banco).

`cadastrar/` está nesta área mas não é tela do Aluno: quem abre é o Coordenador,
pela permissão do Django. É a mesma inversão que existe em `/teacher/cadastrar/`.

## 2. Como o acesso funciona

`StudentOnly` (`students/views/access.py`) é `LoginRequiredMixin` +
`UserPassesTestMixin` com um `test_func` que confere a role:

```python
class StudentOnly(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == CustomUser.Role.ALUNO
```

Quem não está autenticado cai no `/login/` com `next`. Quem está autenticado em
outra role recebe 403, e o `handler403`
(`core.exception_handlers.custom_permission_denied_view`) redireciona para a home
da própria role com a mensagem "Você não tem acesso a essa página." — não existe
tela de erro visível.

O mixin confere a role, não o dono do dado. Quem faz o recorte por pessoa é o
`visible_to` dos querysets (`core/permissions.py`), que para o Aluno resolve em:

| Model | Recorte do Aluno |
|---|---|
| `CaseAssignment` | `student_id = eu` |
| `ProgressNote` | paciente com caso aberto meu |
| `Appointment` | `assigned_student_id = eu` |
| `TriageFeedback` | triagem de autoria minha |
| `TriageRecord` | `student_author_id = eu` **e** status em `VISIBLE_TO_AUTHOR` |
| `Patient` | caso aberto meu, ou paciente de uma triagem minha ainda visível |

`VISIBLE_TO_AUTHOR` é `(OPEN, FINALIZED_EDITION, SUBMITTED)` — o Aluno deixa de
enxergar a própria ficha quando ela é fechada ou encaminhada. Isso tem efeito de
rota, registrado em 3.4.

`perfil/` é a exceção: continua no grupo do Django ("Students"), enquanto o resto
da área confere a role. É a mistura de mecanismos já registrada como pendência no
mapa geral.

## 3. Rota por rota

### 3.1 `/students/` — Página inicial

`HomeEstudanteView` (`students/views/home.py`), um `TemplateView`. Monta tudo em
`overview()`, dentro de um `try/except DatabaseError` que, em caso de falha,
troca o conteúdo por `home_error`.

Quatro indicadores, em `context["indicators"]`:

| Indicador | Consulta |
|---|---|
| Triagens pendentes | `waiting_patients().count()` |
| Encaminhamentos hoje | casos abertos com `start_date` = hoje |
| Pacientes ativos | `CaseAssignment.visible_to(user)` com `end_date` nulo |
| Faltas | `Appointment` com `status = STUDENT_NO_SHOW` |

Três atividades recentes, em `context["activities"]`, cada uma um dicionário com
`kind`, `title`, `detail`, `label`, `level`, `url` e `link_label`: a primeira
paciente da fila de triagem, o caso mais recente e o último feedback recebido.
Quando não há dado, a atividade vira só um `title` explicando o vazio.

O calendário vem de `core/month_calendar.py`, compartilhado com as outras áreas:
`displayed_month` lê `?ano=` e `?mes=`, `month_calendar` devolve
`calendar_weeks`, `calendar_months`, `calendar_years`, `previous_month` e
`next_month`. Os dias marcados são as sessões do Aluno no mês, exceto as
canceladas.

`page_actions` do template leva a `fila_triagem` ("Fazer triagem").

### 3.2 `/students/prontuarios/` — Prontuários e evolução

`StudentRecordsView` (`students/views/records.py`). Percorre os casos abertos do
Aluno em ordem alfabética de paciente e, para cada um, procura a evolução mais
recente em `latest_notes()`, que percorre `ProgressNote.visible_to(user)` por
`updated_at` e guarda a última de cada paciente.

Cada linha traz `patient`, `updated` (o rótulo de `dates.updated_label`:
"Atualizado hoje", "Atualizado há 3h", "Atualizado há 2 dias" ou "Sem evolução
registrada") e o selo de `mocks.record_status`. Paciente sem evolução entra como
"Pendente"/`danger`.

Colunas em `COLUMNS`; falha de banco preenche `records_error`.

### 3.3 `/students/triagens/` — Triagens a realizar

`StudentTriagesView` (`students/views/triages.py`). A fila vem de
`students/views/queue.py`:

```python
def waiting_patients():
    return Patient.objects.awaiting_triage().order_by("created_at")
```

`awaiting_triage()` (`patient/models/patient.py`) filtra
`flow_status__in=("", AWAITING_TRIAGE)` — a string vazia cobre o cadastro legado,
anterior ao campo de fluxo, que senão ficaria invisível para sempre.

A fila **não é por aluno**: qualquer Aluno vê todos os pacientes aguardando
triagem, e quem pega primeiro cria a ficha. Não existe designação de paciente a
aluno; é a pendência 1 de `fluxos-aluno.md`.

Cada linha leva `start_url = reverse("create_triage", args=[paciente.pk])`, que
aponta para a ficha em `/triage/create/<paciente>/`.

### 3.4 `/students/triagens/<pk>/concluida/` — Triagem concluída

`TriageCompletedView`, um `DetailView` cujo `get_queryset` é
`TriageRecord.objects.visible_to(user)`. O recorte do Aluno já faz o trabalho de
segurança: triagem de outro aluno responde 404, sem checagem extra na view.

`completed_at` cai em cascata: `submitted_at`, senão `closed_at`, senão
`created_at` — a ficha nem sempre tem data de envio.

Efeito do `VISIBLE_TO_AUTHOR`: depois que a Coordenação fecha ou encaminha a
triagem, esta tela passa a responder 404 para o próprio autor.

A rota antiga `/triage/minhas-triagens/` não se comporta assim: ela filtra
`student_author_id` direto, sem passar pelo `visible_to`, e por isso continua
listando a ficha fechada. As duas telas discordam sobre o que o autor pode ver —
é a pendência técnica 4.

### 3.5 `/students/encaminhamentos/` — Encaminhamentos recebidos

`StudentReferralsView` (`students/views/referrals.py`). Lista os casos abertos do
Aluno, do mais recente para o mais antigo, e passa cada um por
`mocks.referral_status`, que decide entre "Aguardando confirmação"/`Pendente` e
"Encaminhado por Supervisor geral"/`Ativo` só pela data de início — o
`CaseAssignment` não guarda quem encaminhou nem se houve confirmação.

### 3.6 `/students/feedbacks/` — Feedbacks recebidos

`StudentFeedbacksView` (`students/views/feedbacks.py`). Junta duas origens numa
lista só, ordenada pelo momento, do mais novo para o mais antigo:

- `TriageFeedback.visible_to(user)` — parecer da Coordenação sobre uma triagem,
  com assunto "Triagem - <paciente>";
- `ProgressNote.visible_to(user)` com `confirmed_at` preenchido — confirmação de
  prontuário, com assunto "Prontuário - <paciente>".

O selo vem de `mocks.feedback_status`, que compara `created_at` com `updated_at`
e a idade do registro. `dates.received_label` monta "Recebida às 14:20",
"Recebida ontem" ou "Recebida em 12/03/2026".

### 3.7 `/students/meu-professor/`, `painel/`, `perfil/`, `cadastrar/`

`MeuProfessorView` mostra `aluno.current_advisor`, ou o vazio quando não há
orientador. `PainelEstudanteView` é a tela antiga, um `TemplateView` sem
consulta. `PerfilAlunoView` é um `UpdateView` que só edita os campos de contato e
endereço do próprio usuário (`get_object` devolve `Student` com o `pk` da
sessão), com sucesso em `students:home`. `cadastrar_aluno` recusa com
`PermissionDenied` quem não tem `students.add_student`, salva pelo
`AlunoCreationForm`, sincroniza o grupo e volta para `supervisor:painel`; os
campos de curso e período no formulário vêm de
`supervisor.views.mocks.student_enrollment_fields` e não persistem.

## 4. Rotas de triagem que o Aluno usa

Ficam em `triage/urls.py`, sem `app_name` — os nomes são globais. São funções com
`@login_required` e checagem de role na mão, não CBVs com mixin.

| Rota | Nome | O que faz | Acesso |
|---|---|---|---|
| `/triage/fila/` | `fila_triagem` | Mesma fila da tela 3.3, no layout antigo | role `ALUNO`, senão `PermissionDenied` |
| `/triage/create/<patient_id>/` | `create_triage` | Cria ficha + IARV numa transação | quem existir como `Student` |
| `/triage/concluida/<pk>/` | `triagem_concluida` | Confirmação logo após criar | só o autor |
| `/triage/student_detail/<pk>/` | `triage_detail_student` | Ficha em leitura, campos desabilitados | role `ALUNO` e autor |
| `/triage/edit/<pk>/` | `edit_triage` | Edita ficha + IARV | autor, enquanto `editable_fields_for` devolver campos |
| `/triage/submit/<pk>/` | `submit_triage` | `OPEN → SUBMITTED` | role `ALUNO`, autor |
| `/triage/minhas-triagens/` | `minhas_triagens` | Lista as fichas do próprio Aluno, sem recorte de status | role `ALUNO` |

Detalhes que valem registro:

- O formulário IARV é escolhido pela idade do paciente em `get_iarv_form_class`:
  menos de 13 anos é o infantil, até 17 o adolescente, acima disso o adulto.
  Paciente sem data de nascimento levanta `ValidationError`.
- `create_triage` grava ficha e IARV dentro de `transaction.atomic()` e
  redireciona para `triagem_concluida`, a tela antiga — não para
  `students:triagem_concluida`. As duas telas de confirmação convivem; unificar é
  pendência técnica (seção 9).
- `submit_triage` é **GET**: o link envia a ficha. Veio assim da `dev` e foi
  mantido de propósito; trocar para POST muda o template e a confirmação.
- `edit_triage` monta `cancel_url` na view, apontando para
  `triage_detail_student` quando a role é `ALUNO` e para
  `triage_detail_supervisor` nos demais casos. O template não pode decidir isso
  sozinho porque `user.role` guarda `"AL"`, não `"ALUNO"` — comparar com o nome
  por extenso no template foi exatamente o bug do botão "Cancelar".
- Todas as recusas usam `PermissionDenied`, que o `handler403` transforma em
  redirecionamento com aviso. Recusa com `ValidationError` virava 500.

## 5. Ordem dos fluxos

**Triagem.** Página inicial (indicador "Triagens pendentes" ou a atividade
recente) → Triagens a realizar → "Iniciar" → ficha em `/triage/create/<paciente>/`
→ confirmação → detalhe do Aluno → "Enviar" (`submit_triage`) → a ficha vai para
a Coordenação.

Criar a ficha move o paciente de "Aguardando triagem" para "Em triagem"; enviar
move para "Aguardando parecer". Quem dá o passo seguinte é o Coordenador. Alta
**não** acontece aqui: só existe no fim do atendimento.

**Prontuário.** Página inicial (indicador "Pacientes ativos") → Prontuários e
evolução.

**Encaminhamento.** Página inicial (indicador "Encaminhamentos hoje") →
Encaminhamentos recebidos.

**Feedback.** Página inicial (atividade "Feedback pendente") → Feedbacks
recebidos.

As três últimas não têm tela de detalhe na referência.

## 6. Origem dos dados

| Informação | Origem | Situação |
|---|---|---|
| Triagens pendentes, fila de triagem | `Patient.objects.awaiting_triage()` | Real |
| Encaminhamentos hoje, Pacientes ativos | `CaseAssignment` | Real |
| Faltas | `Appointment` com `STUDENT_NO_SHOW` | Real |
| Calendário | `Appointment` do Aluno, via `core/month_calendar.py` | Real |
| Prontuários: paciente e última evolução | `ProgressNote` | Real |
| Prontuários: selo Revisar/Pendente | Critério não definido | **Mock com TODO** |
| Encaminhamentos: quem encaminhou e confirmação | Sem campos no `CaseAssignment` | **Mock com TODO** |
| Feedbacks: origem, autor e data | `TriageFeedback` e `ProgressNote` | Real |
| Feedbacks: selo Novo/Lida/Editada | Sem marcação de leitura | **Mock com TODO** |

## 7. Mocks e TODOs

Tudo que não existe no banco fica em `students/views/mocks.py`, uma função por
lacuna, com o `TODO` no corpo:

| Função | O que substitui | O que falta no banco |
|---|---|---|
| `referral_status(case, today)` | Situação e selo do encaminhamento | Quem encaminhou e a confirmação |
| `feedback_status(created, updated, now)` | Selo Novo/Lida/Editada | Marcação de leitura por aluno |
| `record_status(note)` | Selo Revisar/Pendente | Critério do produto |

Botão ou link sem lógica leva `{# TODO: botão sem lógica; fica para fazer #}` no
template — é o caso dos três ícones do header em `student/base_student.html`.

## 8. Templates e componentes

Todas as telas novas estendem `student/base_student.html`, que estende
`base.html` e preenche `brand`, `main_nav` (Página inicial, Prontuários,
Triagens, Feedbacks, Encaminhamentos), `user_links` e `footer`. Título, trilha,
ações da página e conteúdo continuam sendo blocos do `base.html`.

As listagens usam `{% data_table %}`; os selos, `components/badge.html`; os
indicadores da home, `components/summary_list.html`; vazio e erro,
`empty_state.html` e `error_state.html`. O inventário e os limites de cada peça
estão em `componentes.md`.

As telas antigas — `student_panel.html`, `perfil.html`, `cadastro.html` — seguem
no layout anterior.

## 9. Pendências técnicas

1. **Duas telas de "triagem concluída".** `students:triagem_concluida` e a rota
   global `triagem_concluida` mostram a mesma coisa em layouts diferentes, e
   `create_triage` redireciona para a antiga. Falta escolher uma.
2. **Fila sem dono.** Enquanto não houver designação de paciente a aluno, dois
   alunos podem abrir a ficha do mesmo paciente. O segundo cria uma segunda
   ficha; nada impede.
3. **Envio por GET.** `submit_triage` muda estado num GET. Mantido como veio da
   `dev`; trocar exige mudar o template e tratar a confirmação.
4. **Ficha some depois de fechada, em uma tela só.** Pelo `VISIBLE_TO_AUTHOR`, o
   Aluno perde o acesso à própria triagem quando ela é fechada ou encaminhada —
   mas `minhas-triagens/` continua listando, porque consulta por autor sem passar
   pelo `visible_to`. Falta decidir se o autor mantém leitura do histórico e
   alinhar as duas consultas com a decisão.
5. **Mecanismos misturados.** `perfil/` está em grupo do Django e o resto da área
   na role; as rotas de `/triage/` conferem role na mão, sem mixin.
