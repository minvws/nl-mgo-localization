import urllib.parse
from logging import Logger

import requests
from fhir.resources.STU3.bundle import Bundle, BundleEntry
from fhir.resources.STU3.organization import Organization as FhirOrganization
from pydantic import ValidationError

from app.healthcarefinder.models import SearchRequest, SearchResponse
from app.healthcarefinder.zorgab.hydration_service import HydrationService


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


class ZorgABAdapter:
    def __init__(
        self,
        base_url: str,
        hydration_service: HydrationService,
        logger: Logger,
        mtls_cert_file: str | None = None,
        mtls_key_file: str | None = None,
        mtls_chain_file: str | None = None,
        proxy: str | None = None,
    ):
        if not base_url.startswith(("http", "https")) and not base_url.endswith("/"):
            raise ValueError("base_url should start with http or https and end with a slash")

        self.__base_url = base_url
        self.__hydration_service = hydration_service
        self.__logger = logger
        self.__session = requests.Session()

        if mtls_chain_file:
            self.__session.verify = mtls_chain_file

        if mtls_cert_file and mtls_key_file:
            self.__session.cert = (mtls_cert_file, mtls_key_file)

        self.__session.headers.update({"Accept": "application/fhir+json", "Content-Type": "application/fhir+json"})

        if proxy:
            self.__session.proxies = {"http": proxy, "https": proxy}

    def search_organizations(self, search: SearchRequest) -> SearchResponse | None:
        """
        Search for organizations in ZorgAB

        :param search: SearchRequest object containing search parameters
        :return: A SearchResponse object if organizations are found, None otherwise
        :raises: ValidationError if the response from ZorgAB is not a valid FHIR bundle
        """
        self.__logger.info("Searching zorgAB with %s" % search)

        try:
            params = self.create_fhir_search(search)
        except ValueError as e:
            self.__logger.error("Error while trying to create a FHIR search: %s", e)
            raise BadSearchParams("No correct search parameters available") from e
        url = "%s/fhir/Organization" % (self.__base_url)

        self.__logger.info("Calling external URL: '%s?%s'" % (url, params))

        try:
            response = self.__session.get(url, params=params)
            if response.status_code != 200:
                self.__logger.error("Incorrect status code returned from ZorgAB API: '%s'" % url)
                raise ApiError("Unexpected status code returned from the ZorgAB API") from None
        except requests.RequestException as e:
            self.__logger.error("Error while trying to call the external ZorgAB API: %s", e)
            raise ApiError("Error while trying to call the external ZorgAB API") from e

        orgs = []
        bundle = Bundle.model_validate(response.json())
        if bundle.total > 0:
            for entry in bundle.entry:
                try:
                    bundle_entry = BundleEntry.model_validate(entry)
                    fhir_org = FhirOrganization.model_validate(bundle_entry.resource)
                    orgs.append(self.__hydration_service.hydrate_to_organization(fhir_org))
                except ValidationError as e:
                    self.__logger.warning("Error while trying to hydrate an organization: %s", e)
                    continue

        return SearchResponse(organizations=orgs)

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

    @staticmethod
    def create_fhir_search(search: SearchRequest) -> str:
        # name/city combination is preferred
        if search.name and search.name.strip() != "" and search.city and search.city.strip() != "":
            name = search.name.replace("'", "''")
            city = search.city.replace("'", "''")
            return urllib.parse.urlencode({"name": name, "address-city": city})

        # Otherwise, raise nothing to search
        raise ValueError("No correct search parameters available")
