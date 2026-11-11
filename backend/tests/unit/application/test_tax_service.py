"""tax_service 单测：税率与展示标签（label）回归。

重点覆盖整数百分比（20% / 10% / 0%）——历史 bug：对 ``Decimal.normalize()`` 的
字符串直接 ``rstrip("0")`` 会把整数位的零一并剥掉，导致 20% 显示成 2%、0% 显示成空。
"""

from decimal import Decimal

import pytest

from forge.application.services.tax_service import TaxResult, TaxRule


@pytest.mark.parametrize(
    ("rate", "expected"),
    [
        ("0", "US Sales Tax (US) 0%"),
        ("0.05", "GST (CA) 5%"),
        ("0.10", "GST (AU) 10%"),
        ("0.13", "VAT (CN) 13%"),
        ("0.19", "VAT (DE) 19%"),
        ("0.20", "VAT (GB) 20%"),
        ("0.22", "VAT (IT) 22%"),
        ("0.075", "Tax (XX) 7.5%"),
    ],
)
def test_label_keeps_integer_percent(rate: str, expected: str) -> None:
    name, jurisdiction = expected.split(" (")[0], expected.split(" (")[1].split(")")[0]
    result = TaxResult(rate=Decimal(rate), name=name, jurisdiction=jurisdiction)
    assert result.label == expected


def test_label_without_jurisdiction_uses_name() -> None:
    assert TaxResult(rate=Decimal("0.2"), name="VAT", jurisdiction="").label == "VAT"


def test_tax_rule_roundtrip() -> None:
    rule = TaxRule.from_dict(
        {
            "country": "gb",
            "region": None,
            "category": None,
            "rate": "0.2",
            "name": "VAT",
            "applies_to_shipping": True,
        }
    )
    assert rule.country == "GB"
    assert rule.rate == Decimal("0.2")
    assert rule.applies_to_shipping is True
    assert TaxRule.from_dict(rule.to_dict()) == rule
