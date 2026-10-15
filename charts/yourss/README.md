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
| `yourss.cacheEnabled` | `true` | `YOURSS_CACHE_ENABLED` |
| `yourss.cacheFolder` | `""` | `YOURSS_CACHE_FOLDER`, only set when not empty |
| `yourss.cacheRssTtl` | `PT30M` | `YOURSS_CACHE_RSS_TTL` |
| `yourss.cacheRssFallbackTtl` | `PT48H` | `YOURSS_CACHE_RSS_FALLBACK_TTL` |
| `yourss.cacheMetadataTtl` | `PT24H` | `YOURSS_CACHE_METADATA_TTL` |
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

`warmup.enabled: true` adds a `CronJob` that loads every user page (`/u/<name>`) on
`warmup.schedule` (hourly by default, in `yourss.timezone`), so that the feeds and the channel
metadata are already on disk when a visitor comes. A run refreshes what is older than
`cacheRssTtl`: a schedule shorter than that TTL does nothing, a longer one leaves the feeds cold
between their expiry and the next run. The job asks Youtube whether anyone visits or not, which
is why it is off by default.

`warmup.users` restricts the job to some user names, every user is loaded when it is empty. The
job sends a clear password as a visitor would, through a curl config file stored in a `Secret`.
A page whose user has an argon2 password cannot be loaded: it is skipped and the install notes
list it, unless it is named in `warmup.users`, which is an error. The job fails when a page could not be loaded (pod unreachable, wrong password,
timeout), after trying all of them; a page whose feeds failed on Youtube's side still answers
200, those errors are in the application logs. It needs `yourss.users` and `cacheEnabled`:
nothing is rendered otherwise.

With several replicas each pod has its own cache and the job only reaches one of them.

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
| `warmup.enabled` | `false` | a `CronJob` loading every user page, see Warmup above |
| `warmup.schedule` | `0 * * * *` | cron expression, in `yourss.timezone` |
| `warmup.users` | `[]` | names of the users to warm up, every user when empty |
| `warmup.timeout` | `120` | seconds given to each page |
| `warmup.image` | `curlimages/curl:8.23.0` | `repository`, `tag`, `pullPolicy` |
| `warmup.resources` | `10m` CPU, `32Mi` / `64Mi` memory | |
| `volumes`, `volumeMounts` | `[]` | extra volumes, for example a persistent cache folder |
| `nodeSelector`, `tolerations`, `affinity` | `{}` / `[]` | |
