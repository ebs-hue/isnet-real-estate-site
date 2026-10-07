-- ISNET CMS - agent orchestration foundation
create table if not exists public.agent_tasks (
  id uuid primary key default gen_random_uuid(),
  agent_id text not null,
  entity_type text not null,
  entity_id text not null,
  city_slug text,
  status text not null default 'pending'
    check (status in ('pending','running','needs_review','completed','failed','cancelled')),
  input jsonb not null default '{}'::jsonb,
  output jsonb not null default '{}'::jsonb,
  confidence numeric(5,2),
  created_by uuid references public.profiles(id),
  reviewed_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.media_assets (
  id uuid primary key default gen_random_uuid(),
  entity_type text,
  entity_id text,
  city_slug text,
  storage_path text,
  source_url text,
  source_name text,
  credit text,
  media_type text not null default 'licensed_image'
    check (media_type in ('original_photo','press_photo','licensed_image','ai_generated','illustration')),
  rights_status text not null default 'needs_review'
    check (rights_status in ('approved','needs_review','blocked')),
  ai_generated boolean not null default false,
  approved_for_homepage boolean not null default false,
  approved_for_social boolean not null default false,
  created_by uuid references public.profiles(id),
  approved_by uuid references public.profiles(id),
  created_at timestamptz not null default now()
);

alter table public.agent_tasks enable row level security;
alter table public.media_assets enable row level security;

grant select,insert,update on public.agent_tasks to authenticated;
grant select,insert,update on public.media_assets to authenticated;

create policy "cms users read agent tasks" on public.agent_tasks
for select to authenticated using (exists(select 1 from public.profiles where id=auth.uid() and is_active=true));

create policy "cms editors manage agent tasks" on public.agent_tasks
for all to authenticated using (public.can_edit_content()) with check (public.can_edit_content());

create policy "cms users read media assets" on public.media_assets
for select to authenticated using (exists(select 1 from public.profiles where id=auth.uid() and is_active=true));

create policy "cms editors manage media assets" on public.media_assets
for all to authenticated using (public.can_edit_content()) with check (public.can_edit_content());
