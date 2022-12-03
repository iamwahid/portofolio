import pytest

from django.urls import reverse, resolve
from plugin_api.teams import utils
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase

from .conftest import CourseTeamFactory, CourseEnrollment

from plugin_api.teams.utils import (
    get_team_context,
    get_context_data,
    get_request_with_data,
)


@pytest.mark.django_db
def test_get_team_context(team_context, team_name_emoji_fx, team_description_emoji_fx):
    response = get_team_context(
        data=team_context,
        user=None,
        params={"course_id": "course-v1:TEST+CS101+2022_T1", "topic_id": "1"},
    )
    assert response.get("name") == team_name_emoji_fx
    assert response.get("description") == team_description_emoji_fx


@pytest.mark.django_db
def test_get_context_data(team_context, team_name_emoji_fx, team_description_emoji_fx):
    response = get_context_data(team=team_context, username=None)
    assert response.get("name") == team_name_emoji_fx
    assert response.get("description") == team_description_emoji_fx


@pytest.mark.django_db
def test_get_request_with_data(
    request_fx, team_create_data, team_name_ascii_fx, team_description_ascii_fx
):
    # create new object
    class Object(object):
        pass

    self = Object()
    self.kwargs = {}

    request = request_fx
    request.data = team_create_data
    response = get_request_with_data(self, request)
    assert response.data["name"] == team_name_ascii_fx
    assert response.data["description"] == team_description_ascii_fx


class TeamUtilTestCase(SharedModuleStoreTestCase):
    @pytest.fixture(autouse=True)
    def _conftest(self, set_test_team_data_non_priviliged):
        set_test_team_data_non_priviliged(self)


class TeamUtilTopicContextUserHasJoined(TeamUtilTestCase):
    @pytest.mark.django_db
    def test_should_cannot_create_team(self):
        self.course_team.add_user(self.user)
        self.user.refresh_from_db()

        expected = {
            'id': self.topic_id,
            'name': self.topic_data['name'],
            'description': self.topic_data['description'],
            'team_count': self.topic_data['team_count'],
            'max_team_size': self.topic_data['max_team_size'],
            'has_joined_teamset': True,
            'is_restricted': True,
            'can_create_team': False,
        }
        result = utils.get_topic_context(self.topic_data, False, self.user, str(self.course.id))
        assert result == expected


class TeamUtilTopicContextUserNotJoined(TeamUtilTestCase):
    @pytest.mark.django_db
    def test_should_allow_to_create_team(self):
        expected = {
            'id': self.topic_id,
            'name': self.topic_data['name'],
            'description': self.topic_data['description'],
            'team_count': self.topic_data['team_count'],
            'max_team_size': self.topic_data['max_team_size'],
            'has_joined_teamset': False,
            'is_restricted': True,
            'can_create_team': True,
        }
        result = utils.get_topic_context(self.topic_data, False, self.user, str(self.course.id))
        assert result == expected


@pytest.mark.parametrize("parameters,expected", [
    (({"type": "open"}, False, False), True), 
    (({"type": "open"}, False, True), False),
    (({"type": "open"}, True, False), True),
    (({"type": "open"}, True, True), True),
    (({"type": "public_managed"}, False, False), False), 
    (({"type": "public_managed"}, False, True), False),
    (({"type": "public_managed"}, True, False), True),
    (({"type": "public_managed"}, True, True), True),
    (({"type": "private_managed"}, False, False), False), 
    (({"type": "private_managed"}, False, True), False),
    (({"type": "private_managed"}, True, False), True),
    (({"type": "private_managed"}, True, True), True),
])
def test_user_can_create_team_should_have_proper_result(parameters, expected):
    """
    | Topic Type       | Privileged | Joined a Team | Expected |
    |==================|============|===============|==========|
    | open             | false      | false         | true     |
    | open             | false      | true          | false    |
    | open             | true       | false         | true     |
    | open             | true       | true          | true     |
    | public_managed   | false      | false         | false    |
    | public_managed   | false      | true          | false    |
    | public_managed   | true       | false         | true     |
    | public_managed   | true       | true          | true     |
    | private_managed  | false      | false         | false    |
    | private_managed  | false      | true          | false    |
    | private_managed  | true       | false         | true     |
    | private_managed  | true       | true          | true     |
    """
    has_permission = bool(utils.user_can_create_team(*parameters))
    assert has_permission == expected
