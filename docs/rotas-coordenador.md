# Rotas da área do Coordenador

Especificação das rotas do Coordenador: o que cada tela mostra, por onde se chega
nela e como está implementada. Complementa `fluxos-coordenador.md`, que registra
o desenho feito antes da implementação, e detalha a linha do Coordenador de
`mapa_rota_permisao.md`.

O papel se chama **Coordenador** em tudo que a pessoa lê. No código, o que é novo
nasce como `Coordinator`; a pasta `supervisor/`, a rota `/supervisor/`, o
namespace `supervisor:`, o grupo do Django "Supervisor" e a role `SV` continuam
com o nome antigo.

Onde o dado ainda não existe no banco, a tela entra com **dado mockado** e um
`TODO` no ponto exato em que a consulta real deve substituí-lo. A lista está na
seção 7.

---

## 1. Mapa das rotas

Prefixo `/supervisor/`, `app_name = "supervisor"`, arquivo `supervisor/urls.py`.

| Rota | Nome | View | Template | Acesso |
|---|---|---|---|---|
| `/supervisor/` | `supervisor:home` | `CoordinatorHomeView` | `supervisor/home_supervisor.html` | `CoordinatorOnly` |
| `/supervisor/professores/` | `supervisor:professores` | `CoordinatorTeachersView` | `supervisor/list_users.html` | `CoordinatorOnly` |
| `/supervisor/professores/<pk>/` | `supervisor:professor_detalhe` | `CoordinatorTeacherDetailView` | `supervisor/professor_detalhe.html` | `CoordinatorOnly` |
| `/supervisor/alunos/` | `supervisor:alunos` | `CoordinatorStudentsView` | `supervisor/alunos.html` | `CoordinatorOnly` |
| `/supervisor/alunos/<pk>/` | `supervisor:aluno_detalhe` | `CoordinatorStudentDetailView` | `supervisor/aluno_detalhe.html` | `CoordinatorOnly` |
| `/supervisor/triagens/` | `supervisor:triagens` | `CoordinatorTriagesView` | `supervisor/triagens.html` | `CoordinatorOnly` + `visible_to` |
| `/supervisor/triagens/<pk>/` | `supervisor:triagem_detalhe` | `CoordinatorTriageDetailView` | `supervisor/triagem_detalhe.html` | `CoordinatorOnly` + `visible_to` |
| `/supervisor/encaminhamentos/` | `supervisor:encaminhamentos` | `CoordinatorReferralsView` | `supervisor/encaminhamentos.html` | `CoordinatorOnly` + `visible_to` |
| `/supervisor/encaminhamentos/<pk>/` | `supervisor:encaminhar` | `CoordinatorReferralsView` | idem | idem, com a triagem fixada |
| `/supervisor/feedbacks/` | `supervisor:feedbacks` | `CoordinatorFeedbacksView` | `supervisor/feedbacks.html` | `CoordinatorOnly` + `visible_to` |
| `/supervisor/usuarios/` | `supervisor:listar_usuarios` | `CoordinatorTeachersView` | `supervisor/list_users.html` | `CoordinatorOnly`, nome antigo da listagem |
| `/supervisor/orientacao/` | `supervisor:orientacao` | `PainelOrientacaoSupervisorView` | `supervisor/orientacao_panel.html` | `GroupRequiredMixin("Supervisor")` |
| `/supervisor/painel/` | `supervisor:painel` | `PainelSupervisorView` | `supervisor/supervisor_panel.html` | `GroupRequiredMixin("Supervisor")`, tela antiga |
| `/supervisor/perfil/` | `supervisor:perfil` | `PerfilSupervisorView` | `supervisor/perfil.html` | `GroupRequiredMixin("Supervisor")` |
| `/supervisor/areas/` | `supervisor:areas` | `ListaAreasView` | `supervisor/area_list.html` | `GroupRequiredMixin("Supervisor")` |
| `/supervisor/areas/nova/` | `supervisor:area_criar` | `CriarAreaView` | `supervisor/area_form.html` | `has_perm("areas.add_areaacting")` |
| `/supervisor/areas/<pk>/editar/` | `supervisor:area_editar` | `EditarAreaView` | `supervisor/area_form.html` | `has_perm("areas.change_areaacting")` |
| `/supervisor/register/` | `supervisor:register` | `cadastrar_supervisor` | `supervisor/cadastro_supervisor.html` | `has_perm("core.add_customuser")`, Superadmin |

