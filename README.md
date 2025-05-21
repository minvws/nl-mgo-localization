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


When you're ready, build your application by running:
`make container-build`.

Before you run `make up` to start the application, make sure you have created a app.conf file which contains the same keys as in the app.conf.example file.
It will be available at http://localhost:8006.

### Open API specs

A browsable and executable version of the REST API can be found at: http://localhost:8006/docs

### Makefile

The Makefile allows some commands to be executed both within Docker and outside Docker.

To execute the commands inside Docker, set the `DOCKER` variable when running make:

```bash
DOCKER=1 make test
```

## Visual Studio Code (VCS)

This repository includes support for development using Visual Studio dev-containers. It is however not a required way of working.

### Shared workspace files

This repository contains shared configuration files which automates the setup of your workspace.

The configuration files reside in the the `./.vscode` folder.

VCS will detect this folder automatically and will recommend you to install several extensions. It is advised to install all of them as it will be a good starting point for this project.

### Developing inside a Container

Once you have installed all the extensions, VSC may detect a Dev Container configuration file, and hence ask you to reopen the folder to develop in a container.

This feature is enabled by the Dev Container extension. It allows you to use a container as a full-featured development environment, providing a better development experience, including auto completions, code navigation, and debugging.

### Version Control in Dev Container

To be able to use VS Code Source Control while in a Dev Container, both git and gnupg are installed. Dev Containers have out-of-the-box support for this, however it does require a running `ssh-agent` daemon with the appropriate identity added to it when booting the Dev Container.

You can access your GPG key from within the Dev Container to sign commits and usually VS Code will copy your local `~/.ssh/known_hosts` to the Dev Container.
The latter is sometimes omitted for unknown reasons, in which case an error might be raised upon storing Github's fingerprint when first connecting.
To fix it, simply manually create an empty `known_hosts` file inside the container.

```
touch ~/.ssh/known_hosts
```

Please refer to the VS Code documentation for more OS-specific explanations.

### References
* [FastAPI guide](https://fastapi.tiangolo.com/)
* [Visual Studio Code: Developing inside a Container](https://code.visualstudio.com/docs/devcontainers/containers)
* [Visual Studio Code: Sharing Git credentials with your container](https://code.visualstudio.com/remote/advancedcontainers/sharing-git-credentials)


## TLS support
It's possible to run the server on SSL/TLS. You can generate a self-signed certificate for this with the following command:

    $ tools/generate_certs.sh

This will generate a new certificate in the `secrets/ssl` directory. Set the `use_ssl` to `True` (with capital T) in
the `uvicorn` section.

## Dataservice signing
Dataservice endpoints can be signed by enabling signing.sign_endpoints in the configuration file. The signed url's can then be verified in the [dvp-proxy](https://github.com/minvws/nl-mgo-dvp-proxy-private) to ensure the DVP will only request trusted URL's. For this a public key corresponding to the private key that is used for signing, needs to be distributed to the DVP service. Such private/public key pair can be generated by running:URL's. For this a public key corresponding to the private key that is used for signing, needs to be distributed to the DVP service. Such private/public key pair can be generated by running:

    $ tools/generate-sign-key.sh


## Cron jobs
It's possible to run cron or one-off tasks. These jobs are automatically listed in the main cron application.

```
app@e681803c504a:/src$ python -m app.cron

Usage: python -m app.cron <command> [args]
```

Commands are added to the `app/cron` directory and should implement the CronCommand interface.

## Documentation

More documentation can be found in de /docs folder

## Contributing

If you encounter any issues or have suggestions for improvements, please feel free to open an issue or submit a pull request on the GitHub repository of this package. For more detailed guidelines on contributing, please refer to our [Contribution Manual](CONTRIBUTING.md).

## License

This repository follows the [REUSE Specification v3.2](https://reuse.software/spec-3.2/). The code is available under the
EUPL-1.2 license, but the fonts and images are not. Please see [LICENSES/](./LICENSES), [REUSE.toml](./REUSE.toml) and
the individual `*.license` files (if any) for copyright and license information.
