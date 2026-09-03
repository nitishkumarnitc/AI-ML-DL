"""Unit tests for the agent tools' core logic. Fully offline, no API key."""
from __future__ import annotations

from src.agent.tools import TOOLS, create_ticket, order_status


def test_order_status_known():
    out = order_status("AC-1001")
    assert "AC-1001" in out and "shipped" in out and "UPS" in out


def test_order_status_is_case_insensitive_and_trims():
    assert order_status("  ac-1001 ") == order_status("AC-1001")


def test_order_status_unknown():
    assert "No order found" in order_status("ZZ-9999")


def test_order_status_empty():
    assert "provide an order id" in order_status("").lower()


def test_create_ticket_is_deterministic():
    a = create_ticket("Broken widget", "It won't power on.")
    b = create_ticket("Broken widget", "It won't power on.")
    assert a == b and "TKT-" in a


def test_create_ticket_includes_email_when_given():
    assert "me@example.com" in create_ticket("Late order", "Where is it?", email="me@example.com")


def test_create_ticket_requires_subject_and_description():
    assert "needs both" in create_ticket("", "desc")
    assert "needs both" in create_ticket("subj", "")


def test_tools_registry_exposes_all_four():
    assert {t.name for t in TOOLS} == {
        "search_knowledge_base",
        "get_current_datetime",
        "get_order_status",
        "create_support_ticket",
    }
