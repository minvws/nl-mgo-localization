from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Protocol

import inject
from fastapi.encoders import jsonable_encoder

from app.benchmark.zorgab.models import (
    BenchmarkOutput,
    BenchmarkQuery,
    BenchmarkQueryInput,
    BenchmarkQueryResult,
)
from app.benchmark.zorgab.utils import normalize_agb_target_id
from app.config.models import Config
from app.healthcarefinder.models import Organization


class BenchmarkQueryLoader(Protocol):
    def load(self, input_data: list[BenchmarkQueryInput] | None) -> list[BenchmarkQuery]: ...


class FileLoader:
    def load(self, path: str) -> list[BenchmarkQueryInput]:
        with open(path, encoding="utf-8") as filepointer:
            raw_data = json.load(filepointer)
        return [BenchmarkQueryInput.model_validate(entry) for entry in raw_data]


@inject.autoparams("file_loader", "config")
class DefaultBenchmarkQueryLoader:
    def __init__(self, file_loader: FileLoader, config: Config) -> None:
        self.file_loader = file_loader
        self._config = config

    def load(self, input_data: list[BenchmarkQueryInput] | None) -> list[BenchmarkQuery]:
        raw_input_data = input_data or self.__load_default_input()
        queries: list[BenchmarkQuery] = []
        for entry in raw_input_data:
            if isinstance(entry, dict):
                entry = BenchmarkQueryInput.model_validate(entry)
            queries.append(
                BenchmarkQuery(
                    query=entry.query,
                    target_id=entry.targetId.strip(),
                )
            )
        return queries

    def __load_default_input(self) -> list[BenchmarkQueryInput]:
        return self.file_loader.load(self._config.benchmark.zorgab_query_input_path)


class ReciprocalRankScorer:
    def score(self, organizations: list[Organization], target_id: str) -> tuple[float, str]:
        rank: int | None = None
        for organization_index, organization in enumerate(organizations):
            if normalize_agb_target_id(organization.identification) == target_id:
                rank = organization_index + 1
                break

        if rank is None:
            return 0.0, "NOT FOUND"

        return 1.0 / rank, f"{rank}/{len(organizations)}"


class BenchmarkOutputWriter(Protocol):
    def write(self, output: BenchmarkOutput) -> None: ...


class JsonFileOutputWriter(BenchmarkOutputWriter):
    @inject.autoparams("config")
    def __init__(
        self,
        config: Config,
    ):
        self._config = config

    def write(self, output: BenchmarkOutput) -> None:
        output_dir = Path(self._config.benchmark.zorgab_output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now().strftime("%Y%m%d-%H%M")
        output_path = output_dir / f"results-zorgab-{now}.json"
        with open(output_path, "w", encoding="utf-8") as file_stream:
            json.dump(
                jsonable_encoder(
                    output,
                    custom_encoder={BenchmarkQueryResult: lambda result: result.as_dict()},
                ),
                file_stream,
                indent=2,
            )
