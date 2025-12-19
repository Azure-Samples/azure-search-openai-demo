# Database Layer - Enterprise Features

## 🎯 Overview

This module adds **PostgreSQL persistence** with **automatic fallback** to in-memory storage. Follows **Microsoft Azure**, **GitHub Enterprise**, and **Stack Overflow** best practices.

## ✅ What's Included

### 1. **Database Models** (`db/models.py`)
- `BrowserAgentModel` - Browser agent persistence
- `TaskModel` - Task tracking with status/priority
- `ProjectModel` - Taskade project metadata
- `AuditLogModel` - Compliance and security audit trail

**Features:**
- Timestamps for all records
- Soft deletes (deleted_at)
- JSON fields for flexible metadata
- Proper indexes on frequently queried columns
- Enum types for status/priority

### 2. **Database Manager** (`db/database.py`)
- Async SQLAlchemy with `asyncpg` driver
- Connection pooling (Azure PostgreSQL optimized)
- Health checks for monitoring
- **Graceful fallback** to in-memory if DB unavailable

### 3. **Helper Functions** (`db/helpers.py`)
- `save_agent_to_db()` - Persist browser agent
- `update_agent_status()` - Update agent state
- `delete_agent_from_db()` - Soft delete agent
- `log_audit_event()` - Compliance logging
- All functions work with or without database

### 4. **Database Migrations** (`alembic/`)
- Alembic configuration for schema changes
- Async support
- Auto-generate migrations from models

## 🚀 Quick Start

### Option 1: Local Development (Docker PostgreSQL)

```bash
# Start PostgreSQL container
docker run --name postgres-agentdb \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=agentdb \
  -p 5432:5432 \
  -d postgres:16-alpine

# Set environment variable
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/agentdb"

# Run migrations
cd app/backend
alembic upgrade head

# Start app
python -m quart run --port 50505
```

### Option 2: Azure PostgreSQL

```bash
# Get connection string from Azure Portal
export DATABASE_URL="postgresql+asyncpg://user@server:password@server.postgres.database.azure.com:5432/agentdb?sslmode=require"

# Or set individual components
export POSTGRES_HOST="myserver.postgres.database.azure.com"
export POSTGRES_USER="myadmin"
export POSTGRES_PASSWORD="mypassword"
export POSTGRES_DB="agentdb"

# Run migrations
alembic upgrade head

# Start app
python -m quart run --port 50505
```

### Option 3: No Database (Fallback Mode)

```bash
# Don't set DATABASE_URL - app runs in-memory mode
python -m quart run --port 50505
```

**App will log:**
```
WARNING: No database configuration found. Will run in fallback mode (in-memory).
```

## 📊 Database Schema

```sql
-- Browser Agents
CREATE TABLE browser_agents (
    id VARCHAR(255) PRIMARY KEY,
    channel VARCHAR(50) NOT NULL,
    headless BOOLEAN NOT NULL DEFAULT FALSE,
    status ENUM('created', 'starting', 'running', 'stopped', 'error'),
    config JSON,
    created_by VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP,
    total_actions INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0
);

-- Tasks
CREATE TABLE tasks (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(512) NOT NULL,
    description TEXT,
    status ENUM('pending', 'running', 'completed', 'failed', 'cancelled'),
    priority ENUM('low', 'medium', 'high', 'urgent'),
    project_id VARCHAR(255) REFERENCES projects(id),
    agent_id VARCHAR(255) REFERENCES browser_agents(id),
    task_type VARCHAR(100),
    payload JSON,
    result JSON,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

-- Projects
CREATE TABLE projects (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(512) NOT NULL,
    workspace_id VARCHAR(255),
    folder_id VARCHAR(255),
    description TEXT,
    metadata JSON,
    created_by VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    deleted_at TIMESTAMP
);

-- Audit Logs (Compliance)
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    user_id VARCHAR(255),
    user_email VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent VARCHAR(512),
    details JSON,
    old_value JSON,
    new_value JSON,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    timestamp TIMESTAMP NOT NULL
);
```

## 🔧 Database Migrations

