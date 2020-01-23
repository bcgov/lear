
app {
    name = 'bcros'
    ns = 'zcd4ou'
    hostname = 'pathfinder.gov.bc.ca'
    namespaces {
        'build'{
            namespace = "${app.ns}-tools"
            disposable = true
        }
        'dev' {
            namespace = "${app.ns}-dev"
            disposable = false
        }
        'e2e' {
            namespace = "${app.ns}-e2e"
            disposable = false
        }
        'test' {
            namespace = "${app.ns}-test"
            disposable = false
        }
    }

    git {
        workDir = ['git', 'rev-parse', '--show-toplevel'].execute().text.trim()
        uri = ['git', 'config', '--get', 'remote.origin.url'].execute().text.trim()
        commit = ['git', 'rev-parse', 'HEAD'].execute().text.trim()
        changeId = "${opt.'pr'}"
        ref = opt.'branch'?:"refs/pull/${git.changeId}/head"
    }

    url {
        api = "https://legal-api-${vars.deployment.env.name}.${app.hostname}/api/v1/businesses/"
        auth = "https://auth-${vars.deployment.env.name}.${app.hostname}/api/v1/"
        auth_api = "https://auth-api-${vars.deployment.env.name}.${app.hostname}/api/v1/entities/{identifier}/authorizations"
        pay_api = "https://pay-api-${vars.deployment.env.name}.${app.hostname}/api/v1/payment-requests"
        nats = "nats://nats-streaming--${vars.deployment.env.name}.${vars.deployment.namespace}.svc:4222"
        reports = "https://report-api-${vars.deployment.env.name}/api/vi/reports"
    }


    /**
     * Note:  This build section is required, even if we're not doing builds from this script
     */
    build {
        env {
            name = "build"
            id = "pr-1"
        }
        id = "${app.name}"
        name = "${app.name}"
        version = opt.pr ? "pr${opt.'pr'}" :  "dev"

        namespace = app.namespaces.'build'.namespace
        timeoutInSeconds = 60*20
        templates = [
/*                [
                    'file':'bc/legal-api.bc.json',
                    'params':[
                        'APP_NAME':             "bcros",
                        'COMP_NAME':            "legal-api",
                        'SUFFIX':               "${app.deployment.version}",
                        'GIT_REPO_URL':         "https://github.com/bsnopek-freshworks/lear.git",
                        'GIT_REF':              "master",
                        'SOURCE_NAMESPACE':     "gl2uos-tools",
                        'SOURCE_CONTEXT_DIR':   "/legal-api",
                        'SOURCE_IMAGE_KIND':    "ImageStreamTag",
                        'SOURCE_IMAGE_TAG':     "3.7",
                        'OUTPUT_IMAGE_TAG':     "${app.build.version}"
                    ]
                ],
                [
                    'file':'bc/entity-filer.bc.json',
                    'params':[
                        'APP_NAME':             "bcros",
                        'COMP_NAME':            "entity-filer",
                        'SUFFIX':               "${app.deployment.version}",
                        'GIT_REPO_URL':         "https://github.com/bsnopek-freshworks/lear.git",
                        'GIT_REF':              "master",
                        'SOURCE_NAMESPACE':     "gl2uos-tools",
                        'SOURCE_CONTEXT_DIR':   "queue_services/entity-filer",
                        'SOURCE_IMAGE_NAME':    "python",
                        'SOURCE_IMAGE_KIND':    "ImageStreamTag",
                        'SOURCE_IMAGE_TAG':     "3.7",
                        'OUTPUT_IMAGE_TAG':     "${app.build.version}"
                    ]
                ],
                [
                    'file':'bc/entity-pay.bc.json',
                    'params':[
                        'APP_NAME':             "bcros",
                        'COMP_NAME':            "entity-pay",
                        'SUFFIX':               "${app.deployment.version}",
                        'GIT_REPO_URL':         "https://github.com/bsnopek-freshworks/lear.git",
                        'GIT_REF':              "master",
                        'SOURCE_NAMESPACE':     "gl2uos-tools",
                        'SOURCE_CONTEXT_DIR':   "queue_services/entity-pay",
                        'SOURCE_IMAGE_NAME':    "python",
                        'SOURCE_IMAGE_KIND':    "ImageStreamTag",
                        'SOURCE_IMAGE_TAG':     "3.7",
                        'OUTPUT_IMAGE_TAG':     "${app.build.version}"
                    ]
                ]
        ]
*/
                [
                    'file':'bc/future-effective-filings.bc.json',
                    'params':[
                        'APP_NAME':             "bcros",
                        'COMP_NAME':            "future-effective-filings",
                        'SUFFIX':               "${app.deployment.version}",
                        'GIT_REPO_URL':         "https://github.com/bsnopek-freshworks/lear.git",
                        'GIT_REF':              "master",
                        'SOURCE_NAMESPACE':     "gl2uos-tools",
                        'SOURCE_CONTEXT_DIR':   "jobs/future-effective-filings",
                        'SOURCE_IMAGE_NAME':    "python",
                        'SOURCE_IMAGE_KIND':    "ImageStreamTag",
                        'SOURCE_IMAGE_TAG':     "3.7",
                        'OUTPUT_IMAGE_TAG':     "${app.build.version}"
                    ]
                ]
        ]

    }

    deployment {
        env {
            name = vars.deployment.env.name
            id = vars.deployment.env.id
        }

        version = opt.pr ? "pr${opt.'pr'}" :  opt.env
        id = "${app.name}-${app.deployment.version}"
        name = "${app.name}-${app.suffix}"

        namespace = "${vars.deployment.namespace}"
        timeoutInSeconds = 60*20
        templates = [
                [
                    'file':'_coops-ui.dc.json',
                    'params':[
                        'APP_NAME':             "bcros",
                        'COMP_NAME':            "coops-ui",
                        'SUFFIX':               "${app.deployment.version}",
                        'APP_NAMESPACE':        "${vars.deployment.namespace}",
                        'WEB_APP_CONTEXT_PATH': "cooperatives",
                        'VUE_APP_API_URL':      "${app.url.api}",
                        'VUE_APP_AUTH_URL':     "${app.url.auth}",
                        'VUE_APP_AUTH_API_URL': "${app.url.auth_api}",
                        'VUE_APP_PAY_API_URL':  "${app.url.pay_api}",
                        'VUE_APP_ADDRESS_COMPLETE_KEY':   "RZ86-BB54-CM96-EE26",
                        'PORT':             2015,
                        'CPU_REQUEST':      "${vars.resources.frontend.cpu_request}",
                        'CPU_LIMIT':        "${vars.resources.frontend.cpu_limit}",
                        'MEMORY_REQUEST':   "${vars.resources.frontend.memory_request}",
                        'MEMORY_LIMIT':     "${vars.resources.frontend.memory_limit}",
                        'REPLICA_MIN':      "${vars.resources.frontend.replica_min}",
                        'REPLICA_MAX':      "${vars.resources.frontend.replica_max}",
                    ]
                ],
                [
                    'file':'_legal-api.dc.json',
                    'params':[
                        'APP_NAME':             "bcros",
                        'COMP_NAME':            "legal-api",
                        'SUFFIX':               "${app.deployment.version}",
                        'DB_SECRET_ADMIN':      'lear-db-admin',
                        'DB_SECRET_ACCESS':     'lear-db-access',
                        'APP_NAMESPACE':        "${vars.deployment.namespace}",
                        'IMAGE_NAMESPACE':      "${vars.deployment.namespace}",
                        'GO_LIVE_DATE':         "2019-08-02",
                        'SENTRY_DSN':           "",
                        'DATABASE_HOST':        "postgresdb-dev-tmp",
                        'DATABASE_NAME':        "lear-${app.deployment.version}",
                        'DATABASE_PORT':        "5444",
                        'DATABASE_TEST_HOST':   "postgresdb-dev-tmp",
                        'DATABASE_TEST_NAME':   "lear_testdb-${app.deployment.version}",
                        'DATABASE_TEST_PASSWORD':"",
                        'DATABASE_TEST_PORT':   "5444",
                        'DATABASE_TEST_USERNAME':"tester",
                        'PAYMENT_SVC_URL':      "${app.url.pay_api}",
                        'AUTH_SVC_URL':         "${app.url.auth_api}",
                        'REPORT_SVC_URL':       "${app.url.reports}",
                        'JWT_OIDC_ALGORITHMS':  "RS256",
                        'JWT_OIDC_AUDIENCE':    "sbc-auth-web",
                        'JWT_OIDC_CLIENT_SECRET':       "aeb2b9bc-672b-4574-8bc8-e76e853c37cbt",
                        'JWT_OIDC_WELL_KNOWN_CONFIG':   "https://sso-dev.pathfinder.gov.bc.ca/auth/realms/fcf0kpqr/.well-known/openid-configuration",
                        'JWT_OIDC_JWKS_CACHE_TIMEOUT':  "300",
                        'JWT_OIDC_CACHING_ENABLED':     "True",
                        'NATS_SERVERS':         "${app.url.nats}",
                        'NATS_CLIENT_NAME':     "entity.filing.payment.worker",
                        'NATS_CLUSTER_ID':      "test-cluster",
                        'NATS_SUBJECT':         "entity.filing.payment",
                        'NATS_QUEUE':           "filing-worker",
                        'CPU_REQUEST':      "${vars.resources.api.cpu_request}",
                        'CPU_LIMIT':        "${vars.resources.api.cpu_limit}",
                        'MEMORY_REQUEST':   "${vars.resources.api.memory_request}",
                        'MEMORY_LIMIT':     "${vars.resources.api.memory_limit}",
                        'REPLICA_MIN':      "${vars.resources.api.replica_min}",
                        'REPLICA_MAX':      "${vars.resources.api.replica_max}"
                    ]
                ],
                [
                    'file':'_entity-filer.dc.json',
                    'params':[
                            'APP_NAME':         "bcros",
                            'COMP_NAME':        "entity-filer",
                            'SUFFIX':           "${app.deployment.version}",
                            'APP_FILE':         "filer_service.py",
                            'APP_NAMESPACE':        "${vars.deployment.namespace}",
                            'IMAGE_NAMESPACE':      "${vars.deployment.namespace}",
                            'DB_SECRET_ACCESS':     'lear-db-access',
                            'DATABASE_HOST':        "postgresdb-dev-tmp",
                            'DATABASE_NAME':        "lear-${app.deployment.version}",
                            'DATABASE_PORT':        "5444",
                            'SENTRY_DSN':           "",
                            'NATS_SERVERS':     "${app.url.nats}",
                            'NATS_CLUSTER_ID':  "test-cluster",
                            'NATS_CLIENT_NAME': "entity.filing.filer.worker",
                            'NATS_SUBJECT':     "entity.filing.filer",
                            'NATS_FILER_SUBJECT':"entity.filing.filer",
                            'NATS_QUEUE':       "filing-worker",
                            'CPU_REQUEST':      "${vars.resources.filer.cpu_request}",
                            'CPU_LIMIT':        "${vars.resources.filer.cpu_limit}",
                            'MEMORY_REQUEST':   "${vars.resources.filer.memory_request}",
                            'MEMORY_LIMIT':     "${vars.resources.filer.memory_limit}",
                            'REPLICA_MIN':      "${vars.resources.filer.replica_min}",
                            'REPLICA_MAX':      "${vars.resources.filer.replica_max}",
                    ]
                ],
                [
                    'file':'_entity-pay.dc.json',
                    'params':[
                            'APP_NAME':         "bcros",
                            'COMP_NAME':        "entity-pay",
                            'SUFFIX':           "${app.deployment.version}",
                            'APP_FILE':         "pay_filer.py",
                            'APP_NAMESPACE':        "${vars.deployment.namespace}",
                            'IMAGE_NAMESPACE':      "${vars.deployment.namespace}",
                            'DB_SECRET_ACCESS':     'lear-db-access',
                            'DATABASE_HOST':        "postgresdb-dev-tmp",
                            'DATABASE_NAME':        "lear-${app.deployment.version}",
                            'DATABASE_PORT':        "5444",
                            'SENTRY_DSN':           "",
                            'NATS_SERVERS':     "${app.url.nats}",
                            'NATS_CLUSTER_ID':  "test-cluster",
                            'NATS_CLIENT_NAME': "entity.filing.payment.worker",
                            'NATS_SUBJECT':     "entity.filing.payment",
                            'NATS_FILER_SUBJECT':"entity.filing.filer",
                            'NATS_QUEUE':       "filing-worker",
                            'CPU_REQUEST':      "${vars.resources.pay.cpu_request}",
                            'CPU_LIMIT':        "${vars.resources.pay.cpu_limit}",
                            'MEMORY_REQUEST':   "${vars.resources.pay.memory_request}",
                            'MEMORY_LIMIT':     "${vars.resources.pay.memory_limit}",
                            'REPLICA_MIN':      "${vars.resources.pay.replica_min}",
                            'REPLICA_MAX':      "${vars.resources.pay.replica_max}",
                    ]
                ],
                [
                    'file':'_nats-streaming.dc.json',
                    'params':[
                            'APP_NAME':         "bcros",
                            'COMP_NAME':        "nats-streaming",
                            'SUFFIX':           "${app.deployment.version}",
                            'CPU_REQUEST':      "${vars.resources.nats.cpu_request}",
                            'CPU_LIMIT':        "${vars.resources.nats.cpu_limit}",
                            'MEMORY_REQUEST':   "${vars.resources.nats.memory_request}",
                            'MEMORY_LIMIT':     "${vars.resources.nats.memory_limit}",
                            'REPLICA_MIN':      "${vars.resources.nats.replica_min}",
                            'REPLICA_MAX':      "${vars.resources.nats.replica_max}"
                    ]
                ],
                [
                    'file':'_future-effective-filings-cron.dc.json',
                    'params':[
                            'APP_NAME':         "bcros",
                            'COMP_NAME':        "future-effective-filings",
                            'SUFFIX':           "${app.deployment.version}",
                            'AUTH_URL':         "${app.url.auth}",
                            'SENTRY_DSN':       "",
                            'CPU_REQUEST':      "${vars.resources.future-effective.cpu_request}",
                            'CPU_LIMIT':        "${vars.resources.future-effective.cpu_limit}",
                            'MEMORY_REQUEST':   "${vars.resources.future-effective.memory_request}",
                            'MEMORY_LIMIT':     "${vars.resources.future-effective.memory_limit}",
                            'REPLICA_MIN':      "${vars.resources.future-effective.replica_min}",
                            'REPLICA_MAX':      "${vars.resources.future-effective.replica_max}"
                    ]
                ]
        ]
    }
}

