import urllib.parse
from logging import Logger
from typing import Type, TypeVar

import requests
from fhir.resources.STU3.bundle import Bundle, BundleEntry
from fhir.resources.STU3.organization import Organization as FhirOrganization
from pydantic import BaseModel

from app.healthcarefinder.interface import HealthcareFinderAdapter
from app.healthcarefinder.models import Organization, SearchRequest, SearchResponse
from app.healthcarefinder.zorgab.hydration_service import HydrationService
from app.healthcarefinder.zorgab.patch import TimestampPatcher

T = TypeVar("T", bound=BaseModel)


class BadSearchParams(Exception):
    """
    Raised when the search parameters are not valid.
    """

    pass


class ApiError(Exception):
    """
    Raised when an error occurs while trying to call the external API.
    """

    pass


class ZorgABAdapter(HealthcareFinderAdapter):
    def __init__(
        self,
        base_url: str,
        hydration_service: HydrationService,
        logger: Logger,
        suppress_hydration_errors: bool,
        mtls_cert_file: str | None = None,
        mtls_key_file: str | None = None,
        mtls_chain_file: str | None = None,
        proxy: str | None = None,
    ):
        self.__base_url = base_url.rstrip("/")
        self.__hydration_service = hydration_service
        self.__logger = logger
        self.__session = requests.Session()
        self.__suppress_hydration_errors = suppress_hydration_errors

        if mtls_chain_file:
            self.__session.verify = mtls_chain_file

        if mtls_cert_file and mtls_key_file:
            self.__session.cert = (mtls_cert_file, mtls_key_file)

        self.__session.headers.update({"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"})

        if proxy:
            self.__session.proxies = {"http": proxy, "https": proxy}

    def __make_singular_resource_url(self, base: str, organization_id: str) -> str:
        return f"{base}/fhir/Organization/{organization_id}"

    def __fetch_bundle(self, search: SearchRequest) -> Bundle:
        self.__logger.debug("Searching zorgAB with %s" % search)

        try:
            params = self.create_fhir_search(search)
        except ValueError as e:
            self.__logger.error("Error while trying to create a FHIR search: %s", e)
            raise BadSearchParams("No correct search parameters available") from e

        base = self.__base_url.rstrip("/")
        url = f"{base}/fhir/Organization"
        self.__logger.debug("Calling external URL: '%s?%s'" % (url, params))

        try:
            response = self.__session.get(url, params=params)
            if response.status_code != 200:
                self.__logger.error("Incorrect status code returned from ZorgAB API: '%s'" % url)
                raise ApiError("Unexpected status code returned from the ZorgAB API") from None
        except requests.RequestException as e:
            self.__logger.error("Error while trying to call the external ZorgAB API: %s", e)
            raise ApiError("Error while trying to call the external ZorgAB API") from e

        try:
            return self.__parse_fhir_response(response, Bundle)
        except ValueError as e:
            self.__logger.warning(
                "ZorgAB API returned FHIR non-compliant data. Error: %s",
                e,
            )
            raise

    def search_organizations(self, search: SearchRequest) -> SearchResponse | None:
        bundle = self.__fetch_bundle(search)
        organizations: list[Organization] = []

        if bundle.total and bundle.entry:
            for entry in bundle.entry:
                try:
                    bundle_entry = BundleEntry.model_validate(entry)
                    fhir_organization = FhirOrganization.model_validate(bundle_entry.resource)

                    if fhir_organization.id is None:
                        self.__logger.warning("Skipping organization without ID")
                        continue

                    organizations.append(self.__hydration_service.hydrate_to_organization(fhir_organization))

                except Exception as e:
                    self.__logger.warning(
                        "Error while trying to hydrate an organization (suppress_hydration_errors=%s)",
                        self.__suppress_hydration_errors,
                        exc_info=True,
                    )
                    if not self.__suppress_hydration_errors:
                        raise e

        return SearchResponse(organizations=organizations)

    def search_organizations_raw_fhir(self, search: SearchRequest) -> Bundle | None:
        base = self.__base_url.rstrip("/")
        bundle = self.__fetch_bundle(search)
        raw_entries: list[BundleEntry] = []
        seen_ids: set[str] = set()  # for deduplication, we could use raw_entries but this is more efficient
        part_of_references: set[str] = set()

        if bundle.total and bundle.entry:
            for entry in bundle.entry:
                try:
                    bundle_entry = BundleEntry.model_validate(entry)
                    fhir_organization = FhirOrganization.model_validate(bundle_entry.resource)

                    if fhir_organization.id is None:
                        self.__logger.warning("Skipping organization without ID")
                        continue

                    bundle_entry.fullUrl = self.__make_singular_resource_url(base, fhir_organization.id)

                    # this deduplication works on a single search basis and prevents duplicates related to partOf
                    if fhir_organization.id not in seen_ids:
                        seen_ids.add(fhir_organization.id)
                        raw_entries.append(bundle_entry)

                    if fhir_organization.partOf and fhir_organization.partOf.reference:
                        part_of_references.add(fhir_organization.partOf.reference)

                except Exception:
                    self.__logger.warning(
                        "Error while parsing organization entry (suppress_hydration_errors=%s)",
                        self.__suppress_hydration_errors,
                        exc_info=True,
                    )
                    if not self.__suppress_hydration_errors:
                        raise

        if part_of_references:
            for entry in self.__fetch_partof_organizations(base=base, references=part_of_references):
                try:
                    fhir_organization = FhirOrganization.model_validate(entry.resource)
                except Exception:
                    continue
                if not fhir_organization.id or fhir_organization.id in seen_ids:
                    continue
                seen_ids.add(fhir_organization.id)
                raw_entries.append(entry)

        if not raw_entries:
            return None

        bundle.entry = raw_entries
        bundle.total = len(raw_entries)
        return bundle

    def verify_connection(self) -> bool:
        test_url = f"{self.__base_url}/fhir/Organization?name=huisarts&address-city=Amsterdam"
        self.__logger.info("Verifying connection to ZorgAB API at %s", test_url)

        try:
            response = self.__session.get(test_url)
            if response.status_code == 200:
                self.__logger.info("Connection to ZorgAB API successful")
                return True
            else:
                self.__logger.error("Failed to verify connection: Status code %d", response.status_code)
                return False
        except requests.RequestException as e:
            self.__logger.error("Error verifying connection to ZorgAB API: %s", e)
            return False

    def __fetch_partof_organizations(self, base: str, references: set[str]) -> list[BundleEntry]:
        part_of_organizations: list[BundleEntry] = []

        for reference in references:
            if not reference.startswith("Organization/"):
                self.__logger.info("Skipping unsupported partOf reference '%s'", reference)
                continue

            url = f"{base}/fhir/{reference}"
            try:
                self.__logger.debug("Fetching partOf organization at '%s'", url)
                response = self.__session.get(url)
                if response.status_code != 200:
                    self.__logger.warning(
                        "Failed to fetch partOf organization %s: status %s", reference, response.status_code
                    )
                    continue

                fhir_organization = self.__parse_fhir_response(response, FhirOrganization)

                if not fhir_organization.id:
                    continue

                trimmed_organization = FhirOrganization.model_validate(
                    {
                        "id": fhir_organization.id,
                        "name": fhir_organization.name,
                        "identifier": fhir_organization.identifier,
                        "address": fhir_organization.address,
                    }
                )
                full_url = self.__make_singular_resource_url(base, fhir_organization.id)
                part_of_organizations.append(BundleEntry(fullUrl=full_url, resource=trimmed_organization))
            except requests.RequestException as e:
                self.__logger.warning("Error while fetching partOf organization %s: %s", reference, e)
            except Exception:
                self.__logger.warning("Error while parsing partOf organization %s", reference, exc_info=True)

        return part_of_organizations

    @staticmethod
    def create_fhir_search(search: SearchRequest) -> str:
        if search.medmij_name and search.medmij_name.strip() != "":
            identifier = f"http://www.medmij.nl/id/medmijnaam|{search.medmij_name}"
            return urllib.parse.urlencode({"identifier": identifier})

        if search.text and search.text.strip() != "":
            return urllib.parse.urlencode({"_text": search.text})

        if search.name and search.name.strip() != "" and search.city and search.city.strip() != "":
            name = search.name.replace("'", "''")
            city = search.city.replace("'", "''")
            return urllib.parse.urlencode({"name": name, "address-city": city})

        if search.type and search.type.strip() != "":
            return urllib.parse.urlencode({"type": search.type, "_summary": "true"})

        if search.ura and search.ura.strip() != "":
            identifier = f"http://fhir.nl/fhir/NamingSystem/ura|{search.ura}"
            return urllib.parse.urlencode({"identifier": identifier})

        if search.agb and search.agb.strip() != "":
            identifier = f"http://fhir.nl/fhir/NamingSystem/agb-z|{search.agb}"
            return urllib.parse.urlencode({"identifier": identifier})

        if search.kvk and search.kvk.strip() != "":
            identifier = f"http://www.vzvz.nl/fhir/NamingSystem/kvk|{search.kvk}"
            return urllib.parse.urlencode({"identifier": identifier})

        # Otherwise, raise nothing to search
        raise ValueError("No correct search parameters available")

    def __parse_fhir_response(
        self,
        zorgab_response: requests.Response,
        fhir_model: Type[T],
    ) -> T:
        data = zorgab_response.json()

        TimestampPatcher.patch(data)

        return fhir_model.model_validate(data)
