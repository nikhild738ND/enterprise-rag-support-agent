from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import csv
from collections import Counter

from app.config import settings
from app.db import execute, executemany, init_db


DOCS = {
    "DOC-PROD-001": {
        "title": "Product Plans and Platform Limits",
        "filename": "product_plans.md",
        "body": """
DOC_ID: DOC-PROD-001
TITLE: Product Plans and Platform Limits

The Starter plan supports up to 10 seats and does not include SSO.
The Growth plan supports up to 250 seats and does not include SSO.
The Enterprise plan supports unlimited seats and includes SAML SSO, SCIM provisioning, audit logs, sandbox workspaces, and status page webhooks.
Usage analytics refresh every 15 minutes.
The standard API rate limit is 600 requests per minute per workspace.
The file upload limit is 250 MB per file.
""",
        "facts": [
            ("What does the Enterprise plan include?", "The Enterprise plan includes SAML SSO, SCIM provisioning, audit logs, sandbox workspaces, and status page webhooks."),
            ("How often does usage analytics refresh?", "Usage analytics refresh every 15 minutes."),
            ("What is the standard API rate limit?", "The standard API rate limit is 600 requests per minute per workspace."),
            ("What is the file upload limit?", "The file upload limit is 250 MB per file."),
        ],
    },
    "DOC-PROD-002": {
        "title": "Billing FAQ",
        "filename": "billing_faq.md",
        "body": """
DOC_ID: DOC-PROD-002
TITLE: Billing FAQ

Annual invoices are net 30.
Monthly subscriptions auto-renew on the billing anniversary.
PO numbers are supported only on Enterprise annual contracts.
Service credits expire 12 months after issue.
Duplicate invoices can be regenerated from Billing > Invoices.
""",
        "facts": [
            ("What are payment terms for annual invoices?", "Annual invoices are net 30."),
            ("Do monthly subscriptions auto-renew?", "Monthly subscriptions auto-renew on the billing anniversary."),
            ("When do service credits expire?", "Service credits expire 12 months after issue."),
            ("Where can duplicate invoices be regenerated?", "Duplicate invoices can be regenerated from Billing > Invoices."),
        ],
    },
    "DOC-POL-001": {
        "title": "Refund Policy",
        "filename": "refund_policy.md",
        "body": """
DOC_ID: DOC-POL-001
TITLE: Refund Policy

The first annual purchase is eligible for a refund within 14 days.
Monthly charges are non-refundable after the billing cycle starts.
Add-on purchases are refundable within 7 days if unused.
Refunds are issued to the original payment method within 5 to 10 business days.
Partial seat reductions take effect at the next renewal.
""",
        "facts": [
            ("What is the refund window for the first annual purchase?", "The first annual purchase is eligible for a refund within 14 days."),
            ("Are monthly charges refundable after the cycle starts?", "Monthly charges are non-refundable after the billing cycle starts."),
            ("How long do unused add-on purchases stay refundable?", "Add-on purchases are refundable within 7 days if unused."),
            ("How long do refunds take to arrive?", "Refunds are issued to the original payment method within 5 to 10 business days."),
        ],
    },
    "DOC-POL-002": {
        "title": "Security Policy",
        "filename": "security_policy.html",
        "body": """
<html><body>
<p>DOC_ID: DOC-POL-002</p>
<p>TITLE: Security Policy</p>
<p>Access tokens expire after 12 hours.</p>
<p>Security incidents must be escalated to the security lead within 1 hour.</p>
<p>Personally identifiable information includes email, phone number, and billing address.</p>
<p>Raw payment card numbers are never stored.</p>
<p>Audit log export requires workspace admin permissions.</p>
</body></html>
""",
        "facts": [
            ("When do access tokens expire?", "Access tokens expire after 12 hours."),
            ("How quickly must a security incident be escalated?", "Security incidents must be escalated to the security lead within 1 hour."),
            ("Does the platform store raw payment card numbers?", "Raw payment card numbers are never stored."),
            ("What permission is needed for audit log export?", "Audit log export requires workspace admin permissions."),
        ],
    },
    "DOC-POL-003": {
        "title": "Data Retention Policy",
        "filename": "data_retention.html",
        "body": """
<html><body>
<p>DOC_ID: DOC-POL-003</p>
<p>TITLE: Data Retention Policy</p>
<p>Support tickets are retained for 24 months.</p>
<p>Audit logs are retained for 12 months.</p>
<p>Deleted workspace data is purged after 30 days.</p>
<p>Temporary CSV exports expire after 7 days.</p>
<p>Chat attachments are retained for 180 days unless legal hold applies.</p>
</body></html>
""",
        "facts": [
            ("How long are support tickets retained?", "Support tickets are retained for 24 months."),
            ("How long are audit logs retained?", "Audit logs are retained for 12 months."),
            ("When is deleted workspace data purged?", "Deleted workspace data is purged after 30 days."),
            ("When do temporary CSV exports expire?", "Temporary CSV exports expire after 7 days."),
        ],
    },
    "DOC-RUN-001": {
        "title": "Password Reset Runbook",
        "filename": "password_reset.md",
        "body": """
DOC_ID: DOC-RUN-001
TITLE: Password Reset Runbook

Verify the user email and account status first.
If SSO is enforced, route the user to the identity provider admin instead of sending a local reset.
Invalidate active sessions before sending the reset link.
The reset link is valid for 30 minutes.
Escalate repeated failures after 3 unsuccessful attempts.
""",
        "facts": [
            ("What should happen before sending a reset link?", "Invalidate active sessions before sending the reset link."),
            ("What if SSO is enforced during password reset?", "If SSO is enforced, route the user to the identity provider admin instead of sending a local reset."),
            ("How long is the reset link valid?", "The reset link is valid for 30 minutes."),
            ("After how many failed attempts should password reset issues be escalated?", "Escalate repeated failures after 3 unsuccessful attempts."),
        ],
    },
    "DOC-RUN-002": {
        "title": "Sev1 Incident Runbook",
        "filename": "sev1_runbook.md",
        "body": """
DOC_ID: DOC-RUN-002
TITLE: Sev1 Incident Runbook

Acknowledge a Sev1 incident within 5 minutes.
Open the incident bridge within 10 minutes.
Update the public status page every 30 minutes.
Escalate to executives at the 15 minute mark.
A Sev1 means broad customer impact or meaningful data risk.
""",
        "facts": [
            ("When must a Sev1 incident be acknowledged?", "Acknowledge a Sev1 incident within 5 minutes."),
            ("When must the incident bridge open?", "Open the incident bridge within 10 minutes."),
            ("How often should the status page be updated during Sev1?", "Update the public status page every 30 minutes."),
            ("When does executive escalation happen for Sev1?", "Escalate to executives at the 15 minute mark."),
        ],
    },
    "DOC-RUN-003": {
        "title": "Rate Limit Runbook",
        "filename": "rate_limit_runbook.md",
        "body": """
DOC_ID: DOC-RUN-003
TITLE: Rate Limit Runbook

A 429 response is returned after 600 requests per minute.
Recommend exponential backoff of 2, 4, 8, and 16 seconds.
Do not advise customers to rotate API keys to bypass rate limits.
Escalate if sustained rate limiting lasts more than 2 hours.
""",
        "facts": [
            ("What response appears after rate limit is exceeded?", "A 429 response is returned after 600 requests per minute."),
            ("What backoff schedule should customers use?", "Recommend exponential backoff of 2, 4, 8, and 16 seconds."),
            ("Should customers rotate API keys to bypass rate limits?", "Do not advise customers to rotate API keys to bypass rate limits."),
            ("When should sustained rate limiting be escalated?", "Escalate if sustained rate limiting lasts more than 2 hours."),
        ],
    },
    "DOC-FAQ-001": {
        "title": "SSO FAQ",
        "filename": "sso_faq.md",
        "body": """
DOC_ID: DOC-FAQ-001
TITLE: SSO FAQ

SAML SSO is available only on Enterprise.
SCIM provisioning is available only on Enterprise.
Just-in-time provisioning is supported with SAML.
The allowed clock skew is 5 minutes.
Okta and Azure AD are tested identity providers.
""",
        "facts": [
            ("Which plan supports SAML SSO?", "SAML SSO is available only on Enterprise."),
            ("Which plan supports SCIM provisioning?", "SCIM provisioning is available only on Enterprise."),
            ("Is just-in-time provisioning supported?", "Just-in-time provisioning is supported with SAML."),
            ("What clock skew is allowed for SSO?", "The allowed clock skew is 5 minutes."),
        ],
    },
    "DOC-FAQ-002": {
        "title": "Integrations FAQ",
        "filename": "integrations_faq.html",
        "body": """
<html><body>
<p>DOC_ID: DOC-FAQ-002</p>
<p>TITLE: Integrations FAQ</p>
<p>Salesforce sync runs every 15 minutes.</p>
<p>Zendesk ticket import runs nightly at 1:00 UTC.</p>
<p>The Slack connector requires workspace admin approval.</p>
<p>Webhook retries continue for 24 hours.</p>
<p>CSV imports are capped at 50,000 rows.</p>
</body></html>
""",
        "facts": [
            ("How often does Salesforce sync run?", "Salesforce sync runs every 15 minutes."),
            ("When does Zendesk ticket import run?", "Zendesk ticket import runs nightly at 1:00 UTC."),
            ("What is required for the Slack connector?", "The Slack connector requires workspace admin approval."),
            ("How long do webhook retries continue?", "Webhook retries continue for 24 hours."),
        ],
    },
    "DOC-FAQ-003": {
        "title": "Order Support FAQ",
        "filename": "order_support.md",
        "body": """
DOC_ID: DOC-FAQ-003
TITLE: Order Support FAQ

Hardware bundle orders ship within 2 business days.
Replacement shipments do not restart the subscription term.
Tracking numbers appear after the carrier scan.
Backordered accessories ship separately from the main order.
""",
        "facts": [
            ("How quickly do hardware bundle orders ship?", "Hardware bundle orders ship within 2 business days."),
            ("Do replacement shipments restart the subscription term?", "Replacement shipments do not restart the subscription term."),
            ("When does a tracking number appear?", "Tracking numbers appear after the carrier scan."),
            ("How are backordered accessories shipped?", "Backordered accessories ship separately from the main order."),
        ],
    },
}


