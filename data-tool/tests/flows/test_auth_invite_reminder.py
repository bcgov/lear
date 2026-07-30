import importlib
import json
import sys
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


FLOWS_PATH = Path(__file__).resolve().parents[2] / 'flows'
sys.path.insert(0, str(FLOWS_PATH))

from auth.auth_create_flow import _build_auth_create_plan  # noqa: E402
from auth.auth_invite_flow import _build_auth_invite_plan  # noqa: E402
from auth.auth_models import AuthCreatePlan  # noqa: E402
from auth.auth_tasks import perform_auth_create_for_corp  # noqa: E402
from common.auth_service import AuthService  # noqa: E402


@pytest.fixture
def config():
    return SimpleNamespace(
        AUTH_SVC_URL='https://auth.example',
        ACCOUNT_SVC_TIMEOUT=17,
        USE_CUSTOM_CONTACT_EMAIL=False,
    )


def test_config_boolean_defaults_false_and_parses_true(monkeypatch):
    import config as config_module

    with monkeypatch.context() as env:
        env.delenv('AUTH_INVITE_IS_REMINDER', raising=False)
        config_module = importlib.reload(config_module)
        assert config_module._Config.AUTH_INVITE_IS_REMINDER is False

        env.setenv('AUTH_INVITE_IS_REMINDER', 'true')
        config_module = importlib.reload(config_module)
        assert config_module._Config.AUTH_INVITE_IS_REMINDER is True

    importlib.reload(config_module)


def test_auth_create_plan_reminder_defaults_false():
    assert AuthCreatePlan().invite_is_reminder is False


@pytest.mark.parametrize('builder', [_build_auth_create_plan, _build_auth_invite_plan])
@pytest.mark.parametrize(('configured_value', 'expected'), [(None, False), (False, False), (True, True)])
def test_flow_plan_builders_propagate_reminder_config(builder, configured_value, expected):
    config = SimpleNamespace()
    if configured_value is not None:
        config.AUTH_INVITE_IS_REMINDER = configured_value

    assert builder(config).invite_is_reminder is expected


@pytest.mark.parametrize(('configured_value', 'expected'), [(None, False), (False, False), (True, True)])
def test_auth_create_plan_builder_preserves_invite_send_config(configured_value, expected):
    config = SimpleNamespace()
    if configured_value is not None:
        config.AUTH_SEND_UNAFFILIATED_EMAIL = configured_value

    assert _build_auth_create_plan(config).send_unaffiliated_invite is expected


@pytest.mark.parametrize('configured_value', [None, False, True])
def test_auth_invite_plan_builder_always_sends_invite(configured_value):
    config = SimpleNamespace()
    if configured_value is not None:
        config.AUTH_SEND_UNAFFILIATED_EMAIL = configured_value

    assert _build_auth_invite_plan(config).send_unaffiliated_invite is True


@pytest.mark.parametrize('explicit_false', [False, True])
def test_service_omitted_or_false_sends_empty_body_without_params(monkeypatch, config, explicit_false):
    response = SimpleNamespace(status_code=HTTPStatus.CREATED)
    post = Mock(return_value=response)
    monkeypatch.setattr('common.auth_service.requests.post', post)

    kwargs = {'token': 'token'}
    if explicit_false:
        kwargs['is_reminder'] = False

    status = AuthService.send_unaffiliated_email(config, 'BC123', 'user@example.com', **kwargs)

    assert status == HTTPStatus.OK
    post.assert_called_once_with(
        url='https://auth.example/affiliationInvitations/unaffiliated/BC123',
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer token'},
        data=json.dumps({}),
        timeout=17,
    )


def test_service_true_sends_exact_reminder_body_without_params(monkeypatch, config):
    response = SimpleNamespace(status_code=HTTPStatus.OK)
    post = Mock(return_value=response)
    monkeypatch.setattr('common.auth_service.requests.post', post)

    status = AuthService.send_unaffiliated_email(
        config,
        'BC123',
        'user@example.com',
        token='token',
        is_reminder=True,
    )

    assert status == HTTPStatus.OK
    post.assert_called_once_with(
        url='https://auth.example/affiliationInvitations/unaffiliated/BC123',
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer token'},
        data=json.dumps({'isReminder': True}),
        timeout=17,
    )


@pytest.mark.parametrize(
    ('response_code', 'expected_status'),
    [(HTTPStatus.BAD_REQUEST, HTTPStatus.BAD_REQUEST), (599, HTTPStatus.BAD_REQUEST)],
)
def test_service_reminder_preserves_non_success_status_mapping(
    monkeypatch, config, response_code, expected_status
):
    response = SimpleNamespace(status_code=response_code)
    post = Mock(return_value=response)
    monkeypatch.setattr('common.auth_service.requests.post', post)

    status = AuthService.send_unaffiliated_email(
        config,
        'BC123',
        'user@example.com',
        token='token',
        is_reminder=True,
    )

    assert status == expected_status
    assert post.call_args.kwargs['data'] == json.dumps({'isReminder': True})
    assert 'params' not in post.call_args.kwargs


def test_service_without_token_never_posts(monkeypatch, config):
    post = Mock()
    monkeypatch.setattr('common.auth_service.requests.post', post)
    monkeypatch.setattr(AuthService, 'get_bearer_token', Mock(return_value=None))

    status = AuthService.send_unaffiliated_email(
        config,
        'BC123',
        'user@example.com',
        is_reminder=True,
    )

    assert status == HTTPStatus.UNAUTHORIZED
    post.assert_not_called()


@pytest.mark.parametrize('is_reminder', [False, True])
def test_task_passes_reminder_and_reports_detail(monkeypatch, config, is_reminder):
    send = Mock(return_value=HTTPStatus.OK)
    monkeypatch.setattr(AuthService, 'send_unaffiliated_email', send)
    plan = AuthCreatePlan(
        create_entity=False,
        send_unaffiliated_invite=True,
        invite_is_reminder=is_reminder,
    )

    result = perform_auth_create_for_corp.fn(
        config,
        'BC123',
        {'identifier': 'BC123', 'admin_email': 'user@example.com'},
        [],
        plan,
        'token',
    )

    send.assert_called_once_with(
        config=config,
        identifier='BC123',
        email='user@example.com',
        token='token',
        is_reminder=is_reminder,
    )
    assert ('invite:reminder' in result['action_detail']) is is_reminder


@pytest.mark.parametrize(
    ('profile', 'plan'),
    [
        (
            {'identifier': 'BC123', 'admin_email': 'user@example.com'},
            AuthCreatePlan(
                create_entity=False,
                send_unaffiliated_invite=True,
                invite_is_reminder=True,
                dry_run=True,
            ),
        ),
        (
            {'identifier': 'BC123'},
            AuthCreatePlan(
                create_entity=False,
                send_unaffiliated_invite=True,
                invite_is_reminder=True,
            ),
        ),
    ],
)
def test_task_dry_run_and_missing_email_do_not_call_service(monkeypatch, config, profile, plan):
    send = Mock()
    monkeypatch.setattr(AuthService, 'send_unaffiliated_email', send)

    perform_auth_create_for_corp.fn(config, 'BC123', profile, [], plan, 'token')

    send.assert_not_called()
