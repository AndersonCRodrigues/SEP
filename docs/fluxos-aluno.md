# Fluxos da área do Aluno

Documento de confirmação das telas do Aluno, escrito a partir das seis imagens de
`docs/Referencia_alunos/`. Serve para fechar nomes, ordem dos fluxos, variações
por role e estados de tela **antes** da implementação, e para registrar o que
depende de decisão de Produto/Design.

Onde o dado ainda não existe no banco, a tela entra com **dado mockado** e um
`TODO` no ponto exato em que a consulta real deve substituí-lo.

---

## 1. Telas

| Frame na referência | Tela | Rota proposta | O que mostra |
|---|---|---|---|
| `Home - aluno(PC)` | Página inicial | `/students/` | Quatro indicadores, atividades recentes e calendário |
| `prontuarios setup aluno (PC)` | Prontuários e evolução | `/students/prontuarios/` | Pacientes do aluno, última evolução e situação |
| `Aba Triagens setup aluno (PC)` | Triagens a realizar | `/students/triagens/` | Paciente, quem encaminhou, data e ação de iniciar |
| `Aba Triagens setup aluno (PC)-1` | Triagem concluída | `/students/triagens/<pk>/concluida/` | Confirmação do envio, com paciente, autor e data |
| `Encaminhamentos setup aluno (PC)` | Encaminhamentos recebidos | `/students/encaminhamentos/` | Paciente, situação e selo |
| `Feedbacks setup aluno (PC)` | Feedbacks recebidos | `/students/feedbacks/` | Origem do feedback, autor, quando chegou e selo |

O header é o mesmo nas seis telas: marca, cinco destinos (Página inicial,
Prontuários, Triagens, Feedbacks, Encaminhamentos) e três ícones (mensagens,
notificações, conta).

## 2. Ordem dos fluxos

**Triagem.** Página inicial (indicador "Triagens pendentes" ou a atividade
recente) → Triagens a realizar → "Iniciar" → ficha de triagem
(`/triage/create/<paciente>/`, que já existe) → envio → Triagem concluída →
"Voltar para Triagens a realizar".

**Encaminhamento.** Página inicial (indicador "Encaminhamentos hoje") →
Encaminhamentos recebidos. A referência não traz tela de detalhe.

**Prontuário.** Página inicial (indicador "Pacientes ativos") → Prontuários e
evolução → ação "Revisar" na linha do paciente. A referência não traz tela de
detalhe.

**Feedback.** Página inicial (atividade "Feedback pendente") → Feedbacks
recebidos. A referência não traz tela de detalhe.

## 3. Variações por role

| Role | O que acontece |
|---|---|
| Aluno | Única role com acesso às seis telas |
| Professor e Supervisor | Têm as telas equivalentes na própria área (`teacher:triagens`, `teacher:prontuarios`, `teacher:presenca`) |
| Administrativo e Paciente | Sem acesso; o `handler403` redireciona para a home da própria role |
| Anônimo | Redirecionado para `/login/` com retorno para a página pedida |

Dentro da própria role ainda há a fase do estágio (`Student.stage`): o aluno em
**Triagem** e o aluno em **Atendimento** não fazem as mesmas coisas. O efeito
disso nas telas é a pendência 4.

## 4. Estados de tela

| Tela | Vazio | Erro | Sucesso |
|---|---|---|---|
| Página inicial | Sem atividades recentes; mês sem sessão no calendário | Falha ao carregar o resumo | — |
| Prontuários e evolução | Nenhum paciente em atendimento | Falha ao carregar a lista | Evolução registrada |
| Triagens a realizar | Nenhuma triagem designada | Falha ao carregar a lista | — |
| Triagem concluída | — | Triagem de outro aluno responde 404 | É a própria tela de sucesso |
| Encaminhamentos recebidos | Nenhum encaminhamento | Falha ao carregar a lista | — |
| Feedbacks recebidos | Nenhum feedback recebido | Falha ao carregar a lista | — |

