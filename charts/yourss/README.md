# yourss Helm chart

Deploys [YouRSS](https://github.com/essembeh/YouRSS), an alternative front-end to Youtube built
on its RSS feeds: a single stateless `Deployment` with a `Service`, an optional `Ingress`, an
optional `HorizontalPodAutoscaler` and a `Secret` holding the pages and users when some are declared.

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
| `yourss.cacheEnabled` | `true` | `YOURSS_CACHE_ENABLED` |
| `yourss.cacheFolder` | `""` | `YOURSS_CACHE_FOLDER`, only set when not empty |
| `yourss.cacheRssTtl` | `PT30M` | `YOURSS_CACHE_RSS_TTL` |
| `yourss.cacheRssFallbackTtl` | `PT48H` | `YOURSS_CACHE_RSS_FALLBACK_TTL` |
| `yourss.cacheMetadataTtl` | `P7D` | `YOURSS_CACHE_METADATA_TTL` |
| `yourss.warmupInterval` | `""` | `YOURSS_WARMUP_INTERVAL`, see below |
| `yourss.pages` | `[]` | `YOURSS_USERS_FILE`, see below |
| `yourss.users` | `[]` | `YOURSS_USERS_FILE`, see below |
| `yourss.extraEnv` | `[]` | any other variable, as a list of `name` / `value` |

### Cache

On by default. Each pod keeps on disk the RSS feeds and the metadata of the channels (name,
avatar, handle to id resolution):

- a feed younger than `cacheRssTtl` is served without asking Youtube;
- when the fetch fails (Youtube answers `404` for a while every day, errors, timeouts), a feed
  younger than `cacheRssFallbackTtl` is served instead of the error. `cacheRssFallbackTtl` must be
  at least `cacheRssTtl`;
- the name and avatar of a channel are served without scraping its page for `cacheMetadataTtl`,
  and whatever their age when the scrape fails.

With `cacheEnabled: false` nothing is cached: every page load fetches its feeds and scrapes a
1 MB page per channel. The pods share nothing, each one has its own cache. With `cacheFolder`
empty the files go to a temporary folder under `/tmp`, an `emptyDir` that disappears with the
pod. The root filesystem is read-only, so a custom `cacheFolder` must live under `/tmp` or on a
volume added with `volumes` and `volumeMounts`; the pod refuses to start when it cannot write
there.

Durations are ISO-8601 (`PT30M`, `PT48H`) or a number of seconds.

### Warmup

`yourss.warmupInterval` (an ISO-8601 duration like `PT1H`, or seconds) makes the application
refresh the feeds of every page in the background: a first round at startup, then one per
interval, so that the feeds and the channel metadata are on disk when a visitor comes, and still
served from the fallback cache during Youtube's bad hours. A round only refreshes what is older
than `cacheRssTtl`. It asks Youtube whether anyone visits or not, which is why it is off by default.
Each pod refreshes its own cache; the failures are in the application logs.

### Pages and users

`yourss.pages` declares the pages served at `/p/<name>`, and `yourss.users` the users which
aggregate them into folders (`/u/<user>/<page>`). Both are rendered to a `Secret`, since a user
may hold a password, and mounted read-only on `/yourss/users.yaml`; the application reads the
file on every request, an update needs no restart.

```yaml
yourss:
  pages:
    - name: fun
      channels:
        - "@jonnygiger"
        - UCVooVnzQxPSTXTMzSi1s6uw
    - name: cards
      visible: false # only through the users holding it
      channels:
        - UCQsmxaMzYr76Yd1iqMEq8TA
  users:
    - name: alice
      password:
        method: argon2 # or clear
        value: "$argon2i$v=19$m=4096,t=3,p=1$..."
      pages:
        - name: fun
        - name: cards
          label: Card magic
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
