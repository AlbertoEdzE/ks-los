from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

request_counter = Counter("requests_total", "Total API requests", ["endpoint"])
request_errors_total = Counter("request_errors_total", "Total API errors", ["endpoint"])
request_latency_seconds = Histogram("request_latency_seconds", "API request latency seconds", ["endpoint"])
training_runs_total = Counter("training_runs_total", "Total training runs")
drift_runs_total = Counter("drift_runs_total", "Total drift runs")
risk_inference_total = Counter("risk_inference_total", "Total risk inferences")
inference_latency_seconds = Histogram("inference_latency_seconds", "Risk inference latency seconds")
approvals_total = Counter("approvals_total", "Total approvals by territory", ["territory"])
declines_total = Counter("declines_total", "Total declines by territory", ["territory"])

v2_conversations_created_total = Counter("v2_conversations_created_total", "Total v2 conversations created", ["chat_role"])
v2_messages_sent_total = Counter("v2_messages_sent_total", "Total v2 messages sent", ["chat_role", "actor_role", "status"])
v2_conversation_updates_total = Counter("v2_conversation_updates_total", "Total v2 conversation updates", ["field"])

v2_loans_created_total = Counter("v2_loans_created_total", "Total v2 loans created", ["source"])
v2_loans_updated_total = Counter("v2_loans_updated_total", "Total v2 loan updates", ["field"])
v2_loan_document_updates_total = Counter("v2_loan_document_updates_total", "Total v2 loan document status updates", ["status"])
v2_underwriting_memo_total = Counter("v2_underwriting_memo_total", "Total v2 underwriting memo generations", ["status"])

v2_phase_actions_total = Counter("v2_phase_actions_total", "Total v2 phase actions executed", ["action", "status"])
v2_catalog_product_writes_total = Counter("v2_catalog_product_writes_total", "Total v2 catalog product writes", ["op", "status"])
