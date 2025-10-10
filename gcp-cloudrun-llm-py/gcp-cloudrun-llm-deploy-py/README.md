# Cloud Run Hosted LLM Using GPUs 

Uses images managed by the `gcp-cloudrun-llm-base` project(s) to deploy an Ollama LLM and OpenWebUI on GCP CloudRun.

Deploys:
- LLM running in CloudRun using GPU processors.
  - Additional model if specified.
- OpenWebUI frontend for the LLM in CloudRun.

## Demonstrated Capabilities
- GCP CloudRun
- Command Provider
- Remote Pulumi component (`StackSettings`)
