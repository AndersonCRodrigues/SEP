# Regras de negócio nos models

Dois mecanismos que você precisa conhecer antes de mexer em qualquer model deste
projeto. Ignorá-los não gera erro de import — gera regra de acesso furada ou
histórico clínico incompleto, que só aparecem em produção.

Para criptografia, auditoria e configuração de ambiente, ver
[seguranca-e-ambiente.md](seguranca-e-ambiente.md).

---

## 1. `BusinessRulesMixin` — quem pode o quê

### O problema que ele resolve

A matriz de permissões do SEP opera em três granularidades, e **só a primeira
cabe no sistema nativo de `Permission` do Django**:

| Granularidade | Exemplo da matriz | Onde vive |
|---|---|---|
| Model | "Supervisor: Read Todos" | `Permission` do Django |
| **Linha** | "Professor vê pacientes dos seus alunos" | `visible_to()` |
| **Campo** | "Paciente edita só endereço e telefone" | `EDITABLE_FIELDS` |

`core/permissions.py` cobre os níveis 2 e 3. Ele não importa nada de
`core.models` de propósito: `CustomUser` importa daqui, e o caminho inverso
criaria ciclo.

O nível 1 é preenchido a partir dos outros dois — ver *Projeção sobre o
`Permission` do Django*, adiante.

### As quatro declarações

Toda model de conteúdo declara quatro coisas — três constantes e um queryset:

```python
class RoomQuerySet(RoleScopedQuerySet):
    VISIBLE_TO = {ANY: ALL}


class Room(BusinessRulesMixin, models.Model):
    name = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=2, choices=Status.choices)

    objects = RoomQuerySet.as_manager()

    CREATABLE_BY = (Role.ADMINISTRATIVO,)
    EDITABLE_FIELDS = {Role.ADMINISTRATIVO: ("name", "room_type", "status")}
    DELETABLE_BY = (Role.ADMINISTRATIVO,)
```

- **`CREATABLE_BY`** — papéis que podem criar.
- **`EDITABLE_FIELDS`** — `{papel: (campos graváveis)}`. Papel ausente do dicionário
  não edita **nada**. Não existe "edita tudo": os campos são sempre explícitos.
- **`DELETABLE_BY`** — papéis que podem apagar. **Vazio é o default correto** neste
  projeto: 14 das 18 models não permitem exclusão, porque prontuário clínico não
  se apaga, encerra-se. Abrem exceção `AreaActing`, `Attendance`,
  `PerformanceReview` e `StudentActivity` — e nesta última só as linhas lançadas
  à mão, nunca as geradas por signal.
- **`VISIBLE_TO`** — no `QuerySet`, `{papel: ALL | callable(user) -> Q}`. Papel
  ausente não enxerga nada. `ANY` como chave atende quem não tem entrada própria —
  é o "todo autenticado lê" de `AreaActing`, `Room` e `ProfessorArea`.

As quatro são **declarações**, não código. Nenhuma delas tem `if` de papel: quem
resolve papel é o `BusinessRulesMixin` e o `RoleScopedQuerySet`, num lugar só.

### Como elas se combinam

O método que importa é `can_be_changed_by()`, e ele **cruza os dois níveis**:

```python
def can_be_changed_by(self, user):
    if not self.editable_fields_for(user):
        return False
    return type(self).objects.visible_to(user).filter(pk=self.pk).exists()
```

Ter permissão de campo não basta — a linha também precisa estar no seu escopo.
É isso que impede um professor de editar a declaração de estágio de um aluno que
não é orientando dele, mesmo que `EDITABLE_FIELDS` liste o papel `PROFESSOR`.

| Pergunta | Chamada |
|---|---|
| Que linhas esse usuário vê? | `Model.objects.visible_to(user)` |
| Ele pode criar? | `Model.can_be_created_by(user, **contexto)` |
| Que campos ele grava nesta linha? | `obj.editable_fields_for(user)` |
| Ele pode alterar esta linha? | `obj.can_be_changed_by(user)` |
| Ele pode apagar esta linha? | `obj.can_be_deleted_by(user)` |

### Papéis que herdam de outro