As views ficam no pacote `supervisor/views/`, um módulo por assunto: `home.py`,
`teachers.py`, `students.py`, `triages.py`, `referrals.py`, `feedbacks.py`,
`areas.py`, `account.py`, `orientation.py`, mais `access.py` (o mixin) e
`mocks.py` (o que ainda não existe no banco). O `__init__.py` reexporta os nomes
que `urls.py` usa.

O cadastro de professor e o de aluno **não** ficam nesta área: continuam em
`/teacher/cadastrar/` e `/students/cadastrar/`, por permissão do Django, e é para
lá que os botões de cadastrar apontam.

## 2. Como o acesso funciona

`CoordinatorOnly` (`supervisor/views/access.py`) é `LoginRequiredMixin` +
`UserPassesTestMixin` com um `test_func` que confere a role:

```python
class CoordinatorOnly(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == CustomUser.Role.SUPERVISOR
```

Quem não está autenticado cai no `/login/` com `next`. Quem está autenticado em
outra role recebe 403, e o `handler403` redireciona para a home da própria role
com a mensagem de aviso — não existe tela de erro visível.

O Coordenador enxerga tudo: em praticamente todos os querysets do projeto,
`VISIBLE_TO[Role.SUPERVISOR]` é `ALL`. Ainda assim as views chamam `visible_to`,
para que o dia em que o alcance mudar não exija reescrever tela por tela.

Há outra herança que importa: `INHERITS = {SUPERVISOR: PROFESSOR}`
(`core/permissions.py`). O Coordenador herda o que o Professor pode criar, e é
por isso que `TriageFeedback.CREATABLE_BY = (Role.PROFESSOR,)` já autoriza o
Coordenador a escrever parecer.

As telas novas conferem a role; `painel/`, `perfil/`, `areas/` e `orientacao/`
seguem no grupo do Django "Supervisor". É a mistura de mecanismos já registrada
como pendência no mapa geral.

## 3. Rota por rota

### 3.1 `/supervisor/` — Página inicial

`CoordinatorHomeView` (`supervisor/views/home.py`), um `TemplateView`. Monta tudo
em `overview()`, dentro de um `try/except DatabaseError` que troca o conteúdo por
`home_error`.

Quatro indicadores:

| Indicador | Consulta |
|---|---|
| Triagens pendentes | triagens com status `SUBMITTED` |
| Encaminhamentos hoje | triagens `REFERRED` com `closed_at` de hoje |
| Professores ativos | professores com orientando vinculado |
| Feedbacks a enviar | triagens finalizadas pelo aluno e sem parecer |

"Feedbacks a enviar" usa a mesma tupla `FINISHED` da tela de feedbacks, importada
de `feedbacks.py`. Foi assim de propósito: o indicador é um atalho para aquela
tela, e duas definições separadas de "finalizada" fariam os números divergirem.

Três atividades recentes, com `kind`, `title`, `detail`, `label`, `level`, `url`
e `link_label`: a triagem enviada mais recente, o último encaminhamento e a
triagem mais recente ainda sem parecer. O calendário vem de
`core/month_calendar.py` e marca os dias com triagem criada ou fechada no mês.

`page_actions` leva a `supervisor:orientacao` ("Meus alunos orientandos").

### 3.2 `/supervisor/professores/` e `/supervisor/professores/<pk>/`

`CoordinatorTeachersView` é um `ListView` sobre `Teacher` com
`role = PROFESSOR`, `prefetch_related("acting_areas")` e
`annotate(advisees=Count("current_advisees", distinct=True))`. Aceita `?q=` (nome
ou sobrenome) e `?area=` (pk da área). O selo é "Ativo"/`success` quando há
orientando e "Sem alunos"/`warning` quando não há.

`/supervisor/usuarios/` aponta para a mesma view: a rota antiga foi mantida, o
menu novo usa `professores/`.

