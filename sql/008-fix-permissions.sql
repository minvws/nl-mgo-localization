-- Fix permissions on existing tables

ALTER TABLE cities OWNER TO lo_ad_mgo;
ALTER TABLE data_services OWNER TO lo_ad_mgo;
ALTER TABLE endpoints OWNER TO lo_ad_mgo;
ALTER TABLE identifying_features OWNER TO lo_ad_mgo;
ALTER TABLE organisations OWNER TO lo_ad_mgo;
ALTER TABLE system_roles OWNER TO lo_ad_mgo;
