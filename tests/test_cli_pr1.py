import json


def test_cli_defaults_derive_mortgage_and_closing_costs(capsys):
    """The CLI default scenario must not silently run mortgage-free."""
    from rbv import __main__ as cli

    rc = cli.main(["--json"])
    assert rc == 0

    out = capsys.readouterr().out
    data = json.loads(out)

    assert data["monthly_payment"] is not None
    assert data["monthly_payment"] > 0.0

    assert data["closing_costs"] is not None
    assert data["closing_costs"] > 0.0

    assert data["cash_at_closing"] is not None
    assert data["cash_at_closing"] > data["closing_costs"]
