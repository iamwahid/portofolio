import pytest
from datetime import timedelta

from django.utils import timezone
from django.urls import reverse
from django.test.client import RequestFactory

from unittest import mock
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase

from .conftest import (
    CourseTeamFactory,
    _expected_team_detail_response_fields,
    _expected_team_list_response_fields,
    _expected_membership_list_response_fields,
    AUTH_KEYCLOAK,
    TEAM_MIXIN,
)

from common.djangoapps.util.testing import patch_sessions, patch_testcase

from plugin_api import settings
from plugin_api.teams.models import CourseTeamExtension
from plugin_api.teams.serializers import CourseTeamExtensionSerializer


# required to bypass auth middleware
patch_testcase()
patch_sessions()


class TeamTestCase(SharedModuleStoreTestCase):
    @pytest.fixture(autouse=True)
    def _conftest(self, team_api_test_data):
        team_api_test_data(self)


class TestTeamsListView(TeamTestCase):
    @pytest.mark.django_db
    def test_teams_list_by_topic_id(self):
        kwargs = {"course_id": self.course.id, "topic_id": self.topic_id}
        course_teams_url = reverse(
            "plugin_api:plugin_api.list_teams", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            response = self.client.get(course_teams_url)
            assert len(response.json()["data"]["results"]) == 1
            assert set(response.json()["data"]["results"][0].keys()) == set(
                _expected_team_list_response_fields
            )
            assert response.status_code == 200


class TestTeamsDetailView(TeamTestCase):
    @pytest.mark.django_db
    def test_teams_detail_by_topic_id(self):
        kwargs = {
            "course_id": self.course.id,
            "topic_id": self.topic_id,
            "team_id": self.course_team.team_id,
        }
        course_teams_url = reverse(
            "plugin_api:plugin_api.get_team_details", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            response = self.client.get(course_teams_url)
            assert set(response.json()["data"].keys()) == set(
                _expected_team_detail_response_fields
            )
            assert response.status_code == 200


class TestTeamsIsNewView(TeamTestCase):
    @pytest.mark.django_db
    def test_teams_list_by_topic_id(self):
        kwargs = {"course_id": self.course.id, "topic_id": self.topic_id}
        course_teams_url = reverse(
            "plugin_api:plugin_api.list_teams", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            # call first time to record last_visisted_teams_at
            response = self.client.get(course_teams_url)
            assert response.status_code == 200

            datenow = timezone.now() + timedelta(hours=1)
            with mock.patch("django.utils.timezone.now", return_value=datenow):
                # create team
                course_team = CourseTeamFactory.create(
                    name="Course team new",
                    course_id=self.course.id,
                    topic_id=self.topic_id,
                )

                # and check new team
                response = self.client.get(course_teams_url)
                assert response.status_code == 200
                data = response.json()["data"]["results"]
                assert len(data) == 2
                assert set(data[0].keys()) == set(_expected_team_list_response_fields)
                assert data[0]["is_new"] == False
                assert data[1]["is_new"] == True


class TeamEmojiTestCase(SharedModuleStoreTestCase):
    @pytest.fixture(autouse=True)
    def _conftest(self, team_emoji_api_test_data):
        team_emoji_api_test_data(self)


class TestTeamsListEmoji(TeamEmojiTestCase):
    @pytest.mark.django_db
    def test_teams_list_with_emoji(self):
        kwargs = {"course_id": self.course.id, "topic_id": self.topic_id}
        course_teams_url = reverse(
            "plugin_api:plugin_api.list_teams", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            response = self.client.get(course_teams_url)
            response_data = response.json()["data"]["results"][0]
            assert response.status_code == 200
            assert response_data["name"] == self.origin_name
            assert response_data["description"] == self.origin_description


class TestTeamDetailEmoji(TeamEmojiTestCase):
    @pytest.mark.django_db
    def test_team_detail_with_emoji(self):
        kwargs = {
            "course_id": self.course.id,
            "topic_id": self.topic_id,
            "team_id": self.course_team.team_id,
        }
        course_teams_url = reverse(
            "plugin_api:plugin_api.get_team_details", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            response = self.client.patch(
                course_teams_url, self.team_create_data, content_type="application/json"
            )
            print(response.json())
            response_data = response.json()["data"]
            assert response.status_code == 200
            assert response_data["name"] == self.origin_name
            assert response_data["description"] == self.origin_description


class TestTeamCreateEmoji(TeamEmojiTestCase):
    @pytest.mark.django_db
    def test_team_create_with_emoji(self):
        kwargs = {"course_id": self.course.id, "topic_id": self.topic_id}
        course_team_create_url = reverse(
            "plugin_api:plugin_api.list_teams", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)):
            response = self.client.post(
                course_team_create_url,
                self.team_create_data,
                content_type="application/json",
            )
            response_data = response.json()["data"]
            assert response.status_code == 200
            assert response_data["name"] == self.origin_name
            assert response_data["description"] == self.origin_description
            assert response_data["joined_team_info"]["name"] == self.origin_name


# My Team Test Case
class MembershipTestCase(SharedModuleStoreTestCase):
    @pytest.fixture(autouse=True)
    def _conftest(self, team_api_data, auth_client):
        for name, data in team_api_data.items():
            setattr(self, name, data)

        self.client = auth_client(self.user_data)
        # create course team with existing fixture
        course_team = CourseTeamFactory.create(
            name="Course one team", course_id=self.course.id, topic_id=self.topic_id
        )
        # add user to team members
        course_team.add_user(self.user)
        self.course_team = course_team
        # context mocking value
        self.context = {
            "request": self.request,
            "admin_token": "dummy_token",
            "token": "dummy_token",
            "course_id": self.course_id,
            "expand": ["team"],  # team field to expanded format
            "topic_id": self.topic_id,
            "enrollment": self.course_enrollment,
        }


class TestMembershipListView(MembershipTestCase):
    @pytest.mark.django_db
    def test_list_teams_user_joined(self):
        kwargs = {"course_id": self.course.id}
        membership_url = reverse(
            "plugin_api:plugin_api.list_teams_user_joined",
            kwargs=kwargs,
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            response = self.client.get(membership_url)
            assert response.status_code == 200
            assert len(response.json()["data"]["results"]) == 1
            assert set(response.json()["data"]["results"][0].keys()) == set(
                _expected_membership_list_response_fields
            )


# Team Image Test Cases
class TeamImageTestCase(SharedModuleStoreTestCase):
    @pytest.fixture(autouse=True)
    def _conftest(self, set_team_image_test_data):
        set_team_image_test_data(self)


class TestTeamImageInvalidCreate(TeamImageTestCase):
    @pytest.mark.django_db
    def test_invalid_image(self):
        kwargs = {"course_id": self.course.id, "topic_id": self.topic_id}
        course_team_create_url = reverse(
            "plugin_api:plugin_api.list_teams", kwargs=kwargs
        )
        expected_invalid_image = self.team_create_with_invalid_image["image"]
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)):
            response = self.client.post(
                course_team_create_url,
                self.team_create_with_invalid_image,
                content_type="application/json",
            )
            response_data = response.json()
            assert response.status_code == 400
            assert response_data == {
                "image": [
                    f"\"{expected_invalid_image}\" is not a valid choice."
                ]
            }


class TestTeamImageCreate(TeamImageTestCase):
    @pytest.mark.django_db
    def test_valid_image(self):
        kwargs = {"course_id": self.course.id, "topic_id": self.topic_id}
        course_team_create_url = reverse(
            "plugin_api:plugin_api.list_teams", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)):
            response = self.client.post(
                course_team_create_url,
                self.team_create_with_image,
                content_type="application/json",
            )
            response_data = response.json()["data"]
            assert response.status_code == 200
            assert "image" in response_data.keys()
            assert response_data["image"] == f'{settings.TEAM_IMAGE_PUBLIC_URL}{self.team_create_with_image["image"]}'


class TestTeamImageInvalidUpdate(TeamImageTestCase):
    @pytest.mark.django_db
    def test_invalid_image(self):
        kwargs = {
            "course_id": self.course.id,
            "topic_id": self.topic_id,
            "team_id": self.course_team.team_id,
        }
        course_teams_url = reverse(
            "plugin_api:plugin_api.get_team_details", kwargs=kwargs
        )
        expected_invalid_image = self.team_create_with_invalid_image["image"]
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            response = self.client.patch(
                course_teams_url,
                self.team_create_with_invalid_image,
                content_type="application/json",
            )
            response_data = response.json()
            assert response.status_code == 400
            assert response_data == {
                "image": [
                    f"\"{expected_invalid_image}\" is not a valid choice."
                ]
            }


class TestTeamImageUpdate(TeamImageTestCase):
    @pytest.mark.django_db
    def test_valid_image(self):
        kwargs = {
            "course_id": self.course.id,
            "topic_id": self.topic_id,
            "team_id": self.course_team.team_id,
        }
        course_teams_url = reverse(
            "plugin_api:plugin_api.get_team_details", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            response = self.client.patch(
                course_teams_url,
                self.team_create_with_image,
                content_type="application/json",
            )
            response_data = response.json()["data"]
            assert response.status_code == 200
            assert "image" in response_data.keys()
            assert response_data["image"] == f'{settings.TEAM_IMAGE_PUBLIC_URL}{self.team_create_with_image["image"]}'


class TestTeamCreateShouldHasValidCreator(TeamImageTestCase):
    @pytest.mark.django_db
    def test_valid_creator(self):
        kwargs = {"course_id": self.course.id, "topic_id": self.topic_id}
        course_team_create_url = reverse(
            "plugin_api:plugin_api.list_teams", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)):
            response = self.client.post(
                course_team_create_url,
                self.team_create_with_image,
                content_type="application/json",
            )
            assert response.status_code == 200
            response_data = response.json()["data"]
            
            team_extension = CourseTeamExtension.objects.filter(team__team_id=response_data['id']).first()
            assert team_extension.creator == self.user


class TeamNonPrivilegedTestCase(SharedModuleStoreTestCase):
    @pytest.fixture(autouse=True)
    def _conftest(self, auth_client, set_base_test_team_data_non_priviliged):
        set_base_test_team_data_non_priviliged(self)
        self.client = auth_client(self.user_data)
        _request = RequestFactory().request()
        _request.user = self.user
        self.request = _request

        self.context = {
            "request": _request,
            "admin_token": "dummy_token",
            "token": "dummy_token",
            "course_id": self.course_id_str,
            "topic_id": self.topic_id,
            "enrollment": self.enrollment,
        }


class TestTeamCreatorShouldAbleToUpdate(TeamNonPrivilegedTestCase):
    @pytest.mark.django_db
    def test_update_team(self):
        course_team = CourseTeamFactory.create(
            name="Course one team", course_id=self.course.id, topic_id=self.topic_id
        )
        # add Team Creator
        course_team.creator = self.user
        course_team.save()
        course_team.refresh_from_db()
        context = {'request': self.request, 'team_id': course_team.team_id, 'save_creator': True}
        team_extension_serializer = CourseTeamExtensionSerializer(data={'image': None}, context=context)
        team_extension_serializer.is_valid(raise_exception=True)
        team_extension = team_extension_serializer.save()

        kwargs = {"course_id": self.course.id, "topic_id": self.topic_id, "team_id": course_team.team_id}
        course_team_update_url = reverse(
            "plugin_api:plugin_api.get_team_details", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            response = self.client.patch(
                course_team_update_url,
                {
                    "name": "New Team Name",
                    "topic_id": self.topic_id,
                    "description": "New Team Description",
                    "country": "US",
                    "language": "en",
                },
                content_type="application/json",
            )
            assert response.status_code == 200
            assert response.json()['data']['can_edit_team'] == True


class TestTeamCreatorShouldHaveEditPermission(TeamNonPrivilegedTestCase):
    @pytest.mark.django_db
    def test_create_team(self):
        kwargs = {"course_id": self.course.id, "topic_id": self.topic_id}
        course_team_create_url = reverse(
            "plugin_api:plugin_api.list_teams", kwargs=kwargs
        )
        with mock.patch(AUTH_KEYCLOAK, return_value=(self.user, None)), mock.patch(
            TEAM_MIXIN, return_value=self.context
        ):
            response = self.client.post(
                course_team_create_url,
                {
                    "name": "New Team Name",
                    "topic_id": self.topic_id,
                    "description": "New Team Description",
                    "country": "US",
                    "language": "en",
                },
                content_type="application/json",
            )
            assert response.status_code == 200
            assert response.json()['data']['can_edit_team'] == True