`CoordinatorTeacherDetailView` é o destino do "Editar" e mostra o professor com
os orientandos em ordem alfabética.

### 3.3 `/supervisor/alunos/` e `/supervisor/alunos/<pk>/`

`CoordinatorStudentsView`, espelho da tela de professores: `select_related` do
orientador, busca por nome ou matrícula, filtro por área do orientador,
`distinct()` porque o filtro atravessa many-to-many. Selo "Vinculado"/`success`
ou "Sem orientador"/`warning`; a fase vem de `get_stage_display()`.

`CoordinatorStudentDetailView` mostra o aluno com `open_cases`.

### 3.4 `/supervisor/triagens/` e `/supervisor/triagens/<pk>/`

`CoordinatorTriagesView` (`supervisor/views/triages.py`) lista
`TriageRecord.visible_to(user)` com status em `QUEUE_STATUS`
(`SUBMITTED`, `CLOSED`, `REFERRED`), da mais recente para a mais antiga. O filtro
`?situacao=` compara com o rótulo em minúsculas, e os rótulos vêm de
`mocks.triage_status`.

`CoordinatorTriageDetailView` acrescenta `risk` (de
`record.get_risk_classification()`) e `can_refer`, verdadeiro enquanto a triagem
não estiver encaminhada.

### 3.5 `/supervisor/encaminhamentos/` e `/supervisor/encaminhamentos/<pk>/`

`CoordinatorReferralsView` (`supervisor/views/referrals.py`) é a tela onde o
Coordenador fecha o ciclo da triagem. As duas rotas usam a mesma view; a segunda
existe para fixar a triagem escolhida no `pk` e sobreviver ao redirecionamento de
erro.

`GET` monta quatro coisas:

- `triagens`: as últimas dez triagens concluídas (`SUBMITTED` ou `CLOSED`), cada
  uma com paciente, aluno e "Recebida em"; a escolhida vem marcada;
- `teachers`: professores, filtráveis por `?area=`;
- `chosen`: os professores que já respondem pelo paciente, para o formulário
  nascer marcado;
- `recent`: os seis encaminhamentos mais recentes, com selo "Concluído" quando o
  paciente já está em atendimento e "Pendente" quando ainda não.

`selected_triage` usa `get_object_or_404` sobre `concluded(user)` quando há `pk`
na URL, e a primeira da lista quando não há.

`POST` recusa sem triagem escolhida e sem professor escolhido, com
`messages.error` e redirecionamento de volta. Dando certo, `refer()` roda dentro
de `transaction.atomic()`: define os responsáveis do paciente, marca a triagem
como `REFERRED`, grava `closed_by` e `closed_at`. O `save()` da `TriageRecord`
propaga o estado para o paciente pelo `FLOW_BY_TRIAGE_STATUS`.

### 3.6 `/supervisor/feedbacks/` — Feedback sobre triagens

`CoordinatorFeedbacksView` (`supervisor/views/feedbacks.py`). A lista percorre
todas as triagens visíveis e classifica cada uma em `situation()`:

| Situação | Quando | Selo | Escreve? |
|---|---|---|---|
| Em triagem | ficha ainda aberta (`OPEN`) | `secondary` | Não |
| Pendente | finalizada pelo aluno e sem parecer | `danger` | Sim |
| Enviado | já tem parecer | `success` | Não |

"Finalizada pelo aluno" é a tupla `FINISHED`: `SUBMITTED`, `FINALIZED_EDITION`,
`CLOSED` e `REFERRED`. `writable()` é `FINISHED` com `pareceres = 0`, e é ela que
alimenta tanto o formulário (`?triagem=<pk>`) quanto o `post()` — pedir parecer
de uma triagem em andamento responde 404 em vez de gravar.

O `POST` recusa parecer em branco com `messages.error` e, dando certo, cria o
`TriageFeedback` e avisa o nome do aluno. O filtro `?situacao=` aceita
`em_triagem`, `pendente` e `enviado`.

### 3.7 `/supervisor/orientacao/` — Painel de orientação

