drop table if exists requests;
drop table if exists request_statuses;
create table requests (
  id text primary key,
  status text check(status in ('W','S','E','SP','DP','C','P','FC','A')) not null,
  status_description text,
  src_url text not null,
  request_checksum text,
  request_checksum_type text,
  pid text
);
