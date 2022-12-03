import pytest
from datetime import timedelta
from django.conf import settings
from unittest import mock

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from lms.djangoapps.teams.models import CourseTeam, CourseTeamMembership
from common.djangoapps.student.models import CourseEnrollment
from lms.djangoapps.teams.tests.factories import (
    CourseTeamFactory,
    CourseTeamMembershipFactory,
)

# test reqs
from opaque_keys.edx.keys import CourseKey
from xmodule.modulestore.tests.factories import CourseFactory
from common.djangoapps.student.tests.factories import UserFactory

from pytest_factoryboy import register
from openedx.core.lib.teams_config import TeamsConfig
from common.djangoapps.course_modes.models import CourseMode

from django.test.client import RequestFactory
from openedx.core.djangoapps.django_comment_common.utils import seed_permissions_roles


User = get_user_model()

AUTH_KEYCLOAK = "plugin_api.auth.KeycloakAuthentication.authenticate"
TEAM_MIXIN = "plugin_api.teams.mixins.TeamsContextView.get_serializer_context"

register(CourseFactory)
register(UserFactory)
register(CourseTeamFactory)
register(CourseTeamMembershipFactory)

_expected_team_detail_response_fields = [
    "id",
    "discussion_topic_id",
    "name",
    "topic_id",
    "description",
    "country",
    "language",
    "last_activity_at",
    "capacity",
    "members",
    "member_count",
    "joined_team_info",
    "unread_post_count",
    "is_new",
    "image",
    "can_edit_team",
    "creator",
]

_expected_team_list_response_fields = [
    "id",
    "discussion_topic_id",
    "name",
    "topic_id",
    "description",
    "country",
    "language",
    "last_activity_at",
    "capacity",
    "members",
    "member_count",
    "is_joined",
    "unread_post_count",
    "is_new",
    "image",
    "can_edit_team",
    "creator",
]

_expected_team_serializer_fields = [
    "id",
    "discussion_topic_id",
    "name",
    "course_id",
    "topic_id",
    "date_created",
    "description",
    "country",
    "language",
    "last_activity_at",
    "membership",
    "organization_protected",
    "max_team_size",
    "members",
    "unread_post_count",
    "is_new",
    "image",
    "creator",
]

_expected_membership_list_response_fields = [
    "id",
    "topic_id",
    "discussion_topic_id",
    "name",
    "description",
    "language",
    "member_count",
    "country",
    "capacity",
    "unread_post_count",
    "members",
    "last_activity_at",
]

_expected_membership_in_team_serializer_fields = [
    "username",
    "profile_image_url",
    "last_activity_at",
    "date_joined",
    "is_current_user",
]

_expected_membership_serializer_fields = [
    "user",
    "team",
    "date_joined",
    "last_activity_at",
]

_expected_team_fields_in_membership_serializer_fields = _expected_team_serializer_fields

_expected_team_creator_serializer_fields = ["is_current_user", "profile_image_url", "username"]


@pytest.fixture(scope="session")
def django_db_setup():
    """
    This is the top-level fixture that ensures that the test databases are created and available.
    This fixture is session scoped (it will be run once per test session) and is responsible for making
    sure the test database is available for tests that need it.

    https://pytest-django.readthedocs.io/en/latest/database.html?highlight=django_db_setup#django-db-setup
    """
    pass


@pytest.fixture
def auth_client():
    def _f(user_data) -> APIClient:
        client = APIClient()
        client.login(password=user_data["password"], username=user_data["username"])
        return client

    return _f


@pytest.fixture
def course_id_str_fx() -> str:
    return "course-v1:course+team+2"


@pytest.fixture
def course_id_fx(course_id_str_fx: str) -> CourseKey:
    return CourseKey.from_string(course_id_str_fx)


@pytest.fixture
def user_data_fx() -> User:
    return {
        "username": "user",
        "email": "user@test.com",
        "password": "password",
        "first_name": "Test",
        "last_name": "User",
        "is_active": True,
        "is_superuser": True,
        "is_staff": True,
    }


@pytest.fixture
def user_fx(user_data_fx) -> User:
    return UserFactory.create(**user_data_fx)

@pytest.fixture
def non_privileged_user_fx(user_data_fx) -> User:
    del user_data_fx["is_superuser"]
    del user_data_fx["is_staff"]
    return UserFactory.create(**user_data_fx)

