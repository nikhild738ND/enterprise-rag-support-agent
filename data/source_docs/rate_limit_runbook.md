DOC_ID: DOC-RUN-003
TITLE: Rate Limit Runbook

A 429 response is returned after 600 requests per minute.
Recommend exponential backoff of 2, 4, 8, and 16 seconds.
Do not advise customers to rotate API keys to bypass rate limits.
Escalate if sustained rate limiting lasts more than 2 hours.
