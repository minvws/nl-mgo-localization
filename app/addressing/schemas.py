from urllib.parse import urlsplit

from .constants import SIGNATURE_PARAM_NAME


class EndpointSignatureRenewResultDTO:
    def __init__(self) -> None:
        self.__added: int = 0
        self.__updated: int = 0
        self.__skipped: int = 0

    @property
    def added(self) -> int:
        return self.__added

    @property
    def updated(self) -> int:
        return self.__updated

    @property
    def skipped(self) -> int:
        return self.__skipped

    def increment_added(self) -> None:
        self.__added += 1

    def increment_updated(self) -> None:
        self.__updated += 1

    def increment_skipped(self) -> None:
        self.__skipped += 1


class SignedUrl:
    def __init__(self, signed_url: str) -> None:
        self.__signed_url = signed_url

    @staticmethod
    def create(url: str, signature: str) -> "SignedUrl":
        split_result = urlsplit(url)
        query_params = [
            query_param
            for query_param in split_result.query.split("&")
            if query_param != "" and not query_param.startswith(SIGNATURE_PARAM_NAME)
        ]
        query_params.append(f"{SIGNATURE_PARAM_NAME}={signature}")

        return SignedUrl(
            "%s://%s%s?%s"
            % (
                split_result.scheme,
                split_result.netloc,
                split_result.path,
                "&".join(query_params) if len(query_params) > 1 else query_params[0],
            )
        )

    def __str__(self) -> str:
        return self.__signed_url
