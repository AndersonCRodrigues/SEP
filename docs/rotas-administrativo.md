# Rotas da área do Administrativo

Especificação das rotas do Administrativo: o que cada tela mostra, por onde se
chega nela e como está implementada. Segue o mesmo formato de `rotas-aluno.md`,
`rotas-coordenador.md` e `rotas-paciente.md`, e detalha a linha do Administrativo
de `mapa_rota_permisao.md`.

A área tem um recorte próprio, e ele explica quase tudo o que vem a seguir: o
Administrativo opera o serviço — cadastro, agenda, salas e documentos — e **não
tem acesso clínico**. Triagem, prontuário e vínculo de caso simplesmente não
aparecem para ele, porque o papel não está declarado no `VISIBLE_TO` desses
querysets. É a única área do sistema em que a pessoa mexe no dia a dia do serviço
sem enxergar o conteúdo do atendimento.

---

## 1. Mapa das rotas

Prefixo `/administration/`, `app_name = "administration"`, arquivo
`administration/urls.py`.

| Rota | Nome | View | Template | Acesso |
|---|---|---|---|---|
| `/administration/` | `administration:home` | `AdministrativeHomeView` | `administration/home_administration.html` | `AdministrativeOnly` |
| `/administration/pacientes/` | `administration:pacientes` | `PatientsView` | `administration/pacientes.html` | `AdministrativeOnly` |
| `/administration/cadastrar-paciente/` | `administration:cadastrar_paciente` | `PatientRegistrationStartView` | — (redireciona) | `CanRegisterPatients` |
| `/administration/cadastrar-paciente/<step>/` | `administration:cadastrar_paciente_etapa` | `PatientRegistrationStepView` | `administration/cadastrar_paciente.html` | `CanRegisterPatients` |
| `/administration/pacientes/<pk>/cadastro-concluido/` | `administration:cadastro_concluido` | `RegistrationCompletedView` | `administration/cadastro_concluido.html` | `CanRegisterPatients` + `visible_to` |
| `/administration/agenda/` | `administration:agenda` | `ScheduleView` | `administration/agenda.html` | `AdministrativeOnly` + `visible_to` |
| `/administration/salas/` | `administration:salas` | `RoomsView` | `administration/salas.html` | `AdministrativeOnly` + `visible_to` |
| `/administration/declaracoes/` | `administration:declaracoes` | `DeclarationsView` | `administration/declaracoes.html` | `AdministrativeOnly` + `visible_to` |
| `/administration/atestados/` | `administration:atestados` | `CertificatesView` | `administration/atestados.html` | `CanIssueCertificates` |
| `/administration/atestados/atendimentos/` | `administration:atestados_atendimentos` | `CertificateAppointmentsView` | — (JSON) | `CanIssueCertificates` |
| `/administration/painel/` | `administration:painel` | `PainelAdministracaoView` | `administration/administration_panel.html` | `AdministrativeOnly`, tela antiga |
| `/administration/perfil/` | `administration:perfil` | `PerfilAdministrativoView` | `administration/perfil.html` | `AdministrativeOnly`, só o próprio |
| `/administration/cadastrar/` | `administration:cadastrar` | `cadastrar_administrativo` | `administration/cadastro.html` | `has_perm("core.add_customuser")`, Superadmin |

As views ficam no pacote `administration/views/`, um módulo por assunto:
`home.py`, `patients.py`, `schedule.py`, `rooms.py`, `declarations.py`,
`certificates.py`, `account.py`, mais `access.py` (os três mixins) e `dates.py`
(rótulos de dia e faixas de período). O assistente de cadastro fica fora do
pacote, em `administration/patient_registration.py`, porque é máquina de estados,
não view.

`cadastrar/` está nesta área mas não é tela do Administrativo: quem abre é o
Superadmin, pela permissão do Django.

## 2. Como o acesso funciona

`administration/views/access.py` tem três mixins, e essa é a diferença desta área
para as outras — em vez de um mixin de role e checagens espalhadas, a regra de
negócio entra na porta:

```python
class AdministrativeOnly(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.role == CustomUser.Role.ADMINISTRATIVO


class CanRegisterPatients(AdministrativeOnly):
    def test_func(self):
        return super().test_func() and Patient.can_be_created_by(self.request.user)


class CanIssueCertificates(AdministrativeOnly):
    def test_func(self):
        return super().test_func() and AttendanceCertificate.can_be_created_by(
            self.request.user
        )
```

Os dois mixins derivados somam a role à regra declarada no model
(`CREATABLE_BY`). O ganho é que, se a matriz de permissões mudar de ideia sobre
quem cadastra paciente ou emite atestado, a rota acompanha sem edição.