@pytest.fixture
def request_fx(user_fx, **request):
    "Construct a generic request object."
    request = RequestFactory().request(**request)
    request.user = user_fx
    return request


@pytest.fixture
def topic_id_fx() -> str:
    return "the-teamset"


@pytest.fixture
def teams_config_fx(topic_id_fx) -> TeamsConfig:
    return TeamsConfig(
        {
            "topics": [
                {
                    "name": "Sustainability in Corporations",
                    "description": "Description for Sustainability in Corporations",
                    "id": topic_id_fx,
                    "max_team_size": 30,
                }
            ]
        }
    )


@pytest.fixture
def team_name() -> str:
    return "team 1"


@pytest.fixture
def team_id() -> str:
    return "team-1"


@pytest.fixture
def course_fx(course_id_fx: CourseKey, teams_config_fx: TeamsConfig):
    course = CourseFactory.create(
        teams_configuration=teams_config_fx,
        org=course_id_fx.org,
        course=course_id_fx.course,
        run=course_id_fx.run,
    )
    return course


@pytest.fixture
def course_enrollment_fx(user_fx, course_fx, course_id_str_fx) -> CourseEnrollment:
    return CourseEnrollment.enroll(
        user_fx, course_fx.id, check_access=True, mode=CourseMode.MASTERS
    )


@pytest.fixture
def course_team_fx(
    topic_id_fx, team_name, course_fx, course_id_str_fx, user_fx, course_enrollment_fx
) -> CourseTeam:
    data = {
        "name": team_name,
        "course_id": course_id_str_fx,
        "description": "description",
        "topic_id": topic_id_fx,
        "country": "",
        "language": "",
        "organization_protected": False,
    }
    course_team = CourseTeamFactory.create(**data)
    return course_team


@pytest.fixture
def seed_course_permissions(course_fx):
    return seed_permissions_roles(course_fx.id)


@pytest.fixture
def team_api_data(
    request_fx,
    course_fx,
    course_enrollment_fx,
    course_id_str_fx,
    user_fx,
    topic_id_fx,
    user_data_fx,
    seed_course_permissions,
    team_id,
):
    return {
        "request": request_fx,
        "course": course_fx,
        "course_id": course_id_str_fx,
        "topic_id": topic_id_fx,
        "user": user_fx,
        "user_data": user_data_fx,
        "course_enrollment": course_enrollment_fx,
        "team_id": team_id,
    }


def pytest_configure():
    """
    To configure test data required by test runtime
    """

    settings.COMMON_TEST_DATA_ROOT = settings.COMMON_ROOT / "test" / "data"
    settings.REST_FRAMEWORK["DATETIME_FORMAT"] = "%Y-%m-%dT%H:%M:%S.%fZ"


@pytest.fixture
def team_name_emoji_fx() -> str:
    return "⬆️ team 1 ✅"


@pytest.fixture
def team_description_emoji_fx() -> str:
    return "✅ desc ✅"


@pytest.fixture
def team_name_ascii_fx() -> str:
    return r"\u2b06\ufe0f team 1 \u2705"


@pytest.fixture
def team_description_ascii_fx() -> str:
    return r"\u2705 desc \u2705"


@pytest.fixture
def team_create_data(
    team_name_emoji_fx, team_description_emoji_fx, topic_id_fx, course_id_fx
):
    return {
        "name": team_name_emoji_fx,
        "topic_id": topic_id_fx,
        "description": team_description_emoji_fx,
        "country": "ID",
        "language": "id",
        "organization_protected": True,
    }


# Team Image Fixtures
@pytest.fixture
def team_description_fx() -> str:
    return "Team number #1"


@pytest.fixture
def team_create_data_for_image(
    team_name: str, team_description_fx: str, topic_id_fx: str, course_id_fx: CourseKey
):
    return {
        "name": team_name,
        "topic_id": topic_id_fx,
        "description": team_description_fx,
        "country": "ID",
        "language": "id",
        "organization_protected": True,
    }


@pytest.fixture
def team_image() -> str:
    return "smiling-face-with-smiling-eyes.png"


@pytest.fixture
def team_image_invalid() -> str:
    return "smiling-non-exist.png"


@pytest.fixture
def team_create_with_image(team_create_data_for_image, team_image):
    _create_data = team_create_data_for_image.copy()
    _create_data.update({"image": team_image})
    return _create_data


