# Changelog

All notable changes to SoftLanding will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [CalVer](https://calver.org/) versioning (YYYY.0M.MICRO).

## [2026.02.1] - 2026-02-28

### Maintenance

- Add VERSION file (CalVer 2026.02.0)

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