Quem não está autenticado cai no `/login/` com `next`. Quem está autenticado em
outra role recebe 403, e o `handler403` redireciona para a home da própria role
com a mensagem de aviso. O Superadmin **não** entra: `AdministrativeOnly` confere
a role, e `is_superuser` não é role.

O que o Administrativo lê:

| Model | Recorte |
|---|---|
| `Patient` | `ALL` |
| `Appointment` e `AppointmentRequest` | `ALL` |
| `Room` | `ALL` (o queryset declara `ANY`) |
| `RoomBooking` | `ALL` |
| `AttendanceCertificate` e `InternshipDeclaration` | `ALL` |
| `TriageRecord`, `TriageFeedback`, `Referral`, IARV | **nada** |
| `ProgressNote` | **nada** |
| `CaseAssignment` | **nada** |

"Nada" é literal: `scope_for` não encontra o papel nem a chave `ANY` e
`visible_to` devolve `none()` (`core/permissions.py`). Não é um filtro que
esvazia a tela — é a ausência de qualquer tela dessas na área.

O que o Administrativo escreve:

| Model | Regra |
|---|---|
| `Patient` | `CREATABLE_BY`, e `EDITABLE_FIELDS` nos campos de cadastro |
| `AttendanceCertificate` e `InternshipDeclaration` | `CREATABLE_BY`, e os campos do documento |
| `AppointmentRequest` | `status`, `response`, `answered_by`, `answered_at` — sem tela, pendência 3 |

## 3. Rota por rota

### 3.1 `/administration/` — Página inicial

`AdministrativeHomeView` (`administration/views/home.py`), um `TemplateView`.

Quatro indicadores, em `operational_summary()`:

| Indicador | Consulta |
|---|---|
| Salas ocupadas | `len(busy_until(user))` sobre o total de salas utilizáveis |
| Atendimentos hoje | `Appointment` com `scheduled_at` de hoje |
| Declarações pendentes | `AttendanceCertificate` do tipo declaração + `InternshipDeclaration`, ambos pendentes |
| Atestados emitidos | `AttendanceCertificate` com `issued_at` de hoje |

"Declarações pendentes" soma dois models diferentes porque a declaração de
comparecimento e a de estágio são tabelas separadas, com o mesmo significado para
quem está no balcão.

`recent_activities()` junta três origens numa lista só, ordena por momento e
corta nas cinco mais recentes: agendamentos criados, documentos emitidos e salas
liberadas. A liberação de sala não tem hora — só `end_date` — então
`as_instant()` converte a data em meia-noite para que a ordenação funcione. É um
empate assumido: a sala liberada aparece no fim do dia dela.

O calendário vem de `core/month_calendar.py` e marca os dias com atendimento.

Diferente das outras homes, esta não trata `DatabaseError`: falha de banco sobe
como erro. As telas de sala, declaração e agenda tratam.

### 3.2 `/administration/pacientes/` — Pacientes

`PatientsView` é um `TemplateView` sem consulta nenhuma, e o template tem só o
título e o link "+ Novo Cadastro". Apesar do nome, a tela **não lista pacientes**
— é uma porta para o assistente. Está registrado como pendência 1.

### 3.3 O assistente de cadastro de paciente

Três rotas e um objeto de estado, `PatientRegistration`
(`administration/patient_registration.py`), que guarda as respostas na sessão sob
a chave `patient_registration`.

São dez etapas (`STEPS`), agrupadas em cinco seções: Identificação, Contatos,
Endereço, Acompanhante e Encerramento. Cada etapa é um `Step` congelado, com
slug, seção, título, ícone e o formulário de uma pergunta só.

`PatientRegistrationStartView` zera a sessão e manda para a primeira etapa. Daí
em diante, `PatientRegistrationStepView` cuida de tudo:

- **GET** de uma etapa que não existe volta para a primeira; de uma etapa à
  frente da primeira ainda não respondida, volta para essa pendente
  (`is_ahead` + `first_unanswered`). É o que impede terminar o cadastro digitando
  a URL da última etapa.
- **POST** com `action=back` salva o que foi digitado e volta uma etapa, sem
  validar — voltar não pode exigir acerto.
- **POST** normal valida, salva e segue; na última etapa, confere se sobrou
  alguma pendente antes de concluir.
- Duas etapas são condicionais (`only_if_accompanied`): nome do responsável e
  grau de parentesco só entram quando a resposta de "está acompanhado?" for
  "sim". `save()` apaga as respostas dessas etapas quando a pessoa volta e muda a
  resposta, para não gravar responsável de quem veio sozinho.

