# Runbook: Robot Shop Web Unavailable

## Incident details

- Service: Robot Shop Web
- Namespace: robot-shop
- Environment: AWS EKS, eu-north-1
- Alert: RobotShopWebUnavailable
- Severity: Critical
- Owner: DevOps Capstone operations team

## Trigger

The synthetic HTTP availability probe returns probe_success == 0
for at least one minute.

This measures internal endpoint availability, not the success
rate of all customer requests.

## 1. Detect and assess

Record the UTC detection time.

Check the Grafana HTTP availability dashboard and Prometheus
expression:

`probe_success{job="robot-shop-blackbox",service="web"}`

Determine whether Web alone is unavailable or other services
are affected.

## 2. Diagnose

Run these commands:

- `kubectl get deployment web -n robot-shop`
- `kubectl get pods -n robot-shop -l service=web -o wide`
- `kubectl describe deployment web -n robot-shop`
- `kubectl logs -n robot-shop deployment/web --tail=100`
- `kubectl get svc web -n robot-shop`
- `kubectl get endpoints web -n robot-shop`

Search centralized logs in Grafana Loki using:

`{job="robot-shop",service="web"}`

## 3. Mitigate

Select the corrective action based on evidence.

For the authorized capstone scale-to-zero drill, restore the
previously recorded replica count (baseline: one):

`kubectl scale deployment/web -n robot-shop --replicas=1`

Then verify:

`kubectl rollout status deployment/web -n robot-shop --timeout=180s`

For other incidents, investigate the cause before restarting
Pods, changing configuration, or performing a rollback.

Do not disturb Capstone 1 or persistent database storage.

## 4. Confirm recovery

- Web Deployment is Ready and Available.
- Web probe returns probe_success == 1.
- Prometheus alert transitions to resolved.
- Cart, Catalogue and Payment remain healthy.
- Record the UTC recovery time and estimated impact.

## 5. Escalate

If recovery fails, inspect Pod events, node health, image
pull errors, service endpoints and application logs.

Escalate with the timeline, impact and attempted mitigations.

## 6. Post-incident review

Write a blameless postmortem documenting the timeline,
root cause, detection, response, recovery and action items.

Never commit credentials, tokens or Slack webhooks.
