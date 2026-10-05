# SPDX-FileCopyrightText: 2026 Seleshi Yalew and Fairflow contributors (copyright holder to be confirmed with IHE Delft before the first public tag)
# SPDX-License-Identifier: MIT
"""Every value in fixtures/default-basin-v1.json that the blueprint prints must equal the blueprint, exactly."""

import pytest
from blueprint import dry_year, fixture, normal_year, wet_year

V1 = fixture("default-basin-v1.json")


def test_tables_parse():
    assert set(dry_year()) == {
        "utilitarian",
        "weighted_utilitarian",
        "egalitarian",
        "proportional",
        "capability",
        "sufficientarian",
        "prioritarian",
        "equal_sacrifice",
        "talmud",
    }
    assert set(normal_year()) == {
        "utilitarian",
        "egalitarian",
        "proportional",
        "capability",
        "prioritarian",
        "equal_sacrifice",
    }


@pytest.mark.parametrize("year,table", [("dry", dry_year), ("normal", normal_year)])
def test_fixture_rows_equal_blueprint(year, table):
    bp = table()
    rows = V1[year]
    assert {r["lens"] for r in rows} == set(bp), "fixture lenses differ from the blueprint table"
    for row in rows:
        want = bp[row["lens"]]
        for key, value in row.items():
            if key in ("lens", "params"):
                continue
            assert value == want[key], f"{year} {row['lens']} {key}: fixture {value} ≠ blueprint {want[key]}"


def test_wet_year_equals_blueprint():
    bp = wet_year()
    for key, value in V1["wet"].items():
        assert value == bp[key], f"wet {key}: fixture {value} ≠ blueprint {bp[key]}"
