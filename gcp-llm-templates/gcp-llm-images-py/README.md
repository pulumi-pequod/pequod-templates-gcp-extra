# Cloud Run LLM Base Infrastructure

Deploys the image(s) used by the CloudRun LLM infrastructure managed by `gcp-cloudrun-llm-deploy` project(s).

Deploys:
- GCP Artifact Registry
- Agent Development Kit (ADK) Image
- OpenWebUI Image
- Ollama Image with Gemma model installed
- ESC environment

## Demonstrated Capabilities
- GCP Artifact Registry
- Docker-Build
- Pulumi Service provider managing ESC environment
- Remote Pulumi component (`StackSettings`)

