from src.utils.numeric_parser import parse_absolute_interval, parse_rate_interval


def test_mixed_unit_intervals():
    assert parse_absolute_interval("8,000~1万") == 9000
    assert parse_absolute_interval("5000~1万") == 7500
    assert parse_absolute_interval("2万~3万") == 25000


def test_single_side_intervals():
    assert parse_absolute_interval("<1000") == 500
    assert parse_absolute_interval("1000以上") == 1000


def test_rate_interval():
    assert parse_rate_interval("3%~5%") == 4


def test_empty_value():
    assert parse_absolute_interval("") is None
