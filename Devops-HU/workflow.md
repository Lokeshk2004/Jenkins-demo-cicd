# EKS Production Platform — End-to-End Workflow
**Project Tag:** `su-devops-lokesh26`  
**Repo 1 (App + Infra + CI):** `github.com/Lokeshk2004/su-lokesh-devops` (private)  
**Repo 2 (CD/GitOps):** `github.com/Lokeshk2004/su-lokesh-cd-devops` (private)

---

## Repository & Branch Structure

### Repo 1: `su-lokesh-devops`

| Branch | Purpose | Contents |
|---|---|---|
| `su/application` | Application source code | Flask microservices (frontend, users, products, orders), Dockerfiles |
| `su/infra` | Infrastructure as Code | Terraform modules (VPC, EKS, EC2, GCR, IAM, SGs) |
| `su/cipipeline` | CI automation | GitHub Actions workflows (build, scan, push) |

### Repo 2: `su-lokesh-cd-devops`

| Branch | Purpose | Contents |
|---|---|---|
| `su/cdpipeline` | GitOps / CD | Helm charts, ArgoCD Application manifests, Kyverno policies, NetworkPolicies |

> **Branch protection:** `main` on both repos must be protected — require PR reviews before merging. No direct pushes to `main`.

---

## Phase 1 — Infrastructure (Terraform)

> All infrastructure is provisioned via Terraform pipeline. **No console clicking.**

### 1.1 Remote State Backend

Configure an S3 bucket + DynamoDB table for Terraform state locking before any other resource creation.

```
s3://su-devops-lokesh26-tfstate
DynamoDB table: su-devops-lokesh26-tflock
```

### 1.2 Terraform Module Layout (`su/infra` branch)

```
infra/
├── backend.tf
├── main.tf
├── variables.tf
├── outputs.tf
└── modules/
    ├── vpc/              # VPC, subnets, IGW, NAT Gateway, route tables
    ├── eks/              # EKS cluster, node group, OIDC, add-ons
    ├── ec2/              # Bastion/jump host in private subnet
    ├── iam/              # Roles, policies for EKS, nodes, GCR access
    ├── security_groups/  # SG rules for bastion, EKS, nodes
    └── gcr/              # GCP service account + key for GCR access (output stored in Secrets Manager)
```

### 1.3 VPC Layout

| Component | Detail |
|---|---|
| CIDR | `10.0.0.0/16` |
| Public Subnet | `10.0.1.0/24` — NAT GW, Load Balancer |
| Private Subnet A | `10.0.2.0/24` — EKS nodes, Bastion |
| Private Subnet B | `10.0.3.0/24` — EKS nodes (multi-AZ) |
| Internet Gateway | Attached to VPC |
| NAT Gateway | In public subnet — allows private subnet egress (image pulls, API calls) |

### 1.4 EKS Cluster

- **Type:** Private cluster (API endpoint private only)
- **Node group:** 2 × `t2.medium`, single managed node group
- **Add-ons (declared in Terraform):** `vpc-cni`, `coredns`, `kube-proxy`, `aws-ebs-csi-driver`
- **OIDC:** Enabled for IRSA (IAM Roles for Service Accounts)
- **Naming:** `su-devops-lokesh26-eks`

### 1.5 EC2 Bastion

- Private subnet, no public IP
- Access via AWS Systems Manager (SSM) — no open SSH ports
- Used for `kubectl` and `kubeseal` operations
- Name: `su-devops-lokesh26-bastion`

### 1.6 Terraform Pipeline (`su/cipipeline` branch)

Triggered on push to `su/infra`:

```
Workflow: terraform.yml
Steps:
  1. Checkout su/infra branch
  2. Configure AWS credentials (OIDC or IAM keys from GitHub Secrets)
  3. terraform init   (remote S3 backend)
  4. terraform validate
  5. terraform plan   (output saved as artifact)
  6. terraform apply  (auto-approve on merge to main; manual approval on PR)
```

