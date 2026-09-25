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
| `/login/` | CustomLoginView | redirect_authenticated_user | Público; usuário já logado é redirecionado para `/`, que leva à home da própria role |
| `/logout/` | CustomLogoutView | — | Autenticado, só por POST (o botão Sair do header); GET responde 405 |
 
## administration/ (prefixo /administration/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| home | AdministrativeHomeView | AdministrativeOnly (LoginRequiredMixin + UserPassesTestMixin, role ADMINISTRATIVO) | ADMINISTRATIVO |
| painel/ | PainelAdministracaoView | AdministrativeOnly | ADMINISTRATIVO |
| cadastrar/ | cadastrar_administrativo | has_perm("core.add_customuser") | Superadmin |
| perfil/ | PerfilAdministrativoView | AdministrativeOnly | ADMINISTRATIVO, só o próprio |
| pacientes/ | PatientsView | AdministrativeOnly | ADMINISTRATIVO |
| cadastrar-paciente/ | PatientRegistrationStartView | CanRegisterPatients (AdministrativeOnly + Patient.can_be_created_by) | ADMINISTRATIVO; inicia o cadastro e redireciona para a primeira etapa |
| cadastrar-paciente/\<step\>/ | PatientRegistrationStepView | CanRegisterPatients | ADMINISTRATIVO |
| pacientes/\<pk\>/cadastro-concluido/ | RegistrationCompletedView | CanRegisterPatients + Patient.visible_to | ADMINISTRATIVO |
| agenda/ | ScheduleView | AdministrativeOnly + Appointment.visible_to | ADMINISTRATIVO |
| salas/ | RoomsView | AdministrativeOnly + Room.visible_to | ADMINISTRATIVO |
| declaracoes/ | DeclarationsView | AdministrativeOnly + visible_to dos documentos | ADMINISTRATIVO |
| atestados/ | CertificatesView | CanIssueCertificates (AdministrativeOnly + AttendanceCertificate.can_be_created_by) | ADMINISTRATIVO |
| atestados/atendimentos/ | CertificateAppointmentsView (JSON) | CanIssueCertificates | ADMINISTRATIVO |

O Superadmin (superuser) não acessa as telas do Administrativo: o `AdministrativeOnly` confere só a role.
 
## patient/ (prefixo /patient/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| home | PatientHomeView | PatientOnly (LoginRequiredMixin + UserPassesTestMixin, role PACIENTE) | PACIENTE, só os próprios dados |
| agendamentos/ | PatientAppointmentsView | PatientOnly + Appointment e AppointmentRequest.visible_to | PACIENTE |
| agendamentos/solicitar/ | AppointmentRequestView | PatientOnly + AppointmentRequest.can_be_created_by | PACIENTE; uma solicitação pendente por vez |
| historico/ | PatientHistoryView | PatientOnly + Appointment.visible_to | PACIENTE |
| historico/\<pk\>/ | PatientSessionDetailView | PatientOnly + Appointment.visible_to | PACIENTE; sessão de outro paciente ou ainda agendada responde 404 |
| triagens/ | PatientTriagesView | PatientOnly + TriageRecord.visible_to | PACIENTE; só as próprias triagens encerradas |
| triagens/\<pk\>/ | PatientTriageDetailView | PatientOnly + TriageRecord.visible_to | PACIENTE; triagem de outro paciente, aberta ou enviada responde 404 |
| contato/ | PatientContactView | PatientOnly | PACIENTE |
 
## students/ (prefixo /students/)
 
| Rota | View | Mecanismo | Quem acessa |
|---|---|---|---|
| home | HomeEstudanteView | StudentOnly (LoginRequiredMixin + UserPassesTestMixin, role ALUNO) | ALUNO |
| painel/ | PainelEstudanteView | StudentOnly | ALUNO |
| cadastrar/ | cadastrar_aluno | has_perm("students.add_student") | Supervisor |
| perfil/ | PerfilAlunoView | GroupRequiredMixin("Students") | Grupo Students, só o próprio |
| meu-professor/ | MeuProfessorView | StudentOnly | ALUNO |
| prontuarios/ | StudentRecordsView | StudentOnly | ALUNO |
| triagens/ | StudentTriagesView | StudentOnly | ALUNO |
| triagens/\<pk\>/concluida/ | TriageCompletedView | StudentOnly | ALUNO |
| encaminhamentos/ | StudentReferralsView | StudentOnly | ALUNO |
| feedbacks/ | StudentFeedbacksView | StudentOnly | ALUNO |

As rotas valem para WEB e MOBILE: é o mesmo template responsivo, sem rota separada por dispositivo.

O `perfil/` continua no grupo do Django enquanto as outras rotas do Aluno conferem a role — é a mistura de mecanismos já registrada como pendência na legenda.
 
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

O redirecionamento sozinho era silencioso: a pessoa pedia uma página e aparecia noutra, sem explicação. Por isso o handler passou a deixar uma mensagem, que o `base.html` já exibe: "Você não tem acesso a essa página." para quem está autenticado, e "Sua sessão expirou. Entre novamente para continuar." para quem não está. É esse o estado de acesso negado — um aviso na página de destino, não uma tela de erro.
 
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
Um detalhe importante: o handler403 é acionado tanto com DEBUG True quanto com DEBUG False. Foi conferido no container de desenvolvimento: um paciente que digita `/administration/` é redirecionado para `/patient/`. Com DEBUG True, só as páginas de 404 e 500 continuam sendo as páginas técnicas do Django.


## Card 1, relevante pra esse mapa
 
Comparando com as telas do Figma, ficou claro que a separação entre uma tela home vazia e uma tela painel cheia de conteúdo, presente hoje em quase todos os apps, foi uma decisão provisória tomada antes do Figma estar pronto. No fluxo definitivo, cada role tem uma única tela inicial, que já reúne os contadores, atalhos e conteúdo. Não existem as duas telas separadas.
 
será preciso decidir qual das duas views vira a definitiva, normalmente a que já carrega dados reais, garantir que ela tenha a checagem de role certa, remover a outra rota, e atualizar o HOME_BY_ROLE em core/exception_handlers.py, que hoje aponta para os nomes de rota home de cada app.


## Pendências encontradas

não existe hoje nenhum template customizado de erro, nem para 403, nem para 404 ou 500. Como a decisão do time foi nunca mostrar tela de erro pra usuário autenticado sem permissão, isso importa menos pro caso de 403, que já é resolvido pelo redirecionamento. Mas ainda vale considerar se faz sentido ter uma tela de 404 ou 500 com a cara do produto, em vez da página técnica padrão do Django, especialmente pensando em ambiente de produção.
 