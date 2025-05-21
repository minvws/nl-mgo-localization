from typing import Any

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.db.repositories import repository_registry


class DbSession:
    def __init__(self, engine: Engine) -> None:
        self.__session = Session(engine)

    def __getattr__(self, item: str) -> Any:
        return getattr(self.__session, item)

    def get_repository(self, model_class: Any):  # type: ignore[no-untyped-def]
        """
        Returns an instantiated repository for the given model class

        :param model_class:
        :return:
        """
        repo_class = repository_registry.get(model_class)
        if repo_class:
            return repo_class(self.__session)

        raise ValueError(f"No repository registered for model {model_class}")
