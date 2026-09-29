# 🧪 Chaos Lab — Diretrizes de Engenharia & Governança Local (GEMINI.md)

> **Governança Local do Chaos Lab** — Aplicação Companheira de Simulação de Caos e Testes de Resiliência para o OpsMesh.  
> **Nível:** Tier 2 (Microsserviço de Produção / Chaos Engineering)  
> **Stack:** Python 3.12+ com `uv`, FastAPI, Pydantic v2, Datadog APM (`ddtrace`), Scalar API Docs, Tailwind CSS.  

---

## 1. Missão & Arquitetura do Chaos Lab
* **Papel:** Simular um microsserviço de e-commerce real e crítico (`shopcore-api`), com rotas reais de catálogo, checkout e pedidos.
* **Injeção de Falhas:** Endpoints cirúrgicos para injetar cenários de crise controlados (esgotamento de pool PostgreSQL, cascade timeouts de 15s, memory leaks, oscilação de gateway de pagamento).
* **Telemetria Ativa:** Instrumentado nativamente com **Datadog Pro APM (`ddtrace`)** para geração de traces distribuídos e disparo de webhooks para o OpsMesh.
* **Remediação em Runtime:** Endpoint operacional padronizado `POST /operations/mitigate` para que o OpsMesh consiga estancar a crise em < 5s (Nível 1 de remediação).

---

## 2. Padrões Normativos de Backend & API
* **Gerenciador de Pacotes:** `uv` (`pyproject.toml` PEP 621).
* **Framework:** FastAPI assíncrono com lifespan `@asynccontextmanager`.
* **Validação de Dados:** Pydantic v2 com modelos estritos e imutáveis quando aplicável.
* **Documentação Viva de API:** **Scalar obrigatório** em `/docs` ou `/scalar`. Proibido Swagger UI clássico.
* **Observabilidade:** Datadog APM (`ddtrace-run uvicorn`) e logging estruturado com `structlog`.
* **Frontend / Dashboard:** Interface HTML moderna renderizada com Jinja2 e estilizada com **Tailwind CSS** (via CDN/standalone), fornecendo botões interativos para disparar falhas e visualizar status em tempo real.

---

## 3. Qualidade, Testes & Anti-Vibe-Coding
* **Linter & Formatter:** `ruff` estrito (`ruff check --fix`, `ruff format`).
* **Testes Automatizados:** `pytest` assíncrono com cobertura de rotas de negócio, injeção de falhas e endpoints de mitigação.
* **Validação Determinística em Terminal:** Nenhuma alteração é dada por concluída sem evidência em terminal com 100% dos testes passando e 0 erros de linter.
* **Docker & Infraestrutura:** Dockerfile multi-stage non-root elegível para Google Cloud Run com Scale-to-Zero ($0/mês).

---

## 4. Git & Repositório
* **Repositório GitHub:** `henriquebotelhogomes/chaos-lab`.
* **Branch Principal:** `main`. Todas as inspeções remotas de código do OpsMesh serão direcionadas a esta branch.
* **Commits:** Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`).