"Supervisor pode fazer tudo que o Professor faz" é regra do negócio, e estava
escrita à mão em cada model — quando estava. O resultado mensurável: o Supervisor
tinha **37** permissões e o Professor, **40**. Nove pontos em que o mais graduado
podia menos, porque alguém esqueceu de repetir a linha.

A herança agora é declarada uma vez, em `core/permissions.py`:

```python
INHERITS = {Role.SUPERVISOR: Role.PROFESSOR}
```

`roles_for(role)` devolve a cadeia (`SUPERVISOR` → `PROFESSOR`), e as três
consultas do mixin percorrem ela: `creatable_by_role`, `deletable_by_role` e
`editable_fields_for_role`. Os campos são **união**, não substituição — declarar o
papel herdeiro serve para ampliar, nunca para reduzir. `Advising` usa isso: o
Professor fecha (`end_date`), o Supervisor também troca `teacher` e `term`.

**Declare sempre pelo papel mais restrito.** Escrever
`CREATABLE_BY = (Role.PROFESSOR,)` já contempla o Supervisor. Repetir os dois é
ruído que volta a divergir no próximo campo novo.

A herança vale para `VISIBLE_TO` também, mas ali ela quase nunca dispara: o
Supervisor lê **tudo**, não o mesmo que o Professor, então cada queryset declara
`Role.SUPERVISOR: ALL` explicitamente. E é bom que declare — o log de auditoria é
o único que **não** dá nada a ele, e um `SUPERVISOR: ALL` embutido na base abriria
a trilha inteira sem ninguém pedir.

Uma coisa a herança **não** alcança, de propósito:

- **O teto por linha.** `can_be_created_by` com contexto continua sendo escrito à
  mão, porque a restrição do Professor é dele, não do cargo acima:

  ```python
  def can_reach_student(user, student):
      if student is None:
          return False
      if user.role == Role.PROFESSOR:
          return student.current_advisor_id == user.pk
      return True
  ```

  O Professor alcança os próprios orientandos; o Supervisor alcança qualquer aluno.
  Herdar esse `if` daria ao Supervisor um teto que ele não tem — ele não orienta
  ninguém, e passaria a não poder criar nada.

`setup_roles` consulta pelos métodos do mixin, nunca pelas tuplas cruas. Ler
`role in model.CREATABLE_BY` direto ignora a herança e devolve o Supervisor ao
estado anterior, em silêncio.

### Quando a regra depende do contexto

`can_be_created_by` aceita `**context` justamente para isso. O professor só pode
abrir uma orientação **para si mesmo**:

```python
@classmethod
def can_be_created_by(cls, user, teacher=None, **context):
    if not super().can_be_created_by(user):
        return False
    if user.role == Role.PROFESSOR:
        return teacher is not None and teacher.pk == user.pk
    return True
```

O mesmo padrão aparece em `ProgressNote` (o paciente tem de estar em tratamento
ativo **e** sob responsabilidade do aluno), `Attendance`, `PerformanceReview`,
`StudentActivity` e `CaseAssignment`.

Repare no `super()` na primeira linha: a checagem de papel continua valendo, e a
sobrescrita só **restringe**. Nunca escreva uma sobrescrita que amplie.

### Quando a regra depende do estado da linha

Aí a sobrescrita é de `editable_fields_for`:

```python
def editable_fields_for(self, user):
    if user.is_authenticated and user.role == Role.ALUNO and not self.is_open:
        return ()
    return super().editable_fields_for(user)
```

Esse é o `TriageRecord`: o aluno preenche a ficha enquanto a triagem está aberta
e perde a edição quando o Supervisor fecha o caso. Outros casos no projeto:

- `BaseIarv` — o instrumento de risco segue o estado da **triagem**, não o próprio.
- `ProgressNote` — o Supervisor só grava a confirmação **enquanto pendente**.
- `StudentActivity` — linha gerada por signal (com `appointment` preenchido) não
  é editável **por ninguém**, porque o próximo `save()` do agendamento
  sobrescreveria a edição em silêncio.

