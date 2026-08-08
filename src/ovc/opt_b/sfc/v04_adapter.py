from __future__ import annotations

from typing import Any, Mapping, Sequence

from ovc.opt_b.srfd.sensitivity import sensitivity_metrics as frozen_sensitivity_metrics

from .evidence import residual_rate

FROZEN_V04_REGISTRY_PATH = "registries/research/srfd/stability_metric_specs_v0_4.json"
FROZEN_V04_GIT_BLOB = "e4f5ce02a103000a48ed98e2110b8f1a7d497fcd"
FROZEN_V04_LOGICAL_SHA256 = "371a058e26c05a351a99689ad23b7f844fbc956a6d81449fd237a2f420bf564b"


def compare_residual_semantics(catalogs: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Prove wrapper equivalence for the frozen v0.4 residual numerator/denominator.

    The frozen implementation emits decimal residual_rate; SFC retains exact rational
    numerator/denominator. Equivalence is over the same numerator, denominator and
    decimal value on shared synthetic inputs. The frozen implementation is not modified.
    """
    frozen = frozen_sensitivity_metrics(catalogs)
    by_config = {str(row.get("configuration_id")): row for row in frozen}
    receipts=[]
    for catalog in catalogs:
        config=str(catalog.get("configuration_id")); wrapped=residual_rate(catalog); old=by_config[config]
        denominator=int(old["assignment_denominator"]); numerator=int(old["residual_count"])
        if (wrapped["numerator"],wrapped["denominator"]) != (numerator,denominator):
            raise ValueError("SFC_V04_EQUIVALENCE_FAIL:COUNTS")
        old_rate=old["residual_rate"]
        if denominator:
            n,d=(int(x) for x in wrapped["rate"].split("/")); new_decimal=format(__import__("decimal").Decimal(n)/__import__("decimal").Decimal(d),"f")
            if old_rate != new_decimal:
                raise ValueError("SFC_V04_EQUIVALENCE_FAIL:RATE")
        elif old_rate is not None or wrapped["rate"] is not None:
            raise ValueError("SFC_V04_EQUIVALENCE_FAIL:ZERO_DENOMINATOR")
        receipts.append({"configuration_id":config,"frozen_numerator":numerator,"frozen_denominator":denominator,"frozen_decimal_rate":old_rate,"sfc_exact_rate":wrapped["rate"],"equivalent":True})
    return receipts
