class CouldNotImportOrganisations(Exception):
    @staticmethod
    def because_import_reference_exists(
        import_reference: str,
    ) -> "CouldNotImportOrganisations":
        return CouldNotImportOrganisations(f"Import reference '{import_reference}' already exists")
