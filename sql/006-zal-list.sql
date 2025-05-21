CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

create table zal_list
(
    id  uuid primary key default uuid_generate_v4(),
    name varchar(300) not null,
    type varchar(10)  not null
);
alter table zal_list owner to lo_ad_mgo_dba;

create table zal_dataservice
(
    id  uuid primary key default uuid_generate_v4(),
    zal_id            uuid      not null references zal_list on delete cascade,
    interface_version integer      not null,
    service_id        integer      not null,
    auth_endpoint     varchar(300) not null,
    token_endpoint    varchar(300) not null
);
alter table zal_dataservice owner to lo_ad_mgo_dba;

create table zal_identification
(
    id  uuid primary key default uuid_generate_v4(),
    zal_id               uuid     not null references zal_list on delete cascade,
    identification_type  varchar(10) not null,
    identification_value varchar(50) not null
);
alter table zal_identification owner to lo_ad_mgo_dba;

create table zal_active_dataservice
(
    id  uuid primary key default uuid_generate_v4(),
    zal_id          uuid      not null references zal_list on delete cascade,
    data_service_id uuid      not null references zal_dataservice on delete cascade,
    name            varchar(300) not null
);
alter table zal_active_dataservice owner to lo_ad_mgo_dba;

create table zal_dataservice_role
(
    id  uuid primary key default uuid_generate_v4(),
    data_service_id   uuid      not null references zal_dataservice on delete cascade,
    code              varchar(30)  not null,
    resource_endpoint varchar(300) not null
);
alter table zal_dataservice_role owner to lo_ad_mgo_dba;