Uma exceção que vale entender: quando a triagem fecha, o aluno perde o caso mas
**mantém o `TriageFeedback`**. O `TriageFeedbackQuerySet` não filtra por status
de propósito — o parecer é o retorno pedagógico, e é o que sobra para ele.

### Campos editáveis calculados, não listados

`TriageRecord` tem mais de 30 campos de ficha. Listá-los em `EDITABLE_FIELDS`
viraria lista morta na primeira alteração do model. Nesses casos, declare os
campos de **controle** e derive o resto:

```python
CONTROL_FIELDS = frozenset(
    {"id", "patient", "student_author", "status", "closed_by", "closed_at", "created_at"}
)

@classmethod
def ficha_fields(cls):
    return tuple(
        f.name for f in cls._meta.concrete_fields if f.name not in cls.CONTROL_FIELDS
    )

@classmethod
def editable_fields_for_role(cls, role):
    if role == Role.ALUNO:
        return cls.ficha_fields()
    if role == Role.SUPERVISOR:
        return cls.ficha_fields() + ("status", "closed_by", "closed_at")
    return ()
```

Campo novo na ficha entra editável sozinho; campo de controle novo tem de entrar
em `CONTROL_FIELDS`. É a inversão certa: a lista curta é a das exceções.

### Regras em model abstrato

`BaseIarv` é abstrato e declara as regras uma vez; `IarvAdult`, `IarvAdolescent`
e `IarvChild` herdam tudo, inclusive o `objects = IarvQuerySet.as_manager()`.
Quando três models compartilham a mesma regra, declare na base — não copie.

### Projeção sobre o `Permission` do Django

`core/management/commands/setup_roles.py` cria os `Group` dos papéis e aplica as
permissões **derivadas das declarações acima**:

```python
if role in model.CREATABLE_BY:            → add_<model>
if model.editable_fields_for_role(role):  → change_<model>
if role in model.DELETABLE_BY:            → delete_<model>
if _le(model, role):                      → view_<model>
```

O `view_` sai de `readable_by_role()`, que lê o `VISIBLE_TO` direto. Antes era
uma sondagem: o comando fabricava um `CustomUser(pk=0)` falso, montava o queryset
e checava `query.is_empty()`. Funcionava, mas dependia de a consulta ficar vazia
para concluir que o papel não lê — frágil. As permissões de gestão de usuário saem
de `MANAGEABLE_ROLES_BY`.

**Não mantenha lista fixa de permissões.** A versão anterior do comando tinha uma,
e ela apontava para `students.add_aluno` e `teacher.add_professor` muito depois da
renomeação — 12 permissões eram puladas em silêncio e o grupo `Students` ficava
sem nenhuma.

### O que **não** está aqui: gestão de usuário

`CustomUser`, `Teacher` e `Student` **não** usam o mixin. É deliberado, e há duas
razões:

