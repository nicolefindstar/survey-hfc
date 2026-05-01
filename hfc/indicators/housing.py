"""
Housing — Household Status & Tenure

Checks:
  Sequential : Missing values (HHStatus), Erroneous values (invalid choice codes)
  Independent:
    DisplacedOwner — displaced/IDP/refugee household claims property ownership
"""

import pandas as pd

from .base import BaseIndicator


class HousingIndicator(BaseIndicator):
    NAME = "Housing"

    def _run_specific_checks(self):
        displaced_statuses = self.std.get("displaced_statuses", [3, 4, 5, 6])
        ownership_code     = self.std.get("ownership_code", 1)

        if "HHStatus" in self.df.columns and "HHTenureType" in self.df.columns:
            is_displaced = self.df["HHStatus"].isin(displaced_statuses)
            owns_property = self.df["HHTenureType"] == ownership_code
            self._add_flag(
                "Flag_Housing_DisplacedOwner",
                is_displaced & owns_property,
                "Displaced/IDP/refugee household reports owning the dwelling",
            )
