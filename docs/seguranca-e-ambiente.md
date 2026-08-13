# Segurança e ambiente

Regras que valem para o projeto inteiro, não para um model específico:
criptografia de dado sensível, trilha de auditoria e a configuração que sustenta
as duas.

Para as regras de quem pode o quê em cada model, ver
[regras-nos-models.md](regras-nos-models.md).

---

## 1. Criptografia de dado sensível

Base: `utils/fields.py`, com `cryptography.fernet` — AES autenticado, simétrico.
`get_prep_value()` cifra antes de gravar, `from_db_value()` decifra ao ler. O
processo é transparente ao ORM.

Ver `docs/backend_criptografia/Criptografia_de_Dados.pdf` para a pesquisa que
originou o módulo, incluindo a rejeição de `django-cryptography` (quebra no
Django 6: `django.utils.baseconv` foi removido) e a medição de custo — ~0,15ms
por registro, linear.

### Cifrado no banco, em claro em Python

Esta é a distinção que mais confunde: `EncryptedTextField` protege o valor **na
tabela**. O atributo em Python está em texto puro — é o que torna o ORM
transparente, e é o que exige cuidado em qualquer lugar que persista esse valor
em outro canto.

### Não filtre nem ordene por campo cifrado

O Fernet usa IV aleatório: o mesmo texto gera token diferente a cada gravação.
Consequência:

```python
TriageRecord.objects.filter(chief_complaint__icontains="ansiedade")  # sempre vazio
TriageRecord.objects.filter(cpf__exact="12345678900")                # sempre vazio
```

Não levanta erro — **retorna vazio em silêncio**, que é pior.

Mitigações previstas no documento do módulo, ainda não implementadas aqui:

- **busca por conteúdo** — campo auxiliar não cifrado com palavras-chave
- **busca exata** — campo auxiliar com HMAC-SHA256 determinístico e indexado,
  usado só para localizar; o campo cifrado continua sendo a fonte da verdade

Hoje **nenhuma consulta do projeto toca campo cifrado** — 19 campos, zero
ocorrências em `filter`, `order_by`, `search_fields`, `list_filter` ou `unique`.
Ao mexer, mantenha assim ou implemente a mitigação junto.

### `CustomUser.cpf` ainda não é cifrado

Está em texto puro com `unique=True`. Se for cifrado, o `unique` deixa de
funcionar — tokens diferentes para o mesmo CPF — e o login por matrícula/CPF
quebra. É a mitigação do hash determinístico, e é tarefa própria.

---

## 2. Trilha de auditoria

`audit/` grava `SecurityLog`: quem fez o quê, quando, de qual IP, com o diff
antes→depois em JSON. Retenção de 1 ano, purgada por `pg_cron` dentro do banco.

### Campo cifrado é sensível por construção

Sem isto, o diff da auditoria gravaria a queixa clínica em **texto puro** dentro
do `audit_securitylog` — tabela com retenção e regras de acesso próprias. A
criptografia seria desfeita pela porta dos fundos.

```python
def _is_sensitive(field):
    return isinstance(field, EncryptedFieldMixin) or field.name in SENSITIVE_FIELDS
```

Critério **estrutural**, não lista de nomes: campo cifrado que alguém adicione
depois entra mascarado sozinho. Campo sensível não cifrado (CPF, endereço)
continua na lista explícita `SENSITIVE_FIELDS`.

No log, o sensível vira `{"changed": true}`; o comum mantém `{"old": ..., "new": ...}`.
Não se perde capacidade de auditoria — só o que não pode ser gravado.

### O que é auditado

Todo model do projeto que não seja do Django nem do próprio `audit` — este último
se exclui para não se auditar em laço.

O critério anterior era "herda `BusinessRulesMixin` ou `CustomUser`", e deixava
de fora model de negócio que ainda não declara regra de CRUD. Foi o caso do
`TriageRecord`, que entrou no projeto sem regra e ficaria sem trilha.

### Imutabilidade tem uma porta aberta de propósito