`complete()` roda em `transaction.atomic()`: revalida todas as etapas, monta o
`Patient`, chama `full_clean(exclude=["password"])` antes de criar — para que
erro de modelo apareça como mensagem, não como 500 —, cria pelo
`Patient.objects.create_with_credentials`, que gera senha temporária, marca
`must_change_password` e envia o e-mail, sincroniza o grupo e limpa a sessão.
Erro de validação aqui volta para a primeira etapa com `messages.error`.

`RegistrationCompletedView` é um `DetailView` sobre `Patient.visible_to(user)`.

### 3.4 `/administration/agenda/` — Agenda

`ScheduleView` (`administration/views/schedule.py`). Quatro filtros, todos por
query string, e todos validados contra uma lista fechada antes de irem para o
banco:

| Filtro | Parâmetro | Valores |
|---|---|---|
| Período | `?periodo=` | `hoje` (padrão), `semana`, `mes`, `todos` |
| Situação | `?situacao=` | `Appointment.Status.values` |
| Tipo | `?tipo=` | `Appointment.Kind.values` |
| Sala | `?sala=` | pk, só se `isdigit()` |

`chosen()` devolve string vazia para valor fora da lista, então parâmetro
inventado é ignorado em vez de quebrar a consulta. As faixas de data saem de
`dates.period_range`; a semana começa no domingo, como o calendário do projeto.

Cada linha traz `day_label` ("Hoje", "Ontem", "Amanhã", o nome do dia da semana
quando está a menos de sete dias, ou a data), o horário, a sala, quem atende
(aluno designado ou professor) e o selo de situação por `STATUS_LEVELS`.

### 3.5 `/administration/salas/` — Salas

`RoomsView` (`administration/views/rooms.py`) mostra cartões, não tabela. O
estado de cada sala sai de `as_card()`, nesta ordem:

| Estado | Quando | Selo |
|---|---|---|
| `maintenance` | sala em manutenção | `warning` |
| `inactive` | sala inativa | `secondary` |
| `occupied` | sala em `busy_until` | `danger`, "Ocupada até HH:MM" |
| `available` | o resto | `success` |

A ordem importa: sala em manutenção com reserva antiga aparece como manutenção, e
não como ocupada.

A ocupação vem de `scheduling/occupancy.py`, compartilhado com a home:
`running_appointments()` acha os atendimentos acontecendo agora (começaram, ainda
não terminaram pela duração), e `busy_until()` junta esses com as reservas fixas
de `RoomBooking.occupying()`, ficando com o horário de término mais tarde entre
os dois. A janela de um dia no filtro de `running_appointments` existe para não
varrer a tabela inteira a cada carregamento.

Falha de banco troca a lista por vazio e preenche `rooms_error`.

### 3.6 `/administration/declaracoes/` — Declarações

`DeclarationsView` (`administration/views/declarations.py`) junta os dois models
numa lista só, ordenada pela data de referência, da mais recente para a mais
antiga:

- `AttendanceCertificate` do tipo declaração, de paciente ou de aluno, com
  assunto "Comparecimento — <data>";
- `InternshipDeclaration`, sempre de aluno, com assunto "Estágio — <início> a
  <fim>".

`reference()` usa `issued_at` quando existe e a data de criação quando não — o
documento pendente ainda não tem data de emissão, e sem isso não daria para
ordenar as duas listas juntas. O selo é `success` quando emitido e `danger` no
resto.

A tela é de leitura: emitir declaração ainda não tem botão (pendência 2).

### 3.7 `/administration/atestados/` — Atestados

`CertificatesView` é um `FormView` com `MedicalCertificateForm`
(`administration/forms.py`), e é a tela com mais regra da área.

O campo `person` lista pacientes e alunos num select só, com o valor no formato
`"<tipo>:<pk>"` e o rótulo com nome, tipo e CPF mascarado. Os pacientes passam
pelo `visible_to`; os alunos são todos.

O campo `appointment` só aceita atendimentos **com presença registrada**
(`status = ATTENDED`) da pessoa escolhida — `appointments_for()` devolve
`none()` para qualquer entrada que não case. É a regra que impede emitir atestado
de comparecimento para quem não compareceu, e ela vale no servidor, não só na
tela.

`/administration/atestados/atendimentos/` é o outro lado disso:
`CertificateAppointmentsView` devolve JSON com os atendimentos da pessoa, para o
segundo select carregar sem recarregar a página. Usa o mesmo
`appointments_for()`, então o endpoint não é uma porta mais larga que o
formulário.

`issue()` monta o conteúdo a partir da data e hora do atendimento, acrescenta as
observações quando houver, e cria o `AttendanceCertificate` já emitido, com
`issued_at` de hoje e `issued_by` do usuário. A tela mostra os cinco atestados
mais recentes.

