import pytest
import os
import shutil

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files import File
from django.conf import settings

from rest_framework import exceptions

from lms.djangoapps.teams.models import CourseTeam, CourseTeamMembership
from plugin_api.teams.serializers import (
    ExtendedCourseTeamSerializer,
    ExtendedMembershipSerializer,
    TeamCreatorSerializer,
    TeamDiscussionFileUploadSerializer,
)
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from .conftest import (
    CourseTeamMembershipFactory,
    _expected_team_serializer_fields,
    _expected_membership_serializer_fields,
    _expected_membership_in_team_serializer_fields,
    _expected_team_fields_in_membership_serializer_fields,
    _expected_team_creator_serializer_fields,
)
from unittest import mock


DIR_PATH = os.path.dirname(os.path.realpath(__file__))
TEST_MAX_UPLOAD_FILE_SIZE = 1024


class SerializerTestCase(SharedModuleStoreTestCase):
    @pytest.fixture(autouse=True)
    def _conftest(
        self,
        request_fx,
        course_team_fx,
        course_id_str_fx,
        user_fx,
        topic_id_fx,
        course_enrollment_fx,
    ):
        self._course_team = course_team_fx
        self._team_membership = CourseTeamMembershipFactory.create(
            team=self._course_team, user=user_fx
        )
        self._user = user_fx
        self._context = {
            "request": request_fx,
            "admin_token": "dummy_token",
            "token": "dummy_token",
            "course_id": course_id_str_fx,
            "expand": ["team"],  # team field to expanded format
            "topic_id": topic_id_fx,
            "enrollment": course_enrollment_fx,
        }


class TestCourseTeamSerializer(SerializerTestCase):
    @pytest.mark.django_db
    def test_contains_expected_fields(self):
        serializer = ExtendedCourseTeamSerializer(
            self._course_team, context=self._context
        )
        data = serializer.data

        assert set(data.keys()) == set(_expected_team_serializer_fields)
        assert len(data["members"]) == 1
        assert set(data["members"][0].keys()) == set(
            _expected_membership_in_team_serializer_fields
        )


class TestMembershipSerializer(SerializerTestCase):
    @pytest.mark.django_db
    def test_contains_expected_fields(self):
        serializer = ExtendedMembershipSerializer(
            self._team_membership, context=self._context
        )
        data = serializer.data

        assert set(data.keys()) == set(_expected_membership_serializer_fields)
        assert set(data["team"].keys()) == set(
            _expected_team_fields_in_membership_serializer_fields
        )


class TestTeamCreatorSerializer(SerializerTestCase):
    @pytest.mark.django_db
    def test_contains_expected_fields(self):
        serializer = TeamCreatorSerializer(instance=self._user, context=self._context)
        data = serializer.data

        assert set(data.keys()) == set(_expected_team_creator_serializer_fields)


class TeamDiscussionFileTestCase(SharedModuleStoreTestCase):
    @pytest.fixture(autouse=True)
    def _conftest(
        self,
        request_fx,
        course_id_str_fx,
        user_fx,
        topic_id_fx,
    ):
        self._user = user_fx
        self.team_id = "dummy-team-1"

        image_file = File(open(DIR_PATH + "/data/unnamed.jpeg", "rb"))
        self.image_upload_file = SimpleUploadedFile(
            "unnamed.jpeg", image_file.read(), content_type="multipart/form-data"
        )
        self.expected_image_filename = f"{self.team_id}/team_file_123456.jpeg"

        attachment_file = File(open(DIR_PATH + "/data/testfile.txt", "rb"))
        self.attachment_upload_file = SimpleUploadedFile(
            "testfile.txt", attachment_file.read(), content_type="multipart/form-data"
        )
        self.expected_attachment_filename = f"{self.team_id}/team_file_123456.txt"

        invalid_file = File(open(DIR_PATH + "/data/unnamed.jp", "rb"))
        self.invalid_upload_file = SimpleUploadedFile(
            "unnamed.jp", invalid_file.read(), content_type="multipart/form-data"
        )

        self._context = {
            "request": request_fx,
            "admin_token": "dummy_token",
            "token": "dummy_token",
            "course_id": course_id_str_fx,
            "expand": ["team"],  # team field to expanded format
            "topic_id": topic_id_fx,
        }

    def tearDown(self):
        if os.path.exists(settings.MEDIA_ROOT + self.team_id):
            shutil.rmtree(settings.MEDIA_ROOT + self.team_id)


