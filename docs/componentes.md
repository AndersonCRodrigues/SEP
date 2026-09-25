# Componentes estruturais

Inventário do que existe em `templates/components/`, o que cada peça cobre e onde
ela não serve. A regra de uso é literal: componente que não couber na tela não
deve ser forçado — escreva a marcação própria e registre o motivo.

## Dois modos de uso

**Slot tag**, quando o componente embrulha conteúdo próprio. Carregue com
`{% load components %}` e feche a tag; o que estiver entre a abertura e o
fechamento vira `body`. Todo argumento é `chave=valor`, e valor com espaço
precisa de aspas.

```django
{% section title="Atividades recentes" class="activities" id="activities-title" %}
  ...
{% endsection %}
```

**Include**, quando o componente só recebe dados.

```django
{% include "components/empty_state.html" with message="Nenhuma triagem designada." %}
```

## O que cobre o quê

| Peça | Arquivo | Uso | Limite conhecido |
|---|---|---|---|
| Template de página | `templates/base.html` e a base de cada área, como `student/base_student.html` | `{% extends %}` | Não é componente: é herança. O `base.html` entrega header, trilha, título, slot de ações, conteúdo e rodapé |
| Seção | `_section.html` | `{% section %}` | Emite `<h2>`; não serve como título de página |
| Card | `_card.html` | `{% card %}` | Também emite `<h2>` e sempre ocupa altura total |
| Lista | `list.html` | include | Só itens escalares; item com título, selo ou data pede marcação própria |
| Tabela | `table.html` | include | Só células escalares; não comporta selo, link nem `<details>` |
| Tabela com células próprias | `_data_table.html` | `{% data_table %}` | As linhas são escritas na tela; o componente entrega cabeçalho e corpo |
| Formulário | `form.html` | include | É `method="post"` com `form.as_p`; não serve para filtro em GET |
| Modal | `_modal.html` | `{% modal %}` | Depende do JavaScript do Bootstrap para abrir |
| Alerta | `alert.html` | include | Mensagem única; para aviso de sistema use as mensagens do Django, que o `base.html` já exibe |
| Loading | `loading.html` | include | Estado estático; não há carregamento assíncrono no projeto |
| Estado vazio | `empty_state.html` | include | — |
| Estado de erro | `error_state.html` | include | Aceita `retry_url` para repetir a ação |
| Selo | `badge.html` | include | `level` segue os níveis do Bootstrap |
| Indicadores | `summary_list.html` | include | Recebe `indicators`, uma lista de `label` e `value`, já montada na view |

## Notas

Os componentes trazem classes do Bootstrap, mas `administration/base_admin.html`
não carrega Bootstrap — só o `base.html` carrega. Nas telas do Administrativo as
classes ficam inertes até o frontend estilizar.

As homes do Administrativo e do Paciente escrevem os indicadores à mão, com a
mesma marcação que o `summary_list.html` agora concentra. Elas migram quando
alguma tarefa tocar nessas views, porque a lista de indicadores passa a ser
montada na view em vez de campo a campo no template.
