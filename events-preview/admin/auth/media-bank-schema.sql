-- ISNET central media bank
-- Persistent structure for reusable media across cities, artists and productions.

create table if not exists public.cms_media_assets (
  id uuid primary key default gen_random_uuid(),
  media_key text not null unique,
  storage_path text,
  source_url text,
  origin_url text,
  credit text,
  rights_status text not null default 'unknown',
  status text not null default 'needs_review',
  media_type text not null default 'image',
  ai_generated boolean not null default false,
  verified boolean not null default false,
  publishable boolean not null default false,
  width integer,
  height integer,
  bytes integer,
  checksum text,
  strategy text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.cms_media_entities (
  id bigserial primary key,
  media_id uuid not null references public.cms_media_assets(id) on delete cascade,
  entity_type text not null,
  entity_key text not null,
  entity_label text,
  city_slug text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique(media_id,entity_type,entity_key,city_slug)
);

create index if not exists cms_media_entities_lookup_idx
on public.cms_media_entities(entity_type,entity_key,city_slug);

create index if not exists cms_media_assets_status_idx
on public.cms_media_assets(status,publishable,updated_at desc);

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname='cms_media_assets_status_check'
  ) then
    alter table public.cms_media_assets
      add constraint cms_media_assets_status_check
      check (status in ('approved','needs_review','rejected'));
  end if;
end $$;

grant usage on schema public to service_role;
grant select, insert, update, delete on public.cms_media_assets to service_role;
grant select, insert, update, delete on public.cms_media_entities to service_role;

-- Authenticated CMS users may read the bank. Write policies are added when
-- role/site-scope enforcement is connected to the CMS permissions model.
grant select on public.cms_media_assets to authenticated;
grant select on public.cms_media_entities to authenticated;
