#!/bin/sh
# Start ollama in background, wait for it, pull the model, then exit.
# The Dockerfile ENTRYPOINT restarts ollama serve as the main process after this.
ollama serve &
SERVER_PID=$!

echo "Waiting for Ollama to start..."
for i in $(seq 1 30); do
    if ollama list >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "Pulling model: ${OLLAMA_MODEL:-llama3.2:3b}"
ollama pull "${OLLAMA_MODEL:-llama3.2:3b}"

kill $SERVER_PID
wait $SERVER_PID 2>/dev/null || true
