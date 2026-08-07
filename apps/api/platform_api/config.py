from __future__ import annotations

import os


def cube_api_url() -> str:
    return os.environ.get("CUBE_API_URL", "http://cube:4000/cubejs-api/v1")


def cube_api_secret() -> str:
    return os.environ.get("CUBE_API_SECRET", "cube-dev-secret-please-rotate")


def stac_api_url() -> str:
    return os.environ.get("STAC_API_URL", "http://stac-api:8080")


def keycloak_url() -> str:
    return os.environ.get("KEYCLOAK_URL", "http://keycloak:8083")


def keycloak_realm() -> str:
    return os.environ.get("KEYCLOAK_REALM", "geodata")


def keycloak_client_id() -> str:
    return os.environ.get("KEYCLOAK_CLIENT_ID", "platform-bff")


def keycloak_client_secret() -> str:
    return os.environ.get("KEYCLOAK_CLIENT_SECRET", "bff-dev-secret")


def keycloak_jwks_url() -> str:
    return f"{keycloak_url()}/realms/{keycloak_realm()}/protocol/openid-connect/certs"


def keycloak_issuer() -> str:
    return f"{keycloak_url()}/realms/{keycloak_realm()}"


def titiler_url() -> str:
    return os.environ.get("TITILER_URL", "http://titiler:80")


def seaweedfs_endpoint() -> str:
    return os.environ.get("SEAWEEDFS_ENDPOINT", "http://seaweedfs:8333")
