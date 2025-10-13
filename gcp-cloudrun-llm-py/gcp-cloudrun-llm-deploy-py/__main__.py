import pulumi
from pulumi import Config
from pulumi_command import local
import pulumi_gcp as gcp
from pulumi_gcp import cloudrunv2 as cloudrun

# Pequod Components
from pulumi_pequod_stackmgmt import StackSettings, StackSettingsArgs

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
openwebui_image = config.get("openwebuiImage")

### LLM Deployment ###
# LLM Bucket
llm_bucket = gcp.storage.Bucket("llm-bucket",
    name=str(base_name)+"-llm-bucket",
    location=gcp_region,
    force_destroy=True,
    uniform_bucket_level_access=True,
)

# Deploy Ollama Cloud Run service using base image 
ollama_cr_service = cloudrun.Service("ollama_cr_service",
    name=f"{base_name}-ollama-cr"[:50], # Cloud Run service name max length is 50 chars
    location=gcp_region,
    deletion_protection= False,
    ingress="INGRESS_TRAFFIC_ALL",
    launch_stage="BETA",
    template={
        "containers":[{
            "image": ollama_image,
            "resources": {
                "cpuIdle": False,
                "limits":{
                    "cpu": llm_cpu,
                    "memory": llm_memory,
                    "nvidia.com/gpu": llm_num_gpus
                },
                "startup_cpu_boost": True,
            },
            "ports": {
                "container_port": 11434,
            },
            "volume_mounts": [{
                "name": "ollama-bucket",
                "mount_path": "/root/.ollama/",
            }],
            "startup_probe": {
                "initial_delay_seconds": 0,  # Increased to allow model download
                "timeout_seconds": 1,
                "period_seconds": 1,
                "failure_threshold": 360,  # 60 minutes max for model download
                "tcp_socket": {
                    "port": 11434,
                },
            },
        }],
        "node_selector": {
            "accelerator": "nvidia-l4", 
        },
        "gpu_zonal_redundancy_disabled": True,
        "scaling": {      
            "max_instance_count":3,
            "min_instance_count":1,
        },
        "volumes":[{
            "name": "ollama-bucket",
            "gcs": {
                "bucket": llm_bucket.name,
                "read_only": False,
            },
        }],
    },
)

ollama_binding = cloudrun.ServiceIamBinding("ollama-binding",
    name=ollama_cr_service,
    location=gcp_region,
    role="roles/run.invoker",
    members=["allUsers"],
    opts=pulumi.ResourceOptions(depends_on=[ollama_cr_service]),
)

# Use Command provider to install an model if specified via Ollama API
# The base image already has gemma3, so this is optional for other models
install_model_command = ollama_cr_service.uri.apply(lambda ollama_service_uri, model=llm_model:  f"sleep 5;curl -s -o /dev/null {ollama_service_uri}/api/pull -d '{{\"model\":\"{model}\"}}'")
install_model = local.Command(f"install_model_{llm_model.replace(':', '_')}",
    create=install_model_command,
    opts=pulumi.ResourceOptions(depends_on=[ollama_binding]),
)

### Open WebUI Deployment ###
# Open WebUI Cloud Run instance
openwebui_cr_service = cloudrun.Service("openwebui-service",
    name=f"{base_name}-openwebui-cr"[:50], # Cloud Run service name max length is 50 chars
    location=gcp_region,
    deletion_protection= False,
    ingress="INGRESS_TRAFFIC_ALL",
    launch_stage="BETA",
    template={
        "containers":[{
            "image": openwebui_image,
            "envs": [{
                "name":"OLLAMA_BASE_URL",
                "value":ollama_cr_service.uri,
            }
            ,{
                "name":"WEBUI_AUTH",
                "value":'false',  
            }],
            "resources": {
                "cpuIdle": False,
                "limits":{
                    "cpu": "8",
                    "memory": "16Gi",
                },
                "startup_cpu_boost": True,
            },
            "startup_probe": {
                "initial_delay_seconds": 0,
                "timeout_seconds": 1,
                "period_seconds": 1,
                "failure_threshold": 1800,
                "tcp_socket": {
                    "port": 8080,
                },
            },
        }],
        "scaling": {      
            "max_instance_count":3,
            "min_instance_count":1,
        },
    },
    traffics=[{
        "type": "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST",
        "percent": 100,
    }],
    opts=pulumi.ResourceOptions(depends_on=[ollama_binding]),
)

openwebui_binding = cloudrun.ServiceIamBinding("openwebui-binding",
    project=gcp_project,
    location=gcp_region,
    name=openwebui_cr_service,
    role="roles/run.invoker",
    members=["allUsers"],
    opts=pulumi.ResourceOptions(depends_on=[openwebui_cr_service]),
)

stackmgmt = StackSettings("stacksettings", 
                          drift_management=drift_management if drift_management else None,
                          ttl_minutes=(stack_ttl * 60) if stack_ttl else None,
)

pulumi.export("LLM model deployed", llm_model)
pulumi.export("ollama_url", ollama_cr_service.uri)
pulumi.export("open_webui_url", openwebui_cr_service.uri)