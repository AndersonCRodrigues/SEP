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
| Formulário | `form.html` | include | É `method="post"` com `form.as_p` e as classes `figma-*`; a tela precisa carregar `form_cadastro.css`. Não serve para filtro em GET |
| Modal | `_modal.html` | `{% modal %}` | Depende do JavaScript do Bootstrap para abrir |
| Alerta | `alert.html` | include | Mensagem única; para aviso de sistema use as mensagens do Django, que o `base.html` já exibe |
| Loading | `loading.html` | include | Estado estático; não há carregamento assíncrono no projeto |
| Estado vazio | `empty_state.html` | include | — |
| Estado de erro | `error_state.html` | include | Aceita `retry_url` para repetir a ação |
| Selo | `badge.html` | include | `level` segue os níveis do Bootstrap; só funciona nas áreas que carregam Bootstrap |
| Selo de situação | `badge_situacao.html` | include | Recebe `label` e `level` (`success`, `warning`, `danger` ou vazio) e emite o selo do painel de lista; funciona em todas as áreas |
| Indicadores | `summary_list.html` | include | Recebe `indicators`, uma lista de `label` e `value`, já montada na view; `text: True` no indicador diminui a fonte, para valor em palavra em vez de número |
| Atividades recentes | `activity_list.html` | include | Recebe `activities` com `kind`, `title`, `detail`, `url` e `link_label`; o `kind` escolhe o ícone |
| Calendário do mês | `calendar_month.html` | include | Recebe o que `core.month_calendar.month_calendar()` devolve; a navegação é por `?ano=&mes=` |
| Marca do cabeçalho | `site_brand.html` | include | Recebe `home_url` por `{% url 'x' as home_url %}` antes do include; sem isso aponta para a raiz |
| Ícones e menu do usuário | `site_user_menu.html` | include | Os ícones de mensagem e notificação ainda não têm lógica; o menu traz o nome e o Sair. Precisa ser include, não slot tag: usa `request.user` e `{% csrf_token %}`, que a slot tag não repassa |
| Rodapé | `site_footer.html` | include | Barra vinho com a marca da universidade; é o rodapé de todas as áreas |
| Cartão de alerta | `alert_card.html` | include | Recebe `alert_title`, `alert_message` e, se houver ação, `alert_url` e `alert_action`; `alert_level="ok"` troca o ícone e a cor do título |

## Componentes de CSS

Em `core/static/core/css/components/` fica o desenho que se repete entre as
roles. A regra é a mesma nas duas pontas: **o que é igual em mais de uma role
vira componente; o que varia fica no CSS da role, carregado depois do
componente** — a ordem dos `<link>` é que resolve a sobreposição. Ao estilizar
uma role nova, primeiro veja o que já existe aqui e reaproveite; só escreva
regra própria para o que aquela tela realmente tem de diferente.

| Arquivo | Cobre | Quem carrega |
|---|---|---|
| `tokens.css` | As variáveis de cor, a fonte (`--font-main`) e os cinzas | `base.html`, os shells próprios e as telas |
| `site_header.css` | A barra inteira: fundo, marca, navegação centralizada, ícones e menu do usuário | `base.html` e os três shells próprios |
| `site_footer.css` | O rodapé | `base.html` e os três shells próprios |
| `greeting.css` | Saudação e trilha do topo da home (`greeting-title`, `greeting-subtitle`) | Homes de todas as áreas |
| `indicator_list.css` | Faixa de indicadores: cartões vinho com rótulo e número | Homes de todas as áreas |
| `home_panel.css` | Painel duplo da home e a régua vinho entre as colunas; `panel-plain` tira a régua | Homes de todas as áreas |
| `activity_list.css` | Lista de atividades recentes: ícone, título e detalhe | Homes de todas as áreas |
| `calendar.css` | Calendário do mês: caixa, grade, dias, navegação, legenda | Homes de Aluno, Paciente e Professor |
| `list_panel.css` | Painel de lista: pílula de título, subtítulo, cabeçalho, linhas e os selos `badge-situacao` (`ok`, `atencao`, `critica`, `neutra`) | Telas de lista de todas as áreas |
| `list_filters.css` | Barra de busca/filtro acima da lista, a barra de título com busca ou ação (`list-toolbar`) e o botão `btn-acao` | Telas de lista de todas as áreas |
| `row_button.css` | Botão no fim da linha: `btn-iniciar` (verde), `btn-ver` (vinho) e `btn-editar` (cinza) | Listas de todas as áreas |
| `hover_lift.css` | Elevação no hover de linha ou cartão clicável (`hover-lift`) | Listas de todas as áreas |
| `detail_panel.css` | Tela de detalhe: caixas empilhadas com título, linhas de rótulo e valor e texto corrido | Telas de detalhe de Professor, Superadmin e Coordenador |
| `option_list.css` | Lista de opções com caixa de marcar, uma por linha do painel | Área de atuação (Professor) e encaminhamento (Coordenador) |
| `alert_card.css` | Cartão de alerta cinza com título laranja e botão de ação | Home do Superadmin |
| `<área>/<área>_lists.css` | Só a grade de colunas de cada tela de lista e o que é exclusivo dela | Uma por área: `administrativo`, `superadmin`, `coordenacao`, `teacher_lists.css` |
| `mobile_shell.css` | Reset do mobile das telas do Paciente | `patient/base_patient.html` |

