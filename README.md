# MGO LOCALIZATION

## Disclaimer

This project and all associated code serve solely as documentation
and demonstration purposes to illustrate potential system
communication patterns and architectures.

This codebase:

- Is NOT intended for production use
- Does NOT represent a final specification
- Should NOT be considered feature-complete or secure
- May contain errors, omissions, or oversimplified implementations
- Has NOT been tested or hardened for real-world scenarios

The code examples are only meant to help understand concepts and demonstrate possibilities.

By using or referencing this code, you acknowledge that you do so at your own
risk and that the authors assume no liability for any consequences of its use.

## Purpose of this repository

This application provides an API to search for healthcare providers.

This module serves a few functions:

- Locate names and addresses for healthcare services (zorgaanbieders), searchable by name and city (LOCATION)
- Identify api endpoints that allows connection to these healthcare services (ADDRESSING)
- Periodically downloading and storing the ZAL XML listing into a postgres database

## Integration with External Systems
The search functionality for healthcare providers is implemented through an integration with the ZORG-AB API. [ZORG-AB](https://www.vzvz.nl/diensten/gemeenschappelijke-diensten/zorg-ab) is managed and facilitated by VZVZ.


## Setup and install instructions

### Auto-pilot

If you just want to use the project as a dependency for your own modules, you can use auto-pilot. This will setup
the application automatically and will get you up and running without configuration. See docs/auto-pilot.md for more
information.


### Building and running your application

To install and run this application we assume you have to following installed or available on your machine:

1. [Docker](https://docs.docker.com/get-started/get-docker/) and [Docker Compose](https://docs.docker.com/compose/).
2. [Make](https://www.gnu.org/software/make/)
3. [pre-commit](https://pre-commit.com/) (recommended to validate commit messages — see [Commit Guidelines](CONTRIBUTING.md#commit-guidelines) for setup and usage)

When you're ready, build your application by running:
`make container-build`.

Before you run `make up` to start the application, make sure you have created a app.conf file which contains the same keys as in the app.conf.example file.
The `app.mock_base_url` setting is required.
It will be available at http://localhost:8006.

### Open API specs

A browsable and executable version of the REST API can be found at: http://localhost:8006/docs

### Makefile

The Makefile allows some commands to be executed both within Docker and outside Docker.

To execute the commands inside Docker, set the `DOCKER` variable when running make:

```bash
DOCKER=1 make test
```

## TLS support
It's possible to run the server on SSL/TLS. You can generate a self-signed certificate for this with the following command:

    $ tools/generate_certs.sh

This will generate a new certificate in the `secrets/ssl` directory. Set the `use_ssl` to `True` (with capital T) in
the `uvicorn` section.

## Dataservice signing
Dataservice endpoints are always signed and wrapped in a JWE envelope. The public key corresponding to the signing key must be distributed to DVP Proxy for verification. Check `pki_overview.json` for more information about keys.

### Automatic key generation (local Docker development)
When running the application locally in Docker, the entrypoint script (`docker-entrypoint.sh`) automatically generates both signing and encryption keys if they don't exist in the `secrets/` directory. The example config (`app.conf.example`) points to these paths, so the app should work out of the box when using the example config and running in Docker.

Outside local Docker development (for example in test or production environments), keys must be provisioned and configured explicitly.

### Manual key generation
If you need to manually generate keys (e.g., for local development outside Docker):

#### Signing keys
Generate a signing key pair with:

    $ tools/generate-sign-key.sh

#### Encryption keys
Generate encryption keys with:

    $ tools/generate-encryption-key.sh

### Configuration
Configure the paths in the `[jwe]` section of your `app.conf` file:

```
[jwe]
signing_private_key_path = secrets/private_signing.key
encryption_public_key_path = secrets/placeholder_jwe_encryption.pub
```

### Search index update command
`search-index:update` builds the downloadable search-index output in two files:

- `organizations.json`: normalized organizations from ZorgAB.
- `endpoints.json`: encrypted endpoint URLs referenced by organizations.

This split keeps organization data and endpoint addressing separate while preserving references by endpoint ID.

When available, normalized organizations can include MedMij-specific fields:

- `medmij_id`: the MedMij name/id (eenofanderezorgaanbieder@medmij) of the organization.
- `data_services`: data service entries with endpoint IDs that resolve via `endpoints.json`.

### Search index mock merge
When `search-index:update` runs, mock data can be mixed into the generated search-index output.

- Organizations: mock organizations are appended to normalized organizations.
- Organization ID collisions: the run fails fast (no output is written).
- Endpoint ID collisions: mock endpoint wins (it overwrites the database endpoint for that ID in `endpoints.json`).



## Cron jobs
It's possible to run cron or one-off tasks. These jobs are automatically listed in the main cron application.

```bash
app@e681803c504a:/src$ python -m app.cron
```

Usage: python -m app.cron <command> [args]

Commands are added to the `app/cron` directory and should implement the CronCommand interface.

### Debugging cron jobs

Cron jobs can be debugged locally using VS Code and `debugpy`.

Start the cron command with debugging enabled:

```bash
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client -m app.cron <command> [args]
```

Then attach the VS Code debugger using the **Attach to debugpy** configuration (see [launch.json](.vscode/launch.json)). Once attached, execution continues and breakpoints will be hit.

## Documentation

More documentation can be found in the `/docs` folder.

## Contributing

If you encounter any issues or have suggestions for improvements, please feel free to open an issue or submit a pull request on the GitHub repository of this package. For more detailed guidelines on contributing, please refer to our [Contribution Manual](CONTRIBUTING.md).

## License

This repository follows the [REUSE Specification v3.2](https://reuse.software/spec-3.2/). The code is available under the
EUPL-1.2 license, but the fonts and images are not. Please see [LICENSES/](./LICENSES), [REUSE.toml](./REUSE.toml) and
the individual `*.license` files (if any) for copyright and license information.
