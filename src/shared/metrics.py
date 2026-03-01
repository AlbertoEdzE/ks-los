from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

request_counter = Counter("requests_total", "Total API requests", ["endpoint"])
request_errors_total = Counter("request_errors_total", "Total API errors", ["endpoint"])
training_runs_total = Counter("training_runs_total", "Total training runs")
drift_runs_total = Counter("drift_runs_total", "Total drift runs")
risk_inference_total = Counter("risk_inference_total", "Total risk inferences")
inference_latency_seconds = Histogram("inference_latency_seconds", "Risk inference latency seconds")
