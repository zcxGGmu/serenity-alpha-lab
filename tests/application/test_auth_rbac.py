from __future__ import annotations

import json

from serenity_alpha_lab.application.auth_rbac import (
    AUTH_RBAC_CONTRACT_VERSION,
    ApiAuthorizationRequirement,
    AuthMode,
    AuthPermission,
    AuthRole,
    AuthSubject,
    AuthorizationIssueCode,
    AuthorizationStatus,
    OidcClaimMapping,
    OidcProviderConfig,
    RbacPolicy,
    ResourceScope,
    default_api_authorization_catalog,
)


def test_desktop_mode_grants_local_owner_without_oidc_or_team_setup() -> None:
    policy = RbacPolicy.default(AuthMode.DESKTOP)
    subject = AuthSubject.local_desktop_owner()
    resource = ResourceScope(
        tenant_id=subject.tenant_id,
        team_id=None,
        owner_user_id=subject.subject_id,
        resource_kind="report",
    )

    assert policy.mode is AuthMode.DESKTOP
    assert policy.oidc_required is False
    assert AuthRole.LOCAL_OWNER in subject.roles

    for permission in (
        AuthPermission.CONFIG_WRITE,
        AuthPermission.USER_ADMIN,
        AuthPermission.DATASET_WRITE,
        AuthPermission.EVIDENCE_WRITE,
        AuthPermission.REPORT_WRITE,
        AuthPermission.RUN_CREATE,
        AuthPermission.RUN_CANCEL,
        AuthPermission.ARTIFACT_DOWNLOAD,
        AuthPermission.AUDIT_READ,
    ):
        decision = policy.authorize(subject, permission, resource)
        assert decision.status is AuthorizationStatus.ALLOWED
        assert decision.allowed is True
        assert AuthRole.LOCAL_OWNER in decision.matched_roles

    serialized_subject = json.dumps(subject.to_record(), sort_keys=True)
    assert "token" not in serialized_subject.lower()
    assert "password" not in serialized_subject.lower()
    assert "secret" not in serialized_subject.lower()


def test_team_mode_separates_data_run_config_and_admin_permissions() -> None:
    policy = RbacPolicy.default(AuthMode.TEAM)
    resource = ResourceScope(tenant_id="tenant-a", team_id="team-alpha", resource_kind="dataset")
    data_steward = AuthSubject(
        subject_id="user-data",
        tenant_id="tenant-a",
        team_ids=("team-alpha",),
        roles=(AuthRole.DATA_STEWARD,),
        mode=AuthMode.TEAM,
    )
    run_operator = AuthSubject(
        subject_id="user-run",
        tenant_id="tenant-a",
        team_ids=("team-alpha",),
        roles=(AuthRole.RUN_OPERATOR,),
        mode=AuthMode.TEAM,
    )
    config_admin = AuthSubject(
        subject_id="user-config",
        tenant_id="tenant-a",
        team_ids=("team-alpha",),
        roles=(AuthRole.CONFIG_ADMIN,),
        mode=AuthMode.TEAM,
    )
    admin = AuthSubject(
        subject_id="user-admin",
        tenant_id="tenant-a",
        team_ids=("team-alpha",),
        roles=(AuthRole.ADMIN,),
        mode=AuthMode.TEAM,
    )

    assert policy.authorize(data_steward, AuthPermission.DATASET_WRITE, resource).allowed
    assert policy.authorize(data_steward, AuthPermission.EVIDENCE_WRITE, resource).allowed
    assert not policy.authorize(data_steward, AuthPermission.RUN_CREATE, resource).allowed
    assert not policy.authorize(data_steward, AuthPermission.CONFIG_WRITE, resource).allowed
    assert not policy.authorize(data_steward, AuthPermission.USER_ADMIN, resource).allowed

    assert policy.authorize(run_operator, AuthPermission.RUN_CREATE, resource).allowed
    assert policy.authorize(run_operator, AuthPermission.RUN_CANCEL, resource).allowed
    assert not policy.authorize(run_operator, AuthPermission.DATASET_WRITE, resource).allowed
    assert not policy.authorize(run_operator, AuthPermission.CONFIG_WRITE, resource).allowed
    assert not policy.authorize(run_operator, AuthPermission.USER_ADMIN, resource).allowed

    assert policy.authorize(config_admin, AuthPermission.CONFIG_READ, resource).allowed
    assert policy.authorize(config_admin, AuthPermission.CONFIG_WRITE, resource).allowed
    assert not policy.authorize(config_admin, AuthPermission.RUN_CREATE, resource).allowed
    assert not policy.authorize(config_admin, AuthPermission.DATASET_WRITE, resource).allowed
    assert not policy.authorize(config_admin, AuthPermission.USER_ADMIN, resource).allowed

    for permission in (
        AuthPermission.DATASET_WRITE,
        AuthPermission.RUN_CREATE,
        AuthPermission.CONFIG_WRITE,
        AuthPermission.USER_ADMIN,
        AuthPermission.AUDIT_READ,
    ):
        assert policy.authorize(admin, permission, resource).allowed

    mismatch = ResourceScope(tenant_id="tenant-b", team_id="team-alpha", resource_kind="dataset")
    mismatch_decision = policy.authorize(run_operator, AuthPermission.RUN_READ, mismatch)
    assert mismatch_decision.status is AuthorizationStatus.DENIED
    assert mismatch_decision.issue_code is AuthorizationIssueCode.TENANT_SCOPE_MISMATCH

    wrong_team = ResourceScope(tenant_id="tenant-a", team_id="team-beta", resource_kind="dataset")
    team_decision = policy.authorize(run_operator, AuthPermission.RUN_READ, wrong_team)
    assert team_decision.status is AuthorizationStatus.DENIED
    assert team_decision.issue_code is AuthorizationIssueCode.TEAM_SCOPE_MISMATCH


