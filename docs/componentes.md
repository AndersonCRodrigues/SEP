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
| Feedbacks do aluno | `feedback_list.html` | include | `feedbacks` com `author`/`when`/`content` — a view normaliza, porque o Professor lê `PerformanceReview` e o Coordenador, `TriageFeedback`; `empty_message` opcional e `components/feedback_list.css` na tela |
| Paciente em foco | `patient_card.html` | include | Caixa do encaminhamento: `name`, `code` (o `#id`), `detail` e `detail_date` opcionais |
| Lista de opções | `option_list.html` | include | Caixas de marcar do encaminhamento: `options` com `value`/`label`/`checked`, mais `field_name` e `empty_message` |
| Encaminhamentos recentes | `referral_recent.html` | include | `items` com `title`/`subtitle`/`label`/`level`; o selo sai do `badge_situacao.html` |
| Cabeçalho do celular | `mobile_header.html` | include | Voltar, saudação e os ícones; recebe `back_url` |
| Rodapé do celular | `mobile_footer.html` | include | Faixa vinho com a logo; `standalone=True` o esconde no desktop, para usar fora do `mobile-page` |
| Abas do celular | `mobile_tabs.html` | include | "Opções de Serviço"; recebe `tabs_items` com o caminho do partial de links da área |
| Indicadores do celular | `mobile_stats.html` | include | As três primeiras entradas de `indicators` como pílulas coloridas |
| Alerta do celular | `mobile_alert.html` | include | Mesmas variáveis `alert_*` do `alert_card.html` do desktop |
| Atividades do celular | `mobile_activity.html` | include | Os mesmos `activities` da home, em cartão com selo e seta |
| Linha do celular | `mobile_row.html` | include | Cartão de lista: `name`, `code` (o `#id`), `person`, `when`, `place` (a sala), `info`/`info_icon` (dado livre com ícone) e o selo (`label`/`level`). `url` transforma a linha em link; `action_url`/`action_label` troca o selo por um botão verde, que `action_tone="maroon"` deixa vinho e `"dark"`, preto; `action_post=True` envia a ação por POST, com CSRF; `variant="white"` dá a versão branca de fila de trabalho. O `when` e o `info` são texto pronto: data ou número se juntam antes, num `{% with %}` com `\|date` ou `\|stringformat:"s"`, porque o `\|add` entre texto e número devolve vazio |
| Selo do celular | `mobile_badge.html` | include | Traduz `success`/`warning`/`danger` para as cores do celular |
| Título do celular | `mobile_title.html` | include | Pílula vinho das telas internas |
| Busca do celular | `mobile_search.html` | include | Campo pílula com lupa e botão **Filtrar**: `search_value`, `search_label` e `search_name` (padrão `q`) |
| Tile do celular | `mobile_tile.html` | include | Item da grade `mobile-tiles`: círculo colorido pelo `level`, `name`, `label`, `note` e `icon` (padrão porta) |
| Filtro do celular | `_mobile_filter.html` | slot `{% mobile_filter %}` | Moldura pílula com ícone e botão **Filtrar**; o corpo é o `<select>` da tela; aceita `icon` e `action` |
| Caixa do celular | `_mobile_box.html` | slot `{% mobile_box %}` | Título vinho e moldura branca; o corpo são `mobile_field` ou `mobile_row` |
| Dado do celular | `mobile_field.html` | include | Caixa cinza com `label` em cima e `value` em vinho |
| Cartão de paciente (celular) | `mobile_patient_card.html` | include | Paciente em foco: `name`, `code`, `detail` e `detail_date` |
| Opções marcáveis (celular) | `mobile_option_list.html` | include | Checkboxes envolvidos pelo rótulo, sem `id` (convive com a versão desktop na mesma página): `options`, `field_name`, `empty_message` |
| Feedbacks (celular) | `mobile_feedback_list.html` | include | Autor, data e texto numa moldura; `feedbacks` e `empty_message` |
| Topo parcial (celular) | `mobile_top.html` | include | Faixa vinho com cabeçalho e pílula de `title`, só no celular; para telas de formulário renderizadas uma vez |
| Alerta | `alert.html` | include | Mensagem única; para aviso de sistema use as mensagens do Django, que o `base.html` já exibe |
| Loading | `loading.html` | include | Estado estático; não há carregamento assíncrono no projeto |
| Estado vazio | `empty_state.html` | include | Mensagem centralizada na largura toda do bloco (`empty-state`, de `components/empty_state.css`, que os quatro layouts base já carregam). Dentro de uma grade, o item que o envolve precisa de `grid-column: 1 / -1`, senão fica preso na primeira coluna — é o que `rooms-empty` e `indicator-empty` fazem |
| Estado de erro | `error_state.html` | include | Aceita `retry_url` para repetir a ação |
| Mostrar/ocultar senha | `password_toggle.html` | include | Olho dentro do campo de senha: recebe `target` (o `id` do campo) e vai dentro de `<span class="password-field">` junto do input; a tela carrega `components/password_toggle.css` e `core/js/password_toggle.js`. Usado na troca de senha do primeiro acesso |
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
| `list_filters.css` | Barra de busca/filtro acima da lista, a barra de título com busca ou ação (`list-toolbar`), o botão `btn-acao` e o link `btn-limpar` ("Limpar filtros", só com filtro ativo); `list-filters-spread` joga o botão para o extremo oposto da busca | Telas de lista de todas as áreas |
| `row_button.css` | Botão no fim da linha: `btn-iniciar` (verde), `btn-ver` (vinho) e `btn-editar` (cinza) | Listas de todas as áreas |
| `hover_lift.css` | Elevação no hover de linha ou cartão clicável (`hover-lift`) | Listas de todas as áreas |
| `detail_panel.css` | Tela de detalhe: caixas empilhadas com título, linhas de rótulo e valor e texto corrido | Telas de detalhe de Professor, Superadmin e Coordenador |
| `option_list.css` | Lista de opções com caixa de marcar, uma por linha do painel | Área de atuação (Professor) e encaminhamento (Coordenador) |
| `alert_card.css` | Cartão de alerta cinza com título laranja e botão de ação | Home do Superadmin |
| `feedback_list.css` | Entradas de feedback: autor e data na mesma linha, texto com as quebras preservadas | Avaliações e perfil do aluno (Professor) |
| `referral_panel.css` | Tela de encaminhamento: duas colunas, caixa do paciente, filtro, rolagem da lista de opções, recentes e fila | Encaminhamentos do Coordenador e do Professor |
| `question_wizard.css` | Uma pergunta por vez: cartão branco, barra vinho de progresso à esquerda, contador, título, campos e os botões Voltar/Avançar | Pré-cadastro de paciente (Administrativo) e ficha de triagem (Aluno) |
| `<área>/<área>_lists.css` | Só a grade de colunas de cada tela de lista e o que é exclusivo dela | Uma por área: `administrativo`, `superadmin`, `coordenacao`, `teacher_lists.css` |
| `empty_state.css` | A mensagem de lista vazia, centralizada | `base.html` e os três shells próprios |
| `password_toggle.css` | Campo de senha com o olho de mostrar/ocultar dentro, à direita | Troca de senha do primeiro acesso |
| `mobile_shell.css` | Moldura do celular: a troca `mobile-page`/`desktop-page`, o `mobile-only` das telas renderizadas uma vez, faixa vinho, cabeçalho, conteúdo e rodapé; esconde a barra e o rodapé do desktop (`.sep-navbar`, `.admin-navbar`, `.site-footer`) | Shells de Paciente, Aluno, Professor, Administrativo e Coordenador; no Superadmin, cada tela |
| `mobile_nav.css` | "Opções de Serviço": título, ver todos, abas roláveis, a régua e o título de bloco (`mobile-block-title`) | Telas iniciais e telas com seções |
| `mobile_cards.css` | Coluna de 340px (`mobile-column`), indicadores, alerta, cartão de atividade, linha de lista e as ações dela, moldura de lista, selos, busca e filtro, tiles, caixa com título e dado, cartão de paciente, opções marcáveis, feedbacks, pessoa, painel de canais, caixa de informação, conclusão, formulário, pílula de título, botões e estado vazio | Telas de celular de todas as áreas |

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

