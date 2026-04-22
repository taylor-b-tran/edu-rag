BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION prevent_audit_log_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs is append-only and does not allow UPDATE or DELETE operations';
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    role TEXT NOT NULL CHECK (role IN ('student', 'lecturer', 'admin')),
    password_hash VARCHAR(60) NOT NULL,
    last_login_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_code VARCHAR(32) NOT NULL UNIQUE,
    course_name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS course_memberships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    membership_role TEXT NOT NULL CHECK (membership_role IN ('student', 'lecturer')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, course_id)
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    uploaded_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    original_filename TEXT NOT NULL,
    stored_path TEXT NOT NULL UNIQUE,
    mime_type VARCHAR(127) NOT NULL,
    file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes >= 0),
    page_count INTEGER NULL CHECK (page_count IS NULL OR page_count >= 0),
    sha256_checksum CHAR(64) NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_documents_id_course_id UNIQUE (id, course_id)
);

CREATE TABLE IF NOT EXISTS indexing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    queued_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    job_status TEXT NOT NULL CHECK (job_status IN ('queued', 'running', 'completed', 'failed')),
    progress_percent SMALLINT NOT NULL DEFAULT 0 CHECK (progress_percent BETWEEN 0 AND 100),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    error_message TEXT NULL,
    enqueued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_indexing_jobs_document_course
        FOREIGN KEY (document_id, course_id)
        REFERENCES documents(id, course_id)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    session_title VARCHAR(255) NULL,
    session_status TEXT NOT NULL DEFAULT 'active' CHECK (session_status IN ('active', 'archived')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL CHECK (turn_index > 0),
    message_role TEXT NOT NULL CHECK (message_role IN ('student', 'assistant', 'system')),
    message_text TEXT NOT NULL,
    source_references JSONB NOT NULL DEFAULT '[]'::JSONB,
    confidence_label TEXT NULL CHECK (confidence_label IS NULL OR confidence_label IN ('Low', 'Medium', 'High')),
    is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, turn_index)
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash CHAR(64) NOT NULL UNIQUE,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_used_at TIMESTAMPTZ NULL,
    revoked_at TIMESTAMPTZ NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (expires_at > issued_at)
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    course_id UUID NULL REFERENCES courses(id) ON DELETE SET NULL,
    session_id UUID NULL REFERENCES conversation_sessions(id) ON DELETE SET NULL,
    event_type VARCHAR(100) NOT NULL,
    event_level TEXT NOT NULL CHECK (event_level IN ('info', 'warning', 'error')),
    event_payload JSONB NOT NULL DEFAULT '{}'::JSONB,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_documents_id_course_id'
    ) THEN
        ALTER TABLE documents
            ADD CONSTRAINT uq_documents_id_course_id UNIQUE (id, course_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_indexing_jobs_document_course'
    ) THEN
        ALTER TABLE indexing_jobs
            ADD CONSTRAINT fk_indexing_jobs_document_course
            FOREIGN KEY (document_id, course_id)
            REFERENCES documents(id, course_id)
            ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_last_login_at ON users(last_login_at);

CREATE INDEX IF NOT EXISTS idx_courses_is_active ON courses(is_active);

CREATE INDEX IF NOT EXISTS idx_course_memberships_user_id ON course_memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_course_memberships_course_id_role ON course_memberships(course_id, membership_role);

CREATE INDEX IF NOT EXISTS idx_documents_course_id ON documents(course_id);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by_user_id ON documents(uploaded_by_user_id);
CREATE INDEX IF NOT EXISTS idx_documents_uploaded_at ON documents(uploaded_at);

CREATE INDEX IF NOT EXISTS idx_indexing_jobs_document_id ON indexing_jobs(document_id);
CREATE INDEX IF NOT EXISTS idx_indexing_jobs_course_id ON indexing_jobs(course_id);
CREATE INDEX IF NOT EXISTS idx_indexing_jobs_status ON indexing_jobs(job_status);
CREATE INDEX IF NOT EXISTS idx_indexing_jobs_enqueued_at ON indexing_jobs(enqueued_at);

CREATE INDEX IF NOT EXISTS idx_conversation_sessions_user_id_last_activity
    ON conversation_sessions(user_id, last_activity_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_course_id ON conversation_sessions(course_id);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_session_turn
    ON conversation_messages(session_id, turn_index);
CREATE INDEX IF NOT EXISTS idx_conversation_messages_created_at
    ON conversation_messages(created_at);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_active
    ON refresh_tokens(user_id, expires_at)
    WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_audit_logs_occurred_at ON audit_logs(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id_occurred_at ON audit_logs(user_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type_occurred_at ON audit_logs(event_type, occurred_at DESC);

DROP TRIGGER IF EXISTS trg_users_set_updated_at ON users;
CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_courses_set_updated_at ON courses;
CREATE TRIGGER trg_courses_set_updated_at
BEFORE UPDATE ON courses
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_course_memberships_set_updated_at ON course_memberships;
CREATE TRIGGER trg_course_memberships_set_updated_at
BEFORE UPDATE ON course_memberships
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_documents_set_updated_at ON documents;
CREATE TRIGGER trg_documents_set_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_indexing_jobs_set_updated_at ON indexing_jobs;
CREATE TRIGGER trg_indexing_jobs_set_updated_at
BEFORE UPDATE ON indexing_jobs
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_conversation_sessions_set_updated_at ON conversation_sessions;
CREATE TRIGGER trg_conversation_sessions_set_updated_at
BEFORE UPDATE ON conversation_sessions
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_refresh_tokens_set_updated_at ON refresh_tokens;
CREATE TRIGGER trg_refresh_tokens_set_updated_at
BEFORE UPDATE ON refresh_tokens
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_audit_logs_no_mutation ON audit_logs;
CREATE TRIGGER trg_audit_logs_no_mutation
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW
EXECUTE FUNCTION prevent_audit_log_mutation();

COMMIT;
