# Contributing to MGO Localization API

Thank you for considering contributing to the MGO Localization API! We welcome contributions from everyone. Below are some guidelines to help you get started.

## How to Report Issues

If you encounter any issues or have suggestions for improvements, please feel free to open an issue on the GitHub repository. When reporting an issue, please include as much detail as possible, including steps to reproduce the issue and any relevant logs or screenshots.

## How to Submit Pull Requests

1. Fork the repository and create your branch from `develop`.
2. If you have added code that should be tested, add tests.
3. Ensure the test suite passes (make test).
4. Make sure your code lints (make lint).
5. Make sure your code passes the analyzers (make check).
6. Submit a pull request to the `develop` branch with a clear description of your changes.

## Coding Standards

- Follow the existing coding style.
- Write clear and concise commit messages following the [Conventional Commits specification](https://www.conventionalcommits.org/).
- Include comments in your code where necessary.

## Visual Studio Code

This repository contains shared configuration files, which automates the setup
of your workspace.
The configuration files reside in the `./.vscode` folder.
VS Code will detect this folder automatically and will recommend that you
install several extensions. It is advised to install all of them, as it will be
a good starting point for this project.

### Developing inside a Container

Once you have installed all the extensions, VS Code may detect a Dev Container
configuration file and, hence, ask you to reopen the folder to develop in a
container.
This feature is enabled by the Dev Container extension. It allows you to use a
container as a full-featured development environment, providing a better
development experience, including auto-completion, code navigation, and
debugging.

### Version Control in the Dev Container

To be able to use VS Code Source Control while in a Dev Container, both GIT and
GnuPG are installed. Dev Containers have out-of-the-box support for this;
however, it does require a running `ssh-agent` daemon with the appropriate
identity added to it when booting the Dev Container.
You can access your GPG key from within the Dev Container to sign commits, and
usually VS Code will copy your local `~/.ssh/known_hosts` to the Dev Container.
The latter is sometimes omitted for unknown reasons, in which case an error
might be raised upon storing GitHub's fingerprint when first connecting. To fix
it, simply manually create an empty `known_hosts` file inside the container.

```bash
touch ~/.ssh/known_hosts
```

## Commit Guidelines

This project follows the
**[Conventional Commits](https://www.conventionalcommits.org/)** specification
for commit messages. To help enforce this, a
**[pre-commit](https://pre-commit.com/)** configuration is included that can
validate your commit messages.

To enable the commit message validation hook, run:

```bash
pre-commit install --install-hooks
```

**Note:** Pre-commit is already preconfigured in the devcontainer.

## Code of Conduct

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project, you agree to abide by its terms.

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.

Thank you for your contributions!
