# Fluxos da área do Coordenador

Documento de confirmação das telas do Coordenador, escrito a partir das sete
imagens de `docs/Referencia_coordenador/`. Serve para fechar nomes, ordem dos
fluxos, variações por role e estados de tela **antes** da implementação, e para
registrar o que depende de decisão de Produto/Design.

O papel passa a se chamar **Coordenador** em tudo que a pessoa lê. No código,
o que for novo nasce como `Coordinator`; a pasta `supervisor/`, a rota
`/supervisor/`, o namespace `supervisor:` e o papel `SV` continuam como estão,
para não quebrar o trabalho das outras branches.

Onde o dado ainda não existe no banco, a tela entra com **dado mockado** e um
`TODO` no ponto exato em que a consulta real deve substituí-lo.

---

## 1. Telas

| Frame na referência | Tela | Rota proposta | O que mostra |
|---|---|---|---|
| `Home - SupervisorGeral(PC)` | Página inicial | `/supervisor/` | Quatro indicadores, atividades recentes e calendário |
| `professores setup supervisor(PC)` | Professores cadastrados | `/supervisor/professores/` | Nome, área de atuação, alunos vinculados e situação |
| *(sem referência)* | Alunos cadastrados | `/supervisor/alunos/` | Nome, orientador, área e fase do estágio |
| `triagens setup supervisor(PC)` | Triagens para analisar | `/supervisor/triagens/` | Paciente, quem realizou, quando chegou e situação |
| `encaminhamentos setup supervisor(PC)` | Novo encaminhamento | `/supervisor/encaminhamentos/` | Paciente da triagem, professores para alocar e encaminhamentos recentes |
| `feedback setup supervisor(PC)` | Feedback sobre triagens | `/supervisor/feedbacks/` | Aluno, paciente, situação da triagem (Em triagem, Pendente, Enviado) e campo para escrever |
| `cadastrar professor setup supervisor(PC)` | Adicionar professores | `/supervisor/professores/cadastrar/` | Formulário de cadastro |
| `cadastrar aluno setup supervisor(PC)` | Adicionar alunos | `/supervisor/alunos/cadastrar/` | Formulário de cadastro |

Detalhe de professor e de aluno ficam em `/supervisor/professores/<pk>/` e
`/supervisor/alunos/<pk>/`, que é para onde o "Editar" da listagem leva.

O header é o mesmo nas oito telas: marca, seis destinos (Página inicial, Alunos,
Professores, Triagens, Feedbacks, Encaminhamentos) e três ícones (mensagens,
notificações, conta).

## 2. Ordem dos fluxos

**Triagem e encaminhamento.** O aluno conclui a triagem e ela vai para a
coordenação. Página inicial (indicador "Triagens pendentes") → Triagens para
analisar → "Analisar" abre a triagem → Novo encaminhamento, que lista as últimas
triagens concluídas: o Coordenador escolhe o paciente, filtra os professores pela
área de atuação do caso e marca quem vai receber → "Confirmar encaminhamento" →
o caso aparece em Encaminhamentos recentes.

Concluir a triagem **não** dá alta ao paciente: a triagem é a etapa inicial do
atendimento, e a alta só existe no fim dele. O paciente fica aguardando o parecer
da coordenação até ser encaminhado.

**Feedback.** Página inicial (indicador "Feedbacks a enviar") → Feedback sobre
triagens → "Escrever" abre o campo de escrita daquele aluno → "Enviar avaliação"
→ a linha passa a "Enviado".

A situação acompanha a triagem: enquanto o aluno preenche a ficha ela fica "Em
triagem" e não há o que escrever; quando o aluno finaliza, passa a "Pendente" e
o campo de escrita é liberado; depois do parecer, "Enviado".

**Professores.** Página inicial → Professores cadastrados → "+ cadastrar
professor" abre o formulário, ou "Editar" abre o detalhe do professor.

