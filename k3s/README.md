# k3s Deployment

These manifests deploy agentic-it to a k3s cluster as a DaemonSet (one agent pod
per node) with a shared Ollama deployment for offline inference.

## Apply order

```bash
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
# Copy secret.yaml.example, fill in your API key, then:
kubectl apply -f secret.yaml          # (your real secret, not the example)
kubectl apply -f ollama-deployment.yaml
kubectl apply -f agent-daemonset.yaml
```

## Notes

- The agent DaemonSet uses `hostNetwork: true` and `privileged: true` so it can
  reach and reconfigure the node's real Wi-Fi adapters.
- The Ollama deployment exposes port 11434 as a ClusterIP service; the agent
  resolves it via `http://ollama:11434` (set in the DaemonSet env).
- When `LLM_PROVIDER=auto`, the agent prefers Claude and falls back to Ollama
  automatically if the API is unreachable.