### 3.8 `painel/`, `perfil/` e `cadastrar/`

`PainelAdministracaoView` é a tela antiga, um `TemplateView` sem consulta.
`PerfilAdministrativoView` é um `UpdateView` cujo `get_object` devolve
`self.request.user` — só o próprio cadastro, só os campos de contato e endereço.
`cadastrar_administrativo` recusa com `PermissionDenied` quem não tem
`core.add_customuser`, salva, sincroniza o grupo e volta para
`superadmin:painel`.

## 4. Ordem dos fluxos

**Cadastro de paciente.** Página inicial → Pacientes → "+ Novo Cadastro" →
assistente, uma pergunta por tela, com o mapa das seções ao lado → conclusão →
tela de cadastro concluído. O paciente recebe a senha temporária por e-mail e
troca no primeiro acesso.

**Agenda.** Página inicial (indicador "Atendimentos hoje" ou a atividade
recente) → Agenda, que abre no dia de hoje → filtros de período, situação, tipo e
sala.

**Salas.** Página inicial (indicador "Salas ocupadas") → Salas, que mostra o
estado de cada uma neste instante.

**Documentos.** Página inicial (indicadores "Declarações pendentes" e "Atestados
emitidos") → Declarações, que é leitura, ou Atestados, onde se escolhe a pessoa,
a data do atendimento e emite.

## 5. Origem dos dados

| Informação | Origem | Situação |
|---|---|---|
| Salas ocupadas e estado das salas | `Room`, `RoomBooking` e `Appointment`, via `scheduling/occupancy.py` | Real |
| Atendimentos hoje e agenda | `Appointment` | Real |
| Declarações pendentes e emitidas | `AttendanceCertificate` e `InternshipDeclaration` | Real |
| Atestados emitidos | `AttendanceCertificate` do tipo atestado | Real |
| Atividades recentes | Agendamentos, documentos e salas liberadas | Real |
| Calendário | `Appointment` do mês | Real |
| Pessoas do formulário de atestado | `Patient.visible_to` e `Student` | Real |
| Atendimentos do formulário de atestado | `Appointment` com presença registrada | Real |
| Cadastro de paciente | Persiste de verdade, com senha temporária por e-mail | Real |

A área não tem mock de dado: tudo que aparece existe no banco. O que tem `TODO`
são botões sem lógica — os três ícones do header em `base_admin.html` e um botão
em `agenda.html` e outro em `declaracoes.html`, todos com
`{# TODO: botão sem lógica; fica para fazer #}`.

## 6. Templates e componentes

Todas as telas estendem `administration/base_admin.html`, que estende `base.html`
e preenche `brand`, `main_nav` (Página inicial, Pacientes, Agenda, Salas,
Declarações, Atestados), `user_links` e `footer`, além de declarar um bloco
`page_header` próprio.

Agenda e Declarações usam `{% data_table %}`; os selos são
`components/badge.html`; vazio e erro, `empty_state.html` e `error_state.html`; o
formulário de atestado usa `components/form.html`. Salas é marcação própria,
porque a tela é de cartões e nenhum componente cobre isso. A home escreve os
indicadores à mão, em vez de usar `summary_list.html`.

## 7. Pendências técnicas

1. **A tela de Pacientes não lista pacientes.** `PatientsView` não consulta
   nada; o template tem só o título e o link do assistente. Ou ganha a listagem
   (com busca, como as do Coordenador), ou o item do menu deveria apontar direto
   para o cadastro.
2. **Declarações só de leitura.** A tela lista pendentes e emitidas, mas não há
   como emitir uma declaração — só atestado tem formulário. Falta a tela de
   emissão, ou a decisão de que a declaração nasce em outro lugar.
3. **Solicitações de horário sem tela.** O `AppointmentRequest` dá ao
   Administrativo `status`, `response`, `answered_by` e `answered_at` em
   `EDITABLE_FIELDS`, e nenhuma view usa esses campos. O Paciente manda o pedido
   e ele fica pendente para sempre — a mesma pendência aparece em
   `rotas-paciente.md`.
4. **Home sem tratamento de falha.** As outras telas da área tratam
   `DatabaseError` e mostram estado de erro; a home não.
5. **Indicadores da home.** Escritos à mão, fora do `summary_list.html`, como os
   do Paciente.
6. **Nota desatualizada em `componentes.md`.** Lá está escrito que
   `administration/base_admin.html` não carrega Bootstrap; hoje ele estende
   `base.html`, que carrega. A nota deve sair na próxima passagem por aquele
   documento.
