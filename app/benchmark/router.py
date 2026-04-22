from __future__ import annotations

from fastapi import APIRouter, Body
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.utils import resolve_instance

from .zorgab.models import BenchmarkQueryInput, BenchmarkQueryResult
from .zorgab.services import BenchmarkService

router = APIRouter()

BENCHMARK_BODY = Body(
    None,
    description="Benchmark input queries",
    openapi_examples={
        "default": {
            "summary": "Benchmark queries",
            "description": (
                "Each entry contains a query with a target identifier. The type field is optional. "
                "Leave empty to use the default benchmark queries."
            ),
            "value": [
                {"query": "Huisarts de Kaap", "targetId": "agb:01009626"},
                {
                    "query": "Huisarts Janssen Eindhoven",
                    "targetId": "agb:01058073",
                },
            ],
        }
    },
)


@router.post("/benchmark/zorgab", response_class=JSONResponse)
async def benchmark_zorgab(
    body: list[BenchmarkQueryInput] | None = BENCHMARK_BODY,
    benchmark_service: BenchmarkService = resolve_instance(BenchmarkService),
) -> JSONResponse:
    input_data = None if body == [] else body
    benchmark_result = benchmark_service.run(input_data=input_data)

    return JSONResponse(
        content=jsonable_encoder(
            benchmark_result,
            custom_encoder={BenchmarkQueryResult: lambda result: result.as_dict()},
        )
    )
