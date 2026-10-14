# yourss Helm chart

Deploys [YouRSS](https://github.com/essembeh/YouRSS), an alternative front-end to Youtube built
on its RSS feeds: a single stateless `Deployment` with a `Service`, an optional `Ingress`, an
optional `HorizontalPodAutoscaler` and a `Secret` holding the user pages when some are declared.

```sh
helm repo add yourss https://essembeh.github.io/YouRSS/
helm show values yourss/yourss > myvalues.yaml
helm install my-yourss yourss/yourss -f myvalues.yaml
kubectl port-forward service/my-yourss 8000:http
```

The chart version follows the application version: `appVersion` is the default image tag.

## Application values

Each value under `yourss` maps to one `YOURSS_*` environment variable and has the same default as
the application. The meaning of each setting is documented in the
[configuration table of the main README](https://github.com/essembeh/YouRSS#%EF%B8%8F-configuration).

| Value | Default | Variable |
| --- | --- | --- |
| `yourss.image.repository` | `ghcr.io/essembeh/yourss` | |
| `yourss.image.tag` | `appVersion` of the chart | |
| `yourss.image.pullPolicy` | `IfNotPresent` | |
| `yourss.timezone` | `Europe/Paris` | `TZ` |
| `yourss.logLevel` | `INFO` | `LOGURU_LEVEL` |
| `yourss.customPagesEnabled` | `true` | `YOURSS_CUSTOM_PAGES_ENABLED` |
| `yourss.maxPageItems` | `12` | `YOURSS_MAX_PAGE_ITEMS` |
| `yourss.apiDocsEnabled` | `false` | `YOURSS_API_DOCS_ENABLED` |
| `yourss.cleanTitles` | `false` | `YOURSS_CLEAN_TITLES` |
| `yourss.cacheEnabled` | `false` | `YOURSS_CACHE_ENABLED` |
| `yourss.cacheFolder` | `""` | `YOURSS_CACHE_FOLDER`, only set when not empty |
| `yourss.cacheTtl` | `PT30M` | `YOURSS_CACHE_TTL` |
| `yourss.cacheFallbackTtl` | `PT48H` | `YOURSS_CACHE_FALLBACK_TTL` |
| `yourss.channelCacheTtl` | `PT1H` | `YOURSS_CHANNEL_CACHE_TTL` |
| `yourss.users` | `[]` | `YOURSS_USERS_FILE`, see below |
| `yourss.extraEnv` | `[]` | any other variable, as a list of `name` / `value` |

### RSS cache

Off by default: every page load fetches its feeds from Youtube. With `cacheEnabled: true`, each
pod keeps the feeds on disk:

- a feed younger than `cacheTtl` is served without asking Youtube;
- when the fetch fails (Youtube answers `404` for a while every day, errors, timeouts), a feed
  younger than `cacheFallbackTtl` is served instead of the error. `cacheFallbackTtl` must be at
  least `cacheTtl`.

The pods share nothing, each one has its own cache. With `cacheFolder` empty the feeds go to a
temporary folder under `/tmp`, an `emptyDir` that disappears with the pod. The root filesystem is
read-only, so a custom `cacheFolder` must live under `/tmp` or on a volume added with `volumes`
and `volumeMounts`.

Durations are ISO-8601 (`PT30M`, `PT48H`) or a number of seconds.

### User pages

`yourss.users` declares the pages served at `/u/<name>`. The list is rendered to a `Secret`,
since a page may hold a password, and mounted read-only on `/yourss/users.yaml`.

```yaml
yourss:
  users:
    - name: demo
      channels:
        - "@jonnygiger"
        - UCVooVnzQxPSTXTMzSi1s6uw
    - name: alice
      password:
        method: argon2 # or clear
        value: "$argon2i$v=19$m=4096,t=3,p=1$..."
      channels:
        - "@berrics"
```

A channel is a channel id (`UC…`) or a handle (`@…`), a playlist is its id (`PL…`).

## Kubernetes values

| Value | Default | Notes |
| --- | --- | --- |
| `replicaCount` | `1` | ignored when autoscaling is on |
| `imagePullSecrets` | `[]` | |
| `nameOverride`, `fullnameOverride` | `""` | |
| `serviceAccount.create` | `false` | the application never talks to the Kubernetes API |
| `serviceAccount.automount` | `false` | |
| `podAnnotations`, `podLabels` | `{}` | |
| `podSecurityContext` | non-root uid 10001, `RuntimeDefault` seccomp | |
| `securityContext` | read-only root filesystem, no capabilities, no privilege escalation | the image only writes to `/tmp` |
| `service.type` | `ClusterIP` | |
| `service.port` | `8000` | |
| `ingress.enabled` | `false` | `className`, `annotations`, `hosts`, `tls` as usual |
| `resources.requests` | `50m` CPU, `256Mi` memory | the CPU request is required by the HPA |
| `resources.limits` | `512Mi` memory, no CPU limit | the application is I/O-bound and bursty |
| `autoscaling.enabled` | `false` | `minReplicas` 1, `maxReplicas` 3, `targetCPUUtilizationPercentage` 80 |
| `volumes`, `volumeMounts` | `[]` | extra volumes, for example a persistent cache folder |
| `nodeSelector`, `tolerations`, `affinity` | `{}` / `[]` | |
