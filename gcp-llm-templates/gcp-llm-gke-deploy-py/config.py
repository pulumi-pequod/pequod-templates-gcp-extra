from pulumi import Config, get_organization, get_project, get_stack, StackReference

config = Config()

base_name = config.get("baseName") or f"{get_project()}-{get_stack()}"
drift_management = config.get("driftManagement") or "Correct"

# The default set up for this template is to leverage the shared-k8s-cluster ESC environment for the kubeconfig.
# However, if the kubeconfig is not found, then use the stack reference to get the kubeconfig.
# It's not necessarily a real-world use-case, but provides a way to contrast ESC-based stack references and in-code stack references.
# The big talking point here is using ESC means this project does not need to be aware of the k8s cluster's stack.
# It just gets it as config. 
# This also enable testing use-cases since one can initialize a test stack and hand-copy a kubeconfig to use in the stack config file
kubeconfig = config.get("kubeconfig") 

# If no kubeconfig found in config (via ESC or otherwise), then use the stack reference to get the kubeconfig.
if not kubeconfig:
  # Get stack name of the base k8s infra to deploy to and get the kubeconfig for the cluster.
  base_infra_stack_name = config.get("base_infra_stack_name")  or "shared-dev-eks/dev"
  k8s_stack_name = f"{get_organization()}/{base_infra_stack_name}"
  k8s_stack_ref = StackReference(k8s_stack_name)
  kubeconfig = k8s_stack_ref.require_output("kubeconfig") 

pulumi_config = Config("pulumiservice")
pulumi_access_token = pulumi_config.get_secret("accessToken")
