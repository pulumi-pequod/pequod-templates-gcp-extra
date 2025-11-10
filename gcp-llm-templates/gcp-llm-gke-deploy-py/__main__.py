import pulumi
import pulumi_command as command
import pulumi_kubernetes as k8s
from pulumi_pequod_stackmgmt import StackSettings
from pulumi_pequod_k8sapp import ServiceDeployment

# Local modules
import config

base_name = config.base_name
k8s_provider = k8s.Provider(
    "k8s-provider", kubeconfig=config.kubeconfig, delete_unreachable=True
)

llm_ns = k8s.core.v1.Namespace(base_name, pulumi.ResourceOptions(provider=k8s_provider))
llm_ns_name = llm_ns.metadata.name

## Deploy Ollama LLM service using GPU SKU on GKE Autopilot
ollama_port = 11434

# Use the existing ServiceDeployment component with proper GPU resource configuration
# Pass resources as a dict - the remote component provider should handle it
ollama = ServiceDeployment(
    "ollama",
    namespace=llm_ns_name,
    image=config.ollama_image,
    container_port=ollama_port,
    allocate_ip_address=True,
    # Don't use cpu/mem shortcuts when specifying resources with GPU
    resources={
        "requests": {
            "cpu": config.llm_cpu,
            "memory": config.llm_mem,
            "nvidia.com/gpu": config.llm_gpu_count,
        },
        "limits": {
            "nvidia.com/gpu": config.llm_gpu_count,
        },
    },
    node_selector={
        "cloud.google.com/gke-accelerator": config.llm_gke_accelerator,
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider),
)

ollama_ip_address = ollama.ip_address
ollama_uri = pulumi.Output.concat("http://", ollama_ip_address, ":", str(ollama_port))

# Use Command provider to install a model if specified via Ollama API
install_model_command = ollama_uri.apply(
    lambda ollama_service_uri, model=config.llm_model: f'sleep 5;curl -s -o /dev/null {ollama_service_uri}/api/pull -d \'{{"model":"{model}"}}\''
)
install_model = command.local.Command(
    f"install_model_{config.llm_model.replace(':', '_')}",
    create=install_model_command,
    triggers=[ollama],
    opts=pulumi.ResourceOptions(depends_on=[ollama]),
)

openwebui_port = 8080
openwebui = ServiceDeployment(
    "openwebui",
    namespace=llm_ns_name,
    image=config.openwebui_image,
    container_port=openwebui_port,
    allocate_ip_address=True,
    mem="5Gi",
    env_vars=[
        {
            "name": "OLLAMA_BASE_URL",
            "value": ollama_uri,
        },
        {
            "name": "WEBUI_AUTH",
            "value": "false",
        },
    ],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[ollama]),
)

agent_port = 8080
agent = ServiceDeployment(
    "agent",
    namespace=llm_ns_name,
    image=config.agent_image,
    container_port=agent_port,
    allocate_ip_address=True,
    mem="5Gi",
    env_vars=[
        {
            "name": "GOOGLE_CLOUD_PROJECT",
            "value": config.gcp_project or "",
        },
        {
            "name": "GOOGLE_CLOUD_LOCATION",
            "value": config.gcp_region,
        },
        {
            "name": "MODEL_NAME",
            "value": config.llm_model,
        },
        {
            "name": "OLLAMA_API_BASE",
            "value": ollama_uri,
        },
    ],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[ollama]),
)

stackmgmt = StackSettings(
    base_name,
    drift_management=config.drift_management,
    ttl_minutes=(config.ttl * 60),
    delete_stack=config.delete_stack,
)

pulumi.export(
    "ollama_url",
    pulumi.Output.concat("http://", ollama_ip_address, ":", str(ollama_port)),
)
pulumi.export(
    "openwebui_url",
    pulumi.Output.concat("http://", openwebui.ip_address, ":", str(openwebui_port)),
)
pulumi.export(
    "agent_url", pulumi.Output.concat("http://", agent.ip_address, ":", str(agent_port))
)
