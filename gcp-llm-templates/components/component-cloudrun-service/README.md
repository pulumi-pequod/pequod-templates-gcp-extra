# component-cloudrun-service

Abstraction for resources needed when using Google Cloud Run.

This repo delivers a component to abstract the details related to:
- Creating a Google Cloud Run Service

# Usage
## Specify Package in `Pulumi.yaml`

Add the following to your `Pulumi.yaml` file:
Note: If no version is specified, the latest version will be used.

```
packages:
  cloudrun-service: https://github.com/pulumi-pequod/pequod-templates-gcp-extra/gcp-cloudrun-llm-py/components/component-cloudrun-service[@vX.Y.Z]

``` 

## Use SDK in Program

### Python
```
import pulumi_pequod_cloudrunservice as cloudrunservice

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
```

### Typescript
```
import * as cloudrunservice from "@pulumi-pequod/cloudrun-service";

const ollamaService = new cloudrunservice.CloudRunService(`ollama-${baseName}`, {
  location: gcpRegion,
  image: ollamaImage,
  cpu: llmCpu,
  memory: llmMemory,
  numGpus: llmNumGpus,
  servicePort: 11434,
  bucketName: llmBucket.name,
  mountPath: "/root/.ollama/",
});
```

### Dotnet
```
using PulumiPequod.CloudrunService;

var ollamaService = new CloudRunService($"ollama-{baseName}", new CloudRunServiceArgs
{
    Location = gcpRegion,
    Image = ollamaImage,
    Cpu = llmCpu,
    Memory = llmMemory,
    NumGpus = llmNumGpus,
    ServicePort = 11434,
    BucketName = llmBucket.Name,
    MountPath = "/root/.ollama/",
});
```

### YAML
```
  ollamaService:
    type: cloudrun:index:CloudRunService
    properties:
      location: ${gcpRegion}
      image: ${ollamaImage}
      cpu: ${llmCpu}
      memory: ${llmMemory}
      numGpus: ${llmNumGpus}
      servicePort: 11434
      bucketName: ${llmBucket.name}
      mountPath: /root/.ollama/
```



