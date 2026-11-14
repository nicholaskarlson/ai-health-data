"""Cost and wage tables for the scribe and for rapid-response workload (Milestone 5).

Block 44 (costs) is reserved and draws nothing: both tables are written as
spec.ECONOMICS states them. Prices are invented. Wages are public national
figures, and PROVENANCE.md section 6 gives each source and the date it was seen.
The loaded cost is the wage times one loading for benefits, rounded half up to cents.

Everything generated is fictional.
"""
import math

import pandas as pd

import spec
from common import write_csv

BUILT = True

E = spec.ECONOMICS


def loaded(wage):
    """Wage times the loading, rounded half up to cents with exact operations."""
    return math.floor(wage * E["loading"] * 100.0 + 0.5) / 100.0


def write(outdir):
    wages = pd.DataFrame([{"role": role, "hourly_wage": wage, "loaded_hourly_cost": loaded(wage),
                           "source_note": f"{E['wage_source']}: {what}"}
                          for role, wage, what in E["wages"]])
    write_csv(wages, outdir, "data/economics/wage_rates.csv")
    costs = pd.DataFrame([{"cost_line": line, "unit": unit, "unit_cost": unit_cost, "quantity": quantity,
                           "wage_role": role, "quantity_basis": basis, "notes": notes}
                          for line, unit, unit_cost, quantity, role, basis, notes in E["costs"]])
    write_csv(costs.astype(object).where(costs.notna(), None), outdir, "data/economics/scribe_costs.csv")
    return {"cost_lines": len(costs), "wage_roles": len(wages)}