No mobile as telas desenham o próprio cabeçalho dentro do conteúdo, e o
`mobile_shell.css` esconde a barra do desktop (`.sep-navbar` e `.admin-navbar`),
então o componente só aparece no desktop. O desenho do celular está em
[mobile.md](mobile.md).

Telas que não pertencem a uma área, como a troca de senha do primeiro acesso
(`force_password_change.html`), estendem o `base.html` com o `{% block main_nav %}`
vazio: ficam a marca e o menu do usuário, sem links de navegação, porque o
usuário ainda não pode usar o sistema.

## Notas

As bases de Paciente, Aluno e Professor estendem o `base.html`, que é quem
carrega o Bootstrap. `administration/base_admin.html`,
`supervisor/base_coordinator.html` e `superadmin/base_superadmin.html` ficam fora
dessa herança: são documentos próprios, com o `base_area.css` e as classes
`admin-*`, sem Bootstrap. Por isso nenhum componente pode depender de classe do
framework — o `empty_state.html` dependia (`text-body-secondary`) e saía sem
estilo nessas três áreas até ganhar o CSS próprio.

`list.html`, `loading.html` e `table.html` existem e estão descritos acima, mas
nenhuma tela os usa ainda: as listagens precisaram de selo ou link na célula e
foram para o `{% data_table %}`, e o projeto não tem carregamento assíncrono.

As seis páginas iniciais usam o `summary_list.html`, com os indicadores montados
na view.

## Busca por nome

Fora dos templates, a busca por nome também é compartilhada:
`core.search.full_name_lookup(queryset, busca, *relações)` junta nome e
sobrenome, normaliza os espaços e devolve o queryset anotado e o `Q` que casa a
busca com o nome completo. Com relações (`"patient__"`, `"student__"`), procura
no nome de cada uma. Toda tela que busca pessoa por nome usa esse helper —
"Marina Costa" encontra a aluna, o que a comparação de nome e sobrenome
separados não fazia.

```python
alunos, por_nome = full_name_lookup(alunos, busca)
alunos = alunos.filter(por_nome | Q(matricula__icontains=busca))
```
