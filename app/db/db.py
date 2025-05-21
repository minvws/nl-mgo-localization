from logging import Logger

import inject
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.db.db_session import DbSession
from app.db.models import Base


class Database:
    @inject.autoparams("logger")
    def __init__(self, dsn: str, logger: Logger):
        self.__logger = logger

        try:
            self.engine = create_engine(dsn, echo=False)
        except BaseException as e:
            self.__logger.error("Error while connecting to database: %s", e)
            raise e

    def generate_tables(self) -> None:
        self.__logger.info("Generating tables...")
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        self.__logger.info("Dropping tables...")
        Base.metadata.drop_all(self.engine)

    def is_healthy(self) -> bool:
        """
        Check if the database is healthy

        :return: True if the database is healthy, False otherwise
        """

        self.__logger.info("Checking database health")

        try:
            with Session(self.engine) as session:
                session.execute(text("SELECT 1"))

            self.__logger.info("Database is healthy")
            return True
        except Exception as e:
            self.__logger.info("Database is not healthy: %s", e)
            return False

    def get_db_session(self) -> DbSession:
        return DbSession(self.engine)
