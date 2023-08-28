# neuro-query-dense-vectors
To hold the code that maps between the NeuroBridge ontology and the neuro-query terms


## Helm Instructions

This repo contains a Helm chart in the "neurobridges-chart" folder, which installs the neuroquery Flask app alongside [Elasticsearch 7](https://github.com/elastic/helm-charts/tree/main/elasticsearch) in any Kubernetes cluster.

To install the helm chart in Sterling:

```bash
helm install neurobridges neurobridges-chart -n neurobridges -f sterling_values.yaml
```

To upgrade the helm chart once already installed:

```bash
helm upgrade neurobridges neurobridges-chart -n neurobridges -f sterling_values.yaml
```

To view the rendered manifests (without installing):

```bash
helm template neurobridges-chart -n neurobridges -f sterling_values.yaml | less
```

I recommend installing the [helm diff](https://github.com/databus23/helm-diff) plugin, which helps make upgrades less scary since you know exactly what will change.

### `neurobridges-query` deployment `/healthz` endpoint timeout

The deployments have startup/liveness probes which hit the /healthz endpoint on a specified port. We had an incident on 8-28-23 after a power loss when all the pods were restarting. The `neurobridges-query` deployment was unresponsive and the liveness probe was producing an error. The issue was fixed by uninstalling the `neurobridges` release and reinstalling. Be aware it may take some time for the container to properly deploy and accept requests.
