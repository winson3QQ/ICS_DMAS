# ICS_DMAS — Incident Command System / Disaster Management & Assistance System

A monorepo for ICS field operations tools.

## Projects

| Directory | Description | Status |
|---|---|---|
| `command-dashboard/` | 指揮部幕僚儀表板（FastAPI backend） | Active |
| `shelter-pwa/` | 收容組 PWA | Planned |
| `medical-pwa/` | 醫療組 PWA | Planned |

## Architecture

- PWAs push data to the command dashboard via REST API when online
- Offline-capable via IndexedDB; auto-sync on reconnect
- LAN fallback available in disconnected environments