environments {
    'dev' {
        vars {
            DB_PVC_SIZE = '1Gi'
            deployment {
                env {
                    name ="dev"
                    id = "pr-1"
                }
                id = "${app.name}-dev"
                name = "${app.name}"
                namespace = app.namespaces[env.name].namespace
            }
            resources {
              frontend {
                  cpu_request = "100m"
                  cpu_limit = "250m"
                  memory_request = "512Mi"
                  memory_limit = "750Mi"
                  replica_min = 1
                  replica_max = 1
              }
              api {
                  cpu_request = "100m"
                  cpu_limit = "750m"
                  memory_request = "100Mi"
                  memory_limit = "4Gi"
                  replica_min = 1
                  replica_max = 1
              }
              postgres {
                  cpu_request = "50m"
                  cpu_limit = "100m"
                  memory_request = "256Mi"
                  memory_limit = "512Mi"
              }
              filer {
                  cpu_request = "100m"
                  cpu_limit = "750m"
                  memory_request = "100Mi"
                  memory_limit = "2Gi"
                  replica_min = 1
                  replica_max = 1
              }
              pay {
                  cpu_request = "100m"
                  cpu_limit = "750m"
                  memory_request = "100Mi"
                  memory_limit = "2Gi"
                  replica_min = 1
                  replica_max = 1
              }
              nats  {
                  cpu_request = "100m"
                  cpu_limit = "250m"
                  memory_request = "256Mi"
                  memory_limit = "1Gi"
                  replica_min = 1
                  replica_max = 1
              }
              future-effective  {
                  cpu_request = "100m"
                  cpu_limit = "250m"
                  memory_request = "256Mi"
                  memory_limit = "1Gi"
                  replica_min = 1
                  replica_max = 1
              }
            }
        }
    }
}