# Robot Shop Helm Chart — AWS EKS

This chart deploys the upstream Stan's Robot Shop sample application into the existing EKS cluster used for DevOps Capstone 2.

It deploys the application workloads only. **It does not create an EKS cluster, VPC, IAM roles, or monitoring stack.** The cluster infrastructure is managed separately in Capstone 1.

For the full architecture, monitoring design, validation evidence, and operational limitations, see the [repository README](../../README.md).

## Chart details

| Property | Value |
|---|---|
| Chart name | **robot-shop** |
| Chart version | **1.1.0** |
| Namespace | **robot-shop** |
| Cluster | **devops-capstone-eks** |
| Region | **eu-north-1** |
| Web Service type | **ClusterIP** |

The current EKS evidence records Helm release robot-shop, chart robot-shop-1.1.0, deployed in the robot-shop namespace.

## Prerequisites

- AWS CLI v2 with an authenticated AWS IAM Identity Center / SSO profile.
- kubectl with permission to access the existing EKS cluster.
- Helm.
- Access to the devops-capstone-eks cluster in eu-north-1.

The commands below use the terraform-process AWS profile. Replace it if your configured profile has a different name.

## Connect to the cluster

~~~bash
aws sso login --profile terraform-process

aws eks update-kubeconfig \
  --region eu-north-1 \
  --name devops-capstone-eks \
  --profile terraform-process

kubectl config current-context
kubectl get nodes
~~~

Confirm the active context before deploying.

## Install or upgrade

Run from the repository root:

~~~bash
helm upgrade --install robot-shop ./K8s/helm \
  --namespace robot-shop \
  --create-namespace

helm status robot-shop -n robot-shop
~~~

The chart uses the values in values.yaml. Review the values before changing an existing release.

## Important values

| Key | Current default | Purpose |
|---|---|---|
| image.repo | robotshop | Base image repository |
| image.version | 2.1.0 | Application image tag |
| image.pullPolicy | IfNotPresent | Kubernetes image pull policy |
| payment.gateway | https://example.com/ | Sample payment gateway URL |
| web.serviceType | ClusterIP | Internal Web Service type |
| psp.enabled | false | Legacy Pod Security Policy setting |
| openshift | false | OpenShift-specific configuration |
| ocCreateRoute | false | OpenShift Route creation |

The configured payment gateway is a placeholder for the sample application. No real payment transaction is performed.

## Verify the workloads

~~~bash
kubectl get deployments,statefulsets,pods,services -n robot-shop
kubectl rollout status deployment/web -n robot-shop --timeout=180s
helm status robot-shop -n robot-shop
~~~

The expected application workloads are Web, Catalogue, Cart, User, Ratings, Payment, Shipping, Dispatch, MongoDB, MySQL, RabbitMQ, and Redis.

## Access the Web frontend

The Web Service is internal (ClusterIP). Use port-forwarding for local access:

~~~bash
kubectl port-forward -n robot-shop svc/web 8080:8080
~~~

Open http://localhost:8080 while the port-forward process is running.

No public LoadBalancer or Ingress is configured by the current chart values.

## Load generation

The capstone load generator is defined separately in monitoring/load-deployment.yaml:

~~~bash
kubectl apply -n robot-shop -f monitoring/load-deployment.yaml
kubectl get deployment load -n robot-shop
kubectl logs -n robot-shop deployment/load --tail=50
~~~

Remove it when it is no longer required:

~~~bash
kubectl delete -n robot-shop -f monitoring/load-deployment.yaml
~~~

## Uninstall

~~~bash
helm uninstall robot-shop -n robot-shop
kubectl delete namespace robot-shop
~~~

The namespace contains the Robot Shop application. The EKS cluster itself is shared with Capstone 1 and must not be deleted as part of this chart cleanup.

## Operational notes

- This chart deploys the upstream sample application; it does not make the application production-ready.
- The current values use ClusterIP; use port-forwarding for the capstone demonstration.
- Review image tags and values before upgrades. Avoid floating tags for reproducible deployments.
- Do not commit credentials, Kubernetes configuration files, tokens, or webhook URLs.
- The full observability stack is maintained separately under the repository's monitoring/ directory.