`PainelOrientacaoSupervisorView` (`supervisor/views/orientation.py`) veio da
`dev`. É a tela do Coordenador sobre os alunos orientandos: alunos vinculados e
disponíveis, triagens pendentes (`SUBMITTED`), histórico das que já saíram do
"aguardando parecer" e todos os encaminhamentos, mais os formulários de vincular
aluno e lançar horas. Continua no grupo do Django, não na role.

### 3.8 `painel/`, `perfil/`, `areas/` e `register/`

`PainelSupervisorView` lista alunos e professores como suas subclasses reais, não
como `CustomUser` genérico, para que `crp`, `acting_areas` e `matricula` venham
preenchidos. `PerfilSupervisorView` edita o próprio cadastro e cria o `Teacher`
correspondente quando o usuário ainda não tem um. As três telas de área são
`ListView`/`CreateView`/`UpdateView` sobre `AreaActing`, as duas de escrita com
`PermissionRequiredMixin`. `cadastrar_supervisor` é do Superadmin: gera senha
temporária, envia por e-mail e volta para `superadmin:painel`.

## 4. Rotas de triagem que o Coordenador usa

Ficam em `triage/urls.py`, sem `app_name`. São funções com `@login_required` e
checagem de role na mão.

| Rota | Nome | O que faz | Acesso |
|---|---|---|---|
| `/triage/supervisor_detail/<pk>/` | `triage_detail_supervisor` | Ficha completa com as ações | role `SV` ou `PR`, e `visible_to` |
| `/triage/lock_triage_editing/<pk>/` | `lock_triage_editing` | `SUBMITTED → FINALIZED_EDITION` | role `SV` |
| `/triage/feedback/<pk>/` | `create_feedback` | Parecer pela tela antiga | `TriageFeedback.can_be_created_by` |
| `/triage/create_referral/<pk>/` | `create_referral` | Encaminhamento por área, tela antiga | role `SV` |
| `/triage/edit/<pk>/` | `edit_triage` | Edita ficha + IARV | `SV`/`PR` com `visible_to` |

Detalhes que valem registro:

- `triage_detail_supervisor` calcula `triagem_editada_pos_envio` comparando
  `updated_at` da ficha e do IARV com `submitted_at` — é como a tela avisa que o
  aluno mexeu depois de enviar.
- `lock_triage_editing` é a trava: com a edição finalizada, o `editable_fields_for`
  do `TriageRecord` passa a devolver vazio para o Aluno.
- `create_referral` é o caminho antigo, por área de atuação, e cria um `Referral`
  de verdade; a tela nova (3.5) trabalha direto nos responsáveis do paciente e no
  status da triagem. Os dois convivem — é a pendência técnica 1.
- Todas as recusas usam `PermissionDenied`, que o `handler403` transforma em
  redirecionamento com aviso. Recusa com `ValidationError` virava 500.

## 5. Ordem dos fluxos

**Triagem e encaminhamento.** O aluno conclui a triagem e ela vai para a
coordenação. Página inicial (indicador "Triagens pendentes") → Triagens para
analisar → "Analisar" abre a ficha → Novo encaminhamento: escolher o paciente,
filtrar os professores pela área do caso, marcar quem recebe → "Confirmar
encaminhamento" → o caso aparece em Encaminhamentos recentes.

Concluir a triagem **não** dá alta ao paciente: a triagem é a etapa inicial do
atendimento, e a alta só existe no fim dele. Pelo `ALLOWED_TRANSITIONS`, a única
origem possível para "Alta" é "Em atendimento".

**Feedback.** Página inicial (indicador "Feedbacks a enviar") → Feedback sobre
triagens → "Escrever" → "Enviar avaliação" → a linha passa a "Enviado". Enquanto
o aluno não finaliza, a linha fica em "Em triagem" e não há o que escrever.

**Professores e Alunos.** Página inicial → listagem → "+ cadastrar" abre o
formulário na área correspondente, ou "Editar" abre o detalhe.

## 6. Origem dos dados

