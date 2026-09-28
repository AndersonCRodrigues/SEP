# O mobile do SEP

As telas de celular das seis roles são a **mesma tela** com conteúdo diferente. Este
documento registra o que as referências de `docs/referencia-*/` mostram, para o CSS e os
templates de mobile saírem de um lugar só em vez de um por área — do mesmo jeito que o
desktop já sai de `core/static/core/css/components/` e `templates/components/`.

A leitura foi feita sobre as páginas iniciais de Paciente, Aluno, Professor, Administrativo
e Superadmin e sobre as telas internas do Paciente (`Setup 4 - paciente-1..4`), que são as
mais completas. As telas de Encaminhamentos, Avaliação e Detalhe do aluno vieram das
referências "Setup 3 - supervisor" (em `docs/referencia-professor/`), que serviram ao
Coordenador e ao Professor.

As seis roles já têm as telas principais no celular; a seção 4 lista o que cada uma cobre e a
seção 5, o que ainda falta alinhar.

## 1. O que é igual em todas as roles

Toda tela de celular tem, de cima para baixo:

| Bloco | Aparece em | Observação |
|---|---|---|
| Faixa vinho com cantos arredondados embaixo | Todas | Envolve o cabeçalho e o que vier logo abaixo dele |
| Cabeçalho: voltar, saudação, sino e conta | Todas | "Olá, Paciente!", "Olá, Equipe de TI!", "Olá, Secretaria!" |
| Indicadores **ou** calendário | Home | Paciente, Administrativo, Coordenador e Superadmin usam indicadores; Aluno, o calendário; Professor, o calendário na faixa e os indicadores abaixo das abas |
| Cartão de alerta | Home | Borda laranja, título de atenção e botão vinho de largura inteira |
| "Opções de Serviço" + abas roláveis + régua vinho | Home | A régua fecha a seção |
| "Atividade Recente" + cartões cinza | Home | Categoria em vinho, selo, título, detalhe e seta |
| Pílula de título | Telas internas | "Minhas Triagem", "Histórico de sessões", "Contato" |
| Linhas de lista em cartão cinza | Telas internas | Com selo de situação à direita |
| Botão pílula vinho | Telas internas | "Ver mais detalhes", "Continuar", "Enviar mensagem" |
| Rodapé vinho com a logo | Todas | Fecha a página |

O desktop **não** muda: o corte é em 768px, e acima disso continua valendo o painel de lista
e a navegação do cabeçalho.

## 2. Anatomia de cada bloco

### Cabeçalho
Faixa `#6D1D20` com `border-radius` de 30px só embaixo. Dentro: a seta de voltar (chevron
branco de 28px), a saudação (22px, peso 700, branca) e, à direita, o sino e o ícone de conta
(22px). O ícone de conta é o `<form>` de sair — no celular não há menu suspenso.

### Indicadores (Paciente, Administrativo, Coordenador, Superadmin e Professor)
Três pílulas lado a lado dentro da faixa vinho, com `border-radius` 16px e altura mínima de
80px: rótulo em duas linhas (11px) e valor grande (20px, peso 900). As cores são fixas por
posição — verde `#556B2F`, vermelho `#A92024` e laranja `#BA681F`.

### Calendário (Aluno, Professor)
Cartão branco arredondado dentro da faixa vinho, com os seletores de mês e ano, a grade do
mês e os pontos coloridos. Abaixo dele, a legenda numa pílula branca: Disponível (verde),
Agendado (vermelho), Pendente (laranja). É o mesmo `components/calendar_month.html` do
desktop, só mudando a moldura.

### Cartão de alerta
Cartão branco, borda laranja `#E89C1E` em toda a volta, `border-radius` 12px e sombra leve.
Dentro: título em laranja com o triângulo de atenção (14px, peso 800), o texto (14px, com o
número em negrito) e um botão vinho de largura inteira, `border-radius` 20px.

### Opções de serviço
Título "Opções de Serviço" (17px, peso 800) com "Ver todos ›" à direita (13px). Abaixo, uma
fila de pílulas cinza `#D9D9D9` que rola na horizontal sem barra de rolagem visível, e uma
régua de 2px vinho fechando a seção. As abas são os mesmos destinos da navegação do desktop.

