-- ISNET CMS - publishing migration
alter table public.cms_event_records
  add column if not exists seo_slug text,
  add column if not exists publication_status text not null default 'draft',
  add column if not exists published_at timestamptz,
  add column if not exists public_path text;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname='cms_event_records_publication_status_check'
  ) then
    alter table public.cms_event_records
      add constraint cms_event_records_publication_status_check
      check (publication_status in ('draft','published','unpublished'));
  end if;
end $$;

create unique index if not exists cms_event_records_city_slug_published_idx
on public.cms_event_records(city_slug,seo_slug)
where seo_slug is not null and publication_status='published';

grant select on public.cms_event_records to anon;

drop policy if exists "public read published cms events" on public.cms_event_records;
create policy "public read published cms events"
on public.cms_event_records
for select
to anon
using (publication_status='published');

create index if not exists cms_event_records_publication_idx
on public.cms_event_records(city_slug,publication_status,published_at desc);
