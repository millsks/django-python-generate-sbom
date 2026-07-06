---
title: Generate SBOM — Project Overview
subtitle: "Software Bills of Materials for Python: security, licences, and compliance in one place"
description: >-
  A self-hosted web application that turns a Python dependency manifest into a
  standards-based Software Bill of Materials, plus vulnerability, licence,
  dependency-graph, and version-currency analysis — delivered in one dashboard,
  exportable, and API-accessible.
type: presentation
format: executive-overview
status: final
version: "1.0"
date: 2026-07-06
language: en-GB
license: Apache-2.0
authors:
  - name: Kevin Mills
    role: Author
audience:
  - Engineering leadership
  - Security / DevSecOps
  - Legal / compliance
tags:
  - sbom
  - software-supply-chain
  - security
  - licence-compliance
  - python
  - cyclonedx
  - spdx
  - self-hosted
source:
  deck: presentations/Generate-SBOM-Executive-Overview.pptx
  pdf: presentations/Generate-SBOM-Executive-Overview.pdf
slides: 9
summary: >-
  One dependency file in, a complete software inventory out. Generate SBOM
  resolves every direct and transitive Python dependency and produces a
  standards-based bill of materials with vulnerability, licence, graph, and
  currency reports — self-hosted, in under two minutes.
key_facts:
  status: Delivered — 14 epics complete
  inputs: 5 Python manifest formats
  outputs: CycloneDX JSON/XML · SPDX 2.3
  reports: Vulnerabilities, licences, dependency graph, version currency
  speed: Results in under 2 minutes (average)
  quality: 95%+ backend test coverage
  model: Multi-tenant, self-hosted, Apache 2.0
---

# Generate SBOM — Project Overview

> **Know what's inside your software — before someone else has to ask.**
>
> *Software Bills of Materials for Python · security, licences, and compliance in one place.*
> Prepared by Kevin Mills · July 2026 · Self-hosted · Open source · Apache 2.0

Generate SBOM is a self-hosted web application that turns a Python project's dependency
file into a standards-based software inventory, plus security, licence, and currency
analysis. This document mirrors the executive-overview deck slide by slide — why we built
it, how it works and how it was built, what shipped, and what comes next — with the
speaker notes preserved for each section.

## Contents

