from django.db import models
from django.conf import settings

class AuditLog(models.Model):

    class Action(models.TextChoices):
        CREATE = "create", "Criação"
        UPDATE = "update", "Atualização"
        DELETE = "delete", "Exclusão"
        LOGIN = "login", "Login"

    model_name = models.CharField(max_length=100)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, blank=True,
        on_delete=models.SET_NULL, 
        related_name="audit_events",
    )

    action = models.CharField(max_length=20, choices=Action.choices)
    object_id = models.CharField(max_length=64)

    changes = models.JSONField(default=dict, blank=True) 
 
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True) 
  
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["model_name", "object_id"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Segurança: Logs de Auditoria não podem ser alterados após criados.")
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        raise ValueError("Segurança: Logs de Auditoria não podem ser apagados pelo sistema.")
    