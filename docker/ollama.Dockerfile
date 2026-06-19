FROM ollama/ollama:latest

# Pre-pull the default model so the container is ready offline.
# The entrypoint below starts the server, waits for it, pulls the model, then
# hands control back to the default ollama entrypoint for normal operation.
ENV OLLAMA_MODEL=llama3.2:3b

COPY docker/pull_model.sh /pull_model.sh
RUN chmod +x /pull_model.sh

ENTRYPOINT ["/bin/sh", "-c", "/pull_model.sh && exec ollama serve"]
