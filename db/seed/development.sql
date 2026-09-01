BEGIN;

-- These seed users use a reusable bcrypt-format placeholder hash so the schema
-- remains structurally correct for local development. Replace with real hashes
-- before any serious authentication testing.
-- Placeholder hash length is 60 chars and uses bcrypt cost factor 12.

INSERT INTO users (id, username, email, role, password_hash, last_login_at, created_at, updated_at)
VALUES
    ('11111111-1111-4111-8111-111111111111', 'admin_demo', 'admin@uow.edu.au', 'admin', '$2a$12$GnQ1/tiGhP3Ouc2K3i00o.JeQjJTzv6/x6nVZcf5hNVxNYzQ6W4Xi', '2026-04-21 08:45:00+10', NOW(), NOW()),
    ('22222222-2222-4222-8222-222222222222', 'lecturer_demo', 'lecturer@uow.edu.au', 'lecturer', '$2a$12$GnQ1/tiGhP3Ouc2K3i00o.JeQjJTzv6/x6nVZcf5hNVxNYzQ6W4Xi', '2026-04-21 09:00:00+10', NOW(), NOW()),
    ('33333333-3333-4333-8333-333333333333', 'student_demo', 'student@uow.edu.au', 'student', '$2a$12$GnQ1/tiGhP3Ouc2K3i00o.JeQjJTzv6/x6nVZcf5hNVxNYzQ6W4Xi', '2026-04-21 09:15:00+10', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO courses (id, course_code, course_name, description, is_active, created_at, updated_at)
VALUES
    ('44444444-4444-4444-8444-444444444444', 'CSIT321', 'Project', 'Sample course used for EduRAG Sprint 3 development.', TRUE, NOW(), NOW()),
    -- T8-13 (Sprint 8): real UOW subjects added alongside CSIT321/CSIT214 so
    -- local dev Postgres matches the multi-subject ChromaDB corpus.
    ('44444444-4444-4444-8444-444444444445', 'CSIT214', 'IT Project Management', 'Scope, schedule, cost estimation, Agile/Scrum, risk, and ethics for IT projects.', TRUE, NOW(), NOW()),
    ('44444444-4444-4444-8444-444444444446', 'CSCI369', 'Ethical Hacking', 'Penetration testing concepts, information gathering, TCP/IP, scanning, and MITM techniques.', TRUE, NOW(), NOW()),
    ('44444444-4444-4444-8444-444444444447', 'MATH202', 'Differential Equations. Analysis and Applications', 'First- and second-order ODEs and their applications.', TRUE, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO course_memberships (id, user_id, course_id, membership_role, joined_at, created_at, updated_at)
VALUES
    ('55555555-5555-4555-8555-555555555555', '22222222-2222-4222-8222-222222222222', '44444444-4444-4444-8444-444444444444', 'lecturer', NOW(), NOW(), NOW()),
    ('66666666-6666-4666-8666-666666666666', '33333333-3333-4333-8333-333333333333', '44444444-4444-4444-8444-444444444444', 'student', NOW(), NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO documents (
    id,
    course_id,
    uploaded_by_user_id,
    original_filename,
    stored_path,
    mime_type,
    file_size_bytes,
    page_count,
    sha256_checksum,
    uploaded_at,
    updated_at
)
VALUES (
    '77777777-7777-4777-8777-777777777777',
    '44444444-4444-4444-8444-444444444444',
    '22222222-2222-4222-8222-222222222222',
    'week01-introduction.pdf',
    'data/uploads/csit321/week01-introduction.pdf',
    'application/pdf',
    154321,
    12,
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    NOW(),
    NOW()
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO indexing_jobs (
    id,
    document_id,
    course_id,
    queued_by_user_id,
    job_status,
    progress_percent,
    attempt_count,
    error_message,
    enqueued_at,
    started_at,
    completed_at,
    updated_at
)
VALUES (
    '88888888-8888-4888-8888-888888888888',
    '77777777-7777-4777-8777-777777777777',
    '44444444-4444-4444-8444-444444444444',
    '22222222-2222-4222-8222-222222222222',
    'completed',
    100,
    1,
    NULL,
    NOW() - INTERVAL '10 minutes',
    NOW() - INTERVAL '9 minutes',
    NOW() - INTERVAL '8 minutes',
    NOW() - INTERVAL '8 minutes'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO conversation_sessions (
    id,
    user_id,
    course_id,
    session_title,
    session_status,
    started_at,
    last_activity_at,
    updated_at
)
VALUES (
    '99999999-9999-4999-8999-999999999999',
    '33333333-3333-4333-8333-333333333333',
    '44444444-4444-4444-8444-444444444444',
    'Week 1 concepts',
    'active',
    NOW() - INTERVAL '5 minutes',
    NOW() - INTERVAL '1 minute',
    NOW() - INTERVAL '1 minute'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO conversation_messages (
    id,
    session_id,
    turn_index,
    message_role,
    message_text,
    source_references,
    confidence_label,
    is_fallback,
    created_at
)
VALUES
    (
        'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
        '99999999-9999-4999-8999-999999999999',
        1,
        'student',
        'What is retrieval-augmented generation in the context of EduRAG?',
        '[]'::JSONB,
        NULL,
        FALSE,
        NOW() - INTERVAL '2 minutes'
    ),
    (
        'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
        '99999999-9999-4999-8999-999999999999',
        2,
        'assistant',
        'Retrieval-augmented generation combines document retrieval with answer generation so responses can be grounded in course materials.',
        '[{"document_name":"week01-introduction.pdf","page_number":1,"chunk_index":0}]'::JSONB,
        'High',
        FALSE,
        NOW() - INTERVAL '1 minute'
    )
ON CONFLICT (id) DO NOTHING;

INSERT INTO refresh_tokens (
    id,
    user_id,
    token_hash,
    issued_at,
    expires_at,
    last_used_at,
    revoked_at,
    updated_at
)
VALUES (
    'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
    '33333333-3333-4333-8333-333333333333',
    '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
    NOW() - INTERVAL '30 minutes',
    NOW() + INTERVAL '7 days',
    NOW() - INTERVAL '1 minute',
    NULL,
    NOW() - INTERVAL '1 minute'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO audit_logs (
    id,
    user_id,
    course_id,
    session_id,
    event_type,
    event_level,
    event_payload,
    occurred_at
)
VALUES
    (
        'dddddddd-dddd-4ddd-8ddd-dddddddddddd',
        '22222222-2222-4222-8222-222222222222',
        '44444444-4444-4444-8444-444444444444',
        NULL,
        'document.upload.completed',
        'info',
        '{"document_id":"77777777-7777-4777-8777-777777777777","job_id":"88888888-8888-4888-8888-888888888888"}'::JSONB,
        NOW() - INTERVAL '8 minutes'
    ),
    (
        'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',
        '33333333-3333-4333-8333-333333333333',
        '44444444-4444-4444-8444-444444444444',
        '99999999-9999-4999-8999-999999999999',
        'query.completed',
        'info',
        '{"session_id":"99999999-9999-4999-8999-999999999999","retrieved_chunk_count":5,"fallback_used":false}'::JSONB,
        NOW() - INTERVAL '1 minute'
    )
ON CONFLICT (id) DO NOTHING;

COMMIT;