ACCOUNTS = [
    ("A-1001", "Alpha Logistics", "Starter", 8, "2026-09-30", "us-west", "active", "mia@alpha.example"),
    ("A-1002", "Beacon Health", "Enterprise", 540, "2027-01-15", "us-east", "active", "noah@beacon.example"),
    ("A-1003", "Cedar Retail", "Growth", 120, "2026-11-20", "eu-west", "active", "ava@cedar.example"),
    ("A-1004", "Delta Finance", "Enterprise", 880, "2026-12-10", "us-east", "active", "liam@delta.example"),
    ("A-1005", "Echo Labs", "Starter", 6, "2026-08-18", "ap-south", "trial", "zoe@echo.example"),
    ("A-1006", "Fjord Energy", "Growth", 200, "2026-10-05", "eu-north", "active", "kai@fjord.example"),
    ("A-1007", "Grove Media", "Enterprise", 320, "2027-03-01", "us-west", "active", "ivy@grove.example"),
    ("A-1008", "Harbor Foods", "Starter", 10, "2026-07-14", "us-central", "past_due", "leo@harbor.example"),
    ("A-1009", "Ion Systems", "Enterprise", 1100, "2027-05-21", "eu-west", "active", "nina@ion.example"),
    ("A-1010", "Juniper Travel", "Growth", 95, "2026-09-01", "ap-southeast", "active", "omar@juniper.example"),
]

