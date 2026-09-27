# Setup verification — 2026-09-27

- Python 3.14.7 (uv-managed); uv 0.12.19; Node 25.9.0; pnpm 11.19.0.
- Next.js 16.3.6, React 19.2.8, MapLibre 6.11.2; pinned dependency resolutions in pnpm-lock.yaml and uv.lock.
- PostGIS 3.5 / PostgreSQL 17 Docker container healthy, localhost:5432.
- Alembic upgrade head passed; alembic check found no pending schema operations.
- reservoirs.location verified as POINT, SRID 4326.
- Development seed created DT001 and DEMO002; repeated seed inserted zero duplicates.
- HTTP 200: /api/v1/health, /api/v1/reservoirs, /docs, frontend /.
- API returned both actual database records and expected coordinates.
- Next.js rendered both records; verified in browser.
- CORS response allowed http://localhost:3000.
- Ruff, ESLint and Next.js production build passed.
- MapLibre worker and shared module copied successfully.
- Local environment files excluded from Git.

The sample data is only for software integration testing. No research validation is implied.