---

## Phase 2 — Application Code (`su/application` branch)

### 2.1 Service Overview

| Service | Namespace | Table | Port |
|---|---|---|---|
| Frontend | `frontend` | — | 5000 |
| Users Service | `backend-users` | `users` | 5001 |
| Products Service | `backend-products` | `products` | 5002 |
| Orders Service | `backend-orders` | `orders` | 5003 |

### 2.2 Application Structure

```
app/
├── frontend/
│   ├── app.py            # Flask UI, proxies to backend via gateway routes
│   ├── Dockerfile
│   └── requirements.txt
├── users-service/
│   ├── app.py            # CRUD: id, name, email, role
│   ├── Dockerfile
│   └── requirements.txt
├── products-service/
│   ├── app.py            # CRUD: id, name, price, category
│   ├── Dockerfile
│   └── requirements.txt
└── orders-service/
    ├── app.py            # CRUD: id, user_id, product_id, quantity, status
    ├── Dockerfile
    └── requirements.txt
```

### 2.3 Instrumentation (All Flask Services)

Every Flask service must include:
- **OpenTelemetry SDK** — traces exported to Tempo via OTEL Collector
- **Prometheus client** — `/metrics` endpoint for scraping
- **Structured JSON logging** — log fields include `trace_id`, `span_id`, `service`, `level`

---

## Phase 3 — CI Pipeline (`su/cipipeline` branch)

**Trigger:** Push or PR merge into `su/application`

```
Workflow: ci.yml

Jobs:
  build-and-push:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [frontend, users-service, products-service, orders-service]
    steps:
      1. Checkout su/application branch
      2. Authenticate to GCP (service account key from GitHub Secrets → GCR_SA_KEY)
      3. Configure Docker for GCR (gcr.io)
      4. Build Docker image
           Tag: gcr.io/<GCP_PROJECT>/su-devops-lokesh26-<service>:${{ github.sha }}
      5. Scan image with Trivy
           - Exit on CRITICAL/HIGH vulnerabilities
           - Upload SARIF report as artifact
      6. Push image to GCR (only if scan passes)
      7. Update image tag in CD repo (su-lokesh-cd-devops / su/cdpipeline)
           - Patch values.yaml with new image SHA
           - Commit and push → triggers ArgoCD sync
```

> GCR service account and IAM binding are provisioned by the `gcr` Terraform module in Phase 1.

---

## Phase 4 — Kubernetes Namespaces

All workloads use dedicated namespaces. `default` namespace is unused.

| Namespace | Workloads |
|---|---|
| `frontend` | Frontend Flask app |
| `backend-users` | Users service |
| `backend-products` | Products service |
| `backend-orders` | Orders service |
| `database` | Percona PostgreSQL Operator + PostgreSQL cluster |
| `api-gateway` | Kong Gateway, GatewayClass, Gateway, HTTPRoutes, ReferenceGrants |
| `monitoring` | Prometheus, Grafana, Tempo, OTEL Collector |
| `logging` | Loki, Promtail/Alloy |
| `argocd` | ArgoCD server and controllers |
| `sealed-secrets` | Sealed Secrets controller |
| `security` | Kyverno, admission policies |

---

## Phase 5 — CD Pipeline & GitOps (ArgoCD + Helm)

### 5.1 CD Repo Structure (`su/cdpipeline` branch)

```
cd/
├── argocd/
│   ├── Chart.yaml
│   └── values.yaml
├── apps/
│   ├── frontend/
│   ├── users-service/
│   ├── products-service/
│   ├── orders-service/
│   ├── percona-operator/
│   ├── postgres-cluster/
│   ├── api-gateway/
│   ├── sealed-secrets/
│   ├── kyverno/
│   ├── monitoring/
│   └── logging/
├── network-policies/
│   └── *.yaml           # Default-deny + explicit allow rules per namespace
├── resource-quotas/
│   └── *.yaml           # ResourceQuota + LimitRange per namespace
└── argocd-apps/
    └── app-of-apps.yaml # Root ArgoCD Application (app-of-apps pattern)
```