Nenhum componente depende de utilitários do Bootstrap (`d-flex`, `mx-auto`,
`text-end` e afins): as áreas de Administrativo, Superadmin e Coordenador não
carregam o framework, e o que dependia deles saía desalinhado nessas telas. As
poucas classes utilitárias que os templates ainda usam estão definidas no
`base_area.css`.

Duas notas de uso: a grade de colunas da lista fica na tela, porque cada uma tem
um número de colunas, e o `hover_lift.css` precisa vir junto do `list_panel.css`
— ele guarda só o movimento, enquanto a cor de fundo do hover fica ao lado da
cor de fundo da linha.

Fora de `components/`, o `form_cadastro.css` é o desenho de todo formulário com
a classe `figma-custom-form`: bloco cinza por campo e caixa de digitação branca
com borda própria, em `box-sizing: border-box` para não passar do bloco. O
`help_text` do Django — as regras de senha, que vêm como `<ul>` — fica apagado e
em itálico, para ler como sugestão e não como mais um campo. Essa regra é escrita
pelo conteúdo da lista (`ul:not(.errorlist):not(:has(input))`), e não pela posição
dela: o navegador tira o `<ul>` de dentro do `<p>` ao interpretar a página, então
a dica deixa de estar dentro do bloco do campo.

## O desenho da página inicial

As páginas iniciais seguem o mesmo desenho das referências, que a home do
Administrativo já aplicava: saudação, faixa de quatro indicadores vinho e, em
duas colunas separadas por uma régua vinho, as atividades recentes (ícone,
título e detalhe, uma por linha) e o calendário do mês. Os valores dos
componentes vieram da home do Administrativo, que já aplicava esse desenho; o
arquivo original saiu quando a última área migrou, porque tudo o que ele tinha
virou componente.

```django
<section class="greeting">
  <h1 class="greeting-title">Olá, aluno!</h1>
  <p class="greeting-subtitle">Página inicial - Aluno</p>
</section>

{% include "components/summary_list.html" with title="Resumo" id="summary-title" %}

<div class="panel">
  <section class="activities">
    <h2>Atividades recentes</h2>
    {% include "components/activity_list.html" %}
  </section>
  <section class="calendar">
    <h2>Calendário</h2>
    {% include "components/calendar_month.html" %}
  </section>
</div>
```

A view entrega `indicators` (`label`/`value`) e `activities` no contrato comum
(`kind`, `section`, `title`, `detail`, `url`, `link_label`), e o calendário vem
de `core.month_calendar.month_calendar()`. As cinco áreas com página inicial
seguem esse desenho; no Superadmin a coluna da direita traz o cartão de alerta
em vez do calendário.

## Cabeçalho e rodapé

Os seis shells montam o mesmo cabeçalho a partir de três peças: a barra e o menu
do meio ficam no shell, porque os links mudam por role, e a marca e os ícones da
direita vêm dos componentes. O "Sair" não é mais um botão na barra: mora no menu
que abre ao clicar no ícone de usuário, feito com `<details>` — assim funciona
igual nos shells com e sem Bootstrap. O `core/js/user_menu.js` só fecha o menu
ao clicar fora ou no `Esc`.

```django
<header class="admin-navbar">
  {% url 'administration:home' as home_url %}
  {% include "components/site_brand.html" %}
  <nav class="main-nav">... menu da role ...</nav>
  {% include "components/site_user_menu.html" %}
</header>
```

A barra segue o desenho do Administrativo: marca à esquerda, navegação
**centralizada** entre a marca e os ícones, e os ícones à direita. Nas áreas com
Bootstrap, a navegação fica dentro de `<div class="site-nav">`; nos shells
próprios, é o `<nav class="main-nav">` direto. Os valores estão todos no
componente, que é a única fonte — foi por isso que o `core/css/base.css` deixou
de existir.

No mobile as telas desenham o próprio cabeçalho dentro do conteúdo e escondem a
barra do desktop (`.sep-navbar`), então o componente só aparece no desktop.

## Notas

Os componentes trazem classes do Bootstrap, e as bases das áreas de Aluno,
Paciente e Coordenador estendem o `base.html`, que é quem carrega o Bootstrap.
`administration/base_admin.html` e `superadmin/base_superadmin.html` ficam fora
dessa herança: são documentos próprios, com o `base_area.css` e as classes
`admin-*`, sem Bootstrap.

`list.html`, `loading.html` e `table.html` existem e estão descritos acima, mas
nenhuma tela os usa ainda: as listagens precisaram de selo ou link na célula e
foram para o `{% data_table %}`, e o projeto não tem carregamento assíncrono.

As homes do Administrativo e do Paciente escrevem os indicadores à mão, com a
mesma marcação que o `summary_list.html` agora concentra — no caso do Paciente,
já com as classes do `stat_card.css`. Elas migram quando alguma tarefa tocar
nessas views, porque a lista de indicadores passa a ser montada na view em vez
de campo a campo no template.
