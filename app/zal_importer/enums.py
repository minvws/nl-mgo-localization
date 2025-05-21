from enum import Enum


class ImportType(str, Enum):
    LIST = "Zorgaanbiederslijst"
    JOIN_LIST = "Zorgaanbiederskoppellijst"


class IdentifyingFeatureType(str, Enum):
    AGB = "AGB"
    URA = "URA"
    OIN = "OIN"
    HRN = "HRN"
    KVK = "KVK"


class OrganisationType(str, Enum):
    ZA = "ZA"
    BAZB = "BAZB"
