"""FHIR URI constants.

These values are *identifiers* (FHIR `Identifier.system`, extension URLs, etc.).
They are not used to make network requests.

SonarQube may still flag `http://` literals as an insecure protocol; we suppress
that rule on these constants to avoid noisy false-positives.
"""

# FHIR NL naming systems
FHIR_NAMINGSYSTEM_AGB_Z = "http://fhir.nl/fhir/NamingSystem/agb-z"  # NOSONAR
FHIR_NAMINGSYSTEM_URA = "http://fhir.nl/fhir/NamingSystem/ura"  # NOSONAR

# Other identifier systems
MEDMIJ_ID_MEDMIJNAAM = "http://www.medmij.nl/id/medmijnaam"  # NOSONAR
VZVZ_NAMINGSYSTEM_KVK = "http://www.vzvz.nl/fhir/NamingSystem/kvk"  # NOSONAR

# FHIR extension URLs
FHIR_STRUCTUREDEFINITION_GEOLOCATION = "http://hl7.org/fhir/StructureDefinition/geolocation"  # NOSONAR
