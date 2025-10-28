import pulumi
from pulumi import Config
from pulumi_command import local
import pulumi_pulumiservice as pulumiservice
import pulumi_docker_build as docker_build
import pulumi_gcp as gcp
import time

# Pequod Components
from pulumi_pequod_stackmgmt import StackSettings, StackSettingsArgs

# Get GCP project and region from config or environment
gcp_config = Config("gcp")
gcp_project = gcp_config.get("project") 
gcp_region = gcp_config.get("region") or "us-central1"
gcp_zone = gcp_config.get("zone") or "us-central1-a"

# Get some provider-namespaced configuration values 
config = pulumi.Config()
base_name = config.get("baseName") or f"{pulumi.get_project()}-{pulumi.get_stack()}"
stack_ttl = config.get_int("stackTtl") 
drift_management = config.get("driftManagement") 

# Configure Docker to use gcloud credential helper
configure_docker = local.Command("configure-docker-gcp",
    create=f"gcloud auth configure-docker {gcp_region}-docker.pkg.dev --quiet",
    triggers=[time.time()], # Ensure this runs every time
)

## Artifact Registry Repo for Docker Images
repository_id = "llm-base-images-"+str(base_name)
image_repo = gcp.artifactregistry.Repository("llm-base-images-repo",
    location=gcp_region,
    repository_id=repository_id,
    description="Repo for LLM Base Images",
    format="DOCKER",
    # docker_config={
    #     "immutable_tags": True,
    # }
)

# OpenWebUI Docker image URL
openwebui_image = image_repo.name.apply(lambda repo_name: f"{gcp_region}-docker.pkg.dev/{gcp_project}/{repo_name}/openwebui")

# Build and Deploy Open WebUI Docker
openwebui_docker_image = docker_build.Image('openwebui',
    tags=[openwebui_image],                                  
    context=docker_build.BuildContextArgs(
        location="./",
    ),
    dockerfile=docker_build.DockerfileArgs(
        location="./Dockerfile.openwebui",
    ),
    platforms=[
        docker_build.Platform.LINUX_AMD64,
        docker_build.Platform.LINUX_ARM64,
    ],
    push=True,
    opts=pulumi.ResourceOptions(depends_on=[image_repo, configure_docker])
)

# Agent Docker image URL
agent_image = image_repo.name.apply(lambda repo_name: f"{gcp_region}-docker.pkg.dev/{gcp_project}/{repo_name}/adk-agent")

# Build and Deploy Agent Docker
agent_docker_image = docker_build.Image('adk-agent',
    tags=[agent_image],
    context=docker_build.BuildContextArgs(
        location="./adk-agent/",
    ),
    dockerfile=docker_build.DockerfileArgs(
        location="./adk-agent/Dockerfile",
    ),
    platforms=[
        docker_build.Platform.LINUX_AMD64,
        docker_build.Platform.LINUX_ARM64,
    ],
    push=True,
    opts=pulumi.ResourceOptions(depends_on=[image_repo, configure_docker])
)

# Ollama Docker image URL
ollama_image = image_repo.name.apply(lambda repo_name: f"{gcp_region}-docker.pkg.dev/{gcp_project}/{repo_name}/ollama")

# Build and Deploy Ollama Docker
ollama_docker_image = docker_build.Image('ollama',
    tags=[ollama_image],                                  
    context=docker_build.BuildContextArgs(
        location="./",
    ),
    dockerfile=docker_build.DockerfileArgs(
        location="./Dockerfile.ollama",
    ),
    platforms=[
        docker_build.Platform.LINUX_AMD64,
        docker_build.Platform.LINUX_ARM64,
    ],
    push=True,
    opts=pulumi.ResourceOptions(depends_on=[image_repo, configure_docker])
)

esc_yaml = pulumi.Output.all(ollama_image, agent_image, openwebui_image).apply(
        lambda args: pulumi.StringAsset(f"""values:
    pulumiConfig:
        ollamaImage: {args[0]}
        agentImage: {args[1]}
        openwebuiImage: {args[2]}"""
        )
)

esc_baseimages = pulumiservice.Environment("esc_baseimages",
    name="base-images",
    organization="pequod",
    project="gcp-cloudrun-llm",
    yaml=esc_yaml,
)

pulumi.export("openwebuiImage", openwebui_image)
pulumi.export("ollamaImage", ollama_image)
pulumi.export("images ESC env", esc_baseimages.id)

stackmgmt = StackSettings("stacksettings", 
                          drift_management=drift_management if drift_management else None,
                          ttl_minutes=(stack_ttl * 60) if stack_ttl else None,
)