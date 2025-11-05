from pulumi.provider.experimental import component_provider_host

from cloudRunService import CloudRunService # Deploy to CloudRun

if __name__ == "__main__":
    component_provider_host(name="cloudrunservice", components=[ CloudRunService ])
