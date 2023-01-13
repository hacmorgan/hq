#!/usr/bin/env python3
# coding: utf-8


"""
Various financial calculators
"""


import sys


def interest_charge(
    principal: float,
    interest_rate_per_annum: float = 0.0479,
    interest_charges_per_year: int = 12,
) -> float:
    """
    Compute the new principal after interest is applied
    """
    interest_rate_per_charge = interest_rate_per_annum / interest_charges_per_year
    return principal * interest_rate_per_charge


def main() -> int:
    """
    Basic main routine
    """
    principal = 376861.4
    offset_balance = 3e4
    pet_fund = 6000

    print(
        "Interest charged without pet fund:"
        f" {interest_charge(principal - offset_balance)}"
    )
    print(
        "Interest charged with pet fund:"
        f" {interest_charge(principal - offset_balance - pet_fund)}"
    )


if __name__ == "__main__":
    sys.exit(main())
