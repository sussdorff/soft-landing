# Changelog

All notable changes to SoftLanding will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [CalVer](https://calver.org/) versioning (YYYY.0M.MICRO).

## [Unreleased]

### Added

- Close 6 dashboard API gaps (list, bulk options, WS handlers, resolve, profile)

## [2026.02.6] - 2026-02-28

### Added

- **infra**: Docker-based CI/CD with GHCR

### Changed

- **backend**: Introduce Ports & Adapters architecture

### Documentation

- Add dashboard API integration reference
- Update changelog

## [2026.02.5] - 2026-02-28

### Added

- **dashboard**: Add keyboard shortcuts for gate agent workflow
- **dashboard**: Connect to real backend API
- **backend**: Add status-based passenger differentiation and wire all external APIs

### Documentation

- Update changelog

### Fixed

- **dashboard**: Handle null disruptionId loading state
- **infra**: Remove duplicate CORS headers from Caddy
- Add base path for dashboard subdirectory deployment

### Maintenance

- Build dashboard in GitHub Actions and fix Caddy path handling
- Add lufthansa-api skill for LH Open API queries
- Bump version to 2026.02.5

## [2026.02.4] - 2026-02-28

### Added

- Initial Safe-Landing KMP project setup
- **dashboard**: Make agent control buttons much more prominent
- **docs**: Add user documentation site with MkDocs Material
- **landing**: Add marketing landing page at get-softlanding.sussdorff.de

### Changed

- Move KMP passenger app into passenger-app/ subdirectory

### Documentation

- Add CLAUDE.md for Claude Code onboarding
- Update changelog

### Fixed

- **infra**: Use handle_path for docs Caddy route
- **infra**: Add /docs -> /docs/ redirect in Caddy

### Maintenance

- Bump version to 2026.02.3
- Bump version to 2026.02.4

## [2026.02.3] - 2026-02-28

### Added

- **dashboard**: Add flight selector and multi-disruption mock data
- **backend**: Add disruption engine, move API docs to /api/docs

### Documentation

- Update changelog

## [2026.02.2] - 2026-02-28

### Added

- **dashboard**: Add search filter and move resolve buttons to front
- **dashboard**: Make overview panel and flight summary collapsible
- **backend**: Switch to Postgres with async SQLAlchemy and realistic seed data

### Documentation

- Add problem/solution overview slides to deck
- Update changelog

### Maintenance

- Add auto-deploy GitHub Action for Hetzner
- Bump version to 2026.02.2

## [2026.02.1] - 2026-02-28

### Added

- **dashboard**: Gate agent dashboard with flight overview and manual resolution

### Documentation

- Distill deck to concise overview, fix mermaid errors
- Update changelog for v2026.02.1

### Maintenance

- Add VERSION file (CalVer 2026.02.0)
- Bump version to 2026.02.1

## [2026.02.0] - 2026-02-28

### Added

- **backend**: Scaffold FastAPI project with mock API, LH client, and Gemini grounding

### Documentation

- Initial planning documents for SoftLanding
- Add beads setup guide, CalVer config, and changelog
- Add Gemini CLI and multi-agent setup instructions to beads guide
- Update tech stack — KMP passenger app, React dashboard, Python backend
- Rename to Soft Landing, update Gemini to 3.0, add architecture doc
- Apply architecture review — parallel roadmap, simplified cascade, simulator-first, gate-agent framing, API contract
- Add Slidev architecture deck
- Extend API contract with WS paths, option detail types, and full REST endpoints
- Record architecture decisions, create monorepo structure
- Add infrastructure section to README
- Update changelog

### Fixed

- Resolve Mermaid parse error in architecture diagram

### Maintenance

- Initialize beads issue tracking
- Add shared configuration template (.env.example)
- Create 6 epics with 25 subtasks, switch beads to JSONL mode

### Infra

- Add Hetzner VPS setup with Caddy, Docker, Python 3.14