**Alunos.** Mesmo caminho, pela aba Alunos.

## 3. Variações por role

| Role | O que acontece |
|---|---|
| Coordenador | Única role com acesso às oito telas |
| Professor | Vê as telas equivalentes da própria área (`teacher:alunos`, `teacher:prontuarios`, `teacher:triagens`), com o recorte dos próprios orientandos |
| Aluno, Administrativo e Paciente | Sem acesso; o `handler403` redireciona para a home da própria role e deixa o aviso |
| Anônimo | Redirecionado para `/login/` com retorno para a página pedida |

O Coordenador enxerga tudo: as regras de visibilidade do projeto já dão a ele
alcance total nas triagens, pacientes, alunos e professores.

## 4. Estados de tela

| Tela | Vazio | Erro | Sucesso |
|---|---|---|---|
| Página inicial | Sem atividades recentes; mês sem evento no calendário | Falha ao carregar o resumo | — |
| Professores cadastrados | Nenhum professor cadastrado | Falha ao carregar a lista | Professor cadastrado |
| Alunos cadastrados | Nenhum aluno cadastrado | Falha ao carregar a lista | Aluno cadastrado |
| Triagens para analisar | Nenhuma triagem aguardando análise | Falha ao carregar a fila | — |
| Novo encaminhamento | Nenhuma triagem concluída esperando encaminhamento | Falha ao carregar, ou professor não escolhido | Encaminhamento confirmado |
| Feedback sobre triagens | Nenhuma triagem para acompanhar | Falha ao carregar a lista | Parecer enviado |
| Adicionar professores | — | Campo inválido, e-mail ou CPF já cadastrado | Cadastro concluído |
| Adicionar alunos | — | Campo inválido, e-mail, CPF ou matrícula já cadastrados | Cadastro concluído |

Os estados usam os componentes que já existem: `loading.html`,
`empty_state.html`, `error_state.html` e `alert.html`. Sem permissão e sessão
expirada são os avisos que o `handler403` já deixa na página de destino.

## 5. Origem dos dados

| Informação | Origem | Situação |
|---|---|---|
| Triagens pendentes | Triagens enviadas pelo aluno e ainda não analisadas | Real |
| Encaminhamentos hoje | Triagens encaminhadas com data de fechamento de hoje | Real |
| Professores ativos | Professores com orientando vinculado | Real |
| Feedbacks a enviar | Triagens finalizadas pelo aluno e ainda sem parecer do Coordenador | Real |
| Atividades recentes e calendário | Triagens, encaminhamentos e pareceres, com o calendário do mês já compartilhado | Real |
| Professores: área, alunos vinculados e situação | Cadastro do professor e orientações abertas | Real |
| Alunos: orientador, área e fase | Cadastro do aluno | Real |
| Triagens: paciente e quem realizou | Ficha de triagem | Real |
| Triagens: "Recebida às" | Não existe data de envio da ficha | **Mock com TODO** |
| Triagens: situação "Editada" e "Atrasada" | Não existe data de alteração nem prazo | **Mock com TODO** |
| Encaminhamento: alocação ao professor | Professores responsáveis pelo paciente | Real |
| Encaminhamentos recentes: Concluído e Pendente | Concluído quando já há aluno designado ao caso | Real |
| Feedback: aluno, paciente e situação | Parecer de triagem | Real |
| Cadastro de professor e de aluno | Persistem de verdade | Real |
| Cadastro de professor: as duas permissões | Não existem como campo | **Mock com TODO** |
| Cadastro de aluno: curso e período | Não existem como campo | **Mock com TODO** |

## 6. Pendências de Produto/Design

1. **Campos obrigatórios que a referência não mostra.** Os formulários do Figma
   pedem nome, e-mail e pouco mais, mas o cadastro só grava com CPF, telefone e
   endereço, que hoje são obrigatórios no banco, além da matrícula do aluno.
   Como persistir é entrega do card, os campos obrigatórios entram no formulário
   e a divergência fica registrada: ou o Figma ganha esses campos, ou o cadastro
   passa a ser em duas etapas, ou o banco deixa de exigi-los.