### Cartão de atividade
Fundo `#E0E0E0`, `border-radius` 12px. Primeira linha: categoria em vinho (14px, peso 800) e
selo à direita. Depois o título (15px, peso 800) e o detalhe (14px, `#444`). Fecha com uma
divisória de 1px vinho e a seta `›` alinhada à direita.

Selos: concluído (fundo `#B3D8A8`, texto `#2D5A27`), atenção (`#EAD0A3` / `#7F5816`) e neutro
(`#D5D5D5` / `#555`), todos 10px peso 800 com `border-radius` 12px.

### Telas internas
- **Pílula de título**: faixa vinho arredondada, texto branco centralizado (20px, peso 800).
- **Linha de lista**: cartão cinza com as informações à esquerda (cada uma com o seu ícone) e
  o selo de situação à direita — verde para concluído, laranja para remarcado, vermelho para
  falta.
- **Caixa de informação**: fundo cinza escuro, texto branco, uma linha por dado com rótulo à
  esquerda, valor à direita e separador branco entre elas.
- **Conclusão**: círculo verde com o visto, título, uma linha de explicação, a caixa de
  informação e o botão pílula.
- **Botão pílula**: vinho, texto branco (14px, peso 700), `border-radius` 20px.

## 3. Onde isso vive no código

**CSS** (em `core/static/core/css/components/`):

| Arquivo | Cobre |
|---|---|
| `mobile_shell.css` | A troca `mobile-page`/`desktop-page` e o `mobile-only`; faixa vinho, cabeçalho, área de conteúdo e rodapé; esconde a barra e o rodapé do desktop; `box-sizing: border-box` no bloco de celular, que as áreas sem Bootstrap não têm |
| `mobile_nav.css` | "Opções de Serviço", abas roláveis, a régua e o título de bloco |
| `mobile_wizard.css` | O wizard de uma pergunta por vez (`question_wizard.css`) no celular, com o desenho da ficha de triagem: esconde a barra lateral e faz das opções pílulas, do Avançar um botão de largura inteira e do Voltar um texto discreto. Carregado depois do CSS da tela |
| `mobile_cards.css` | Todo o resto: coluna de 340px, indicadores, alerta, atividade, linha de lista e ações, moldura de lista, selos, busca e filtro, tiles, caixa com título, dado, cartão de paciente, opções marcáveis, feedbacks, pessoa, canais, caixa de informação, conclusão, formulário, pílula de título, botões, legenda e estado vazio |

**Templates** (em `templates/components/`):

| Componente | Uso | Cobre |
|---|---|---|
| `mobile_header.html` | include | Voltar (`back_url`), saudação e os dois ícones |
| `mobile_footer.html` | include | Faixa com a logo; `standalone=True` para usar fora do `mobile-page` |
| `mobile_top.html` | include | Faixa vinho com o cabeçalho e a pílula de `title`, só no celular, para telas renderizadas uma vez |
| `mobile_tabs.html` | include | Título da seção, abas (`tabs_items` com o partial da área) e régua |
| `mobile_stats.html` | include | As três primeiras entradas de `indicators` como pílulas |
| `mobile_alert.html` | include | Cartão de alerta (`alert_title`, `alert_message`, `alert_url`, `alert_action`) |
| `mobile_activity.html` | include | Lista de atividades recentes; a categoria sai de `section` ou do `kind` |
| `mobile_title.html` | include | Pílula de título das telas internas |
| `mobile_row.html` | include | Linha de lista: dados com ícone, selo, link e botão de ação (GET ou POST) |
| `mobile_badge.html` | include | Selo nas cores do celular |
| `mobile_search.html` | include | Busca por texto com lupa e **Filtrar** |
| `_mobile_filter.html` | `{% mobile_filter %}` | Moldura com ícone e **Filtrar** em volta do `<select>` da tela |
| `_mobile_box.html` | `{% mobile_box %}` | Seção com título vinho e moldura branca |
| `mobile_field.html` | include | Dado com rótulo em cima e valor em vinho |
| `mobile_tile.html` | include | Item da grade de dois (salas), com círculo colorido pela situação |
| `mobile_patient_card.html` | include | Paciente em foco no encaminhamento |
| `mobile_option_list.html` | include | Caixas de marcar sem `id`, para conviver com a versão desktop |
| `mobile_feedback_list.html` | include | Autor, data e texto dos feedbacks |
| `wizard_mobile_head.html` | include | Topo do wizard no celular: cartão com `label` e `name` e a barra de progresso (`<progress>` com `number` e `total`) |

