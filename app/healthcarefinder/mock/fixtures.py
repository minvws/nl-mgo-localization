from enum import Enum
from typing import List


class HealthOrganizationFixtures:
    ORGANIZATION_WITH_INTEROPLAB_DATASERVICE = {
        "display_name": "Interoplab hospital",
        "identification_type": "agb-z",
        "identification_value": "080000",
        "addresses": [
            {
                "active": True,
                "address": "Straatnaam 123A\n1000AB STAD",
                "city": "STAD",
                "country": "LAND",
                "geolocation": {"latitude": 53.21864104881037, "longitude": 6.567660572054596},
                "postalcode": "1000AB",
                "state": None,
                "type": "physical",
            },
            {
                "active": True,
                "address": "Straatnaam 123A\n1000AB STAD",
                "city": "STAD",
                "country": "LAND",
                "geolocation": {"latitude": 53.21864104881037, "longitude": 6.567660572054596},
                "postalcode": "1000AB",
                "state": None,
                "type": "postal",
            },
        ],
        "names": [
            {"full_name": "Interoplab hospital", "preferred": True},
            {"full_name": "Interoplab ziekenhuis", "preferred": False},
            {"full_name": "Interoplab kliniek", "preferred": False},
        ],
        "types": [
            {
                "code": "hospital",
                "display_name": "Ziekenhuis",
                "type": "organization",
            }
        ],
        "data_services": [
            # Empty as this list is filled dynamically
        ],
    }

    ORGANIZATION_WITH_DATASERVICES = {
        "display_name": "Mocky hospital",
        "identification_type": "agb-z",
        "identification_value": "0800001",
        "addresses": [
            {
                "active": True,
                "address": "Straatnaam 123A\n1000AB STAD",
                "city": "STAD",
                "country": "LAND",
                "geolocation": {"latitude": 53.21864104881037, "longitude": 6.567660572054596},
                "postalcode": "1000AB",
                "state": None,
                "type": "physical",
            },
            {
                "active": True,
                "address": "Straatnaam 123A\n1000AB STAD",
                "city": "STAD",
                "country": "LAND",
                "geolocation": {"latitude": 53.21864104881037, "longitude": 6.567660572054596},
                "postalcode": "1000AB",
                "state": None,
                "type": "postal",
            },
        ],
        "names": [
            {"full_name": "Mocky hospital", "preferred": True},
            {"full_name": "Mocky ziekenhuis", "preferred": False},
            {"full_name": "Mocky kliniek", "preferred": False},
        ],
        "types": [
            {
                "code": "hospital",
                "display_name": "Ziekenhuis",
                "type": "organization",
            }
        ],
        "data_services": [
            {
                "id": "48",
                "name": "Basisgegevens Zorg",
                "interface_versions": ["2"],
                "auth_endpoint": "{{MOCK_URL}}auth",
                "token_endpoint": "{{MOCK_URL}}token",
                "roles": [
                    {
                        "code": "MM-3.0-BZB-FHIR",
                        "resource_endpoint": "{{MOCK_URL}}48",
                    }
                ],
            },
            {
                "id": "49",
                "name": "Huisartsgegevens",
                "interface_versions": ["2"],
                "auth_endpoint": "{{MOCK_URL}}auth",
                "token_endpoint": "{{MOCK_URL}}token",
                "roles": [
                    {
                        "code": "MM-3.0-HGB-FHIR",
                        "resource_endpoint": "{{MOCK_URL}}49",
                    }
                ],
            },
            {
                "id": "51",
                "name": "Documenten",
                "interface_versions": ["2"],
                "auth_endpoint": "{{MOCK_URL}}auth",
                "token_endpoint": "{{MOCK_URL}}token",
                "roles": [
                    {
                        "code": "MM-3.0-PLB-FHIR",
                        "resource_endpoint": "{{MOCK_URL}}51",
                    },
                    {
                        "code": "MM-3.0-PDB-FHIR",
                        "resource_endpoint": "{{MOCK_URL}}51",
                    },
                ],
            },
        ],
    }

    ORGANIZATION_WITHOUT_DATASERVICES = {
        "display_name": "Huisartsenpraktijk de Vries",
        "identification_type": "agb-z",
        "identification_value": "0800002",
        "addresses": [
            {
                "active": True,
                "address": "Poststraat 10\r\n1020BD AMSTERDAM",
                "city": "Amsterdam",
                "country": "Nederland",
                "geolocation": {"latitude": 53.21864104881037, "longitude": 6.567660572054596},
                "postalcode": "1020AB",
                "state": None,
                "type": "physical",
            }
        ],
        "names": [{"full_name": "Huisartsenpraktijk de Vries", "preferred": True}],
        "types": [
            {
                "code": "01",
                "display_name": "Huisartsen",
                "type": "https://www.vzvz.nl/fhir/NamingSystem/vektis-zorgsoort",
            }
        ],
        "data_services": [],
    }

    ORGANIZATION_WITH_UNSUPPORTED_DATASERVICE = {
        "display_name": "Verloskundigen praktijk Rotterdam Oost",
        "identification_type": "agb-z",
        "identification_value": "0800003",
        "addresses": [
            {
                "active": True,
                "address": "Kerstant van den Bergeln 3\r\n3125HC ROTTERDAM",
                "city": "Rotterdam",
                "country": "Nederland",
                "geolocation": {"latitude": 53.21864104881037, "longitude": 6.567660572054596},
                "postalcode": "3125HC",
                "state": None,
                "type": "physical",
            }
        ],
        "names": [
            {
                "full_name": "Verloskundigen praktijk Rotterdam Oost",
                "preferred": True,
            }
        ],
        "types": [
            {
                "code": "08",
                "display_name": "Verloskundigen",
                "type": "https://www.vzvz.nl/fhir/NamingSystem/vektis-zorgsoort",
            }
        ],
        "data_services": [
            {
                "id": "65",
                "name": "Niet ondersteunde gegevensdienst: Zwangerschapskaart",
                "interface_versions": ["2"],
                "auth_endpoint": "{{MOCK_URL}}auth",
                "token_endpoint": "{{MOCK_URL}}token",
                "roles": [
                    {
                        "code": "GZ-1.0-IZR-FHIR",
                        "resource_endpoint": "{{MOCK_URL}}65",
                    },
                ],
            }
        ],
    }

    QUALIFICATION_ORGANIZATION_BASE = {
        "display_name": "Qualification",
        "identification_type": "agb-z",
        "identification_value": "0800123",
        "addresses": [
            {
                "active": True,
                "address": "Kwalificatiestraat 123",
                "city": "Rotterdam",
                "country": "Nederland",
                "geolocation": {"latitude": 53.21864104881037, "longitude": 6.567660572054596},
                "postalcode": "3125HC",
                "state": None,
                "type": "physical",
            }
        ],
        "names": [
            {
                "full_name": "Qualification",
                "preferred": True,
            }
        ],
        "types": [
            {
                "code": "08",
                "display_name": "Verloskundigen",
                "type": "https://www.vzvz.nl/fhir/NamingSystem/vektis-zorgsoort",
            }
        ],
        "data_services": [],
    }


