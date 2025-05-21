create role lo_ad_mgo;
create role lo_ad_mgo_dba;
GRANT CONNECT ON DATABASE lo_ad_db to lo_ad_mgo;
GRANT CONNECT ON DATABASE lo_ad_db to lo_ad_mgo_dba;
alter role lo_ad_mgo with login;

create table deploy_releases
(
        version varchar(255),
        deployed_at timestamp default now()
);

alter table deploy_releases owner to lo_ad_mgo_dba;
insert into deploy_releases values('v000-initial.sql', '2024-09-16 14:00:00' );
grant select on deploy_releases to lo_ad_mgo;

