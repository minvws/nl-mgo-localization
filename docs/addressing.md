# Addressing

In order to connect to a healthcare provider, you must first search for this provider. This is done via
"localization" and uses the `/localization/origanization/search` endpoint. Ultimately, you will receive a healthcare provider ID.

This ID is usually in the form of `test.huisarts.amsterdam@medmij`.


This endpoint will return a list of data services provided by the DVA of that healthcare provider.


```json

{
    "medmij_id": "test.huisarts.amsterdam@medmij",
    "display_name": "Huisarts Amsterdam",
    "identification": "medmij:huisarts.amsterdam@medmij",
    "types": [
                {
                    "code": "01",
                    "display_name": "Huisartsen",
                    "type": "https://www.vzvz.nl/fhir/NamingSystem/vektis-zorgsoort"
                }
            ],
    "datas_services": [
         {
            "id": "49",
            "name": "Huisartsgegevens",
            "interface_versions": [
                "2"
            ],
            "auth_endpoint": "https://medmij-inlog.vzvz.nl/2.0.0/oauth2/authorize?mgo_signature=MEQCICfOfr3nEN3sJu323060wz6NEbjfGRigfTq03zqmh55rAiBV6Zni-_3VOkinbUy61h4K_d7DU1QvsdobLhnRJNX1tA==",
            "token_endpoint": "https://medmij-inlog.vzvz.nl/2.0.0//oauth2/token?mgo_signature=MEUCIBgk562j1fy9a0sQ_5mKBziZbWIww6YaZI_NXVh8tZmSAiEAzgqteEbUCn5HfqJDtIw7P0gl-_ZbJvlBA8yS-w2drKs=",
            "roles": [
                {
                    "code": "MM-2.0-HGB-FHIR",
                    "resource_endpoint": "https://medmij.vzvz.nl/2.0.0/fhir/?mgo_signature=MEYCIQCyQpat97cHHbRYypWIQcH0PMAEkvmU-HHSDV8njWsWWAIhAOshrqmgvCVHcDTOk46NZVHo-sNRdHS39XPDzU7R4vOS"
                }
            ]
        },
        {
            "id": "50",
            "name": "Basisgegevens GGZ",
            "interface_versions": [
                "2"
            ],
            "auth_endpoint": "https://medmij-inlog.vzvz.nl/2.0.0/oauth2/authorize?mgo_signature=MEUCIQDjsYu4xObTr3_Yr73Gp9usNP3VNantKtILnXDTuP8NlgIgay6DOTSih1BevAxm21wJPI07dwq47_usweLV8pzFG9Y=",
            "token_endpoint": "https://medmij-inlog.vzvz.nl/2.0.0/oauth2/token?mgo_signature=MEUCIFfRuYq5BDzjzvkRuk8v68vVs3BaIxq85GWxNt6t6dziAiEAmykon4iJDIH3fefTUY85fDnWIQMMvkOh_e7fHvgdhYE=",
            "roles": [
                {
                    "code": "MM-2.0-GGB-FHIR",
                    "resource_endpoint": "https://medmij.vzvz.nl/2.0.0/fhir/?mgo_signature=MEYCIQCyH4kR11lZ9XQ89Q_oR6qYZq-VquBIDL56TJIkyrzAcQIhAMntawR4RjKjFeOSQ5yzbhpVUdIxUs6gtUgOTxAcWcsY"
                }
            ]
        },
    ],
}

```

In this case, this healthcare provider offers two services. The first service is called "Huisartsgegevens" and
the second service is called "Basisgegevens GGZ". Each service has a unique ID and a set of roles.

You can use the endpoints in the services to retrieve the data from the healthcare provider.
