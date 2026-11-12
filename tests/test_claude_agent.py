from decimal import Decimal

from app.agent.claude import ClaudeAgent, InvoiceDraftResult
from app.schemas import InvoiceDraft, InvoiceDraftItem


class FakeStructuredModel:
    def __init__(self, result):
        self.result = result
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return self.result


def test_claude_agent_returns_a_validated_draft_without_executing_actions():
    draft = InvoiceDraft(
        client_name="Acme Studio",
        client_email="billing@example.com",
        items=[InvoiceDraftItem(description="Design work", quantity=2, unit_price=Decimal("50.00"))],
        due_in_days=15,
    )
    model = FakeStructuredModel(InvoiceDraftResult(reply="Draft ready for review.", draft=draft))
    agent = ClaudeAgent(model=model)

    reply, returned_draft = agent.respond("Please invoice Acme for design work")

    assert reply == "Draft ready for review."
    assert returned_draft == draft
    assert model.messages[-1]["content"] == "Please invoice Acme for design work"
