# Blameless Postmortem: Robot Shop Web Availability Incident

**Date:** 17 November 2026
**Environment:** AWS EKS, eu-north-1
**Service:** Robot Shop Web
**Classification:** Planned incident simulation
**Status:** Recovered
**Time zone:** UTC throughout this report

## Executive summary

A controlled failure was introduced by scaling the Robot Shop
Web Deployment from one replica to zero. The Blackbox Exporter
detected failed HTTP probes, Prometheus fired the critical
RobotShopWebUnavailable alert, and Alertmanager received it.

The operator restored Web manually. Kubernetes confirmed the
rollout succeeded, and the synthetic availability probe recovered.

The recovery guard encountered repeated 'replicas' lookup errors.
Its automatic restoration capability was not demonstrated.
External Slack notification delivery was not configured.

## Impact

The Web frontend was intentionally unavailable during the drill.
This was a controlled test, not an unplanned production outage.

No evidence indicates that Capstone 1 workloads were affected.
Backend application services were not intentionally scaled down.

The interval between initiating the outage and observing probe
recovery was approximately 2 minutes 22 seconds.

## Verified timeline

- 17:28:19 - Web baseline and recovery guard initially verified.
- 17:28:29 - Web scale-to-zero initiated.
- 17:28:57 - First failed synthetic HTTP probe observed.
- 17:30:22 - Prometheus firing and Alertmanager receipt confirmed.
- 17:30:30 - Web scale-up succeeded.
- 17:30:33 - Web Deployment rollout completed.
- 17:30:51 - Synthetic HTTP probe recovered.

Monitoring observations were sampled. Actual state transitions
may have occurred between the timestamps listed above.

## Root cause

The primary outage was deliberately triggered by scaling the
Web Deployment to zero replicas.

The recovery-guard logs separately revealed repeated Python
KeyError-style messages referencing 'replicas'. The precise
reason for the missing field was not established during the drill.

## Detection and response

Detection used the Blackbox Exporter probe_success metric.
Prometheus evaluated the RobotShopWebUnavailable alert rule.
The firing alert was confirmed through the Prometheus API and
the Alertmanager API.

The operator restored the Deployment to one replica, verified
a successful rollout and confirmed probe recovery.

## What worked

- Availability monitoring detected the simulated outage.
- The critical Prometheus alert fired.
- Alertmanager received the firing alert.
- The documented manual recovery procedure succeeded.
- Evidence was captured as timestamped files.

## What needs improvement

- Repair and retest the recovery guard before reusing it.
- Configure a real Alertmanager notification receiver.
- Verify Slack delivery in a future alert test.
- Add real application request/error/latency instrumentation.
- Expand tracing beyond isolated Payment validation.

## Corrective actions

1. Remove the faulty temporary recovery guard after the drill.
2. Investigate the Scale API response and add defensive parsing.
3. Add an automated test for recovery guard functionality.
4. Configure Slack through a Kubernetes Secret, never in Git.
5. Verify actual channel notification and resolution messages.
6. Add broader service-level observability.

## Evidence

- Incident timeline: ../evidence/robot-shop/incident-20261117T172805Z/timeline.txt
- Prometheus firing alert: ../evidence/robot-shop/incident-20261117T172805Z/firing-prometheus.json
- Alertmanager received alert: ../evidence/robot-shop/incident-20261117T172805Z/firing-alertmanager.json
- Recovered probe: ../evidence/robot-shop/incident-20261117T172805Z/recovery.json
- Guard logs: ../evidence/robot-shop/incident-20261117T172805Z/recovery-guard.log
- Runbook: ../runbooks/robot-shop-web-unavailable.md

## Conclusion

The drill successfully demonstrated alert detection, delivery
to Alertmanager and manual application recovery.

Automatic guard restoration and Slack notification delivery
remain unverified. These are documented follow-up items,
not completed capabilities.