@pytest.fixture
def team_create_with_invalid_image(team_create_data_for_image, team_image_invalid):
    _create_data = team_create_data_for_image.copy()
    _create_data.update({"image": team_image_invalid})
    return _create_data


@pytest.fixture
def set_team_base_test_data(team_api_data, auth_client):
    def _f(self):
        for name, data in team_api_data.items():
            setattr(self, name, data)
        self.client = auth_client(self.user_data)
        # context mocking value
        self.context = {
            "request": self.request,
            "admin_token": "dummy_token",
            "token": "dummy_token",
            "course_id": self.course_id,
            "topic_id": self.topic_id,
            "enrollment": self.course_enrollment,
        }

    return _f


@pytest.fixture
def set_team_image_test_data(
    set_team_base_test_data,
    team_name,
    team_description_fx,
    team_create_with_image,
    team_create_with_invalid_image,
):
    def _f(self):
        set_team_base_test_data(self)
        # create course team with existing fixture
        course_team = CourseTeamFactory.create(
            name=team_name,
            description=team_description_fx,
            course_id=self.course.id,
            topic_id=self.topic_id,
        )
        # add user to team members
        course_team.add_user(self.user)
        self.course_team = course_team
        # team data post
        self.team_create_with_image = team_create_with_image
        self.team_create_with_invalid_image = team_create_with_invalid_image

    return _f


# Fixture for Class TestCase Based
@pytest.fixture
def team_api_test_data(set_team_base_test_data):
    def _f(self):
        set_team_base_test_data(self)
        # create course team with existing fixture
        course_team = CourseTeamFactory.create(
            name="Course one team", course_id=self.course.id, topic_id=self.topic_id
        )
        # add user to team members
        self.user_membership = course_team.add_user(self.user)
        self.course_team = course_team

    return _f


@pytest.fixture
def team_emoji_api_test_data(
    set_team_base_test_data,
    team_name_ascii_fx,
    team_description_ascii_fx,
    team_name_emoji_fx,
    team_description_emoji_fx,
    team_create_data,
):
    def _f(self):
        set_team_base_test_data(self)
        # origin name and description
        self.origin_name = team_name_emoji_fx
        self.origin_description = team_description_emoji_fx
        # team data post
        self.team_create_data = team_create_data
        # course team with emoji name and description
        course_team = CourseTeamFactory.create(
            name=team_name_ascii_fx,
            description=team_description_ascii_fx,
            course_id=self.course.id,
            topic_id=self.topic_id,
        )
        # delete previous membership
        if hasattr(self, 'membership') and self.user_membership.user == self.user:
            self.user_membership.delete()
            self.course_team.delete()
        # add user to team members
        self.user_membership = course_team.add_user(self.user)
        self.course_team = course_team

    return _f


# Utils Fixtures
@pytest.fixture
def team_context(team_name_ascii_fx: str, team_description_ascii_fx: str):
    return {
        "id": "1",
        "topic_id": "1",
        "discussion_topic_id": "1",
        "name": team_name_ascii_fx,
        "image": None,
        "description": team_description_ascii_fx,
        "language": "en",
        "membership": [],
        "country": "",
        "max_team_size": 20,
        "members": [],
        "unread_post_count": 0,
        "last_activity_at": "2022-06-23T14:26:15.000Z",
    }


@pytest.fixture
def topic_data(topic_id_fx):
    return {
        'description': 'test-description',
        'name': 'empty-topic',
        'id': topic_id_fx,
        'type': 'open',
        'max_team_size': 20,
        'team_count': 2,
    }


@pytest.fixture
def set_base_test_team_data_non_priviliged(topic_data, course_id_str_fx, user_data_fx, topic_id_fx, course_fx, teams_config_fx, non_privileged_user_fx):
    def _f(self):
        self.user = non_privileged_user_fx
        self.user_data = user_data_fx
        self.course = course_fx
        self.course_id_str = course_id_str_fx
        self.topic_data = topic_data
        self.topic_id = topic_id_fx
        self.enrollment = CourseEnrollment.enroll(
            self.user, self.course.id, check_access=False
        )
    return _f


@pytest.fixture
def set_test_team_data_non_priviliged(set_base_test_team_data_non_priviliged):
    def _f(self):
        set_base_test_team_data_non_priviliged(self)
        self.course_team = CourseTeamFactory.create(
            name="Course one team", course_id=self.course.id, topic_id=self.topic_id
        )
    return _f
