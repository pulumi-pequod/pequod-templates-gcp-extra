import pulumi
from pulumi import Config
from pulumi_command import local
import pulumi_gcp as gcp
from pulumi_gcp import cloudrunv2 as cloudrun

# Pequod Components
import pulumi_pequod_cloudrunservice as cloudrunservice
from pulumi_pequod_stackmgmt import StackSettings, StackSettingsArgs

# Local modules and files
from utilities import service_name_shortener

# Get GCP project and region from config or environment
gcp_config = Config("gcp")
gcp_project = gcp_config.get("project") 
gcp_region = gcp_config.get("region") or "us-central1"
gcp_zone = gcp_config.get("zone") or "us-central1-a"

# Get some provider-namespaced configuration values 
config = pulumi.Config()
llm_model = config.get("llmModel") or "gemma3:latest"
llm_cpu = config.get_int("llmCpu") or 8
llm_memory = config.get("llmMemory") or "16Gi"
llm_num_gpus = config.get_int("llmNumGpus") or 1
stack_ttl = config.get_int("stackTtl") 
drift_management = config.get("driftManagement") 

base_name = config.get("baseName") or f"{pulumi.get_project()}-{pulumi.get_stack()}"

# Get outputs from base infra stack
ollama_image = config.get("ollamaImage")
agent_image = config.get("agentImage")
openwebui_image = config.get("openwebuiImage")

### LLM Deployment ###
# LLM Bucket
llm_bucket = gcp.storage.Bucket("llm-bucket",
    name=str(base_name)+"-llm-bucket",
    location=gcp_region,
    force_destroy=True,
    uniform_bucket_level_access=True,
)

ollama_cr_service = cloudrunservice.CloudRunService(f"ollama-{base_name}",
    location=gcp_region,
    image=ollama_image,
    cpu=llm_cpu,
    memory=llm_memory,
    num_gpus=llm_num_gpus,
    service_port=11434,
    bucket_name=llm_bucket.name,
    mount_path="/root/.ollama/",
)

# Use Command provider to install an model if specified via Ollama API
# The base image already has gemma3, so this is optional for other models
install_model_command = ollama_cr_service.uri.apply(lambda ollama_service_uri, model=llm_model:  f"sleep 5;curl -s -o /dev/null {ollama_service_uri}/api/pull -d '{{\"model\":\"{model}\"}}'")
install_model = local.Command(f"install_model_{llm_model.replace(':', '_')}",
    create=install_model_command,
    opts=pulumi.ResourceOptions(depends_on=[ollama_cr_service]),
)

### ADK Agent Deployment ###
agent_cr_service = cloudrunservice.CloudRunService(f"agent-{base_name}",
    location=gcp_region,
    image=agent_image,
    cpu=2,
    memory="4Gi",
    service_port=8080,
    envs=[
        {
            "name":"GOOGLE_CLOUD_PROJECT",
            "value":gcp_project,
        },
        {
            "name":"GOOGLE_CLOUD_LOCATION",
            "value": gcp_region,  
        },{
            "name":"MODEL_NAME",
            "value":llm_model,
        },{
            "name":"OLLAMA_API_BASE",
            "value":ollama_cr_service.uri,
        }
    ],
    opts=pulumi.ResourceOptions(depends_on=[ollama_cr_service]),
)

### Open WebUI Deployment ###
openwebui_cr_service = cloudrunservice.CloudRunService(f"openwebui-{base_name}",
    location=gcp_region,
    image=openwebui_image,
    cpu=8,
    memory="16Gi",
    service_port=8080,
    envs=[
        {
            "name":"OLLAMA_BASE_URL",
            "value":ollama_cr_service.uri,
        }
        ,{
            "name":"WEBUI_AUTH",
            "value":'false',  
        }
    ],
    opts=pulumi.ResourceOptions(depends_on=[ollama_cr_service]),
)

stackmgmt = StackSettings("stacksettings", 
                          drift_management=drift_management if drift_management else None,
                          ttl_minutes=(stack_ttl * 60) if stack_ttl else None,
)

pulumi.export("LLM model deployed", llm_model)
pulumi.export("ollama_url", ollama_cr_service.uri)
pulumi.export("agent_url", agent_cr_service.uri)
pulumi.export("open_webui_url", openwebui_cr_service.uri)



