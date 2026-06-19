FROM ollama/ollama:latest

# Bake llama3.2:3b into the image at build time so the container
# requires no internet access at runtime. The model weights (~2 GB)
# are stored in /root/.ollama inside this layer.
#
# Pattern: start the server in the background during the build,
# wait until it accepts requests, pull the model, then shut it down.
# Docker commits the filesystem state (including the downloaded weights)
# into the final image layer.
ENV OLLAMA_MODEL=llama3.2:3b

RUN ollama serve & \
    SERVER_PID=$! && \
    echo "Waiting for Ollama to be ready..." && \
    for i in $(seq 1 60); do \
        ollama list >/dev/null 2>&1 && break; \
        sleep 1; \
    done && \
    echo "Pulling ${OLLAMA_MODEL}..." && \
    ollama pull "${OLLAMA_MODEL}" && \
    kill $SERVER_PID && \
    wait $SERVER_PID 2>/dev/null || true

# Default entrypoint from the base image (ollama serve) runs at container start.
