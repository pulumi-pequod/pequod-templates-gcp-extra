import pulumi
from pulumi_gcp import cloudrunv2 as cloudrun
from typing import Optional, TypedDict, List, Dict

class CloudRunServiceArgs (TypedDict):

    bucket_name: Optional[pulumi.Input[str]]
    """Bucket for the service. (optional)"""
    cpu: pulumi.Input[int]
    """CPU allocation for the container."""
    envs: Optional[List[Dict[str, pulumi.Input[str]]]]
    """Environment variables for the container. List of dicts with 'name' and 'value' keys. (optional)"""
    image: pulumi.Input[str] 
    """The link for the container image to deploy."""
    location: pulumi.Input[str]
    """GCP region for the Cloud Run service."""
    memory: pulumi.Input[str]
    """Memory allocation for the container."""
    mount_path: Optional[pulumi.Input[str]]
    """Mount path for the bucket. (optional)"""
    num_gpus: Optional[pulumi.Input[int]]
    """Number of GPUs to allocate for the container. (optional)"""
    service_port: pulumi.Input[int]
    """Port for the service."""

class CloudRunService(pulumi.ComponentResource):
    """
    Deploys Google Cloud Run Service with the specified container image and configuration.
    """
    uri: pulumi.Output[str]
    """URI for accessing the deployed Cloud Run service."""

    def __init__(
            self,
            name: str,
            args: CloudRunServiceArgs,
            opts: Optional[pulumi.ResourceOptions] = None
    ):

        super().__init__('cloudrun:index:CloudRunService', name, {}, opts)

        resource_group_name = args.get("resource_group_name")
        registry_login_server = args.get("registry_login_server")
        registry_username = args.get("registry_username")
        registry_password = args.get("registry_password")
        image_ref = args.get("image_ref")
        insights_sku = args.get("insights_sku") or "PerGB2018"
        app_ingress_port = args.get("app_ingress_port") or 80

        # Helper function to shorten service names
        def service_name_shortener(name):
            max_length = 50  # Cloud Run service name max length is 50 chars
            if len(name) <= max_length:
                return name
            truncated_name = name[:max_length]
            # Check if the last character is undesirable and adjust if needed
            while truncated_name and not truncated_name[-1].isalnum():
                truncated_name = truncated_name[:-1]
            return truncated_name


        # Build resource limits conditionally
        resource_limits = {
            "cpu": args.get("cpu"),
            "memory": args.get("memory"),
        }
        if args.get("num_gpus"):
            resource_limits["nvidia.com/gpu"] = args.get("num_gpus")

        # Build container configuration
        container_config = {
            "image": args.get("image"),
            "resources": {
                "cpuIdle": False,
                "limits": resource_limits,
                "startup_cpu_boost": True,
            },
            "ports": {
                "container_port": args.get("service_port"),
            },
            "startup_probe": {
                "initial_delay_seconds": 0,  # Increased to allow model download
                "timeout_seconds": 1,
                "period_seconds": 1,
                "failure_threshold": 360,  # 60 minutes max for model download
                "tcp_socket": {
                    "port": args.get("service_port"),
                },
            },
        }
        
        # Add volume mounts if bucket_name is provided
        if args.get("bucket_name"):
            container_config["volume_mounts"] = [{
                "name": args.get("bucket_name"),
                "mount_path": args.get("mount_path"), 
            }]

        # Add environment variables if provided
        if args.get("envs"):
            container_config["envs"] = args.get("envs")

        # Build template configuration
        template_config = {
            "containers": [container_config],
            "scaling": {      
                "max_instance_count": 3,
                "min_instance_count": 1,
            },
        }
        
        # Add node_selector if num_gpus is provided
        if args.get("num_gpus"):
            template_config["node_selector"] = {
                "accelerator": "nvidia-l4", 
            }
            template_config["gpu_zonal_redundancy_disabled"] = True
        
        # Add volumes if bucket_name is provided
        if args.get("bucket_name"):
            template_config["volumes"] = [{
                "name": "ollama-bucket",
                "gcs": {
                    "bucket": args.get("bucket_name"),
                    "read_only": False,
                },
            }]

        cr_service = cloudrun.Service(name,
            name=service_name_shortener(f"{name}-cr-service"),
            location=args.get("location"),
            deletion_protection= False,
            ingress="INGRESS_TRAFFIC_ALL",
            template=template_config,
            opts=pulumi.ResourceOptions(parent=self)
        )

        binding = cloudrun.ServiceIamBinding(f"{name}-cr-binding",
            name=cr_service,
            # location=gcp_region,
            role="roles/run.invoker",
            members=["allUsers"],
            opts=pulumi.ResourceOptions(parent=self, depends_on=[cr_service]),
        )

        self.uri = cr_service.uri

        self.register_outputs({})