```bash
# Create new migration (auto-detect changes)
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

## 🏥 Health Checks

The system provides three health check endpoints:

### 1. `/api/agents/health` - Basic Liveness
```bash
curl http://localhost:50505/api/agents/health
```
Returns simple OK status. Always 200 if app is running.

### 2. `/api/agents/health/ready` - Readiness Check
```bash
curl http://localhost:50505/api/agents/health/ready
```
Returns detailed component status:
- Database connectivity
- Taskade API availability
- In-memory state

Returns 200 if ready, 503 if not ready.

### 3. `/api/agents/health/live` - Liveness Probe
```bash
curl http://localhost:50505/api/agents/health/live
```
Always returns 200. For Kubernetes liveness probes.

## 📝 Audit Logging

All significant actions are logged to `audit_logs` table for compliance:

**Event Types:**
- `agent.create`, `agent.delete`, `agent.start`, `agent.stop`
- `task.create`, `task.complete`, `task.fail`
- `project.create`, `project.update`

**Example Query:**
```sql
-- Find all agent creations in last 24 hours
SELECT * FROM audit_logs
WHERE event_type = 'agent.create'
  AND timestamp >= NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- Audit trail for specific agent
SELECT * FROM audit_logs
WHERE resource_type = 'agent'
  AND resource_id = 'agent_12345'
ORDER BY timestamp ASC;
```

## 🔐 Security Best Practices

1. **Connection Strings**: Never commit to Git
   - Use environment variables
   - Azure: Store in Key Vault
   - Local: Use `.env` file (git-ignored)

2. **SSL/TLS**: Always use SSL in production
   - Azure PostgreSQL: `?sslmode=require`
   - Local dev: SSL optional

3. **Least Privilege**: Database user permissions
   - App user: `SELECT, INSERT, UPDATE, DELETE` only
   - No `CREATE TABLE`, `DROP` permissions
   - Migrations: Use separate admin user

4. **Connection Pooling**: Already configured
   - Pool size: 10
   - Max overflow: 20
   - Pre-ping: Enabled
   - Recycle: 3600s

## 🎯 Performance Tips

1. **Indexes**: Already added on:
   - `status` (frequent filtering)
   - `created_by` (multi-tenant queries)
   - `created_at` (time-range queries)
   - Foreign keys

2. **Connection Pool**: Tune based on load
   ```python
   # In db/database.py
   self.engine = create_async_engine(
       url,
       pool_size=20,        # Increase for high load
       max_overflow=40,     # Double pool_size
   )
   ```

3. **Query Optimization**:
   - Use `select()` with specific columns
   - Add `.limit()` for large result sets
   - Use indexes in WHERE clauses

## 🐛 Troubleshooting

### Database Connection Fails
```
ERROR: Failed to initialize database: asyncpg.exceptions.InvalidPasswordError
```
**Solution**: Check `DATABASE_URL` or `POSTGRES_PASSWORD`

### Migrations Fail
```
ERROR: Can't locate revision identified by 'abc123'
```
**Solution**: Reset Alembic history
```bash
alembic stamp head
```

### App Runs in Fallback Mode
```
WARNING: No database configuration found. Will run in fallback mode.
```
**Solution**: Set `DATABASE_URL` environment variable

### SSL Certificate Error (Azure)
```
ERROR: SSL error: certificate verify failed
```
**Solution**: Add `?sslmode=require` to connection string

## 📊 Monitoring

### Key Metrics to Track

1. **Database Health**:
   - Connection pool usage
   - Query latency (p50, p95, p99)
   - Failed connections

2. **Audit Logs**:
   - Events per minute
   - Failed operations rate
   - User activity patterns

3. **Storage**:
   - Table sizes
   - Index usage
   - Disk space growth

### Example Queries

```sql
-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Active connections
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';

-- Slow queries (>1 second)
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC
LIMIT 10;
```

## 🎓 Next Steps (Tier 2)

After completing Tier 1 (Database), next Enterprise features:

1. **Redis Cache** - Session management, rate limiting
2. **Rate Limiting** - Per-user, per-API quotas
3. **Application Insights** - Azure monitoring
4. **CORS + Security Headers** - Production hardening

See main Enterprise upgrade plan in project root.

## 📚 References

- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Migrations](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Azure PostgreSQL Best Practices](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-best-practices)
- [asyncpg Documentation](https://magicstack.github.io/asyncpg/current/)

---

**Questions?** Check the main project documentation or create an issue.
