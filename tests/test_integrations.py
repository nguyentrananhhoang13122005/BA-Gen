"""Bộ kiểm thử cho các mô-đun tích hợp Jira, GitHub Issues và Trello."""

from unittest.mock import MagicMock, patch
from src.core.models import AcceptanceCriteriaDTO, UserStoryDTO
from src.integrations.github_sync import GitHubIssueSync
from src.integrations.jira_sync import JiraSync
from src.integrations.trello_sync import TrelloSync


def create_sample_story() -> UserStoryDTO:
    return UserStoryDTO(
        story_id="US-01",
        req_id="REQ-01",
        role="Khách hàng",
        goal="đăng nhập tài khoản bằng số điện thoại",
        benefit="truy cập nhanh vào hệ thống",
        acceptance_criteria=[
            AcceptanceCriteriaDTO(
                scenario="Đăng nhập thành công",
                given="Người dùng nhập đúng số điện thoại và OTP",
                when="Người dùng nhấn nút xác nhận",
                then="Hệ thống chuyển hướng vào trang chủ"
            )
        ],
        puml_usecase_name="Đăng nhập OTP"
    )


def test_jira_csv_generation():
    stories = [create_sample_story()]
    csv_text = JiraSync.generate_import_csv(stories, project_key="SHOP")
    assert "Issue Type" in csv_text
    assert "US-01" in csv_text
    assert "Khách hàng" in csv_text
    assert "GIVEN" in csv_text


@patch("requests.post")
def test_jira_api_sync_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"key": "SHOP-12", "self": "https://jira.test/issue/SHOP-12"}
    mock_post.return_value = mock_resp

    stories = [create_sample_story()]
    result = JiraSync.sync_to_jira_api(
        domain="my-company",
        email="test@company.com",
        api_token="token_secret",
        project_key="SHOP",
        stories=stories
    )
    assert result["success_count"] == 1
    assert result["created_issues"][0]["jira_key"] == "SHOP-12"


def test_github_issue_formatting_and_json():
    story = create_sample_story()
    body = GitHubIssueSync.format_issue_body(story)
    assert "### 🎯 Agile User Story" in body
    assert "GIVEN" in body

    json_export = GitHubIssueSync.generate_export_json([story])
    assert "US-01" in json_export


@patch("requests.post")
def test_github_api_sync_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"number": 42, "html_url": "https://github.com/test/repo/issues/42"}
    mock_post.return_value = mock_resp

    stories = [create_sample_story()]
    result = GitHubIssueSync.sync_to_github_api(
        repo="user/repo",
        token="ghp_testtoken",
        stories=stories
    )
    assert result["success_count"] == 1
    assert result["created_issues"][0]["issue_number"] == 42


def test_trello_board_json_and_formatting():
    story = create_sample_story()
    desc = TrelloSync.format_card_description(story)
    assert "**Agile User Story:**" in desc
    assert "- [ ]" in desc

    board_json = TrelloSync.generate_board_json([story], board_name="E-Commerce Sprint 1")
    assert "E-Commerce Sprint 1" in board_json
    assert "Product Backlog" in board_json


@patch("requests.post")
def test_trello_api_sync_success(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "card_999", "shortUrl": "https://trello.com/c/xyz"}
    mock_post.return_value = mock_resp

    stories = [create_sample_story()]
    result = TrelloSync.sync_to_trello_api(
        api_key="api_key_test",
        token="token_test",
        list_id="list_123",
        stories=stories
    )
    assert result["success_count"] == 1
    assert result["created_cards"][0]["card_id"] == "card_999"
