import inject
from faker import Faker
from fastapi.testclient import TestClient

from app.version.models import VersionInfo


def test_root_endpoint_prints_version_info(test_client: TestClient, faker: Faker) -> None:
    version = faker.numerify("v#.#.#")
    git_ref = faker.hexify("^^^^^^")

    def config_callable(binder: inject.Binder) -> None:
        binder.bind(VersionInfo, VersionInfo(version=version, git_ref=git_ref))

    inject.configure(clear=True, config=config_callable)

    response = test_client.get("/")

    assert response.status_code == 200
    assert f"Release version: {version}\nGit ref: {git_ref}" in response.text
