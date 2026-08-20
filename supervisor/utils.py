import string
import secrets 
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

def enviar_email_credenciais(user, senha_temporaria):
    """
    Formata e envia o e-mail de boas-vindas com a senha temporária.
    """
    link_portal = "https://seusistema.com.br/login" #Adicionar o link da pagia de login
    
    mensagem = (
        f"Olá {user.nome_completo},\n\n"
        f"Seu cadastro foi realizado com sucesso.\n"
        f"Sua senha temporária é: {senha_temporaria}\n\n"
        f"Acesse o portal em {link_portal}"
    )
    
    send_mail(
        subject="Bem-vindo ao Sistema - Cadastro Realizado",
        message=mensagem,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False, 
    )

def gerar_senha_temporaria(tamanho=8):
    caracteres = string.ascii_letters + string.digits
    senha_provisoria = ''.join(secrets.choice(caracteres) for _ in range(tamanho))
    return senha_provisoria