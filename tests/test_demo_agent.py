from decimal import Decimal

from app.agent.demo import DemoAgent


def test_invoice_description_is_extracted_when_amount_follows_commas():
    reply, draft = DemoAgent().respond(
        "Invoice Acme Studio, billing@acme.com, $125 for design audit due in 15 days"
    )

    assert "Acme Studio" in reply
    assert draft is not None
    assert draft.items[0].description == "design audit"
    assert draft.items[0].unit_price == Decimal("125")
    assert draft.due_in_days == 15
