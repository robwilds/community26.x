#!/bin/bash
##
# Start Ollama in the background.
/bin/ollama serve &
# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

echo "🔴 Retrieve LLAMA3 model..."
#ollama pull gemma3n:e2b
#ollama pull qwen3:0.6b
#ollama pull llama3
echo "🟢 Done!"

# Wait for Ollama process to finish.
wait $pid