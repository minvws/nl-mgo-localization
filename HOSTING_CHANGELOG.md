# HOSTING_CHANGELOG

## [NEXT FUTURE RELEASE]

## [0.14.0]

- No changes required

## [0.13.0]

- No changes required

## [0.12.0]

- No changes required

## [0.11.0]

- No changes required

## [0.10.0]

### Changed
- CONF: `default.mock_base_url`
    - The app now expects a fully qualified domain without trailing slash. It should be removed if present

## [0.9.0]

- No changes required

## [0.8.0]

- No changes required

## [0.7.1]

- No changes required

## [0.7.0]

- No changes required

## [0.6.0]

- No changes required

## [0.5.2]

## [0.5.1]

## [0.5.0]

### Added
- ENV: `logging` section
- ENV `logging.logger_name`: "load"
    - The name of the logger used for application logs
- ENV `logging.log_level`
    - Defaults to "DEBUG"

### Deleted
- `app.log_level`
    - Replaced by app.logging.log_level

### Removed
- ENV: `signing.param_name`
    - This value has been hardcoded.

## [0.4.0]

### Changed
- ENV: `healthcarefinder.allow_search_bypass`
    - A config value is added to allow bypassing of the zorgab search with search keys test/test. This
    config is not required. Default value is false.

### Added
- ENV: `app.healthcare_adapter`
    - The `HealthcareAdapterType.mock_zorgab` has been renamed to `HealthcareAdapterType.mock_zorgab_hydrated`

## [0.3.3]
No changes required

## [0.3.0]

### Added
- ENV: `app.mock_base_url` string
  - A config value that is used to populate the mock response with the mock dataservice urls

- `HealthcareFinderAdapter.mock_hydrated` Enum case, which is used for mocking the hydration of a SearchResponse

### Changed
- `HealthcareFinderAdapter.mock` is now used to generate a "realistic" output for the mock hospital, along with their dataservices


## [0.2.0]

### Added
- ENV: `app.version`
  - A config value that versions the OpenAPI spec

### Fixed
The signing.sign_endpoints config setting actually has impact now.

### Changed
- ENV: The `signing.private_key` is no longer required when `signing.sign_endpoints` is `False`
- ENV: The `signing.param_name` is no longer required when `signing.sign_endpoints` is `False`


## [0.1.0]

### Added
- ENV: [signing] section
  - A new section for the signing configuration
- ENV: signing.sign_endpoints
  - This is the feature flag for the signing functionality. If False imported ZAL endpoints will not be signed
- ENV: signing.private_key :str
  - The path to the private key that is used for signing
    - This key can be generated using the ./tools/generate-sign-key.sh cli script
- ENV: signing.param_name
  - The name for the signature query string parameter key

### Changed
- Change version from 0.0.4 to 0.1.0 to start using semver properly
