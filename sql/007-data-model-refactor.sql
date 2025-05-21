CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Drop obsolete tables
DROP TABLE zal_dataservice_role;
DROP TABLE zal_active_dataservice;
DROP TABLE zal_identification;
DROP TABLE zal_dataservice;
DROP TABLE zal_list;

-- Create new tables
CREATE TABLE endpoints
(
    id        SERIAL PRIMARY KEY,
    url       TEXT NOT NULL,
    signature VARCHAR(100) NULL
);

CREATE TABLE organisations
(
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    type       VARCHAR(4) NOT NULL,
    import_ref VARCHAR(24) NOT NULL
);

CREATE TABLE identifying_features
(
    id              SERIAL PRIMARY KEY,
    organisation_id INTEGER NOT NULL REFERENCES organisations ON DELETE CASCADE,
    type            VARCHAR(4) NOT NULL,
    value           VARCHAR(32) NOT NULL,
    import_ref      VARCHAR(24) NOT NULL
);

CREATE TABLE data_services
(
    id                 SERIAL PRIMARY KEY,
    organisation_id    INTEGER NOT NULL REFERENCES organisations ON DELETE CASCADE,
    external_id        VARCHAR(32) NOT NULL,
    name               VARCHAR(255) NULL,
    interface_versions JSON NULL,
    auth_endpoint_id   INTEGER NOT NULL REFERENCES endpoints ON DELETE SET NULL,
    token_endpoint_id  INTEGER NOT NULL REFERENCES endpoints ON DELETE SET NULL
);

CREATE TABLE system_roles
(
    id                   SERIAL PRIMARY KEY,
    data_service_id      INTEGER NOT NULL REFERENCES data_services ON DELETE CASCADE,
    code                 VARCHAR(32) NOT NULL,
    resource_endpoint_id INTEGER NOT NULL REFERENCES endpoints ON DELETE SET NULL
);

