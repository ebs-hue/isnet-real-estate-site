-- ISNET CMS - central event records
create table if not exists public.cms_event_records (
  city_slug text not null,
  event_id text not null,
  record_type text not null default 'override'
    check (record_type in ('override','manual')),
  payload jsonb not null default '{}'::jsonb,
  status text,
  updated_by uuid references public.profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (city_slug,event_id)
);

alter table public.cms_event_records enable row level security;

grant select, insert, update, delete
on public.cms_event_records
to authenticated;

create or replace function public.can_edit_content()
returns boolean
language sql
stable
security definer
set search_path=public
as $$
  select exists (
    select 1
    from public.profiles
    where id=auth.uid()
      and is_active=true
      and role in ('super_admin','admin','site_admin','editor','writer','agent')
  );
$$;

grant execute on function public.can_edit_content() to authenticated;

drop policy if exists "authenticated read cms events" on public.cms_event_records;
create policy "authenticated read cms events"
on public.cms_event_records
for select
to authenticated
using (
  exists (
    select 1 from public.profiles
    where id=auth.uid() and is_active=true
  )
);

drop policy if exists "editors create cms events" on public.cms_event_records;
create policy "editors create cms events"
on public.cms_event_records
for insert
to authenticated
with check (
  public.can_edit_content()
  and updated_by=auth.uid()
);

drop policy if exists "editors update cms events" on public.cms_event_records;
create policy "editors update cms events"
on public.cms_event_records
for update
to authenticated
using (public.can_edit_content())
with check (
  public.can_edit_content()
  and updated_by=auth.uid()
);

drop policy if exists "editors delete cms events" on public.cms_event_records;
create policy "editors delete cms events"
on public.cms_event_records
for delete
to authenticated
using (public.can_edit_content());

create index if not exists cms_event_records_status_idx
on public.cms_event_records(status);

create index if not exists cms_event_records_updated_at_idx
on public.cms_event_records(updated_at desc);
