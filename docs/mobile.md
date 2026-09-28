# O mobile do SEP

As telas de celular das seis roles são a **mesma tela** com conteúdo diferente. Este
documento registra o que as referências de `docs/referencia-*/` mostram, para o CSS e os
templates de mobile saírem de um lugar só em vez de um por área — do mesmo jeito que o
desktop já sai de `core/static/core/css/components/` e `templates/components/`.

A leitura foi feita sobre as páginas iniciais de Paciente, Aluno, Professor, Administrativo
e Superadmin e sobre as telas internas do Paciente (`Setup 4 - paciente-1..4`), que são as
mais completas.

## 1. O que é igual em todas as roles

Toda tela de celular tem, de cima para baixo:

| Bloco | Aparece em | Observação |
|---|---|---|
| Faixa vinho com cantos arredondados embaixo | Todas | Envolve o cabeçalho e o que vier logo abaixo dele |
| Cabeçalho: voltar, saudação, sino e conta | Todas | "Olá, Paciente!", "Olá, Equipe de TI!", "Olá, Secretaria!" |
| Indicadores **ou** calendário | Home | Paciente, Administrativo e Superadmin usam indicadores; Aluno e Professor, o calendário |
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

### Indicadores (Paciente, Administrativo, Superadmin)
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

| Componente | Cobre |
|---|---|
| `components/mobile_shell.css` | Faixa vinho, cabeçalho, área de conteúdo e rodapé |
| `components/mobile_nav.css` | "Opções de Serviço", abas roláveis e a régua |
| `components/mobile_cards.css` | Indicadores, alerta, cartão de atividade, selos, linha de lista, caixa de informação, pílula de título e botão pílula |
| `components/mobile_header.html` | Voltar, saudação e os dois ícones |
| `components/mobile_footer.html` | Faixa com a logo |
| `components/mobile_tabs.html` | Título da seção, abas e régua |
| `components/mobile_stats.html` | As três pílulas de indicador |
| `components/mobile_alert.html` | Cartão de alerta |
| `components/mobile_activity.html` | Lista de atividades recentes |
| `components/mobile_title.html` | Pílula de título das telas internas |

Os componentes de mobile só valem abaixo de 768px: o CSS inteiro fica dentro de
`@media (max-width: 768px)`, e os templates saem do mesmo `{% block content %}` das telas,
marcados com `d-block d-md-none`. Acima de 768px quem manda continua sendo o painel de lista.

## 4. Divergências entre a referência e o que já estava feito

Registradas aqui para não voltarem por engano:

- O cartão de alerta do `patient_home.css` tinha só uma barra laranja à esquerda; a referência
  mostra a borda laranja em toda a volta.
- A home do Paciente trazia os três indicadores e os três cartões de atividade com números
  fixos no template. Os valores passam a vir do contexto, como no desktop.
- As telas internas do Paciente escreviam o cabeçalho, o rodapé e os cartões com `style=` no
  próprio HTML, repetidos tela a tela. É o que os componentes acima substituem.
