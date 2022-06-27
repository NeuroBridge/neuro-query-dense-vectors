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
