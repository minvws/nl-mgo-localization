import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class AtomicFileWriter:
    """
    Provides an atomic file writing mechanism to ensure data integrity during file operations.

    This class writes data to a temporary file in the specified directory, flushes and fsyncs the data,
    and then atomically moves the temporary file to the target output path. This strategy prevents partial
    writes and ensures that the output file is either fully written or not modified at all, even in the
    event of a failure or interruption.
    """

    def write(
        self,
        data: bytes,
        output_path: Path,
        temp_path: Path,
        prefix: str = "tmp_",
    ) -> None:
        logger.debug("Writing file to %s", output_path)

        os.makedirs(temp_path, exist_ok=True)

        target_dir = os.path.dirname(output_path) or "."
        os.makedirs(target_dir, exist_ok=True)

        tmp_path: str | None = None

        try:
            with tempfile.NamedTemporaryFile(
                "wb",
                dir=temp_path,
                prefix=prefix,
                delete=False,
            ) as tmp:
                tmp_path = tmp.name
                logger.debug("Temporary file created at %s", tmp_path)

                tmp.write(data)
                tmp.flush()
                os.fsync(tmp.fileno())

                logger.debug("Temporary file %s flushed and fsynced", tmp_path)

            os.replace(tmp_path, output_path)
            logger.debug("File written successfully to %s", output_path)

        except Exception:
            logger.exception("Failed to write file to %s", output_path)
            raise

        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                    logger.debug("Cleaned up temporary file %s", tmp_path)
                except OSError:
                    logger.warning("Failed to cleanup temporary file %s", tmp_path, exc_info=True)
