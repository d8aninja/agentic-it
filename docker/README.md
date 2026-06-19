# Docker images

## agent.Dockerfile

Builds the Python agent. Installs `requirements.txt` and sets the entrypoint
to `python -m agent.main`. Expects `ANTHROPIC_API_KEY` and other settings via
environment variables or an `--env-file`.

## ollama.Dockerfile

Builds a self-contained Ollama image with `llama3.2:3b` baked in.

### How the model is embedded

During `docker build`, the Dockerfile:

1. Starts `ollama serve` in the background as a temporary build-time process.
2. Polls until the server is ready to accept requests.
3. Runs `ollama pull llama3.2:3b`, which downloads the weights into
   `/root/.ollama` inside the build container.
4. Shuts down the temporary server.

Docker commits the resulting filesystem — including the model weights — into
the final image layer. The container needs no internet access when it starts.

### Tradeoff

| | Baked-in model (this approach) | Pull at runtime |
|---|---|---|
| Image size | ~2–3 GB | ~500 MB base |
| First startup | Instant | Minutes (download) |
| Air-gap / offline | Yes | No |
| Model update | Rebuild image | Restart container |

This tradeoff is intentional for edge deployments where internet access at
runtime cannot be assumed. If you want a smaller image and are willing to pull
on first boot, revert the `RUN` block to an `ENTRYPOINT` script.

### Build

```bash
# From the repo root (build context must be .)
docker build -f docker/ollama.Dockerfile -t agentic-it-ollama .
```

Build takes several minutes the first time — most of that is the model download.
Subsequent builds use the Docker layer cache and are fast as long as
`OLLAMA_MODEL` hasn't changed.
