# Mapa de Rotas e Permissões — SEP
 
## Legenda de mecanismo de permissão
 
O projeto usa quatro mecanismos diferentes para controlar acesso, o que já é a primeira pendência registrada mais abaixo.
 
- Role direto: a view checa `request.user.role == CustomUser.Role.X` na mão.
- has_perm: usa o sistema de permissões nativo do Django (`request.user.has_perm("app.codename")`).
- GroupRequiredMixin: mixin customizado (`core/mixins.py`) que checa grupo do Django através de `required_group = "Nome"`.
- UserPassesTestMixin: mixin nativo do Django, com um `test_func()` escrito à mão em cada view.
## Raiz (config/urls.py)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| `/` | RedirecionarHomeView | — | Público ou qualquer autenticado, redireciona |
| `/login/` | CustomLoginView | — | Público |
| `/logout/` | CustomLogoutView | — | Autenticado |
 
## administration/ (prefixo /administration/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| home | PainelAdministracaoView | UserPassesTestMixin | Superuser ou ADMINISTRATIVO |
| painel/ | PainelAdministracaoView | UserPassesTestMixin | Superuser ou ADMINISTRATIVO |
| cadastrar/ | cadastrar_administrativo | has_perm("core.add_customuser") | Superadmin |
| perfil/ | PerfilAdministrativoView | GroupRequiredMixin("Administration") | Grupo Administration |
| cadastrar-paciente/ | cadastrar_paciente | Role direto | Superuser ou ADMINISTRATIVO |
 
## patient/ (prefixo /patient/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| home | HomePacienteView | GroupRequiredMixin("Patient") | Grupo Patient |
| edit/ | EditarDadosPacienteView | GroupRequiredMixin("Patient") | Grupo Patient, só o próprio |
 
## students/ (prefixo /students/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| home | HomeEstudanteView | LoginRequiredMixin + UserPassesTestMixin | ALUNO, corrigido e testado nesta sessão |
| painel/ | PainelEstudanteView | LoginRequiredMixin + UserPassesTestMixin | ALUNO, corrigido e testado nesta sessão |
| cadastrar/ | cadastrar_aluno | has_perm("students.add_student") | Supervisor |
| perfil/ | PerfilAlunoView | GroupRequiredMixin("Students") | Grupo Students |
| meu-professor/ | MeuProfessorView | LoginRequiredMixin + UserPassesTestMixin | ALUNO, corrigido e testado nesta sessão |
 
## teacher/ (prefixo /teacher/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| home | HomeProfessorView | LoginRequiredMixin + UserPassesTestMixin | PROFESSOR, SUPERVISOR, corrigido e testado nesta sessão |
| painel/ | PainelProfessorView | UserPassesTestMixin | PROFESSOR, SUPERVISOR, testado |
| cadastrar/ | cadastrar_professor | has_perm("teacher.add_teacher") | Supervisor |
| perfil/ | PerfilProfessorView | LoginRequiredMixin + UserPassesTestMixin | PROFESSOR, SUPERVISOR, corrigido nesta sessão |
| vincular-aluno/ | vincular_aluno | Role direto | PROFESSOR, SUPERVISOR, testado |
| lancar-horas/ | lancar_horas | Role direto + can_be_created_by | PROFESSOR, SUPERVISOR, testado, 403 confirmado |
 
## supervisor/ (prefixo /supervisor/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| home | HomeSupervisorView | GroupRequiredMixin("Supervisor") | Grupo Supervisor |
| painel/ | PainelSupervisorView | GroupRequiredMixin("Supervisor") | Grupo Supervisor |
| usuarios/ | ListarUsuariosView | GroupRequiredMixin("Supervisor") | Grupo Supervisor |
| register/ | cadastrar_supervisor | has_perm("core.add_customuser") | Superadmin |
| areas/ | ListaAreasView | GroupRequiredMixin("Supervisor") | Grupo Supervisor |
| areas/nova/ | CriarAreaView | has_perm("areas.add_areaacting") | Supervisor |
| areas/<pk>/editar/ | EditarAreaView | has_perm("areas.change_areaacting") | Supervisor |
 
## superadmin/ (prefixo /superadmin/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| home | HomeSuperadminView | GroupRequiredMixin("Superadmin") | Grupo Superadmin ou is_superuser |
| painel/ | PainelSuperadminView | GroupRequiredMixin("Superadmin") | Grupo Superadmin ou is_superuser, lista todos os CustomUser do sistema |
| perfil/ | PerfilSuperadminView | GroupRequiredMixin("Superadmin") | Grupo Superadmin ou is_superuser, só o próprio |
 
## triage/ (prefixo /triage/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| create/<patient_id>/ | create_triage | login_required + checagem manual | Aluno, corrigido e testado nesta sessão |
 
## Rotas mobile
 
Confirmado: não existem rotas mobile separadas. O projeto usa design responsivo, a mesma aplicação Django e as mesmas urls e views. A diferença entre desktop e mobile é resolvida por CSS, via media queries, na camada de apresentação, não por rotas distintas. O mapa de rotas web acima já cobre o que seria o mapa mobile.
 
## Redirecionamento para não autorizado e estado de acesso negado
 
Implementado e testado. A decisão é nunca mostrar uma tela de erro visível.
 
Quando alguém não autenticado tenta acessar uma rota protegida, é redirecionado para a tela de login. Isso já é o comportamento padrão do Django via LoginRequiredMixin ou UserPassesTestMixin, sem precisar de código customizado.
 
Quando alguém autenticado tenta acessar uma rota que não é permitida pra role dele, é redirecionado para a home da própria role, através de um handler de 403 customizado.
 
A implementação fica em core/exception_handlers.py:
 
```python
HOME_BY_ROLE = {
    Role.ALUNO: "students:home",
    Role.PROFESSOR: "teacher:home",
    Role.SUPERVISOR: "supervisor:home",
    Role.ADMINISTRATIVO: "administration:home",
    Role.SUPERADMIN: "superadmin:home",
    Role.PACIENTE: "patient:home",
}
```
 
E é registrado em config/urls.py:
 
```python
handler403 = "core.exception_handlers.custom_permission_denied_view"
```
Um detalhe importante: o handler403 só é ativado pelo Django quando DEBUG é False. Em desenvolvimento, com DEBUG True, o Django mostra a página de erro técnica detalhada em vez de acionar o handler. Pra testar esse comportamento de verdade é preciso rodar com DJANGO_DEBUG=False no .env.


## Card 1, relevante pra esse mapa
 
Comparando com as telas do Figma, ficou claro que a separação entre uma tela home vazia e uma tela painel cheia de conteúdo, presente hoje em quase todos os apps, foi uma decisão provisória tomada antes do Figma estar pronto. No fluxo definitivo, cada role tem uma única tela inicial, que já reúne os contadores, atalhos e conteúdo. Não existem as duas telas separadas.
 
será preciso decidir qual das duas views vira a definitiva, normalmente a que já carrega dados reais, garantir que ela tenha a checagem de role certa, remover a outra rota, e atualizar o HOME_BY_ROLE em core/exception_handlers.py, que hoje aponta para os nomes de rota home de cada app.


## Pendências encontradas

não existe hoje nenhum template customizado de erro, nem para 403, nem para 404 ou 500. Como a decisão do time foi nunca mostrar tela de erro pra usuário autenticado sem permissão, isso importa menos pro caso de 403, que já é resolvido pelo redirecionamento. Mas ainda vale considerar se faz sentido ter uma tela de 404 ou 500 com a cara do produto, em vez da página técnica padrão do Django, especialmente pensando em ambiente de produção.
 