def test_oidc_mapping_is_optional_and_maps_claims_without_network_validation() -> None:
    provider = OidcProviderConfig(
        provider_id="corp-oidc",
        issuer="https://idp.example.com",
        client_id="serenity-web",
        audience="serenity-api",
        client_secret_ref="secret://oidc/client",
        enabled=True,
    )
    mapping = OidcClaimMapping(
        tenant_id="tenant-a",
        subject_claim="sub",
        email_claim="email",
        display_name_claim="name",
        roles_claim="roles",
        teams_claim="teams",
        role_aliases={
            "serenity_admin": AuthRole.ADMIN,
            "run_operator": AuthRole.RUN_OPERATOR,
        },
    )

    subject = mapping.map_claims(
        {
            "sub": "oidc-user-1",
            "email": "analyst@example.com",
            "name": "Analyst One",
            "roles": ["run_operator", "unknown-role"],
            "teams": ["team-alpha", "team-beta"],
        },
        provider_id=provider.provider_id,
    )

    assert subject.subject_id == "oidc:corp-oidc:oidc-user-1"
    assert subject.tenant_id == "tenant-a"
    assert subject.team_ids == ("team-alpha", "team-beta")
    assert subject.roles == (AuthRole.RUN_OPERATOR,)
    assert subject.identity_provider == "corp-oidc"
    assert subject.email == "analyst@example.com"
    assert subject.display_name == "Analyst One"

    team_policy = RbacPolicy.default(AuthMode.TEAM)
    resource = ResourceScope(tenant_id="tenant-a", team_id="team-alpha", resource_kind="screen_run")
    assert team_policy.authorize(subject, AuthPermission.RUN_CREATE, resource).allowed
    assert not team_policy.authorize(subject, AuthPermission.CONFIG_WRITE, resource).allowed

    provider_record = provider.to_record()
    assert provider_record["client_secret_configured"] is True
    assert "secret://oidc/client" not in json.dumps(provider_record, sort_keys=True)


def test_api_authorization_catalog_declares_required_permissions_for_p6_surfaces() -> None:
    catalog = default_api_authorization_catalog()
    by_key = {(requirement.method, requirement.path): requirement for requirement in catalog}

    assert all(isinstance(item, ApiAuthorizationRequirement) for item in catalog)
    assert all(item.required_permissions for item in catalog)
    assert all("/api/v1/backtest/" not in item.path for item in catalog)
    assert all("sender" not in item.operation_id.lower() for item in catalog)

    assert _requires(by_key[("POST", "/api/v1/auth/settings")], AuthPermission.USER_ADMIN)
    assert _requires(by_key[("POST", "/api/v1/quant/factor-definitions")], AuthPermission.DEFINITION_WRITE)
    assert _requires(by_key[("POST", "/api/v1/quant/screen-runs")], AuthPermission.RUN_CREATE)
    assert _requires(by_key[("GET", "/api/v1/quant/screen-runs/{run_id}")], AuthPermission.RUN_READ)
    assert _requires(by_key[("POST", "/api/v1/quant/backtest-runs")], AuthPermission.RUN_CREATE)
    assert _requires(
        by_key[("GET", "/api/v1/quant/backtest-runs/{run_id}/artifacts/{artifact_kind}")],
        AuthPermission.ARTIFACT_DOWNLOAD,
    )
    assert _requires(by_key[("GET", "/api/v1/research/evidence/{evidence_id}")], AuthPermission.EVIDENCE_READ)
    assert _requires(by_key[("POST", "/api/v1/research/evidence")], AuthPermission.EVIDENCE_WRITE)
    assert _requires(by_key[("GET", "/api/v1/research/reports/{report_id}")], AuthPermission.REPORT_READ)
    assert _requires(
        by_key[("GET", "/api/v1/research/reports/{report_id}/notifications")],
        AuthPermission.NOTIFICATION_OUTBOX_READ,
    )

    serialized = json.dumps([item.to_record() for item in catalog], ensure_ascii=False, sort_keys=True)
    assert AUTH_RBAC_CONTRACT_VERSION in serialized


def test_rbac_records_are_deterministic_and_do_not_contain_secrets() -> None:
    provider = OidcProviderConfig(
        provider_id="corp-oidc",
        issuer="https://idp.example.com",
        client_id="serenity-web",
        audience="serenity-api",
        client_secret_ref="super-secret-client-value",
    )
    policy = RbacPolicy.default(AuthMode.TEAM)
    subject = AuthSubject(
        subject_id="user-a",
        tenant_id="tenant-a",
        team_ids=("team-alpha",),
        roles=(AuthRole.VIEWER,),
        mode=AuthMode.TEAM,
        email="viewer@example.com",
    )

    assert json.dumps(policy.to_record(), sort_keys=True) == json.dumps(policy.to_record(), sort_keys=True)
    assert json.dumps(subject.to_record(), sort_keys=True) == json.dumps(subject.to_record(), sort_keys=True)

    combined = json.dumps(
        {
            "provider": provider.to_record(),
            "policy": policy.to_record(),
            "subject": subject.to_record(),
        },
        sort_keys=True,
    )
    assert "super-secret-client-value" not in combined
    assert "password" not in combined.lower()
    assert "token" not in combined.lower()


def _requires(requirement: ApiAuthorizationRequirement, permission: AuthPermission) -> bool:
    return permission in requirement.required_permissions