| Informação | Origem | Situação |
|---|---|---|
| Triagens pendentes | Triagens enviadas e não analisadas | Real |
| Encaminhamentos hoje | Triagens `REFERRED` com `closed_at` de hoje | Real |
| Professores ativos | Professores com orientando vinculado | Real |
| Feedbacks a enviar | Triagens finalizadas pelo aluno e sem parecer | Real |
| Atividades recentes e calendário | Triagens, encaminhamentos e pareceres | Real |
| Professores: área, alunos vinculados e situação | Cadastro e orientações abertas | Real |
| Alunos: orientador, área e fase | Cadastro do aluno | Real |
| Triagens: paciente e quem realizou | Ficha de triagem | Real |
| Triagens: "Recebida às" | Não existe data de envio da ficha | **Mock com TODO** |
| Triagens: situação "Editada" e "Atrasada" | Sem data de alteração nem prazo | **Mock com TODO** |
| Encaminhamento: alocação ao professor | Responsáveis pelo paciente | Real |
| Encaminhamentos recentes: Concluído e Pendente | Paciente já em atendimento | Real |
| Feedback: aluno, paciente e situação | Status da triagem e pareceres | Real |
| Cadastro de professor: as duas permissões | Não existem como campo | **Mock com TODO** |
| Cadastro de aluno: curso e período | Não existem como campo | **Mock com TODO** |

## 7. Mocks e TODOs

Tudo que não existe no banco fica em `supervisor/views/mocks.py`:

| Função | O que substitui | O que falta no banco |
|---|---|---|
| `submitted_at(record)` | "Recebida às" | Data de envio da ficha |
| `triage_status(record, now)` | Selo Analisar/Atrasada/Editada | Prazo de análise e data de edição |
| `teacher_permissions()` | As duas caixas do cadastro de professor | As permissões como campo |
| `student_enrollment_fields()` | Curso e período no cadastro de aluno | Os campos no cadastro |

`submitted_at` devolve `created_at` — a ficha já tem `submitted_at` como campo,
mas nem todo registro antigo tem valor, então a fila continua no mock até a
migração de dados. Botão ou link sem lógica leva
`{# TODO: botão sem lógica; fica para fazer #}` no template.

## 8. Templates e componentes

As telas novas estendem `supervisor/base_coordinator.html`, que estende
`base.html` e preenche `brand`, `main_nav` (Página inicial, Alunos, Professores,
Triagens, Feedbacks, Encaminhamentos), `user_links` e `footer`.

Reaproveitados do que já existia: `home_supervisor.html`, `list_users.html`, e os
cadastros em `teacher/cadastro.html` e `student/cadastro.html`. Novos:
`base_coordinator.html`, `alunos.html`, `triagens.html`, `triagem_detalhe.html`,
`encaminhamentos.html`, `feedbacks.html`, `professor_detalhe.html` e
`aluno_detalhe.html`. Seguem no layout antigo `supervisor_panel.html`,
`orientacao_panel.html`, `perfil.html`, `area_list.html`, `area_form.html`,
`cadastro_supervisor.html` e `register.html`.

As listagens usam `{% data_table %}`; os selos, `components/badge.html`; os
indicadores, `components/summary_list.html`; vazio e erro, `empty_state.html` e
`error_state.html`. Limites de cada peça em `componentes.md`.

## 9. Pendências técnicas

1. **Dois caminhos de encaminhamento.** A tela nova
   (`supervisor:encaminhamentos`) define os responsáveis do paciente e muda o
   status da triagem; a antiga (`create_referral`) cria um `Referral` por área.
   Falta escolher qual é o caminho oficial e o que fazer com o model do outro.
2. **Duas telas de parecer.** `supervisor:feedbacks` e `create_feedback` gravam o
   mesmo `TriageFeedback` em layouts diferentes.
3. **Data de envio.** `submitted_at` existe no model mas a fila ainda usa
   `created_at`; falta a migração de dados para trocar o mock pela consulta real.
4. **Prazo de análise.** "Atrasada" usa 24 horas fixas no mock. Falta o prazo
   definido pelo produto.
5. **Mecanismos misturados.** Telas novas na role, `painel/`, `perfil/`,
   `areas/` e `orientacao/` no grupo do Django; as rotas de `/triage/` conferem
   role na mão, sem mixin.
6. **Nome do papel.** Interface e código novo dizem Coordenador; pasta, rota,
   namespace, grupo e role ainda dizem Supervisor. A troca completa é uma task
   própria, porque atravessa migração de grupo e de dados.