1. [Executive summary](#1--executive-summary)
2. [Why we did this](#2--why-we-did-this)
3. [How we did this — the product](#3--how-we-did-this--the-product)
4. [How we did this — the delivery](#4--how-we-did-this--the-delivery)
5. [The outcome](#5--the-outcome)
6. [What comes next](#6--what-comes-next)
7. [Terms & abbreviations](#7--terms--abbreviations)
8. [Closing](#8--closing)

---

## 1 · Executive summary

### One dependency file in, a complete inventory out

The Generate SBOM project answers a question most teams can't: **what is actually inside
this software?**

Upload a project's dependency manifest and, in under two minutes, the system resolves
every direct and transitive library and produces a standards-based Bill of Materials
alongside vulnerability, licence, dependency-graph, and version-currency reports — in one
dashboard, exportable, and API-accessible.

It runs entirely on your own infrastructure. No dependency data leaves your servers, and
it deploys with a single `docker compose up`.

**At a glance**

| | |
|---|---|
| **Status** | Delivered — 14 epics complete |
| **Inputs** | 5 Python manifest formats |
| **Outputs** | CycloneDX JSON/XML · SPDX 2.3 |
| **Reports** | Vulnerabilities, licences, graph, currency |
| **Speed** | Results in under 2 minutes (average) |
| **Quality** | 95%+ backend test coverage |
| **Model** | Multi-tenant, self-hosted, Apache 2.0 |

> **Speaker notes** — The one-slide version: a dependency file goes in; a standards-based
> SBOM and a full analysis suite come out, fast, on your own infrastructure. The panel on
> the right is the whole project in seven lines.

---

## 2 · Why we did this

### Teams can't secure or certify what they can't see

A modern Python project pulls in hundreds of libraries it never names directly. That
invisible chain is exactly where risk — and regulation — now lives.

1. **Security exposure.** A single vulnerable library buried deep in the dependency chain
   is enough to expose a product. Most teams have no fast way to find it until after an
   incident.
2. **Licence risk.** Some open-source licences carry legal obligations on anyone who ships
   them. Without a full inventory, legal and compliance teams are working blind.
3. **Compliance is now mandatory.** The EU Cyber Resilience Act (in force 2027) requires an
   SBOM for products sold in the EU, and enterprise buyers increasingly demand one
   regardless of regulation.

And because dependency data is sensitive, everything runs self-hosted — nothing leaves
your own servers.

> **Speaker notes** — Three drivers, all pointing the same way: you cannot manage what you
> cannot see. Security and licence risk hide in the transitive chain, and from 2027 the EU
> CRA makes an SBOM a condition of selling into Europe. Self-hosting is a deliberate answer
> to the sensitivity of the data itself.

---

## 3 · How we did this — the product

### An asynchronous pipeline from manifest to inventory

1. **Upload** — `requirements.txt`, `pyproject.toml`, pixi, or `environment.yml`
2. **Resolve** — direct + transitive dependencies
3. **Analyse** — vulnerabilities · licences · graph · currency
4. **Assemble** — CycloneDX & SPDX bill of materials
5. **Review & export** — dashboard, download, or API

Jobs run in the background, so a large project resolves without blocking — typically in
under two minutes.

| | |
|---|---|
| **Built on** | Django · DRF · Celery on PostgreSQL, Redis & S3-compatible storage; React + TypeScript UI |
| **Speaks** | CycloneDX (JSON/XML) and SPDX 2.3 — accepted by regulators, buyers, and security tools |
| **Sourced from** | OSV · PyPI · conda-forge (prefix.dev) · endoflife.date |

> **Speaker notes** — The product is an async pipeline: upload, resolve the full dependency
> tree, run four analyses in parallel, assemble a standards-based SBOM, then review or
> export. It's a conventional, boring-on-purpose stack — Django/DRF/Celery with a React UI
> — speaking open standards and pulling from well-known public data sources.

---

## 4 · How we did this — the delivery

### Small stories, one toolchain, a gate that can't be skipped

- **Story-driven delivery.** Every change — feature, fix, or doc — was scoped as a
  contexted story with explicit acceptance criteria before any code was written.
- **One command for everything.** A single toolchain (pixi) orchestrates both the Python
  backend and the Node frontend: build, lint, type-check, test, and docs.
- **A quality gate on every merge.** Formatting, strict type-checking, linting, a security
  scan, and the full test suite must all pass before anything lands — enforced, not
  optional.
- **Reviewed, isolated changes.** Each feature and fix rode its own branch into a small
  pull request; nothing was committed straight to the main line.

**The merge gate**

- [x] format
- [x] type-check (strict)
- [x] lint
- [x] security scan
- [x] full test suite — 90% floor
- [x] package & docs build

*Achieved: 95%+ backend coverage.*

> **Speaker notes** — The method mattered as much as the product. Work was decomposed into
> small, fully-contexted stories; a single toolchain ran the whole project; and an
> automated gate made it impossible to merge anything that wasn't formatted, typed, linted,
> security-scanned, and tested above a 90% floor. That discipline is why the result is
> coherent rather than a pile of features.

---

## 5 · The outcome

### A working platform, not a prototype

| 14 | 95%+ | 5 → 3 | < 2 min | 10 days |
|---|---|---|---|---|
| epics delivered | test coverage | formats in / out | typical run | auto-retention |

**What shipped**

- **Standards-based SBOM** — CycloneDX JSON/XML and SPDX 2.3, viewable in-app or
  downloadable, now with per-component licences embedded in the document.
- **The full report suite** — vulnerabilities, licences, dependency graph, and version
  currency, each with a formatted Excel export.
- **Multi-tenant access** — full isolation between organisations and a guarded two-tier
  admin model (organisation admin and global administrator).
- **Docs, API & deploy** — a published documentation site, a complete REST API with an
  interactive schema, and a one-command `docker compose` deployment.

> **Speaker notes** — The result is a complete, deployable product. All fourteen planned
> epics are done: the SBOM itself, the four analysis reports with Excel export, a
> multi-tenant access model with a carefully-guarded admin hierarchy, a docs site, and a
> full REST API. The headline numbers are real, not aspirational.

---

## 6 · What comes next

### From inventory to continuous assurance

**Near-term**

- **SBOM in the pipeline** — generate and gate on every build through the API and CI, so
  the inventory is never stale.
- **Scheduled re-scans & drift alerts** — re-check existing projects and notify when a new
  vulnerability lands on a dependency you already ship.

**Mid-term**

- **Signing & provenance** — attest SBOMs (e.g. Sigstore) so downstream consumers can trust
  where they came from.
- **VEX support** — record exploitability so teams triage the vulnerabilities that affect
  them, not just the ones that exist.

**Longer-term**

- **Beyond Python** — extend dependency resolution to additional package ecosystems.
- **Configurable conda solve** — platform- and CUDA-aware solving, the one item
  deliberately deferred from this phase.

*The through-line: move from a point-in-time snapshot to continuous, verifiable assurance.*

> **Speaker notes** — The roadmap is honest and sequenced. Near-term is about making the
> SBOM continuous (in CI, with drift alerts). Mid-term adds trust: signing and VEX.
> Longer-term broadens scope beyond Python and picks up the one item we deliberately parked.
> Every item is a real extension of what already ships — nothing speculative.

---

## 7 · Terms & abbreviations

| Term | Meaning |
|---|---|
| **SBOM** | Software Bill of Materials — a machine-readable inventory of every component in a piece of software. |
| **CycloneDX** | An OWASP SBOM standard; the app emits both JSON and XML. |
| **SPDX** | A Linux Foundation SBOM standard (version 2.3 supported here). |
| **CVE** | Common Vulnerabilities and Exposures — a public identifier for a known security flaw. |
| **VEX** | Vulnerability Exploitability eXchange — a statement of whether a known flaw affects a product. |
| **Transitive dependency** | A library pulled in indirectly by another dependency, not declared by you directly. |
| **Manifest** | The file that declares a project's dependencies (e.g. `requirements.txt`, `pyproject.toml`). |
| **OSV** | Open-Source Vulnerabilities — a distributed vulnerability database for open-source projects. |
| **PyPI** | The Python Package Index — the primary source of Python packages. |
| **conda-forge** | A community-run package repository for the conda ecosystem. |
| **Version currency** | How far behind the latest release each dependency is running. |
| **EOL / LTS** | End of Life / Long-Term Support — whether a version still receives updates. |
| **Copyleft / Permissive** | Licence families; copyleft can impose obligations on distributed software, permissive generally does not. |
| **CRA** | EU Cyber Resilience Act — regulation requiring an SBOM for products sold in the EU (effective 2027). |
| **Global admin** | An account that administers the whole installation across every organisation. |

> **Speaker notes** — A plain-language glossary so the deck stands on its own for a mixed
> audience — security, legal, and leadership shouldn't need to decode acronyms to follow it.

---

## 8 · Closing

### Generate SBOM

**Know what's inside your software — before someone else has to ask.**

Self-hosted · open source · Apache 2.0 — deployable in minutes with a single command.
Full documentation and REST API ship with the platform.

*Questions welcome.*

> **Speaker notes** — Close on the core promise. The product exists, it's deployable today,
> and it's documented. Open for discussion.