### 5.2 ArgoCD Sync Flow

```
Code push to su/application
        ↓
GitHub Actions CI runs
        ↓
Image built, scanned, pushed to GCR
        ↓
CI workflow patches image tag in su/cdpipeline
        ↓
ArgoCD detects drift in Helm values
        ↓
ArgoCD syncs → Helm upgrade applied to EKS cluster
        ↓
New pods roll out with updated image
```

### 5.3 Each Helm Chart Must Include

- `resources.requests` and `resources.limits` (required for quota enforcement)
- `securityContext.runAsNonRoot: true` and `runAsUser: <non-zero>`
- `livenessProbe` and `readinessProbe`
- `podDisruptionBudget` (stateless services)
- Linkerd injection annotation (`linkerd.io/inject: enabled`) on meshed namespaces

---

## Phase 6 — Database (Percona PostgreSQL Operator)

- Deployed in `database` namespace via Helm + ArgoCD
- Single PostgreSQL instance with three tables: `users`, `products`, `orders`
- Each backend service connects using a dedicated DB user with table-scoped privileges
- **No hardcoded credentials** — DB passwords stored as Sealed Secrets (`kubeseal`)
- Sealed Secrets controller deployed in `sealed-secrets` namespace

---

## Phase 7 — API Gateway (Kubernetes Gateway API)

**Single external LoadBalancer** — no legacy Ingress.

```
GatewayClass (Kong)
    └── Gateway (api-gateway namespace)
            ├── HTTPRoute: /            → frontend:5000       (frontend ns)
            ├── HTTPRoute: /api/users   → users-svc:5001      (backend-users ns)
            ├── HTTPRoute: /api/products→ products-svc:5002   (backend-products ns)
            └── HTTPRoute: /api/orders  → orders-svc:5003     (backend-orders ns)

ReferenceGrant: api-gateway → frontend, backend-users, backend-products, backend-orders
```

---

## Phase 8 — Observability

### Metrics
- **Prometheus** scrapes all pods via ServiceMonitor CRDs + kube-state-metrics + node-exporter
- **Grafana** dashboards (minimum required):
  - API failure rates per service
  - HTTP request counts by service/endpoint
  - Response times: P50, P95, P99
  - CPU & memory per pod and namespace
  - Node readiness, pod restarts, replica status

### Traces
- **Tempo** receives traces from OTEL Collector
- Grafana configured with Tempo datasource
- Request trace path: `Gateway → Frontend → Backend Service → PostgreSQL`

### Logs
- **Loki** aggregates cluster-wide logs in `logging` namespace
- **Promtail/Alloy** ships pod logs to Loki
- Grafana Log Explorer as query UI
- Logs are structured JSON and correlate `trace_id` to traces

---

## Phase 9 — Security

| Control | Implementation |
|---|---|
| No root containers | Kyverno `ClusterPolicy` — deny pods with `runAsRoot: true` |
| No hardcoded secrets | Sealed Secrets (kubeseal) for all sensitive values |
| Network isolation | Default-deny `NetworkPolicy` per namespace; explicit allow rules only |
| Branch protection | `main` protected on both repos; PR + review required |
| Image scanning | Trivy in CI — blocks push on CRITICAL/HIGH CVEs |
| GitOps only | All cluster changes via ArgoCD — no `kubectl apply` in production |

---

## Phase 10 — Service Mesh (Linkerd)

**Meshed namespaces:** `frontend`, `backend-users`, `backend-products`, `backend-orders`  
**Non-meshed:** `database`, `monitoring`, `logging`, `argocd`, `security`, `sealed-secrets`, `api-gateway`

