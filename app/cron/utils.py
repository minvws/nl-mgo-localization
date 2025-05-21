import sys


def print_progress_bar(progress: int, total: int) -> None:
    if total == 0:
        total = 1
        progress = 1

    bar_length = 40
    block = int(round(bar_length * progress / total))
    text = f"\rProgress: [{'#' * block + '-' * (bar_length - block)}] {progress}/{total}"
    sys.stdout.write(text)
    sys.stdout.flush()