2. **Permissões do professor.** "Acesso a prontuários da área" e "Avaliar
   desempenho de alunos" aparecem como caixas no formulário, mas não existem
   como campo nem correspondem à matriz de permissões atual, em que o professor
   já tem as duas coisas dentro do próprio alcance. Falta definir se são
   permissões de verdade ou rótulos informativos.
3. **Curso e período do aluno.** Estão no formulário e não existem no cadastro.
4. **Envio e prazo da triagem.** A fila mostra "Recebida às 14:20", "Editada" e
   "Atrasada", mas a ficha não guarda quando foi enviada, quando foi alterada,
   nem qual é o prazo de análise. Falta definir o prazo e o que conta como
   edição.
5. **Identificador do paciente.** A referência exibe `José Santos #9872736`, a
   mesma pendência já registrada na área do Aluno: falta definir que número é
   esse antes de exibir qualquer id interno.
6. **Ícones do header.** Mensagens, notificações e conta seguem sem destino,
   inertes e marcados com `TODO`, como nas outras áreas.
7. **Alunos cadastrados sem referência.** Não há frame dessa tela; vou espelhar
   a de professores, trocando "área de atuação" por orientador e fase do
   estágio.
8. **Busca e filtros.** Os cards pedem busca e filtros nas listagens, e o Figma
   não mostra nenhum. Proponho busca por nome e filtro por área nas duas
   listagens, e filtro por situação na fila de triagens.
9. **Mobile.** As sete referências são só de PC. A marcação será responsiva e
   validada em telas estreitas, mas o desenho mobile não está definido.
10. **Telas antigas da área.** `painel/`, `usuarios/`, `areas/` e `perfil/`
    continuam existindo com o layout antigo. Falta decidir se entram no novo
    shell, se saem do menu ou se são absorvidas pelas telas novas.

## 7. Arquivos de template

A área já tem templates; a regra é reaproveitar o arquivo existente e só criar
quando não houver correspondente.

| Tela | Arquivo | Situação |
|---|---|---|
| Página inicial | `templates/supervisor/home_supervisor.html` | Reaproveitado |
| Professores cadastrados | `templates/supervisor/list_users.html` | Reaproveitado; hoje mistura alunos e professores numa lista só |
| Adicionar professores | `templates/teacher/cadastro.html` | Reaproveitado |
| Adicionar alunos | `templates/student/cadastro.html` | Reaproveitado |
| Base da área | `templates/supervisor/base_coordinator.html` | Novo |
| Alunos cadastrados | `templates/supervisor/alunos.html` | Novo |
| Triagens para analisar | `templates/supervisor/triagens.html` | Novo |
| Novo encaminhamento | `templates/supervisor/encaminhamentos.html` | Novo |
| Feedback sobre triagens | `templates/supervisor/feedbacks.html` | Novo |
| Detalhe de professor e de aluno | `templates/supervisor/professor_detalhe.html` e `aluno_detalhe.html` | Novos |

Ficam como estão, no layout antigo: `supervisor_panel.html`, `perfil.html`,
`area_list.html`, `area_form.html`, `cadastro_supervisor.html` e `register.html`.
A rota antiga `usuarios/` passa a mostrar a listagem de professores, que é o
arquivo que ela já renderiza — o menu novo aponta para `professores/`.

## 8. Convenção dos mocks

Cada dado mockado fica isolado numa função ou constante de um módulo próprio da
área, com um `TODO` apontando onde entra a consulta real, como foi feito na área
do Aluno. Botão ou link sem lógica leva
`{# TODO: botão sem lógica; fica para fazer #}` no template. A remoção dos mocks
é uma task própria, depois das decisões das pendências 2, 3 e 4.
