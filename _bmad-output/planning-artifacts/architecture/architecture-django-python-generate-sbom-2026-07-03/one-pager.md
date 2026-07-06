# django-python-generate-sbom — Product Overview

## What It Is

**django-python-generate-sbom** is a self-hosted, open-source web application that answers a simple but critical question: *"What is actually inside this Python project?"* Upload your project's dependency file, and within minutes the system tells you every library your software relies on, whether any of them have known security vulnerabilities, what licences they carry, and how current they are — all presented in a clear web dashboard and available for download in industry-standard formats.

---

## The Problem It Solves

- **Security exposure.** Python projects routinely depend on hundreds of third-party libraries. A single vulnerable library buried deep in that chain can expose your product to attack — but most teams have no easy way to discover it until something goes wrong.
- **Licence risk.** Some open-source licences place strict legal obligations on anyone who ships software using them. Without a clear picture of every licence in your dependency chain, legal and compliance teams are flying blind.
- **Compliance demands.** Regulators and enterprise procurement teams increasingly require a formal inventory of software components. The EU Cyber Resilience Act (effective 2027) mandates this for products sold into European markets; large enterprise buyers often require it regardless of regulation.

---

## What It Produces

| Output | What it tells you |
|---|---|
| **Software Bill of Materials (SBOM)** | A standardised, machine-readable inventory of every library your project uses — the "ingredients label" for your software. Accepted by regulators, procurement teams, and security tools. |
| **Vulnerability Report** | Which of your dependencies have known security weaknesses, how severe they are, and where to find the details. |
| **Licence Report** | Every licence in your dependency chain, grouped by risk level — from permissive (use freely) to copyleft (may impose obligations) to unknown (needs legal review). |
| **Dependency Map** | An interactive visual diagram showing which libraries depend on which others, making it easy to understand your software's structure at a glance. |

---

## Who It Is For

- **Developers** who need a fast, self-service answer before a release or code review
- **Security and DevSecOps teams** who want to integrate SBOM generation into automated pipelines via an API
- **Legal and compliance teams** preparing for regulatory audits or enterprise procurement reviews
- **Any organisation** that builds, ships, or procures Python software

---

## How It Works

1. **Upload** your project's dependency file (the file that lists what your software uses)
2. **Wait** — the system automatically analyses all dependencies, checks for vulnerabilities, reviews licences, and builds a dependency map (typically under 2 minutes)
3. **Review** results in a web dashboard with separate tabs for each report type
4. **Download** your SBOM in your preferred format, or share a link to the results with your team

---

## Why Open Source and Self-Hosted

- **Your data stays on your infrastructure.** No dependency files or analysis results leave your own servers.
- **Free to use.** No licences, subscriptions, or per-scan fees.
- **Apache 2.0 licence.** Safe to use in commercial products and enterprise environments without legal complications.
- **Deployable in minutes.** A single `docker compose up` command starts the entire system.

---

## Teams and Access

One installation can host many organisations, fully isolated from one another. Access follows a simple, deliberate model:

- **Sign up, then get added.** A new account starts with **no organisation** — it is a valid login on its own. You gain access to a workspace when an admin adds you to their organisation (by your email, or by creating an account for you) or when a platform administrator sets up an organisation for you.
- **Two admin levels.** Inside an organisation, an **admin** manages members, promotes or demotes other admins, and controls API keys. A **global administrator** operates across the whole installation: they create organisations, are automatically an admin of every organisation, and decide who else holds global-administrator rights.
- **Guarded by design.** Every organisation always keeps at least one admin, and the platform always keeps at least one global administrator — access can never be accidentally locked out. Administrative actions are enforced on the server, not merely hidden in the interface.

---

## Key Facts

- Supports **5 Python package formats**: `requirements.txt`, `pyproject.toml`, `pixi.lock`, `pixi.toml`, and `conda environment.yml`
- Produces SBOMs in **3 standard formats**: CycloneDX JSON, CycloneDX XML, and SPDX 2.3
- Results ready in **under 2 minutes** for most projects (under 250 packages)
- Analysis results stored for **10 days**, then automatically removed — keeping data fresh and storage lean
- Supports **multiple teams** on one installation, with full isolation between organisations
