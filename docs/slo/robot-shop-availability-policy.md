# Robot Shop: Availability SLO and Error-Budget Policy

## Owner and scope

Owner: DevOps Capstone operations team.
Service: Robot Shop Web on AWS EKS.
Measurement window: rolling 24 hours.
Data source: Prometheus Blackbox Exporter.
Measurement interval: approximately 30 seconds.

## Service Level Indicator

SLI = successful synthetic HTTP checks divided by all
observed synthetic HTTP checks.

Prometheus expression:

`avg_over_time(probe_success{job="robot-shop-blackbox",service="web"}[24h])`

A successful check returns HTTP 2xx under the configured
Blackbox Exporter module.

## Service Level Objective

Target: at least 99.5% synthetic availability over 24 hours.

Allowed failure percentage: 0.5%.
Equivalent downtime allowance: 7 minutes 12 seconds per day.
At 30-second probe intervals: approximately 14 failed checks.

## Error-budget calculation

Error-budget consumption = observed failure fraction / 0.005.

Remaining budget fraction = max(0, 1 - consumption).

Prometheus recording rule:

`robot_shop_web:synthetic_error_budget_remaining:ratio24h`

The budget is exhausted when this value reaches zero.

## Operational decisions

- More than 25% budget remaining: ordinary reviewed releases.
- Between 0% and 25%: pause nonessential releases.
- Budget exhausted: freeze risky changes and prioritize recovery.
- Emergency security fixes remain permitted after risk review.

## Alerting and incident response

A critical alert fires after one minute of failed Web probes.
A separate warning detects missing probe data.

Alerts must link to the Web incident runbook.
Alertmanager handles routing; Slack delivery requires a
configured and verified webhook.

The on-call responder records detection, mitigation, recovery
and follows up with a blameless postmortem.

## Limitations

This is internal synthetic endpoint availability, not
customer-request availability or checkout success.

Missing samples are handled by a separate alert and are not
automatically classified as successful checks.

Prometheus retention is 24 hours. Before a full observation
window exists, SLI results use partial data.

The objective applies only to the observed monitoring period;
a successful short demonstration does not prove sustained
24-hour compliance.
