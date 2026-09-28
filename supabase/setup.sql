-- Fresh-project setup, run manually in the Supabase SQL Editor.
-- Do not run blindly against a shared database with an existing rag_content table.
-- Supports vector installed in either public or extensions.
begin;
create extension if not exists vector;
set local search_path = public, extensions;

create table public.rag_content (
    id text primary key,
    embedding vector(1536) not null,
    context text not null,
    user_id integer not null,
    document_type text not null,
    document_id text,
    username text
);

-- This setup is for an operator-controlled backend using a secret key.
alter table public.rag_content enable row level security;
revoke all on table public.rag_content from anon, authenticated;
grant select, insert, update on table public.rag_content to service_role;

create function public.match_file_reviews(
    query_embedding vector(1536),
    query_repository text,
    query_filename text,
    current_document_id text,
    match_count integer default 3
)
returns table (
    id text,
    document_id text,
    context text,
    similarity double precision
)
language sql
stable
security invoker
set search_path = public, extensions
as $$
    select r.id, r.document_id, r.context,
           1 - (r.embedding <=> query_embedding) as similarity
    from public.rag_content r
    where r.document_type = 'pr_chunk'
      and split_part(r.document_id, '/pulls/', 1) = query_repository
      and r.id = r.document_id || '/files/' || query_filename
      and r.document_id <> current_document_id
    order by r.embedding <=> query_embedding
    limit match_count;
$$;

revoke all on function public.match_file_reviews(vector, text, text, text, integer)
    from public, anon, authenticated;
grant execute on function public.match_file_reviews(vector, text, text, text, integer)
    to service_role;
commit;