`SecurityLog.save()` recusa reedição e `delete()` recusa exclusão. Mas
`QuerySet.delete()` não passa por `Model.delete()` — é assim que a purga de
retenção e o `pg_cron` funcionam. Exceção deliberada, coberta por teste.

---

## 3. Configuração de ambiente

### `FIELD_ENCRYPTION_KEY` é validada no boot

O `settings.py` checa **formato**, não só presença:

```python
if len(base64.urlsafe_b64decode(FIELD_ENCRYPTION_KEY)) != 32:
    raise ImproperlyConfigured("...precisa ser 32 bytes em base64 url-safe...")
```

O motivo é concreto: o guia de setup manda colar
`FIELD_ENCRYPTION_KEY=(aqui cole sua chave)` no `.env`. O placeholder passava na
checagem de presença, a aplicação subia normalmente e só quebrava com
`ValueError: Fernet key must be 32 url-safe base64-encoded bytes` na primeira
gravação cifrada — no meio do cadastro de uma triagem.

**Configuração que só falha em uso é pior que configuração que falha no boot.**

### Uma chave por ambiente, para sempre

Trocar a chave torna ilegível todo dado já cifrado. Gere uma vez por ambiente:

```
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

O CI é a exceção: ele cria o banco do zero a cada execução, então gera uma chave
efêmera no próprio workflow. Nem chave fixa no repositório, nem secret a
administrar. **Não replique isso em ambiente com dado persistente.**

### Migrations não são versionadas

Decisão do time. O `CMD` do Dockerfile roda `makemigrations` a cada boot, e o
diretório `migrations/` só existe dentro do container.

Consequência conhecida e aceita: `docker compose up --build` contra um banco já
existente falha com `InconsistentMigrationHistory`, porque a imagem nova regera a
numeração. A saída é `docker compose down -v`, que **apaga o banco**.

No primeiro boot depois de um `down -v`, o `django-web` pode morrer com
`Connection refused`: o Postgres reporta *healthy* enquanto ainda roda os scripts
de init do `pg_cron` no servidor temporário, e reinicia em seguida. Um
`docker compose up -d django-web` resolve.

---

## 4. Estrutura de pacotes

### Todo app precisa de `__init__.py`

Sem ele o diretório vira *namespace package* (PEP 420). O Django tolera — foi por
isso que a ausência passou despercebida por muito tempo. O pytest não: ele deriva
o nome do módulo do caminho e chama todos os `tests.py` de `tests`, que colidem
entre si.

O `.gitignore` do projeto chegou a ter uma regra `__init__.py`, o que impedia
esses arquivos de existirem no repositório. Foi removida.

Vale também para subpacotes: `management/`, `management/commands/` e
`models/` quando o model vira pacote.

### `constants.py` para quebrar ciclo entre apps

`patient.PatientQuerySet.visible_to` precisa filtrar paciente por triagem aberta,
mas `triage/models/triage_record.py` importa `patient.models.Patient`. Importar de
volta criaria ciclo.

A saída é `triage/constants.py`, sem dependência de model. **Quando dois apps
precisam se conhecer, extraia o pedaço sem dependência** em vez de importar
`models` dos dois lados.

---

## 5. Sinais de alerta em revisão

Dois defeitos do mesmo tipo já entraram no projeto por merge, e nenhum dos dois
gera erro de import:

- **Método desindentado para fora da classe.** O `clean()` do `CustomUser` virou
  função de módulo e a validação simplesmente não rodava. Um teste do `triage`
  virou função solta com `self` no argumento, e o pytest tentou resolver `self`
  como fixture.
- **Auto-merge que remove linha sem gerar conflito.** O `requirements.txt` perdeu
  `crispy-bootstrap5` e `django-crispy-forms` num merge sem conflito; só apareceu
  no `ModuleNotFoundError` durante o build.

Depois de um merge, rode `manage.py check`, a suíte e o build — o `git status`
limpo não é prova de nada.