@mock.patch(
    "plugin_api.teams.serializers.TeamDiscussionFileUploadSerializer._generate_filename",
    return_value="team_file_123456",
)
class TestTeamDiscussionFileUploadSerializer(TeamDiscussionFileTestCase):
    def test_valid_image(self, mock):
        # Arrange
        self._context["request"].FILES["upload_file"] = self.image_upload_file
        data = {
            "team_id": self.team_id,
            "upload_type": "image",
            "upload_file": self.image_upload_file,
        }

        # Act
        serializer = TeamDiscussionFileUploadSerializer(
            data=data, context=self._context
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Assert
        assert serializer.data == {
            "original_filename": "unnamed.jpeg",
            "stored_filename": self.expected_image_filename,
            "upload_type": "image",
            "url": f"/media/{self.expected_image_filename}",
        }

    def test_valid_attachment(self, mock):
        # Arrange
        self._context["request"].FILES["upload_file"] = self.attachment_upload_file
        data = {
            "team_id": self.team_id,
            "upload_type": "attachment",
            "upload_file": self.attachment_upload_file,
        }

        # Act
        serializer = TeamDiscussionFileUploadSerializer(
            data=data, context=self._context
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Assert
        assert serializer.data == {
            "original_filename": "testfile.txt",
            "stored_filename": self.expected_attachment_filename,
            "upload_type": "attachment",
            "url": f"/media/{self.expected_attachment_filename}",
        }

    def test_invalid_image_extension(self, mock):
        # Arrange
        self._context["request"].FILES["upload_file"] = self.invalid_upload_file
        data = {
            "team_id": self.team_id,
            "upload_type": "image",
            "upload_file": self.invalid_upload_file,
        }

        # Act
        serializer = TeamDiscussionFileUploadSerializer(
            data=data, context=self._context
        )

        # Assert
        with pytest.raises(exceptions.PermissionDenied) as e_info:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            # asserting below this line won't called
            assert False

        assert e_info.match(
            "The file must end with one of the following extensions: '.jpg', '.jpeg', '.png'."
        )

    def test_invalid_attachment_extension(self, mock):
        # Arrange
        self._context["request"].FILES["upload_file"] = self.invalid_upload_file
        data = {
            "team_id": self.team_id,
            "upload_type": "attachment",
            "upload_file": self.invalid_upload_file,
        }

        # Act
        serializer = TeamDiscussionFileUploadSerializer(
            data=data, context=self._context
        )

        # Assert
        with pytest.raises(exceptions.PermissionDenied) as e_info:
            serializer.is_valid(raise_exception=True)
            serializer.save()

        assert e_info.match(
            "The file must end with one of the following extensions: '.doc', '.docx', '.pdf', '.rtf', '.txt', '.xls', '.xlsx', '.csv'."
        )

    @mock.patch(
        "plugin_api.settings.MAX_UPLOAD_FILE_SIZE", TEST_MAX_UPLOAD_FILE_SIZE
    )
    def test_invalid_image_size(self, mock):
        # Arrange
        self._context["request"].FILES["upload_file"] = self.image_upload_file
        data = {
            "team_id": self.team_id,
            "upload_type": "image",
            "upload_file": self.image_upload_file,
        }

        # Act
        serializer = TeamDiscussionFileUploadSerializer(
            data=data, context=self._context
        )

        # Assert
        with pytest.raises(exceptions.PermissionDenied) as e_info:
            serializer.is_valid(raise_exception=True)
            serializer.save()

        assert e_info.match(
            f"Maximum upload file size is {TEST_MAX_UPLOAD_FILE_SIZE} bytes."
        )

    @mock.patch(
        "plugin_api.settings.MAX_UPLOAD_FILE_SIZE", TEST_MAX_UPLOAD_FILE_SIZE
    )
    def test_invalid_attachment_size(self, mock):
        # Arrange
        self._context["request"].FILES["upload_file"] = self.attachment_upload_file
        data = {
            "team_id": self.team_id,
            "upload_type": "attachment",
            "upload_file": self.attachment_upload_file,
        }

        # Act
        serializer = TeamDiscussionFileUploadSerializer(
            data=data, context=self._context
        )

        # Assert
        with pytest.raises(exceptions.PermissionDenied) as e_info:
            serializer.is_valid(raise_exception=True)
            serializer.save()

        assert e_info.match(
            f"Maximum upload file size is {TEST_MAX_UPLOAD_FILE_SIZE} bytes."
        )

    def test_invalid_upload_type(self, mock):
        # Arrange
        self._context["request"].FILES["upload_file"] = self.image_upload_file
        data = {
            "team_id": self.team_id,
            "upload_type": "document",
            "upload_file": self.image_upload_file,
        }

        # Act
        serializer = TeamDiscussionFileUploadSerializer(
            data=data, context=self._context
        )

        # Assert
        with pytest.raises(exceptions.ValidationError) as e_info:
            serializer.is_valid(raise_exception=True)
            serializer.save()

        assert e_info.match('"document" is not a valid choice.')
