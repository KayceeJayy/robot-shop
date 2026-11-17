# Capstone 2 — Payment Tracing Evidence

- Verified UTC: 2026-11-17T13:29:19.968088+00:00
- Service: robot-shop-payment-traced
- Trace ID: `b2b58858fee607e3fe349e82624d75ab`
- Verified spans: 1
- Jaeger trace API: HTTP 200
- Pipeline: Payment → OpenTelemetry Collector → Jaeger
- Instrumentation: isolated Payment validation deployment
- Limitation: not an end-to-end production checkout trace
- Jaeger trace storage: ephemeral
