# NovaPay Bank API 🏦

API REST bancaria **deliberadamente vulnerable** para laboratorio de seguridad ofensiva.

Cubre el **100% del OWASP API Security Top 10 2023**.

## Quick Start

```bash
docker compose up --build -d
```

- **API:** http://localhost:8080
- **Swagger UI:** http://localhost:8080/docs
- **OpenAPI JSON:** http://localhost:8080/openapi.json (para importar en OWASP ZAP)

## Credenciales

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| admin | admin123 | admin |
| alice | password123 | user |
| bob | bob2024 | user |
| carlos | qwerty | user |
| diana | letmein | auditor |

## Vulnerabilidades

| OWASP API 2023 | Sub-vulnerabilidad |
|---|---|
| API1 — Broken Object Level Authorization | BOLA / IDOR |
| API2 — Broken Authentication | JWT débil + alg:none |
| API3 — Broken Object Property Level Authorization | Excessive Data Exposure + Mass Assignment |
| API4 — Unrestricted Resource Consumption | Rate Limiting |
| API5 — Broken Function Level Authorization | Admin sin role check |
| API6 — Unrestricted Access to Sensitive Business Flows | Business Logic Flaws |
| API7 — Server Side Request Forgery | SSRF via webhook |
| API8 — Security Misconfiguration | SQLi + NoSQLi + Headers + WAF Bypass |
| API9 — Improper Inventory Management | Legacy API v1 sin auth |
| API10 — Unsafe Consumption of APIs | External payment sin validación |

## Writeup

Ver [writeup/writeup.md](writeup/writeup.md) para la guía de explotación completa.

## ⚠️ Disclaimer

Este proyecto es **EXCLUSIVAMENTE para uso educativo** en entornos controlados.
No desplegarlo en redes públicas ni utilizar las técnicas contra sistemas sin autorización.