| Requirement | Detail |
|---|---|
| mTLS | Automatic for all meshed-to-meshed traffic |
| Authorization Policy | Identity-based; e.g., only `frontend` SA can call `backend-users` |
| NetworkPolicy | Still enforced — Linkerd is an additional layer |

### Validation Proof Points
1. **mTLS proof:** `linkerd viz tap` shows TLS between frontend → backend
2. **Zero-trust proof:** Pod in `database` ns calling meshed backend → connection refused
3. **Least-privilege proof:** `backend-products` calling `backend-users` → denied by AuthorizationPolicy
4. **Defense-in-depth:** Show NetworkPolicy drop still fires even without Linkerd

---

## Phase 11 — Resource Governance

Each namespace gets a `ResourceQuota` and `LimitRange`. Example for `backend-users`:

```yaml
# ResourceQuota
requests.cpu: "500m"
requests.memory: "512Mi"
limits.cpu: "1"
limits.memory: "1Gi"
pods: "10"

# LimitRange (default per container)
defaultRequest.cpu: "100m"
defaultRequest.memory: "128Mi"
default.cpu: "250m"
default.memory: "256Mi"
```

Critical namespaces (`monitoring`, `logging`, `argocd`) get higher quotas to prevent starvation.

---

## Phase 12 — Autoscaling (KEDA)

- KEDA deployed via Helm in `keda` namespace (or `monitoring`)
- `ScaledObject` targeting one backend (e.g., `backend-users` Deployment)
- Trigger: HTTP request rate via Prometheus metrics
- `minReplicaCount: 1`, `maxReplicaCount: 4` (safe for 2-node t2.medium)
- Load test with `k6` or `hey` → observe scale-out, then cooldown → scale-in
- Evidence: `kubectl get hpa`, `kubectl get pods -w`, Grafana replica count graph

---

## Phase 13 — Node Failure Resilience Test

### Procedure
1. Drain one of the two EKS nodes: `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`
2. Observe pod rescheduling to the remaining node
3. Verify service availability via gateway endpoint
4. Check ArgoCD continues reconciling desired state
5. Review Grafana/Loki for node-not-ready events, pod restart spikes, error rates

### Controls in Place
- Stateless services: 2 replicas with `podAntiAffinity` (spread across nodes)
- `PodDisruptionBudget`: `minAvailable: 1` for all stateless deployments
- Liveness/readiness probes on all pods
- **Database caveat:** Single Postgres instance is a known single point of failure — document this explicitly; full HA requires multi-node Percona cluster (out of scope for 2-node constraint)

---

## End-to-End Flow Summary

```
Developer pushes code
        │
        ▼ (su/application branch)
GitHub Actions CI
  • Docker build
  • Trivy scan
  • Push to GCR
  • Update image tag in su/cdpipeline
        │
        ▼ (su/cdpipeline branch)
ArgoCD detects drift
  • Helm upgrade → EKS cluster
  • NetworkPolicies enforced
  • Kyverno admission checks
  • Sealed Secrets decrypted in-cluster
        │
        ▼
Running on EKS (private cluster)
  • Kong Gateway routes external traffic
  • Linkerd mTLS between services
  • OTEL traces → Tempo
  • Metrics → Prometheus → Grafana
  • Logs → Loki → Grafana
  • Postgres (Percona) stores data
```

---

## Naming Convention Reference

| Resource | Name Pattern |
|---|---|
| AWS Tag | `su-devops-lokesh26` |
| EKS Cluster | `su-devops-lokesh26-eks` |
| VPC | `su-devops-lokesh26-vpc` |
| Bastion EC2 | `su-devops-lokesh26-bastion` |
| S3 State Bucket | `su-devops-lokesh26-tfstate` |
| DynamoDB Lock | `su-devops-lokesh26-tflock` |
| GCR Images | `gcr.io/<project>/su-devops-lokesh26-<service>:<sha>` |
| Helm Releases | `su-lokesh26-<component>` |