Parâmetros de cada um estão em [componentes.md](componentes.md).

Os componentes de mobile só valem abaixo de 768px: o CSS inteiro fica dentro de
`@media (max-width: 767.98px)`, e os templates saem do mesmo `{% block content %}` das telas.
Acima de 768px quem manda continua sendo o painel de lista.

**A troca entre as duas versões é por classe própria, não pelo Bootstrap.** O bloco de
celular leva `mobile-page` e o de desktop, `desktop-page`. Os utilitários `d-block`/`d-none`
não servem aqui por dois motivos: eles usam `!important`, o que impedia o `display: flex` do
`mobile-page` — e sem o flex o rodapé não desce até o fim da tela — e as áreas com shell
próprio (Administrativo, Superadmin e Coordenador) não carregam o framework.

## 4. Aplicação por role

| Role | Telas | O que foi próprio dela |
|---|---|---|
| Paciente | Home, Histórico, Agendamentos, Solicitar horário, Minhas triagens, Triagem concluída, Contato | Indicadores na faixa vinho; cartão de pessoa e painel de canais no Contato |
| Aluno | Home, Triagens a realizar, Prontuários, Encaminhamentos, Feedbacks, Minhas triagens, Triagem concluída | Calendário na faixa vinho (com `calendar_id` próprio, para não repetir o `id` do calendário do desktop); linha branca com botão **Iniciar** na fila de trabalho; moldura `mobile-list` em Prontuários e Encaminhamentos; resumo claro (`mobile-info-light`) na conclusão |
| Administrativo | Home, Pacientes, Agenda, Salas, Declarações, Atestados, Meu perfil, Painel de gestão, Pré-cadastro (wizard) e Pré-cadastro concluído | Alerta de declarações pendentes (`pending_alert` da view); busca com **Filtrar** (`mobile_search.html`) em Pacientes e seletor de período na Agenda; grade de salas (`mobile_tile.html`); local da sessão na linha (`place`) |
| Professor | Home, Meus alunos, Detalhe do aluno, Presença, Prontuários, Encaminhar, Avaliações (lista e escrita), Área de atuação | Calendário na faixa vinho com os indicadores e o alerta abaixo das abas, como na referência; período do aluno vindo da orientação ativa (`Advising.term`); **Marcar** presença por POST na linha (`action_post`, tom `dark`); selo do prontuário por prazo de revisão (`note_situation`: Revisada, Analisar ou Atrasada após 7 dias) |
| Superadmin | Home, Servidores, Logs de segurança, Detalhe do log, Permissões, Permissão (form), Backups, Adicionar supervisor, Adicionar administrativo | Abas em `superadmin/_mobile_tabs.html` e cartões de atividade próprios em `superadmin/_mobile_activity.html`; o CSS de celular é carregado tela a tela (ver pendências) |
| Coordenador | Home, Triagens, Detalhe da triagem, Encaminhamentos, Alunos, Detalhe do aluno, Professores, Detalhe do professor, Feedbacks (lista e escrita), Usuários cadastrados, Áreas, Área (form), Meu perfil, Cadastro de aluno e de professor, Meus orientandos | Alerta de triagens aguardando encaminhamento; caixas com título (`{% mobile_box %}`) e dado rótulo/valor (`mobile_field.html`) nos detalhes; cartão do paciente (`mobile_patient_card.html`) e opções marcáveis sem `id` (`mobile_option_list.html`) em Encaminhamentos; botão vinho na linha (`action_tone="maroon"`) em Feedbacks e Áreas; lista de feedbacks (`mobile_feedback_list.html`) |

Cada área entra no mobile pelo próprio shell: `base_<área>.html` carrega os três CSS de
componente e expõe `{% block page_css %}` para o CSS da tela. No Administrativo e no
Coordenador, que não usam Bootstrap, os três ficam no `{% block mobile_css %}` do
`base_admin.html` e do `base_coordinator.html`. As abas de "Opções de Serviço" ficam num partial da área
(`patient/mobile_tabs.html`, `student/mobile_tabs.html`, `administration/mobile_tabs.html`,
`supervisor/mobile_tabs.html`), porque são as rotas dela.

