-- Ejecutar conectado a la base "postgres" con un usuario administrador.
-- Este archivo corresponde al .env incluido en el proyecto.
-- Cambie la contraseña antes de usarla en producción.

CREATE ROLE armamento_user
    WITH LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOINHERIT
    NOREPLICATION
    NOBYPASSRLS
    PASSWORD 'xkaBfqxmXNM_-BD2xoIFjtM4bwk_4Kmp';

CREATE DATABASE control_armamento
    WITH
    OWNER = armamento_user
    ENCODING = 'UTF8'
    TEMPLATE = template0;

REVOKE ALL ON DATABASE control_armamento FROM PUBLIC;
GRANT CONNECT, TEMPORARY ON DATABASE control_armamento TO armamento_user;
