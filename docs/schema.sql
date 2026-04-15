create table if not exists public.trips (
  id text primary key,
  title text not null,
  destination text,
  start_date date,
  end_date date,
  status text not null default 'planning',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.trip_messages (
  id text primary key,
  trip_id text not null references public.trips(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'tool')),
  content text not null,
  tool_name text,
  tool_call_id text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists trips_updated_at_idx
  on public.trips (updated_at desc);

create index if not exists trip_messages_trip_created_idx
  on public.trip_messages (trip_id, created_at asc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists trips_set_updated_at on public.trips;

create trigger trips_set_updated_at
before update on public.trips
for each row
execute function public.set_updated_at();

alter table public.trips enable row level security;
alter table public.trip_messages enable row level security;

drop policy if exists "service role full access on trips" on public.trips;
drop policy if exists "service role full access on trip_messages" on public.trip_messages;

create policy "service role full access on trips"
on public.trips
for all
to service_role
using (true)
with check (true);

create policy "service role full access on trip_messages"
on public.trip_messages
for all
to service_role
using (true)
with check (true);
