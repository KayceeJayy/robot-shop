# Stan's Robot Shop — DevOps Capstone 2

**Keep It Running | AWS EKS · Kubernetes · Helm · Prometheus · Grafana · Fluent Bit · Loki · OpenTelemetry · Jaeger**

This repository is the implementation workspace for **DevOps Capstone 2: Keep It Running**. It uses the upstream Stan's Robot Shop sample microservices application to practise deploying, observing, and responding to failures in a Kubernetes environment.

The application is deployed to an existing Amazon EKS cluster. The project adds metrics collection, synthetic HTTP monitoring, dashboards, centralized logs, a trace-validation pipeline, an availability SLO, an incident runbook, and a documented failure-and-recovery exercise.

> **Project boundary:** This repository does not provision the EKS cluster. The cluster was provisioned for Capstone 1 and is shared with that project. See the [Voting App / Capstone 1 repository](https://github.com/KayceeJayy/example-voting-app) for the infrastructure work.

## Project snapshot

| Item | Current implementation |
|---|---|
| Cloud platform | Amazon Web Services |
| Kubernetes service | Amazon EKS |
| Region | eu-north-1 |
| Cluster | devops-capstone-eks |
| Application namespace | robot-shop |
| Observability namespace | monitoring |
| Application deployment | Helm release robot-shop, chart 1.1.0 |
| Monitoring stack | kube-prometheus-stack, Prometheus, Grafana, Alertmanager, Node Exporter and kube-state-metrics |
| Synthetic monitoring | Prometheus Blackbox Exporter |
| Centralized logging | Fluent Bit and Loki |
| Distributed tracing | OpenTelemetry Collector and Jaeger |
| SLO | 99.5% synthetic Web availability over a rolling 24-hour window |
| Last evidence snapshot | 17 November 2026 |

The 17 November EKS evidence snapshot recorded three Ready worker nodes, all 12 Robot Shop application service workloads Ready, and the load-generator Deployment running. See [EKS deployment evidence](docs/evidence/robot-shop/eks-deployment-2026-11-17.txt).

## What this project demonstrates

- Deploying a multi-service application to an existing AWS EKS cluster with Helm.
- Running a controlled load generator to create application activity.
- Collecting application and infrastructure metrics with Prometheus.
- Probing critical HTTP endpoints with Blackbox Exporter.
- Building version-controlled Grafana dashboards.
- Collecting Robot Shop container logs with Fluent Bit and querying them in Loki.
- Validating an OpenTelemetry-to-Jaeger trace pipeline for an isolated Payment test workload.
- Defining an availability SLI, SLO, and error-budget policy.
- Triggering a controlled Web outage, confirming Prometheus alert evaluation and Alertmanager receipt, and restoring service manually.
- Routing critical capstone alerts to Slack and verifying delivery with a synthetic notification.
- Maintaining a runbook, timestamped evidence, and a blameless postmortem.

## Architecture

### Application

Robot Shop is an upstream sample microservices application. The chart deploys the Web frontend, application services, and supporting data/messaging services into the robot-shop namespace.

~~~mermaid
flowchart LR
    Browser[Browser] --> Web[Web frontend]
    Web --> Services[Catalogue · Cart · User · Ratings · Payment · Shipping]
    Services --> Stores[MongoDB · MySQL · Redis]
    Payment --> RabbitMQ[RabbitMQ]
    RabbitMQ --> Dispatch[Dispatch]
~~~

The Payment-to-RabbitMQ-to-Dispatch message flow was separately validated in the local Kind environment on 15 November 2026. That evidence demonstrates the sample application's messaging path; it is not evidence of a real payment transaction in EKS. See [RabbitMQ message-flow evidence](docs/evidence/robot-shop/rabbitmq-message-flow-2026-11-15.txt).

### Observability

~~~mermaid
flowchart TD
    App[Robot Shop services] --> Metrics[Prometheus scrape targets]
    Endpoints[Web · Catalogue · Cart · Payment HTTP endpoints] --> Blackbox[Blackbox Exporter]
    Blackbox --> Prometheus[Prometheus]
    Metrics --> Prometheus
    Prometheus --> Grafana[Grafana dashboards]
    Prometheus --> Alertmanager[Alertmanager]
    Alertmanager -->|critical capstone alerts| Slack[Slack #random notifications]
    App --> FluentBit[Fluent Bit DaemonSet]
    FluentBit --> Loki[Loki]
    Loki --> Grafana
    PaymentTest[Isolated Payment trace-validation workload] --> OTel[OpenTelemetry Collector]
    OTel --> Jaeger[Jaeger]
~~~

## Application services

The Robot Shop Helm release contains 12 application services:

| Workload | Kubernetes resource | Responsibility |
|---|---|---|
| Web | Deployment | Storefront frontend |
| Catalogue | Deployment | Product catalogue |
| Cart | Deployment | Shopping cart |
| User | Deployment | User service |
| Ratings | Deployment | Product ratings |
| Payment | Deployment | Sample payment service |
| Shipping | Deployment | Shipping service |
| Dispatch | Deployment | Dispatch service |
| MongoDB | Deployment | Document database |
| MySQL | Deployment | Relational database |
| RabbitMQ | Deployment | Message broker |
| Redis | StatefulSet | In-memory data service |

The load generator is an additional Deployment. Its checked-in manifest configures two clients against the Web service: monitoring/load-deployment.yaml.

## Observability implementation

### Metrics and dashboards

The EKS monitoring stack is installed in the monitoring namespace.

| Component | Helm release | Chart version | Evidence |
|---|---|---:|---|
| kube-prometheus-stack | observability | 93.3.1 | Prometheus, Grafana and Alertmanager were Ready |
| Blackbox Exporter | robotshop-probes | 11.21.3 | HTTP probes configured for four services |

Prometheus collects the Cart service's /metrics endpoint and RabbitMQ metrics. Blackbox Exporter performs HTTP 2xx probes every 30 seconds against:

- Web: /
- Catalogue: /products
- Cart: /health
- Payment: /health

The HTTP dashboard tracks probe success, check counts, failed-check percentage, response status, and average/maximum probe latency. A separate RabbitMQ dashboard tracks message rates, queue depth, consumers, redelivery, connections, and memory.

Dashboard definitions and the Prometheus rule are stored in Git:

- monitoring/dashboards/http-synthetic-dashboard.json
- monitoring/dashboards/rabbitmq-dashboard.json
- monitoring/http-synthetic-dashboard-configmap.json
- monitoring/rabbitmq-dashboard-configmap.json
- monitoring/robot-shop-availability-rules.yaml

Prometheus retention is configured for 24 hours in monitoring/kube-prometheus-stack-values.yaml.

### Centralized logging

Fluent Bit runs as a DaemonSet and collects container logs from the robot-shop namespace. It enriches records with Kubernetes metadata, normalizes a log-level label, and forwards them to Loki.

| Component | Helm release | Chart version | Evidence |
|---|---|---:|---|
| Loki | loki | 21.2.3 | Single-binary pod and gateway Ready; 8 GiB gp3 PVC Bound |
| Fluent Bit | robotshop-logs | 0.58.3 | DaemonSet 3/3 Ready |

Loki is exposed internally through its Kubernetes gateway. The Grafana Loki data source is defined in monitoring/loki-datasource-configmap.yaml.

Verified searches included:

~~~logql
{job="robot-shop"}
{job="robot-shop",service="cart"}
{job="robot-shop",level="error"}
~~~

The evidence snapshot recorded successful Loki API access, matching streams, and Cart log entries. The fallback log-level classifier can produce false positives when application records do not contain a structured severity field; this limitation is documented in the evidence.

See [logging deployment evidence](docs/evidence/robot-shop/eks-logging-2026-11-17.txt).

### Distributed tracing

The repository includes:

- monitoring/otel-collector.yaml — OpenTelemetry Collector ConfigMap, Deployment, and ClusterIP Service.
- monitoring/jaeger-values.yaml — Jaeger configuration values.
- monitoring/payment-trace-validation.yaml — isolated Payment validation workload with Python auto-instrumentation.

A trace was successfully retrieved through the Jaeger trace API (HTTP 200). The validation produced one span for the robot-shop-payment-traced service.

**Scope limitation:** this was an isolated Payment validation deployment, not a complete production checkout trace. Jaeger trace storage is ephemeral. See [Payment tracing evidence](docs/evidence/robot-shop/payment-tracing-2026-11-17.md).

## Availability SLO and alerting

The availability policy is documented in [robot-shop-availability-policy.md](docs/slo/robot-shop-availability-policy.md).

| Item | Policy |
|---|---|
| Service | Robot Shop Web |
| SLI | Successful synthetic HTTP checks divided by observed checks |
| Measurement | Blackbox Exporter probe_success |
| Window | Rolling 24 hours |
| SLO target | At least 99.5% synthetic availability |
| Error budget | 0.5% failed checks |
| Equivalent daily allowance | 7 minutes 12 seconds |
| Probe interval | Approximately 30 seconds |

The Prometheus rule file defines:

- RobotShopWebUnavailable — critical alert after one minute of failed Web probes.
- RobotShopWebProbeMissing — warning when Web probe samples are absent.

It also records the rolling availability ratio and remaining error-budget ratio.

The policy pauses nonessential releases when 25% or less of the error budget remains and freezes risky changes when the budget is exhausted. Emergency security fixes remain subject to risk review.

### Slack notification delivery

Alertmanager routing is configured in `monitoring/robot-shop-alertmanager-slack.yaml`. It routes critical alerts labeled `team=devops-capstone` to the workspace's `#random` channel. The incoming webhook URL is stored in the Kubernetes Secret `robot-shop-slack-webhook`; the URL itself is not stored in Git.

**Verification:** On 17 November 2026, a synthetic `RobotShopSlackIntegrationTest` alert was submitted to Alertmanager (HTTP 200), and its notification appeared in Slack `#random`. This verifies the configured Alertmanager-to-Slack delivery path. It was a synthetic integration test, not a newly triggered application outage.

**Measurement caveat:** this SLI measures internal synthetic endpoint availability. It does not measure all customer requests, checkout success, or payment success. A short demonstration does not establish sustained compliance with a full 24-hour SLO window.

## Incident drill and recovery

On 17 November 2026, a controlled drill scaled the Web Deployment from one replica to zero.

The evidence confirms that:

1. Blackbox Exporter detected failed Web probes.
2. Prometheus fired RobotShopWebUnavailable.
3. Alertmanager received the firing alert.
4. The operator manually restored the Web Deployment to one replica.
5. Kubernetes reported a successful rollout.
6. The synthetic probe returned to healthy.

The interval from initiating the scale-to-zero action to observing probe recovery was approximately 2 minutes 22 seconds.

The recovery-guard script encountered repeated replicas lookup errors. **Automatic recovery was not demonstrated.** Manual recovery was successful and is the procedure documented in the runbook.

External Slack notification delivery was not configured or verified during this drill. Alertmanager receipt is proven; Slack delivery remains a follow-up item.

- [Incident runbook](docs/runbooks/robot-shop-web-unavailable.md)
- [Blameless postmortem](docs/postmortems/robot-shop-web-outage-2026-11-17.md)
- [Incident timeline and raw evidence](docs/evidence/robot-shop/incident-20261117T172805Z/)

Only perform the scale-to-zero exercise in the isolated capstone environment. It intentionally makes the Web frontend unavailable.

## Deployment and verification

### Prerequisites

- AWS CLI v2 and an authenticated AWS IAM Identity Center / SSO profile.
- kubectl configured for the target EKS cluster.
- Helm.
- Permission to access the existing devops-capstone-eks cluster in eu-north-1.

The commands below use the terraform-process AWS profile used during the project. Replace it if your local profile is different.

### 1. Connect to EKS

~~~bash
aws sso login --profile terraform-process

aws eks update-kubeconfig \
  --region eu-north-1 \
  --name devops-capstone-eks \
  --profile terraform-process

kubectl config current-context
kubectl get nodes
~~~

Confirm that the current context is the intended EKS cluster before applying manifests.

### 2. Deploy Robot Shop

From the repository root:

~~~bash
helm upgrade --install robot-shop ./K8s/helm \
  --namespace robot-shop \
  --create-namespace

helm status robot-shop -n robot-shop
kubectl get deployments,statefulsets,pods,services -n robot-shop
~~~

The chart defaults are defined in K8s/helm/values.yaml. The current Web Service type is ClusterIP; the application is not exposed through a public LoadBalancer or Ingress.

### 3. Access the Web frontend

Use port-forwarding from a terminal:

~~~bash
kubectl port-forward -n robot-shop svc/web 8080:8080
~~~

Then open http://localhost:8080.

### 4. Run the load generator

~~~bash
kubectl apply -n robot-shop -f monitoring/load-deployment.yaml
kubectl get deployment load -n robot-shop
kubectl logs -n robot-shop deployment/load --tail=50
~~~

The checked-in manifest uses two clients. Remove the load generator when it is no longer needed:

~~~bash
kubectl delete -n robot-shop -f monitoring/load-deployment.yaml
~~~

### 5. Reconcile the EKS monitoring stack

The following commands describe the chart releases and values files recorded for the EKS deployment. Check existing releases before changing a running environment.

~~~bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana-community https://grafana-community.github.io/helm-charts
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update

kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install observability prometheus-community/kube-prometheus-stack \
  --version 93.3.1 \
  --namespace monitoring \
  -f monitoring/kube-prometheus-stack-values.yaml

helm upgrade --install robotshop-probes prometheus-community/prometheus-blackbox-exporter \
  --version 11.21.3 \
  --namespace monitoring \
  -f monitoring/blackbox-values.yaml

helm upgrade --install loki grafana-community/loki \
  --version 21.2.3 \
  --namespace monitoring \
  -f monitoring/loki-values.yaml

helm upgrade --install robotshop-logs fluent/fluent-bit \
  --version 0.58.3 \
  --namespace monitoring \
  -f monitoring/fluent-bit-values.yaml

kubectl apply -f monitoring/robot-shop-availability-rules.yaml

# Create the webhook Secret securely; never commit the URL to Git.
read -rsp "Slack webhook URL: " SLACK_WEBHOOK
echo
printf '%s' "$SLACK_WEBHOOK" | kubectl -n monitoring create secret generic robot-shop-slack-webhook \
  --from-file=url=/dev/stdin --dry-run=client -o yaml | kubectl apply -f -
unset SLACK_WEBHOOK
kubectl apply -f monitoring/robot-shop-alertmanager-slack.yaml

kubectl apply -f monitoring/loki-datasource-configmap.yaml
kubectl apply -f monitoring/http-synthetic-dashboard-configmap.json
kubectl apply -f monitoring/rabbitmq-dashboard-configmap.json

helm list -n monitoring
kubectl get pods -n monitoring
~~~

The tracing manifests are separate from the four releases above. Jaeger must be available before the Collector and isolated Payment trace-validation workload can export traces. The repository contains the Jaeger values file and Collector/validation manifests; the evidence does not record a pinned Jaeger chart version.

### 6. Access observability tools

All monitoring services are internal ClusterIP services. Discover the installed service names and ports before forwarding:

~~~bash
kubectl get services -n monitoring
~~~

For example, Loki's gateway is configured internally as loki-gateway on port 80:

~~~bash
kubectl port-forward -n monitoring svc/loki-gateway 3100:80
~~~

Use the service name and port shown by Kubernetes for Grafana, Prometheus, Alertmanager, and Jaeger. Do not expose these services publicly just for the capstone demonstration.

## Repository layout

~~~text
.
├── K8s/
│   └── helm/                  # Robot Shop application chart
├── monitoring/
│   ├── dashboards/            # Version-controlled Grafana dashboards
│   ├── *-values.yaml          # EKS monitoring chart values
│   ├── otel-collector.yaml    # OpenTelemetry Collector resources
│   ├── robot-shop-alertmanager-slack.yaml # Alertmanager-to-Slack routing
│   ├── payment-trace-validation.yaml
│   └── robot-shop-availability-rules.yaml
└── docs/
    ├── evidence/robot-shop/   # Deployment, logging, tracing and incident evidence
    ├── postmortems/           # Blameless incident reviews
    ├── runbooks/              # Operational procedures
    └── slo/                   # SLI, SLO and error-budget policy
~~~

monitoring/prometheus-values.yaml and monitoring/grafana-values.yaml describe the earlier local Kind monitoring setup. The EKS stack uses monitoring/kube-prometheus-stack-values.yaml.

## Validation evidence

| Validation | Result | Evidence |
|---|---|---|
| Local Robot Shop functional checks | 5/5 checks passed; no real payment transaction | [Local functional validation](docs/evidence/robot-shop/functional-validation-2026-11-14.txt) |
| EKS application deployment | 12 application workloads Ready; Web HTTP 200 | [EKS deployment](docs/evidence/robot-shop/eks-deployment-2026-11-17.txt) |
| Prometheus and Grafana | Stack Ready; Cart and RabbitMQ scrape targets up; dashboard sidecar reload verified | [Monitoring evidence](docs/evidence/robot-shop/eks-prometheus-grafana-2026-11-17.txt) |
| Fluent Bit and Loki | DaemonSet 3/3 Ready; Loki API HTTP 200; log searches returned results | [Logging evidence](docs/evidence/robot-shop/eks-logging-2026-11-17.txt) |
| Payment trace pipeline | Jaeger trace API HTTP 200; one span from isolated validation workload | [Tracing evidence](docs/evidence/robot-shop/payment-tracing-2026-11-17.md) |
| Availability incident drill | Prometheus alert fired; Alertmanager received it; manual recovery and probe recovery verified | [Incident timeline](docs/evidence/robot-shop/incident-20261117T172805Z/timeline.txt) |
| Slack notification integration | Synthetic Alertmanager test accepted (HTTP 200); notification observed in Slack #random | `monitoring/robot-shop-alertmanager-slack.yaml` and operator verification on 17 November 2026 |

## Known limitations and production-readiness gaps

This is a learning and demonstration environment, not a production-ready reference deployment.

- Synthetic HTTP probes do not replace real request-level metrics, distributed request tracing, or customer-experience monitoring.
- The 99.5% SLO is a defined target; the available short test window does not prove sustained 24-hour compliance.
- Slack delivery was verified with a synthetic alert. The actual Web outage alert was not re-triggered after Slack integration, so a live incident notification remains to be tested.
- The recovery-guard automation was faulty during the incident drill; manual recovery worked.
- The Payment trace was isolated validation, contained one verified span, and was not a complete checkout trace.
- Jaeger trace storage is ephemeral.
- Prometheus retention is 24 hours.
- Grafana persistence is disabled in the EKS kube-prometheus-stack values.
- Loki is a single-replica deployment with an 8 GiB gp3 volume. Authentication is disabled in the single-tenant lab configuration; keep it internal and do not expose it publicly.
- Fluent Bit's fallback log-level classification may produce false positives.
- The upstream Robot Shop application is a sample application and has its own application-level limitations. No real payment transaction was performed.

## Cleanup and AWS cost awareness

Robot Shop and the monitoring stack run in a cluster shared with Capstone 1. Remove only the resources you intend to remove.

To uninstall the Robot Shop application:

~~~bash
helm uninstall robot-shop -n robot-shop
kubectl delete namespace robot-shop
~~~

To uninstall the monitoring Helm releases, after confirming they are no longer needed:

~~~bash
helm uninstall robotshop-logs -n monitoring
helm uninstall loki -n monitoring
helm uninstall robotshop-probes -n monitoring
helm uninstall observability -n monitoring
~~~

Before deleting monitoring claims or the namespace, inspect persistent volumes:

~~~bash
kubectl get pvc -n monitoring
kubectl get pv
~~~

The gp3 StorageClass used by the project has a Retain reclaim policy. Deleting a PVC or namespace may therefore leave an EBS volume behind. Inspect AWS EBS volumes in eu-north-1 and deliberately remove only volumes that are no longer required.

**Do not destroy the shared EKS cluster as part of Robot Shop cleanup.** Confirm that Capstone 1 and every other workload have been retired, inventory billable resources, and follow the Capstone 1 infrastructure cleanup procedure before considering cluster deletion.

## Upstream project and licensing

Stan's Robot Shop is based on the [upstream instana/robot-shop project](https://github.com/instana/robot-shop). The upstream application is retained as the sample workload; this repository adds the capstone deployment, monitoring configuration, operational documentation, and validation evidence.

See the repository's LICENSE file for licensing information.
