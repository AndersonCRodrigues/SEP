-- Roda uma vez, na criação do volume do Postgres.
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- Retenção de 1 ano do log de segurança, todo dia às 03:00.
-- O intervalo espelha SecurityLog.RETENTION_DAYS; mudar um exige mudar o outro.
SELECT cron.schedule(
    'purge-security-logs',
    '0 3 * * *',
    $$DELETE FROM audit_securitylog WHERE created_at < now() - interval '365 days'$$
);
