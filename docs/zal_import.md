# Importing MedMij Lists

There are two types of MedMij List:

- ZAL ("ZorgAanbiederLijst", meaning healthcare provider list)
- ZKL ("ZorgaanbiederKoppelLijst", meaning healthcare provider relation list)

To import ZALs or ZKLs into the system, first obtain them from MedMij, then use the `organisation:import` cron command.

```shell
    python -m app.cron organisation:import <xml-file>
```

The import script will determine the type of MedMij List based on the XML and process it accordingly.
 Each MedMij List has a reference and timestamp which is used to mark the import,
 in order for the system to be able to retrieve the latest version of the imported data.

## Structure of the MedMij Lists and the correlation between ZAL and ZKL

In short, the ZAL provides actual addresses of the endpoints for a healthcare provider,
 while the ZKL provides the mapping between the healthcare provider and its identifying characteristics
 (like AGB code, URA code, HRN code), so that an contact information addressing system like zorgab can be used to display healthcare provider contact data, while the actual endpoints are retrieved from the ZAL.

```mermaid

classDiagram
direction TB
    class ZorgaanbiederKoppellijst {
    }

    class IdentificerendeKenmerken {
    }

    class ZAKL_Gegevensdiensten {
    }

    class ZAKL_Gegevensdienst {
     Integer GegevensdienstId
     String Weergavenaam
    }

    class ZAKL_Interfaceversies {
    }

    class ZAKL_Interfaceversie {
     Integer InterfaceversieId
    }

    class ZorgaanbiederLijst {
     String Aanbiedertype
    }

    class ZAL_Interfaceversies {
    }

    class ZAL_Interfaceversie {
     Integer InterfaceversieId
    }

    class ZAL_Gegevensdiensten {
    }

    class ZAL_Gegevensdienst {
     Integer GegevensdienstId
    }

    class AuthorizationEndpoint {
     String AuthorizationEndpointuri
    }

    class TokenEndpoint {
     String TokenEndpointuri
    }

    class Systeemrollen {
    }

    class Systeemrol {
     String Systeemrolcode
    }

    class ResourceEndpoint {
     String ResourceEndpointuri
    }

    class IdentificerendKenmerk {
     String AGB, URA, HRN
    }

    class ZorgaanbiederBase {
     Zorgaanbiedernaam = medmij id
    }

 <<abstract>> ZorgaanbiederBase

    ZorgaanbiederBase <|-- ZorgaanbiederKoppellijst
    ZorgaanbiederBase <|-- ZorgaanbiederLijst
    ZorgaanbiederKoppellijst --> IdentificerendeKenmerken : bevat
    IdentificerendeKenmerken --> IdentificerendKenmerk : 1..*
    ZorgaanbiederKoppellijst --> ZAKL_Gegevensdiensten : bevat
    ZAKL_Gegevensdiensten --> ZAKL_Gegevensdienst : 1..*
    ZAKL_Gegevensdienst --> ZAKL_Interfaceversies : bevat
    ZAKL_Interfaceversies --> ZAKL_Interfaceversie : 1..*
    ZorgaanbiederLijst --> ZAL_Interfaceversies : bevat
    ZAL_Interfaceversies --> ZAL_Interfaceversie : 1..*
    ZAL_Interfaceversie --> ZAL_Gegevensdiensten : bevat
    ZAL_Gegevensdiensten --> ZAL_Gegevensdienst : 1..*
    ZAL_Gegevensdienst --> AuthorizationEndpoint : 0..1
    ZAL_Gegevensdienst --> TokenEndpoint : 0..1
    ZAL_Gegevensdienst --> Systeemrollen : bevat
    Systeemrollen --> Systeemrol : 1..*
    Systeemrol --> ResourceEndpoint : bevat
```