class QualificationDataServiceFixtures(Enum):
    """Basic enumerable for data service qualification fixtures"""

    BGZ = {
        "id": "48",
        "name": "Basisgegevens Zorg",
        "interface_versions": [
            "1.2.0",
            "1.3.0",
            "1.4.0",
            "1.5.0",
            "1.6.0",
            "2.",
        ],
        "auth_endpoint": "{{MOCK_URL}}auth",
        "token_endpoint": "{{MOCK_URL}}token",
        "roles": [
            {
                "code": "MM-3.0-BZB-FHIR",
                "resource_endpoint": "{{MOCK_URL}}48",
            }
        ],
    }

    GPDATA = {
        "id": "49",
        "name": "Huisartsgegevens",
        "interface_versions": [
            "1.2.0",
            "1.3.0",
            "1.4.0",
            "1.5.0",
            "1.6.0",
            "2.",
        ],
        "auth_endpoint": "{{MOCK_URL}}auth",
        "token_endpoint": "{{MOCK_URL}}token",
        "roles": [
            {
                "code": "MM-2.0-HGB-FHIR",
                "resource_endpoint": "{{MOCK_URL}}49",
            }
        ],
    }

    PDFA = {
        "id": "51",
        "name": "Documenten",
        "interface_versions": [
            "1.2.0",
            "1.3.0",
            "1.4.0",
            "1.5.0",
            "1.6.0",
            "2.",
        ],
        "auth_endpoint": "{{MOCK_URL}}auth",
        "token_endpoint": "{{MOCK_URL}}token",
        "roles": [
            {
                "code": "MM-3.0-PLB-FHIR",
                "resource_endpoint": "{{MOCK_URL}}51",
            },
            {
                "code": "MM-3.0-PDB-FHIR",
                "resource_endpoint": "{{MOCK_URL}}51",
            },
        ],
    }

    VACCINATION_IMMUNIZATION = {
        "id": "63",
        "name": "Vaccinaties",
        "interface_versions": ["1.5.0", "1.6.0", "2."],
        "auth_endpoint": "{{MOCK_URL}}auth",
        "token_endpoint": "{{MOCK_URL}}token",
        "roles": [
            {
                "code": "MM-1.0-VAB-FHIR",
                "resource_endpoint": "{{MOCK_URL}}63",
            }
        ],
    }


"""
Interoplab dataservice which can just be accessed directly
"""
INTEROPLAB_DATASERVICES: List[dict[str, str]] = list(
    [
        {
            "id": "47",
            "name": "Afspraken",
            "code": "EA-2.0-AFB-FHIR",
        },
        {
            "id": "48",
            "name": "Basisgegevens zorg",
            "code": "MM-3.0-BZB-FHIR",
        },
        {
            "id": "49",
            "name": "Huisartsgegevens",
            "code": "MM-2.0-HGB-FHIR",
        },
        {
            "id": "50",
            "name": "Basisgegevens GGZ",
            "code": "MM-2.0-GGB-FHIR",
        },
        {
            "id": "51",
            "name": "Documenten",
            "code": "MM-3.0-PDB-FHIR",
        },
        {
            "id": "52",
            "name": "Meetwaarden vitale functies",
            "code": "MM-2.0-MVB-FHIR",
        },
        {
            "id": "58",
            "name": "Medicatiegerelateerde overgevoeligheden",
            "code": "MM-2.A-AIB-FHIR",
        },
        {
            "id": "61",
            "name": "Basisgegevens langdurige zorg",
            "code": "MM-3.0-LZB-FHIR",
        },
        {
            "id": "63",
            "name": "Vaccinaties",
            "code": "MM-1.0-VAB-FHIR",
        },
        {
            "id": "65",
            "name": "Integrale zwangerschapskaart",
            "code": "GZ-1.0-IZB-FHIR",
        },
    ],
)