Telas de formulário (Atestados, Meu perfil, cadastros, Área) não duplicam o formulário: o
conteúdo é renderizado uma vez na coluna `mobile-column`, o topo de celular entra por
`components/mobile_top.html` e o rodapé por `mobile_footer.html` com `standalone=True`, no
`{% block footer %}`; o título do desktop leva `desktop-page`. Assim o script que depende dos
`id`s continua achando um campo só.

Botões de criar da lista (Cadastrar novo paciente, Novo agendamento, Cadastrar aluno,
Cadastrar professor) ficam no topo, centralizados logo abaixo do filtro, em
`mobile-actions mobile-actions-top`.

Filtros com `<select>` usam a slot tag `{% mobile_filter icon="..." %}…{% endmobile_filter %}`
(de `core/templatetags/components.py`): o corpo é o `<label>` e o `<select>` da tela, e a
moldura com o ícone e o botão **Filtrar** vem do componente.

A troca de senha do primeiro acesso (`force_password_change.html`), que vale para qualquer
papel, também usa o `mobile_top.html` e o rodapé `standalone`, com o título "Criar nova senha".

Mensagens de lista vazia usam `mobile-empty` (centralizada), no lugar do `empty_state.html`
do desktop.

O pré-cadastro de paciente (`administration/cadastrar_paciente.html`) usa o `mobile_wizard.css`
com o `wizard_mobile_head.html` sobre o mesmo formulário do desktop, renderizado uma vez só —
o script de máscara de CPF e CEP depende dos `id`s. O campo de data usa o seletor nativo do
celular; o seletor em rolo do mobile antigo saiu junto com o `mobile_patient_registration.css`.

A ficha de triagem (`triage/create_triage.html`) ganhou um bloco `mobile-page` próprio, com o
cartão do paciente, a barra de progresso e os botões Voltar/Avançar em largura inteira. A
referência de celular dela está em `docs/referencia-triagem/`.

## 5. Pendências

O que ainda foge do padrão acima, para a próxima rodada não precisar redescobrir:

- **Superadmin carrega o CSS de celular tela a tela.** O `base_superadmin.html` não tem o
  `{% block mobile_css %}` dos outros shells próprios, então cada tela repete os `<link>` — e a
  que esquece (hoje o Meu perfil) aparece com a versão de desktop no celular.
- **Atividades do Superadmin fora do componente.** `superadmin/_mobile_activity.html` repete o
  `components/mobile_activity.html` e deduz o selo pelo título da atividade; o padrão é a view
  mandar `label` e `level`, como nas outras homes. As abas seguem o mesmo caso: o partial das
  outras áreas se chama `<área>/mobile_tabs.html`, sem sublinhado.
- **Ficha de triagem com o formulário duplicado.** O bloco de celular desenha o formulário uma
  segunda vez, então os `id`s se repetem e o rótulo de cada opção aponta para o campo escondido
  do desktop. O pré-cadastro já resolve isso com o `mobile_wizard.css` sobre o formulário
  único; a triagem pode passar para o mesmo componente, o que também tira os 9 `style=` dela.
- **`style=` no HTML.** Além da triagem, os cadastros de supervisor e de administrativo têm 1
  cada; o resto do mobile não tem nenhum.
- **Telas que nunca abrem.** O detalhe do prontuário do Professor
  (`prontuario_detalhe.html`) é bloqueado pela view e ficou sem mobile; o
  `presenca_feedback.html` saiu de uso quando a Presença voltou para o `presenca.html`.

## 6. Divergências entre a referência e o que já estava feito

Registradas aqui para não voltarem por engano:

- O cartão de alerta do `patient_home.css` tinha só uma barra laranja à esquerda; a referência
  mostra a borda laranja em toda a volta.
- A home do Paciente trazia os três indicadores e os três cartões de atividade com números
  fixos no template. Os valores passam a vir do contexto, como no desktop.
- As telas internas do Paciente escreviam o cabeçalho, o rodapé e os cartões com `style=` no
  próprio HTML, repetidos tela a tela. É o que os componentes acima substituem.
