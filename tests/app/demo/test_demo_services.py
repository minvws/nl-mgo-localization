from __future__ import annotations

from app.healthcarefinder.models import Address, Organization


def _org(
    *,
    name: str,
    identification: str,
    address: str | None = None,
    city: str = "",
    postalcode: str | None = None,
    state: str | None = None,
    country: str | None = None,
) -> Organization:
    return Organization(
        medmij_id=None,
        display_name=name,
        identification=identification,
        addresses=(
            [
                Address(
                    active=True,
                    address=address,
                    city=city,
                    country=country,
                    postalcode=postalcode,
                    state=state,
                )
            ]
            if address is not None
            else []
        ),
        types=[],
        data_services=[],
    )