1. As regras de usuário são chaveadas pelo **papel do alvo** ("Supervisor cria
   Professor/Aluno"), formato diferente das outras tabelas da matriz, que são
   chaveadas pelo objeto.
2. Enquanto foram métodos de `CustomUser`, toda subclasse de herança multi-tabela
   — `Teacher`, `Student`, `Patient` — **herdava poder de administrar usuários sem
   declarar nada**. Um `Patient` podia gerenciar usuários. Mover para funções de
   módulo trocou o comportamento de *fail-open* para *fail-closed*.

Elas vivem em `core/user_management.py`:

```python
can_manage_user(actor, target_role)      # colunas Create e Delete
editable_user_fields(actor, target)      # coluna Update
```

`can_manage_user` trata `is_superuser` como Superadmin: uma conta criada por
`createsuperuser` nasce com `role` no default e perderia acesso a tudo.

### Autorização não é mecanismo

`CREATABLE_BY` e `EDITABLE_FIELDS` dizem **quem pode provocar** a mudança. Não
dizem que a escrita acontece por `Model.objects.create()`.

Em `Advising` e `CaseAssignment`, por exemplo, a autorização está declarada no
model, mas quem executa é um método de manager — ver a parte 2. A view faz sempre
os dois passos:

```python
if not Advising.can_be_created_by(request.user, teacher=prof):
    raise PermissionDenied
Advising.objects.change_advisor(aluno, prof, term="2026.1")
```

### Cuidado: `ModelForm` com `exclude`

Um `ModelForm` declarado com `exclude` inclui **todo campo novo do model
automaticamente**. Ao acrescentar `status`, `closed_by` e `closed_at` ao
`TriageRecord`, os três entraram sozinhos no `TriageRecordForm` — e o aluno
passaria a poder fechar a própria triagem pela tela.

Ao adicionar campo de controle a um model, confira os forms que o usam.

### Checklist para uma model nova

1. Herde `BusinessRulesMixin` **antes** de `models.Model`.
2. Crie um `QuerySet` herdando `RoleScopedQuerySet` e declare `VISIBLE_TO`.
   Deixar vazio levanta `NotImplementedError` — não existe default silencioso.
   Não escreva `visible_to()`: a base resolve papel, herança e `distinct()`.
3. Declare as três constantes. `DELETABLE_BY = ()` até que alguém peça o
   contrário.
4. Se a criação depender de contexto, sobrescreva `can_be_created_by` chamando
   `super()`.
5. Se a edição depender do estado da linha, sobrescreva `editable_fields_for`
   chamando `super()`.
6. Se o model tiver muitos campos de conteúdo, derive os editáveis do `_meta` em
   vez de listá-los.

Existe um teste de cobertura que varre os apps do projeto — `core`, `areas`,
`teacher`, `students`, `patient`, `triage`, `documents`, `audit` — e **falha se
uma model nova não declarar regra**, com lista de exceções explícita
(`CustomUser`, `Teacher`, `Student`). Se você adicionou uma model e o teste
quebrou, ele está certo.

---

## 2. "Histórico é derivado"

### O problema que ele resolve

Duas informações no banco dizem a mesma coisa:

- **O ponteiro** — `Student.current_advisor`.
- **A linha aberta** — o `Advising` com `end_date IS NULL`.

Se as duas puderem ser escritas independentemente, elas divergem. Já divergiam:
gravar `student.current_advisor = prof` direto trocava o orientador **sem deixar
rastro nenhum** no histórico. Só os métodos de manager registravam.

Vale para **um** vínculo por vez. Onde o aluno acumula vínculos simultâneos não há
ponteiro possível, e a regra não se aplica — ver *"Quando não há ponteiro"*,
adiante.

### A regra

> **O ponteiro no aluno é a fonte da verdade. O histórico deriva dele, por signal.**

O ponteiro venceu porque ele é quem as consultas usam: `current_advisor_id`
aparece em 8 filtros de `visible_to`, espalhados por quatro apps. Property não
funciona em `filter()`, e derivar o ponteiro do histórico transformaria cada um
desses filtros num join com `.distinct()`.

### Como funciona

Em `students/signals.py`, dois receptores em `Student`:

```
save()
  │
  ├─ pre_save  ── capture_previous_links()
  │               lê current_advisor_id do banco
  │
  ├─ [ o UPDATE acontece ]
  │
  └─ post_save ── sync_link_history()
                  compara antes x depois; para o que mudou, chama
                  sync_from_student(), que fecha a linha aberta
                  (end_date = hoje) e abre a nova
```

Como **todo** caminho de escrita passa por `Student.save()`, não sobra rota
alternativa: `objects.create()`, `save(update_fields=[...])`, shell, `/admin/` —
todos registram.

### O guard

A outra metade: as models de histórico recusam escrita que não venha da
reconciliação.

```python
def save(self, *args, **kwargs):
    if not getattr(self, "_from_sync", False):
        raise ValueError(
            "Histórico é derivado: mova Student.current_advisor "
            "(Advising.objects.change_advisor)."
        )
    super().save(*args, **kwargs)
```

Isso cobre criação avulsa **e** edição de linha existente. As duas divergiriam:
mudar `teacher` numa orientação aberta, ou reabrir uma linha zerando `end_date`,
deixaria o histórico dizendo uma coisa e o ponteiro outra.

### Como fazer cada coisa

| Quero… | Faça |
|---|---|
| Trocar o orientador | `Advising.objects.change_advisor(aluno, prof, term="2026.1")` |
| Encerrar sem substituir | passe `None` como segundo argumento |
| Corrigir o período | não há caminho; encerre e reabra |
| Consultar o vínculo atual | `aluno.current_advisor` |
| Consultar o histórico | `aluno.advising_history` |

O `term` é opcional em `change_advisor`. Omitido, `current_term()` deriva do mês
(≤ 6 → `.1`, senão `.2`). Informado, ele viaja até o signal por
`student._advising_term`.

`change_advisor` existe porque guarda o que só ele sabe: recusar redesignar o
mesmo professor, e o `term` explícito. **Ele não escreve o histórico** — só move o
ponteiro e deixa o signal registrar.

### A invariante fica no banco

```sql
CREATE UNIQUE INDEX student_with_at_most_one_active_advising
  ON students_advising (student_id) WHERE (end_date IS NULL);
```

É índice parcial, não constraint — é como o Django materializa
`UniqueConstraint(condition=...)`. Por isso não aparece em `pg_constraint`.

### Por que não o contrário

Duas alternativas foram avaliadas e descartadas:

- **Signal na direção inversa** (`Advising.post_save` move o ponteiro). Termina,
  mas passa por um estado em que a reconciliação fecha a linha recém-criada e abre
  outra, deixando duplicata. Só funciona com flag de reentrância — acoplamento em
  anel.
- **Eliminar o ponteiro** e derivar `current_advisor` da linha aberta. Correto em
  teoria, caro na prática: degrada os 8 filtros da camada de permissões, que é
  o coração do projeto.

### Onde a regra vale

Só em `Advising` — é o único par ponteiro/histórico que sobrou. `Attendance`,
`PerformanceReview` e `StudentActivity` são registros independentes, sem ponteiro
correspondente, e se escrevem normalmente. A exceção parcial é `StudentActivity`:
linhas com `appointment` preenchido são mantidas por signal e não aceitam edição
manual, pelo mesmo motivo de fundo — quem manda nelas é o agendamento.

### Quando não há ponteiro

`CaseAssignment` seguia esta regra e **deixou de seguir**, porque o aluno passou a
atender vários pacientes ao mesmo tempo. Uma FK guarda um valor; N vínculos
simultâneos não cabem nela. Sem ponteiro não há o que derivar — a tabela virou a
própria fonte da verdade, e com isso caíram o `_from_sync`, o signal e a constraint
de um caso por aluno.

O que entrou no lugar:

```python
CaseAssignment.objects.assign(aluno, paciente)   # abre e poe o paciente em atendimento
CaseAssignment.objects.release(caso)             # fecha (end_date = hoje)
aluno.open_cases                                 # os casos abertos deste aluno
```

Duas invariantes, cada uma no seu lugar:

```sql
CREATE UNIQUE INDEX one_open_case_per_student_and_patient
  ON students_caseassignment (student_id, patient_id) WHERE (end_date IS NULL);
```

O par aberto é único no banco. O teto de dois alunos por paciente não cabe em
índice — "no máximo 2 linhas por paciente" não é unicidade — então mora em
`CaseAssignment.clean()`, chamado pelo `save()` quando a linha nasce aberta. É
mais fraco que a constraint, e é o melhor disponível.

**A consulta canônica.** "Quem este aluno atende" deixou de ser um atributo e
virou join. Para não escrever o mesmo join em seis lugares, `patient/models/patient.py`
expõe:

```python
def with_open_case(prefix="", **lookups):
    caminho = f"{prefix}assignment_history"
    filtros = {f"{caminho}__end_date__isnull": True}
    filtros.update({f"{caminho}__{campo}": valor for campo, valor in lookups.items()})
    return Q(**filtros)
```

Ela nasceu em `students/`, mas monta um `Q` sobre caminhos do **Patient**
(`assignment_history` é o reverso no paciente) e não era usada uma única vez dentro
de `students` — mudou para o app de quem a usa.

Usada nas quatro `visible_to` que dependiam de `responsible_students` — o acessor
reverso que sumiu junto com a FK — mais `ProgressNote` e os dois documentos. Toda
condição vai num único `Q`, para o ORM prendê-las à mesma linha do join; separá-las
em `filter()` encadeados casaria com linhas diferentes e vazaria acesso.

**Alta encerra o vínculo.** `Patient.advance_to(DISCHARGED)` fecha os casos abertos
do paciente. Sem isso `open_cases` mentiria, e o aluno continuaria enxergando um
paciente que recebeu alta. O contrário não vale: encerrar o caso de um aluno não dá
alta — o paciente pode ser reatribuído.

---

## 3. As horas do aluno

### Duas dimensões, não uma

`StudentActivity` responde a duas perguntas diferentes sobre a mesma hora, e elas
são ortogonais:

- `activity_type` — **o que** foi feito: triagem, atendimento, supervisão em grupo,
  prontuário.
- `category` — **como** a hora foi ganha: `PARTICIPATION` (o aluno foi) ou
  `EXECUTION` (o aluno realizou).

Colapsar as duas num campo só perderia informação: "triagem" não diz se o paciente
apareceu, e "participação" não diz do que o aluno participou. Um relatório de
estágio precisa das duas, e provavelmente vai somar cada uma sob um teto diferente.

### A regra do negócio

O aluno ganha hora por comparecer, mesmo que o paciente falte — foi ao serviço,
ficou à disposição. E ganha hora adicional por atender de fato. Daí o mapa:

| `Appointment.status`  | Participação | Realização |
| --------------------- | ------------ | ---------- |
| `ATTENDED`            | sim          | sim        |
| `PATIENT_NO_SHOW`     | sim          | não        |
| `STUDENT_NO_SHOW`     | não          | não        |
| `CANCELLED`           | não          | não        |
| `SCHEDULED`           | não          | não        |

A participação vale `StudentActivity.PARTICIPATION_HOURS` — valor fixo, porque não
depende da duração da sessão que não aconteceu. A realização vale
`duration_minutes / 60`, o tempo efetivo.

### Um agendamento, até duas linhas

Por isso a constraint é sobre o par, não sobre o agendamento sozinho:

```python
UniqueConstraint(
    fields=["appointment", "category"],
    condition=Q(appointment__isnull=False),
    name="one_activity_per_appointment_category",
)
```

Com `fields=["appointment"]` a segunda linha seria rejeitada pelo banco. A
condição parcial preserva o lançamento manual, que tem `appointment` nulo e não
disputa unicidade.

### O signal reconcilia, não acumula

`sync_student_activity` roda em todo `post_save` de `Appointment` e recalcula o
conjunto inteiro de linhas devidas — cria o que falta, atualiza o que mudou,
apaga o que deixou de ser devido. É idempotente: salvar o mesmo agendamento três
vezes não gera hora a mais.

O caso que exige o `delete` explícito é a correção de desfecho. Um agendamento
marcado como realizado por engano e depois corrigido para falta do paciente tem de
perder a linha de realização e **manter** a de participação — apagar tudo e
recriar seria mais simples, mas trocaria o `id` da linha que continua válida.

### Quem responde pela hora

`responsible_supervisor` é obrigatório com `PROTECT`: toda hora lançada tem alguém
que responde por ela. O agendamento nem sempre tem professor alocado, então o
signal cai no orientador do aluno (`current_advisor`). Sem nenhum dos dois não há
hora — o registro seria órfão, e o banco recusaria de todo jeito.

### Somar

`total_hours_for(student, start_date, end_date, category=None)` soma o período; sem
`category` soma tudo, com `category` soma só aquela fatia. O `Coalesce` devolve
`Decimal("0")` quando não há atividade, para quem chama não precisar tratar `None`.

---

## 4. O fluxo do paciente

### Uma fonte de verdade, não três

Antes desta seção o projeto respondia "onde este paciente está?" de três lugares
que podiam discordar: `Patient.flow_status` (que só tinha `IN_TRIAGE`),
`Patient.active_treatment` (booleano, `default=True`) e `TriageRecord.status`.
Um paciente recém-cadastrado, que nunca passou por triagem, já nascia
"em atendimento ativo" — e era esse booleano que decidia o que o aluno enxergava.

Hoje `flow_status` manda, e `active_treatment` derivou dele:

```python
@property
def active_treatment(self):
    return self.flow_status == self.FlowStatus.IN_TREATMENT
```

### Os cinco estados

| Estado | Entra quando |
|---|---|
| *(vazio)* | Administrativo cadastrou; ainda fora do fluxo |
| `IN_TRIAGE` | Aluno abriu a triagem |
| `AWAITING_REVIEW` | Aluno **enviou** a ficha (`TriageStatus.SUBMITTED`) |
| `REFERRED` | Supervisor encaminhou ao professor da área |
| `IN_TREATMENT` | Professor designou o aluno que vai atender |
| `DISCHARGED` | Alta, ou triagem fechada sem encaminhamento |

O estado vazio é deliberado: cadastrar não é entrar no fluxo. Quem tenta tratá-lo
como um sexto estado acaba escrevendo `flow_status or IN_TRIAGE` espalhado.

### A transição é evento, não campo

`flow_status` não está no `EDITABLE_FIELDS` de **ninguém** — há um teste que trava
se alguém o adicionar. Mover só acontece por `advance_to()`, que consulta o mapa:

```python
ALLOWED_TRANSITIONS = {
    "":               (IN_TRIAGE, IN_TREATMENT),
    IN_TRIAGE:        (AWAITING_REVIEW, REFERRED, DISCHARGED),
    AWAITING_REVIEW:  (IN_TRIAGE, REFERRED, DISCHARGED),
    REFERRED:         (IN_TRIAGE, IN_TREATMENT, DISCHARGED),
    IN_TREATMENT:     (DISCHARGED,),
    DISCHARGED:       (IN_TRIAGE,),
}
```

Três escolhas que não são óbvias:

- **`AWAITING_REVIEW → IN_TRIAGE`** existe porque o supervisor devolve a ficha com
  parecer para o aluno corrigir. É o "envia para os Alunos" da regra do negócio.
- **`DISCHARGED → IN_TRIAGE`** existe porque paciente volta ao serviço. É a única
  saída da alta — reabrir direto em atendimento pularia a triagem.
- **`"" → IN_TREATMENT`** é o buraco consciente: dá para designar um aluno a um
  paciente que nunca foi triado. O model sempre permitiu e esta seção não fechou;
  fechar é decisão de produto, não refatoração.

`advance_to` devolve `False` quando o paciente já está no destino — chamar de novo
não é erro nem escrita. Salto ilegal levanta `ValidationError` com os dois rótulos
em português: *"Não é possível ir de Em atendimento para Encaminhado ao professor."*

### Quem dirige

Ninguém escreve `flow_status` à mão. Dois pontos o movem:

- **`TriageRecord.save()`** compara o `status` gravado com o do banco e, só quando
  mudou, sincroniza o paciente por `FLOW_BY_TRIAGE_STATUS`. A comparação importa:
  sem ela, qualquer `save()` da ficha reempurraria o paciente para trás.
- **`CaseAssignment.objects.assign()`** põe em `IN_TREATMENT` ao abrir o caso.
  Designar o aluno **é** o que inicia o atendimento.

A alta continua sendo chamada explícita, e é a única transição com efeito colateral:
`advance_to(DISCHARGED)` fecha os casos abertos do paciente. O contrário não vale —
encerrar o caso de um aluno não dá alta, porque o paciente pode ser reatribuído, e
confundir as duas coisas apagaria tratamento em curso por efeito colateral.

### O envio da triagem

`TriageStatus` ganhou `SUBMITTED`. O aluno edita enquanto `OPEN` e chama
`submit()`, que recusa ficha já enviada e recusa quem não é o autor. A partir daí
`editable_fields_for` devolve `()` para ele — mas ele **continua lendo**:

```python
VISIBLE_TO_AUTHOR = (TriageStatus.OPEN, TriageStatus.SUBMITTED)
```

Sem isso o aluno perderia a ficha de vista no instante em que a enviasse, e o
feedback do supervisor chegaria sobre um documento que ele não pode mais abrir.
`TriageRecordQuerySet.visible_to` e `PatientQuerySet.visible_to` usam a mesma
constante, para não divergirem.

