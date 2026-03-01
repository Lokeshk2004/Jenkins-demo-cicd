# Node Failure Resilience Test Procedure

## Prerequisites
- 2-node EKS cluster running
- All services deployed and healthy
- Grafana and Loki accessible

## Test Procedure

### Step 1: Pre-test baseline
```bash
kubectl get nodes -o wide
kubectl get pods -A -o wide
# Note which pods are on which nodes
```

### Step 2: Drain one node
```bash
# Identify a node
NODE=$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')

# Drain the node (graceful eviction)
kubectl drain $NODE --ignore-daemonsets --delete-emptydir-data
```

### Step 3: Observe pod rescheduling
```bash
# Watch pods migrate to the remaining node
kubectl get pods -A -o wide -w
```

### Step 4: Verify service availability
```bash
# Hit the gateway endpoint to ensure services are still responding
GATEWAY_URL=$(kubectl get svc -n api-gateway -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')
curl -s http://$GATEWAY_URL/health
curl -s http://$GATEWAY_URL/api/users
curl -s http://$GATEWAY_URL/api/products
curl -s http://$GATEWAY_URL/api/orders
```

### Step 5: Verify ArgoCD is reconciling
```bash
kubectl get applications -n argocd
# All applications should show "Synced" and "Healthy"
```

### Step 6: Check Grafana and Loki
- Check Grafana dashboard for:
  - Node-not-ready events
  - Pod restart spike
  - Error rate changes
  - Replica count drops and recovery
- Check Loki for:
  - Pod eviction logs
  - Rescheduling events

### Step 7: Uncordon the node
```bash
kubectl uncordon $NODE
```

## Controls in Place
- **Stateless services:** 2 replicas with `podAntiAffinity` (spread across nodes)
- **PodDisruptionBudget:** `minAvailable: 1` prevents all pods being evicted at once
- **Liveness/readiness probes:** Detect unhealthy pods quickly
- **Database caveat:** Single Postgres instance is a known SPOF — full HA requires multi-node Percona cluster (out of scope for 2-node setup)

## Expected Results
1. Drained node enters `NotReady`/`SchedulingDisabled` state
2. Pods on drained node are rescheduled to the remaining node
3. Gateway endpoint remains accessible throughout
4. ArgoCD continues reconciling desired state
5. Grafana shows brief spike in pod restarts, then recovery