TICKETS = [
    ("T-2001", "A-1002", "sev1", "investigating", "outage", "2026-04-01T08:00:00", "2026-04-01T08:12:00", "A. Chen", "Pending incident mitigation"),
    ("T-2002", "A-1003", "sev2", "open", "billing", "2026-04-03T09:10:00", "2026-04-03T09:45:00", "R. Singh", "Invoice mismatch under review"),
    ("T-2003", "A-1001", "sev3", "waiting_customer", "login", "2026-04-05T11:30:00", "2026-04-05T12:00:00", "M. Park", "Waiting for reset confirmation"),
    ("T-2004", "A-1004", "sev1", "mitigated", "api", "2026-04-06T07:00:00", "2026-04-06T07:40:00", "A. Chen", "Rate limiting mitigated"),
    ("T-2005", "A-1007", "sev2", "open", "sso", "2026-04-07T14:00:00", "2026-04-07T14:10:00", "L. Gomez", "SAML assertion validation in progress"),
    ("T-2006", "A-1008", "sev3", "resolved", "refund", "2026-04-08T10:00:00", "2026-04-08T11:15:00", "R. Singh", "Refund policy explained"),
    ("T-2007", "A-1005", "sev2", "open", "security", "2026-04-09T06:00:00", "2026-04-09T06:25:00", "P. Roy", "Token expiry confusion"),
    ("T-2008", "A-1006", "sev3", "open", "integrations", "2026-04-10T13:00:00", "2026-04-10T13:20:00", "L. Gomez", "Salesforce sync delay"),
    ("T-2009", "A-1009", "sev1", "investigating", "outage", "2026-04-10T09:30:00", "2026-04-10T09:35:00", "A. Chen", "Regional outage under review"),
    ("T-2010", "A-1010", "sev2", "resolved", "orders", "2026-04-11T16:00:00", "2026-04-11T16:40:00", "S. Patel", "Carrier scan delay explained"),
    ("T-2011", "A-1002", "sev3", "open", "billing", "2026-04-12T12:00:00", "2026-04-12T12:15:00", "R. Singh", "PO number setup question"),
    ("T-2012", "A-1003", "sev2", "open", "api", "2026-04-12T18:20:00", "2026-04-12T18:45:00", "M. Park", "429 guidance requested"),
]

