# component-cloudrun-service

Abstraction for resources needed when using Google Cloud Run.

This repo delivers a component to abstract the details related to:
- Creating a Google Cloud Run Service

# Inputs

* resource_group_name: The resource group in which the image registry should be deployed.
* app_path: Path to the Dockerfile to build the app.
* image_tag (Optional): Image tag to use. Default: latest
* platform (Optional): The platform for the image. Default: linux/amd64
* insights_sku (Optional): Sku for the insights workspace. Default: PerGB2018
* app_ingress_port (Optional): Ingress port for the app. Default: 80

# Outputs

* container_app_fqdn: The DNS name for the container app.

