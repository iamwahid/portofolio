from django.urls import reverse, resolve

import pytest


def test_url_team_list_by_topic_id(course_id_str_fx, topic_id_fx):
    assert (
        reverse(
            "plugin_api:plugin_api.list_teams",
            kwargs={"course_id": course_id_str_fx, "topic_id": topic_id_fx},
        )
        == f"/api/plugin-api/courses/{course_id_str_fx}/topics/{topic_id_fx}/teams"
    )
    assert (
        resolve(
            f"/api/plugin-api/courses/{course_id_str_fx}/topics/{topic_id_fx}/teams"
        ).view_name
        == "plugin_api:plugin_api.list_teams"
    )


def test_url_team_detail_by_topic_id(course_id_str_fx, topic_id_fx, team_id):
    assert (
        reverse(
            "plugin_api:plugin_api.get_team_details",
            kwargs={
                "course_id": course_id_str_fx,
                "topic_id": topic_id_fx,
                "team_id": team_id,
            },
        )
        == f"/api/plugin-api/courses/{course_id_str_fx}/topics/{topic_id_fx}/teams/{team_id}"
    )
    assert (
        resolve(
            f"/api/plugin-api/courses/{course_id_str_fx}/topics/{topic_id_fx}/teams/{team_id}"
        ).view_name
        == "plugin_api:plugin_api.get_team_details"
    )


def test_url_list_teams_user_joined(course_id_str_fx, topic_id_fx, team_id):
    assert (
        reverse(
            "plugin_api:plugin_api.list_teams_user_joined",
            kwargs={
                "course_id": course_id_str_fx,
            },
        )
        == f"/api/plugin-api/courses/{course_id_str_fx}/teams"
    )
    assert (
        resolve(f"/api/plugin-api/courses/{course_id_str_fx}/teams").view_name
        == "plugin_api:plugin_api.list_teams_user_joined"
    )
