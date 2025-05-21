import argparse
import logging
from logging import Logger
from typing import Any, Protocol, Type

import inject

from app.bindings import configure_bindings
from app.config.factories import get_config
from app.cron.commands import CleanupExpiredImportedOrganisationsCommand, EndpointSignatureRenewCommand
from app.cron.zal_importer import OrganisationImportCommand


class CronCommand(Protocol):
    @staticmethod
    def init_arguments(subparser: Any) -> None: ...

    def run(self, args: argparse.Namespace) -> int: ...


CRON_COMMANDS: dict[str, Type[CronCommand]] = {
    OrganisationImportCommand.NAME: OrganisationImportCommand,
    EndpointSignatureRenewCommand.NAME: EndpointSignatureRenewCommand,
    CleanupExpiredImportedOrganisationsCommand.NAME: CleanupExpiredImportedOrganisationsCommand,
}


def show_help() -> None:
    print("""
Usage: python -m app.cron <command> [args]

Commands:
    help
        Show this help message or help for a specific command
""")
    for command_name in CRON_COMMANDS:
        doc = CRON_COMMANDS[command_name].__doc__ or "No description available."
        print(f"    {command_name}")
        print(f"        {doc.strip()}\n")


def run_command() -> None:
    if not inject.is_configured():
        config = get_config(config_file="app.conf")

        inject.configure(
            lambda binder: configure_bindings(
                binder=binder,
                config=config,
            ),
        )

    logger: Logger = inject.instance(logging.Logger)

    parser = argparse.ArgumentParser(description="Cron command line interface")
    subparser: argparse._SubParsersAction[argparse.ArgumentParser] = parser.add_subparsers(
        dest="command", title="cron commands", help="valid cron commands"
    )

    # Add help command
    subparser.add_parser("help", help="Show this help message or help for a specific command")

    for command_class in CRON_COMMANDS.values():
        command_class.init_arguments(subparser)

    args = parser.parse_args()

    if not args.command or args.command == "help":
        show_help()
        exit(0)

    # Run command
    logger.info("Running command %s", args.command)
    code = command_get(args.command).run(args)

    exit(code)


def command_exists(name: str) -> bool:
    return name in CRON_COMMANDS


def command_get(name: str) -> CronCommand:
    if not command_exists(name):
        raise ValueError(f"Unknown command: {name}")

    command_class = CRON_COMMANDS[name]
    return inject.instance(command_class)


if __name__ == "__main__":
    run_command()
