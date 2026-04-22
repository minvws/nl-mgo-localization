import argparse
import json
import logging
import os
from collections.abc import Sequence
from datetime import datetime

import inject
from fhir.resources.STU3.bundle import Bundle

from app.config.models import Config
from app.cron.utils import SubParsers
from app.normalization.bundle import BundleNormalizer
from app.normalization.services import GzipCompressionSizeChecker

logger = logging.getLogger(__name__)


class NormalizationCommand:
    """
    Normalize FHIR organization bundle to Orama-ready JSON.
    """

    NAME: str = "normalize-providers"

    @inject.autoparams()
    def __init__(
        self,
        gzip_checker: GzipCompressionSizeChecker,
    ) -> None:
        self.__gzip_checker = gzip_checker

    @staticmethod
    def _format_size_kb(size_kb: float) -> str:
        if size_kb > 1024:
            size_mb = size_kb / 1024
            return f"{size_mb:.2f} MB."

        return f"{size_kb:.0f} kB."

    @staticmethod
    def init_arguments(subparser: SubParsers) -> None:
        parser = subparser.add_parser(NormalizationCommand.NAME, help="Normalize FHIR bundle to JSON")
        parser.add_argument("input_file", type=str, help="Path to FHIR resource bundle (JSON)")
        parser.add_argument("--output-folder", type=str, default=None, help="Output folder for normalized JSON")
        parser.add_argument("--output-file", type=str, default=None, help="Output file name (overrides default)")

    def _create_output_file_name_from_input_path(self, input_path: str) -> str:
        input_base = os.path.basename(input_path)
        input_name, _ = os.path.splitext(input_base)
        date_str = datetime.now().strftime("%Y%m%d-%H%M")

        return f"normalized-{input_name}-{date_str}.json"

    def _resolve_output_path(self, output_folder: str, output_file: str) -> str:
        return os.path.join(output_folder, output_file) if not os.path.isabs(output_file) else output_file

    def _output_directory_exists(self, path: str) -> None:
        if not os.path.isdir(path):
            raise FileNotFoundError(f"Output folder '{path}' does not exist")

    def _read_json(self, path: str) -> object:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: str, data: object) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _write_output_and_log(self, output_path: str, normalized: Sequence[object]) -> None:
        logger.info(f"Writing normalized data to {output_path}")
        self._write_json(output_path, normalized)

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        gzip_size_kb = self.__gzip_checker.get_size_in_kb(output_path)

        suffix_parts: list[str] = []

        if gzip_size_kb is not None:
            suffix_parts.append(f"gzip: {self._format_size_kb(gzip_size_kb)}")

        suffix = ", " + ", ".join(suffix_parts) if suffix_parts else "."
        logger.info(f"Done. {len(normalized)} records written. Output file size: {file_size_mb:.2f} MB{suffix}")

    @inject.autoparams("bundle_normalizer", "config")
    def run(self, args: argparse.Namespace, bundle_normalizer: BundleNormalizer, config: Config) -> int:
        input_path: str = args.input_file

        output_folder: str = args.output_folder or config.normalization.normalization_output_folder
        output_file: str = args.output_file or self._create_output_file_name_from_input_path(input_path)
        output_path: str = self._resolve_output_path(output_folder, output_file)

        self._output_directory_exists(output_folder)

        logger.info(f"Reading FHIR bundle from {input_path}")
        bundle = Bundle.model_validate(self._read_json(input_path))

        logger.info("Normalizing bundle...")

        def progress_callback(processed: int, total: int) -> None:
            if total > 0 and processed % max(1, total // 100) == 0:
                percent = (processed / total) * 100
                logger.info(f"Progress: {processed}/{total} ({percent:.1f}%)")

        normalized = bundle_normalizer.normalize(bundle, progress_callback=progress_callback)
        self._write_output_and_log(output_path, normalized)
        return 0
