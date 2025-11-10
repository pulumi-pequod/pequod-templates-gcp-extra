import pulumi
import pulumi_command as command
import pulumi_kubernetes as k8s
from pulumi_pequod_stackmgmt import StackSettings, StackSettingsArgs
from pulumi_pequod_k8sapp import ServiceDeployment, ServiceDeploymentArgs

# Local modules
import config

base_name = config.base_name
k8s_provider = k8s.Provider('k8s-provider', kubeconfig=config.kubeconfig, delete_unreachable=True)

llm_ns = k8s.core.v1.Namespace(base_name, 
    pulumi.ResourceOptions(provider=k8s_provider))
llm_ns_name = llm_ns.metadata.name

## Deploy Ollama LLM service using GPU SKU on GKE Autopilot
ollama_port = 11434
ollama = ServiceDeployment(
    "ollama",
    namespace=llm_ns_name,
    image=config.ollamaImage,
    container_port=ollama_port,
    allocate_ip_address=True,
    node_selector={
      'cloud.google.com/gke-accelerator': 'nvidia-a100-80gb', 
      'cloud.google.com/gke-accelerator-count': '1'
    },
    opts=pulumi.ResourceOptions(provider=k8s_provider))
ollama_uri = pulumi.Output.concat("http://", ollama.ip_address, ":", str(ollama_port))

# Use Command provider to install an model if specified via Ollama API
install_model_command = ollama_uri.apply(lambda ollama_service_uri, model=config.llm_model:  f"sleep 5;curl -s -o /dev/null {ollama_service_uri}/api/pull -d '{{\"model\":\"{model}\"}}'")
install_model = command.local.Command(f"install_model_{config.llm_model.replace(':', '_')}",
    create=install_model_command,
    triggers=[ollama],
    opts=pulumi.ResourceOptions(depends_on=[ollama]),
)

openwebui_port = 8080
openwebui = ServiceDeployment(
    "openwebui",
    namespace=llm_ns_name,
    image=config.openwebuiImage,
    container_port=openwebui_port,
    allocate_ip_address=True,
    mem="5Gi",
    env_vars=[
        {
            "name":"OLLAMA_BASE_URL",
            "value":ollama_uri,
        }
        ,{
            "name":"WEBUI_AUTH",
            "value":'false',  
        }
    ],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[ollama]))

agent_port = 8080
agent = ServiceDeployment(
    "agent",
    namespace=llm_ns_name,
    image=config.agentImage,
    container_port=agent_port,
    allocate_ip_address=True,
    mem="5Gi",
    env_vars=[
        {
            "name":"GOOGLE_CLOUD_PROJECT",
            "value":config.gcp_project,
        },
        {
            "name":"GOOGLE_CLOUD_LOCATION",
            "value": config.gcp_region,  
        },
        {
            "name":"MODEL_NAME",
            "value":config.llm_model,
        },
        {
            "name":"OLLAMA_API_BASE",
            "value":ollama_uri,
        }
    ],
    opts=pulumi.ResourceOptions(provider=k8s_provider, depends_on=[ollama]))

stackmgmt = StackSettings(base_name, 
                          drift_management=config.drift_management,
                          ttl_minutes=(60*24),
                          delete_stack="False",
                          )

pulumi.export("ollama_url", pulumi.Output.concat("http://",ollama.ip_address,":",str(ollama_port)))
pulumi.export("openwebui_url", pulumi.Output.concat("http://",openwebui.ip_address,":",str(openwebui_port)))
pulumi.export("agent_url", pulumi.Output.concat("http://",agent.ip_address,":",str(agent_port)))











import pulumi
import pulumi_kubernetes as k8s
from pulumi_pequod_stackmgmt import StackSettings, StackSettingsArgs
from pulumi_pequod_k8sapp import ServiceDeployment, ServiceDeploymentArgs

# Local modules
import config

base_name = config.base_name
k8s_provider = k8s.Provider('k8s-provider', kubeconfig=config.kubeconfig, delete_unreachable=True)

guestbook_ns = k8s.core.v1.Namespace(base_name, 
    pulumi.ResourceOptions(provider=k8s_provider))
guestbook_ns_name = guestbook_ns.metadata.name

ServiceDeployment(
    "redis-leader",
    namespace=guestbook_ns_name,
    image="redis",
    container_port=6379, 
    allocate_ip_address=False,
    opts=pulumi.ResourceOptions(provider=k8s_provider))

ServiceDeployment(
    "redis-replica",
    namespace=guestbook_ns_name,
    image="pulumi/guestbook-redis-replica",
    container_port=6379,
    allocate_ip_address=False,
    opts=pulumi.ResourceOptions(provider=k8s_provider))

frontend = ServiceDeployment(
    "frontend",
    namespace=guestbook_ns_name,
    image="pulumi/guestbook-php-redis",
    replicas=3,
    container_port=80,
    allocate_ip_address=True,
    opts=pulumi.ResourceOptions(provider=k8s_provider))

stackmgmt = StackSettings(base_name, 
                          drift_management=config.drift_management,
                          )

pulumi.export("guestbook_url", pulumi.Output.concat("http://",frontend.ip_address))
