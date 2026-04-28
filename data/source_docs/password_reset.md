DOC_ID: DOC-RUN-001
TITLE: Password Reset Runbook

Verify the user email and account status first.
If SSO is enforced, route the user to the identity provider admin instead of sending a local reset.
Invalidate active sessions before sending the reset link.
The reset link is valid for 30 minutes.
Escalate repeated failures after 3 unsuccessful attempts.
