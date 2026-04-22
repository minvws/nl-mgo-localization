import pytest
from fhir.resources.STU3.organization import Organization as FhirOrganization

from app.normalization.fields import (
    AddressNormalizer,
    AliasesNormalizer,
    CareTypeNormalizer,
    FieldNormalizer,
    LowerCaseArrayNormalizer,
    LowercaseNormalizer,
    PostalCodeNormalizer,
    StripNormalizer,
)
from app.normalization.organization_normalizer import OrganizationNormalizer


def test_field_normalizer_not_implemented() -> None:
    class Dummy(FieldNormalizer):
        pass

    with pytest.raises(TypeError):
        Dummy("example_field")  # type: ignore[abstract]


def test_basic_field_normalizers() -> None:
    # StripNormalizer: non-str value should be returned unchanged
    assert StripNormalizer("field_name").normalize(123) == 123
    assert StripNormalizer("field_name").normalize(" abc ") == "abc"

    # LowercaseNormalizer: non-str returns unchanged, str becomes lower
    assert LowercaseNormalizer("field_name").normalize(123) == 123
    assert LowercaseNormalizer("field_name").normalize("AbC") == "abc"

    # LowerCaseArrayNormalizer: non-list returns unchanged, list items lowered when str
    assert LowerCaseArrayNormalizer("field_name").normalize("not-a-list") == "not-a-list"
    assert LowerCaseArrayNormalizer("field_name").normalize(["A", "b", 3]) == ["a", "b", 3]

    # AliasesNormalizer: filters falsy and strips values
    assert AliasesNormalizer().normalize(["  X  ", None, "", "Y"]) == ["X", "Y"]

    # PostalCodeNormalizer: removes internal whitespace
    assert PostalCodeNormalizer().normalize(" 1234 AB ") == "1234AB"

    # AddressNormalizer: empty or wrong type -> None, list -> joined/stripped
    assert AddressNormalizer("field_name").normalize(None) is None  # type: ignore[arg-type]
    assert AddressNormalizer("field_name").normalize([]) is None
    assert AddressNormalizer("field_name").normalize(["  Street ", None, "10"]) == "Street 10"

    # CareTypeNormalizer: removes specific suffix and strips
    assert (
        CareTypeNormalizer("care_type").normalize("Huisartspraktijk (zelfstandig of groepspraktijk)  ")
        == "Huisartspraktijk"
    )


@pytest.mark.usefixtures("test_client")
def test_aliases_remove_dots_in_initials_and_reflect_in_blob() -> None:
    resource = {
        "resourceType": "Organization",
        "id": "X1",
        "name": "Huisarts C.B. Steendijk",
        # Aliases include initials with dots
        "alias": ["J.C. van Andel", "C.B. Steendijk"],
        # Minimal address to keep other fields valid but not needed
        "address": [{"line": ["Street"], "city": "Town", "postalCode": "1000 AA"}],
        # Minimal type to populate care_type
        "type": [{"coding": [{"display": "Huisartsen"}]}],
    }

    fhir_organization = FhirOrganization.model_validate(resource)
    normalized_organization = OrganizationNormalizer().normalize(fhir_organization)

    # Name should be lowercased and still have dots for initials
    assert "c.b. steendijk" in normalized_organization["name"].lower()

    # search_blob enrichment should include aliases without dots, separated by ' | '
    search_blob = normalized_organization["search_blob"]
    assert "jc van andel" in search_blob
    assert "cb steendijk" in search_blob
    assert " | jc van andel" in search_blob  # enrichment separator present
