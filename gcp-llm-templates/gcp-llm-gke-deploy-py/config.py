from pulumi import Config, get_organization, get_project, get_stack, StackReference

config = Config()

base_name = config.get("baseName") or f"{get_project()}-{get_stack()}"

# Get images
ollama_image = config.get("ollamaImage") 
agent_image = config.get("agentImage")
openwebui_image = config.get("openwebuiImage")

# Get LLM model to use
llm_model = config.get("llmModel") or "gemma3:latest"
llm_cpu = config.get_int("llmCpu") or 4 
llm_mem = config.get("llmMem") or "16Gi"
llm_gpu_count = config.get("gpuCount") or "1"

# GPU accelerator type for GKE Autopilot. Must be a valid accelerator in the target region.
# Examples: 'nvidia-l4', 'nvidia-tesla-t4'. A100 may require special quota and might not be available.
llm_gke_accelerator = config.get("gkeAccelerator") or "nvidia-l4"

# Get stack name of the base k8s infra to deploy to and get the kubeconfig for the cluster.
base_infra_stack_name = config.require("base_infra_stack_name")  
k8s_stack_name = f"{get_organization()}/{base_infra_stack_name}"
k8s_stack_ref = StackReference(k8s_stack_name)
kubeconfig = k8s_stack_ref.require_output("kubeconfig") 

drift_management = config.get("driftManagement") or "Correct"
ttl = config.get_int("stackTtl") or 8
delete_stack = config.get("deleteStack") or "True"

# Get GCP project and region from config or environment
gcp_config = Config("gcp")
gcp_project = gcp_config.get("project") 
gcp_region = gcp_config.get("region") or "us-central1"
gcp_zone = gcp_config.get("zone") or "us-central1-a"

# Get pulumi service config
pulumi_config = Config("pulumiservice")
pulumi_access_token = pulumi_config.get_secret("accessToken")
