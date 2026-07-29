from __future__ import annotations

from typing import Any, Mapping, Sequence

from . import pilot_corrective_review_v2 as review_v2


_ORIGINAL_SIGNATURE_BODY = review_v2._signature_body


def schema_aware_signature_body(
    record: Mapping[str, Any],
    *,
    inventory: bool = False,
) -> dict[str, Any]:
    """Return the exact historical payload body for the record schema.

    The immutable v1 pilot inventory was signed before inventory_id,
    operator_id, signing_binding_id, and status were attached. The structured
    review v2 inventory was signed with operator_id and signing_binding_id in
    its body, then inventory_id and status were attached. CORR2 must preserve
    both historical encodings rather than reinterpret either signature.
    """

    if inventory and record.get("schema") == review_v2.INVENTORY_SCHEMA_V2:
        excluded = set(review_v2._SIGNATURE_FIELDS)
        excluded.update({"inventory_id", "status"})
        return {
            key: value
            for key, value in record.items()
            if key not in excluded
        }
    return _ORIGINAL_SIGNATURE_BODY(record, inventory=inventory)


# Install the schema-aware verifier before importing the CORR2 command module.
# pilot_corr2_review_closure calls review_v2._signature_body at runtime.
review_v2._signature_body = schema_aware_signature_body

from .pilot_corr2_review_closure import main as _corr2_main  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    return _corr2_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