Os estados usam os componentes que já existem: `loading.html`,
`empty_state.html`, `error_state.html` e `alert.html`. Sem permissão é o
redirecionamento do `handler403`; sessão expirada cai no login com `next`.

## 5. Origem dos dados

| Informação | Origem | Situação |
|---|---|---|
| Encaminhamentos hoje, Pacientes ativos | `CaseAssignment` | Real |
| Faltas | `Appointment` com falta do aluno | Real |
| Atividades recentes | Triagens, evoluções e pareceres do aluno | Real |
| Calendário | `Appointment` do aluno, com `core/month_calendar.py` | Real |
| Prontuários: paciente e última evolução | `ProgressNote` | Real |
| Prontuários: selo Revisar/Pendente | Critério não definido | **Mock com TODO** |
| Triagens a realizar: paciente, quem encaminhou, data | Sem model | **Mock com TODO** |
| Triagens pendentes (indicador) | Depende do item acima | **Mock com TODO** |
| Encaminhamentos: "Aguardando confirmação" e autor | Sem campos no `CaseAssignment` | **Mock com TODO** |
| Feedbacks: origem, autor e data | `TriageFeedback` e `PerformanceReview` | Real |
| Feedbacks: selo Novo/Lida/Editada | Sem marcação de leitura | **Mock com TODO** |

## 6. Pendências de Produto/Design

1. **Designação da triagem ao aluno.** A tela de "Triagens a realizar" mostra
   quem encaminhou e quando, mas não existe vínculo entre paciente e aluno antes
   da ficha nascer. A tela do Professor que faria essa designação
   (`teacher:triagem_definir`) também é mock e não grava nada. Falta definir
   quem designa, o que fica registrado e se há prazo.
2. **Confirmação do encaminhamento.** A referência mostra "Ativo" e "Aguardando
   confirmação", mas o `CaseAssignment` nasce ativo e não guarda quem
   encaminhou. Falta definir quem confirma, em quanto tempo e o que acontece se
   não confirmar.
3. **Leitura do feedback.** Os selos "Novo", "Lida" e "Editada" pedem marcação
   de leitura por aluno, que não existe. Falta definir o que marca como lida
   (abrir a lista ou abrir o item) e o que conta como editada.
4. **Fase do estágio.** Definir se o aluno em fase de Triagem vê Prontuários e
   Pacientes ativos, ou se essas telas só valem na fase de Atendimento.
5. **Identificador do paciente.** A referência exibe `José Santos #9872736`.
   Falta definir que número é esse, já que exibir o id interno junto do nome é
   decisão com impacto de privacidade.
6. **Ícones do header.** Mensagens, notificações e conta não têm destino
   definido. Seguem inertes e marcados com `TODO`, como nas áreas do
   Administrativo e do Paciente.
7. **Mobile.** As seis referências são só de PC. A marcação será responsiva e
   validada em telas estreitas, mas o desenho mobile não está definido.
8. **Telas de detalhe.** Não há frame para detalhe de prontuário, de
   encaminhamento ou de feedback. Definir se entram nesta task ou ficam para a
   próxima.
9. **Fim da ficha de triagem.** Hoje o envio da ficha redireciona para uma rota
   que não aceita o parâmetro enviado, e a página quebra. A tela de "Triagem
   concluída" é o destino natural; falta definir se a correção entra nesta
   branch ou na branch do fluxo de triagem.
10. **Calendário da página inicial.** Definir o que marcar: as sessões do aluno,
    as triagens designadas ou os dois.

## 7. Convenção dos mocks

Cada dado mockado fica isolado numa função ou constante da view, com um `TODO`
apontando onde entra a consulta real, no formato usado no projeto. Botão ou link
sem lógica leva `{# TODO: botão sem lógica; fica para fazer #}` no template. A
remoção dos mocks é uma task própria, depois das decisões das pendências 1, 2
e 3.
