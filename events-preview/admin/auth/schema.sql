-- ISNET AI CMS - Auth & permissions schema
-- Run in Supabase SQL editor.

create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  display_name text,
  role text not null default 'viewer' check (role in ('super_admin','admin','site_admin','editor','writer','viewer','agent')),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_scopes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  site_id text not null,
  module_id text not null,
  created_at timestamptz not null default now(),
  unique(user_id,site_id,module_id)
);

create table if not exists public.audit_log (
  id bigint generated always as identity primary key,
  actor_user_id uuid references public.profiles(id),
  action text not null,
  entity_type text not null,
  entity_id text,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.user_scopes enable row level security;
alter table public.audit_log enable row level security;

create or replace function public.is_super_admin()
returns boolean language sql stable security definer set search_path=public as $$
  select exists(
    select 1 from public.profiles
    where id=auth.uid() and role='super_admin' and is_active=true
  );
$$;

drop policy if exists "profile self read" on public.profiles;
create policy "profile self read" on public.profiles
for select to authenticated using (id=auth.uid() or public.is_super_admin());

drop policy if exists "super admin manages profiles" on public.profiles;
create policy "super admin manages profiles" on public.profiles
for all to authenticated using (public.is_super_admin()) with check (public.is_super_admin());

drop policy if exists "scope self read" on public.user_scopes;
create policy "scope self read" on public.user_scopes
for select to authenticated using (user_id=auth.uid() or public.is_super_admin());

drop policy if exists "super admin manages scopes" on public.user_scopes;
create policy "super admin manages scopes" on public.user_scopes
for all to authenticated using (public.is_super_admin()) with check (public.is_super_admin());

drop policy if exists "audit read super admin" on public.audit_log;
create policy "audit read super admin" on public.audit_log
for select to authenticated using (public.is_super_admin());

-- Audit inserts will later be done through secured server functions.
