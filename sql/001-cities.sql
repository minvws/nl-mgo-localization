-- Description: Create cities table

CREATE TABLE cities (
      id SERIAL NOT NULL,
      name VARCHAR(100) NOT NULL,
      PRIMARY KEY (id)
);

alter table cities owner to lo_ad_mgo;