ORDERS = [
    ("O-3001", "A-1002", "HARDWARE-BUNDLE", 1, "shipped", "TRK-9001", "2026-04-14", 1299.00),
    ("O-3002", "A-1003", "ACCESSORY-PACK", 3, "backordered", "", "2026-04-20", 180.00),
    ("O-3003", "A-1005", "REPLACEMENT-UNIT", 1, "processing", "", "2026-04-16", 0.00),
    ("O-3004", "A-1007", "HARDWARE-BUNDLE", 2, "delivered", "TRK-9004", "2026-04-12", 2598.00),
    ("O-3005", "A-1009", "ACCESSORY-PACK", 4, "shipped", "TRK-9005", "2026-04-18", 240.00),
    ("O-3006", "A-1010", "HARDWARE-BUNDLE", 1, "processing", "", "2026-04-19", 1299.00),
]


def write_docs() -> None:
    settings.source_docs_dir.mkdir(parents=True, exist_ok=True)
    for doc in DOCS.values():
        path = settings.source_docs_dir / doc["filename"]
        path.write_text(doc["body"].strip() + "\n", encoding="utf-8")


def seed_sqlite_tables() -> None:
    init_db()
    for table in ["accounts", "tickets", "orders"]:
        execute(f"DELETE FROM {table}")
    executemany(
        """
        INSERT INTO accounts(account_id, company_name, plan, seats, renewal_date, region, account_status, owner_email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ACCOUNTS,
    )
    executemany(
        """
        INSERT INTO tickets(ticket_id, account_id, severity, status, category, opened_at, last_updated_at, assigned_to, resolution_summary)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        TICKETS,
    )
    executemany(
        """
        INSERT INTO orders(order_id, account_id, sku, quantity, order_status, tracking_number, expected_delivery, total_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ORDERS,
    )


def build_eval_rows() -> list[dict[str, str]]:
    rows = []
    qid = 1

    def add(route: str, question: str, answer: str, gold_sources: list[str]) -> None:
        nonlocal qid
        rows.append(
            {
                "qid": f"Q{qid:04d}",
                "route": route,
                "question": question,
                "gold_answer": answer,
                "gold_sources": "|".join(gold_sources),
            }
        )
        qid += 1

    for doc_id, doc in DOCS.items():
        for question, answer in doc["facts"]:
            add("docs", question, answer, [doc_id])
            add("docs", f"Support asks: {question.lower()}", answer, [doc_id])

    account_open_counts = Counter(
        ticket[1] for ticket in TICKETS if ticket[3] in {"open", "investigating", "mitigated", "waiting_customer"}
    )
    for account_id, company_name, plan, seats, renewal_date, region, account_status, owner_email in ACCOUNTS:
        add("sql", f"What plan is account {account_id} on?", f"Account {account_id} is on the {plan} plan.", ["SQL::accounts"])
        add("sql", f"How many seats does account {account_id} have?", f"Account {account_id} has {seats} seats.", ["SQL::accounts"])
        add("sql", f"Which region is account {account_id} hosted in?", f"Account {account_id} is hosted in {region}.", ["SQL::accounts"])
        add("sql", f"How many currently active or open tickets does account {account_id} have?", f"Account {account_id} has {account_open_counts.get(account_id, 0)} currently active or open tickets.", ["SQL::tickets"])

    for ticket_id, account_id, severity, status, category, opened_at, last_updated_at, assigned_to, resolution_summary in TICKETS:
        add("api", f"What is the current status of ticket {ticket_id}?", f"Ticket {ticket_id} is currently {status}.", ["API::ticket_status"])
        add("sql", f"Who is assigned to ticket {ticket_id}?", f"Ticket {ticket_id} is assigned to {assigned_to}.", ["SQL::tickets"])
        add("sql", f"What severity is ticket {ticket_id}?", f"Ticket {ticket_id} has severity {severity}.", ["SQL::tickets"])

    for order_id, account_id, sku, quantity, order_status, tracking_number, expected_delivery, total_amount in ORDERS:
        add("api", f"What is the current status of order {order_id}?", f"Order {order_id} is currently {order_status}.", ["API::order_status"])
        add("sql", f"What is the expected delivery date for order {order_id}?", f"Order {order_id} is expected on {expected_delivery}.", ["SQL::orders"])
        tracking_answer = f"Order {order_id} has tracking number {tracking_number}." if tracking_number else f"Order {order_id} does not have a tracking number yet."
        add("api", f"What tracking number is attached to order {order_id}?", tracking_answer, ["API::order_status"])

    for account_id, company_name, plan, seats, renewal_date, region, account_status, owner_email in ACCOUNTS:
        sso_answer = (
            f"Yes. Account {account_id} is on Enterprise, and SAML SSO is available only on Enterprise."
            if plan == "Enterprise"
            else f"No. Account {account_id} is on {plan}, and SAML SSO is available only on Enterprise."
        )
        add("hybrid", f"Can account {account_id} use SAML SSO?", sso_answer, ["SQL::accounts", "DOC-FAQ-001"])

        scim_answer = (
            f"Yes. Account {account_id} is on Enterprise, and SCIM provisioning is available only on Enterprise."
            if plan == "Enterprise"
            else f"No. Account {account_id} is on {plan}, and SCIM provisioning is available only on Enterprise."
        )
        add("hybrid", f"Can account {account_id} use SCIM provisioning?", scim_answer, ["SQL::accounts", "DOC-FAQ-001"])

        po_answer = (
            f"Yes. Account {account_id} can use PO numbers because PO numbers are supported only on Enterprise annual contracts and this account is Enterprise."
            if plan == "Enterprise"
            else f"No. Account {account_id} cannot use PO numbers because PO numbers are supported only on Enterprise annual contracts and this account is {plan}."
        )
        add("hybrid", f"Can account {account_id} use PO numbers for billing?", po_answer, ["SQL::accounts", "DOC-PROD-002"])

    for ticket_id, account_id, severity, status, category, opened_at, last_updated_at, assigned_to, resolution_summary in TICKETS:
        if severity == "sev1":
            add(
                "hybrid",
                f"Ticket {ticket_id} is marked sev1. How often should the public status page be updated?",
                f"Because ticket {ticket_id} is sev1, the public status page should be updated every 30 minutes.",
                ["API::ticket_status", "DOC-RUN-002"],
            )
            add(
                "hybrid",
                f"Ticket {ticket_id} is a sev1. When should executive escalation happen?",
                f"Because ticket {ticket_id} is sev1, executive escalation should happen at the 15 minute mark.",
                ["API::ticket_status", "DOC-RUN-002"],
            )
        if category == "api":
            add(
                "hybrid",
                f"Ticket {ticket_id} is about API throttling. What backoff should support recommend?",
                f"For ticket {ticket_id}, support should recommend exponential backoff of 2, 4, 8, and 16 seconds.",
                ["API::ticket_status", "DOC-RUN-003"],
            )

    for order_id, account_id, sku, quantity, order_status, tracking_number, expected_delivery, total_amount in ORDERS:
        if sku == "HARDWARE-BUNDLE":
            add(
                "hybrid",
                f"Order {order_id} is a hardware bundle. How quickly should it ship according to policy?",
                f"Order {order_id} is a hardware bundle, so it should ship within 2 business days.",
                ["API::order_status", "DOC-FAQ-003"],
            )
        if sku == "REPLACEMENT-UNIT":
            add(
                "hybrid",
                f"Order {order_id} is a replacement shipment. Does it restart the subscription term?",
                f"No. Order {order_id} is a replacement shipment, and replacement shipments do not restart the subscription term.",
                ["API::order_status", "DOC-FAQ-003"],
            )
        if sku == "ACCESSORY-PACK":
            add(
                "hybrid",
                f"Order {order_id} contains accessories. If it is backordered, how will it ship?",
                f"If order {order_id} is backordered, the accessories ship separately from the main order.",
                ["API::order_status", "DOC-FAQ-003"],
            )

    return rows


def write_eval_csv(rows: list[dict[str, str]]):
    settings.eval_dir.mkdir(parents=True, exist_ok=True)
    path = settings.eval_dir / "eval_set.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["qid", "route", "question", "gold_answer", "gold_sources"])
        writer.writeheader()
        writer.writerows(rows)
    return path


if __name__ == "__main__":
    write_docs()
    seed_sqlite_tables()
    rows = build_eval_rows()
    csv_path = write_eval_csv(rows)
    print(f"Wrote {len(DOCS)} demo documents to {settings.source_docs_dir}")
    print(f"Seeded {len(ACCOUNTS)} accounts, {len(TICKETS)} tickets, and {len(ORDERS)} orders")
    print(f"Wrote {len(rows)} eval rows to {csv_path}")
