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
class Room(BusinessRulesMixin, models.Model):
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=True)

    objects = RoomQuerySet.as_manager()      # traz visible_to()

    CREATABLE_BY = (Role.ADMINISTRATIVO,)
    EDITABLE_FIELDS = {Role.ADMINISTRATIVO: ("name", "active")}
    DELETABLE_BY = ()
```

- **`CREATABLE_BY`** — papéis que podem criar.
- **`EDITABLE_FIELDS`** — `{papel: (campos graváveis)}`. Papel ausente do dicionário
  não edita **nada**. Não existe "edita tudo": os campos são sempre explícitos.
- **`DELETABLE_BY`** — papéis que podem apagar. **Vazio é o default correto** neste
  projeto: 14 das 18 models não permitem exclusão, porque prontuário clínico não
  se apaga, encerra-se. Abrem exceção `AreaActing`, `Attendance`,
  `PerformanceReview` e `StudentActivity` — e nesta última só as linhas lançadas
  à mão, nunca as geradas por signal.
- **`visible_to(user)`** — no `QuerySet`, define quais linhas o usuário enxerga.

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

O `view_` sai de uma sondagem do próprio `visible_to`: monta o queryset para o
papel e checa `query.is_empty()`. Não toca no banco — só inspeciona a query.
As permissões de gestão de usuário saem de `MANAGEABLE_ROLES_BY`.

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
2. Crie um `QuerySet` herdando `RoleScopedQuerySet` e implemente `visible_to`.
   O `visible_to` da base levanta `NotImplementedError` — não existe default.
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

- **O ponteiro** — `Student.current_advisor`, `Student.current_patient`.
- **A linha aberta** — o `Advising` / `CaseAssignment` com `end_date IS NULL`.

Se as duas puderem ser escritas independentemente, elas divergem. Já divergiam:
gravar `student.current_advisor = prof` direto trocava o orientador **sem deixar
rastro nenhum** no histórico. Só os métodos de manager registravam.

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
  │               lê current_advisor_id e current_patient_id do banco
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
| Trocar o paciente | `CaseAssignment.objects.change_patient(aluno, paciente)` |
| Encerrar sem substituir | passe `None` como segundo argumento |
| Corrigir o período | não há caminho; encerre e reabra |
| Consultar o vínculo atual | `aluno.current_advisor` / `aluno.current_patient` |
| Consultar o histórico | `aluno.advising_history` / `aluno.case_history` |

O `term` é opcional em `change_advisor`. Omitido, `current_term()` deriva do mês
(≤ 6 → `.1`, senão `.2`). Informado, ele viaja até o signal por
`student._advising_term`.

Os métodos de manager continuam existindo porque guardam o que só eles sabem: as
validações de negócio (não redesignar o mesmo, respeitar o limite de 2 alunos por
paciente) e o `term` explícito. **Eles não escrevem o histórico** — só movem o
ponteiro e deixam o signal registrar.

### Duas invariantes ficam no banco

```sql
CREATE UNIQUE INDEX student_with_at_most_one_active_advising
  ON students_advising (student_id) WHERE (end_date IS NULL);

CREATE UNIQUE INDEX student_with_at_most_one_active_case
  ON students_caseassignment (student_id) WHERE (end_date IS NULL);
```

São índices parciais, não constraints — é como o Django materializa
`UniqueConstraint(condition=...)`. Por isso não aparecem em `pg_constraint`.

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

Só em `Advising` e `CaseAssignment` — são os dois pares ponteiro/histórico.
`Attendance`, `PerformanceReview` e `StudentActivity` são registros
independentes, sem ponteiro correspondente, e se escrevem normalmente. A exceção
parcial é `StudentActivity`: linhas com `appointment` preenchido são mantidas por
signal e não aceitam edição manual, pelo mesmo motivo de fundo — quem manda nelas
é o agendamento.
