"""Tests for LinkedIn posting agent."""

import pytest
from agents.linkedin.post import create_post_payload


def test_create_post_payload():
    """Test post payload generation."""
    content = "Test post content"
    user_sub = "test123"

    payload = create_post_payload(content, user_sub)

    assert payload["author"] == "urn:li:person:test123"
    assert payload["lifecycleState"] == "PUBLISHED"
    assert payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"] == content
    assert payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareMediaCategory"] == "NONE"
    assert payload["visibility"]["com.linkedin.ugc.MemberNetworkVisibility"] == "PUBLIC"


def test_create_post_payload_special_chars():
    """Test post payload with special characters."""
    content = "Test with emojis 🚀 and\nnewlines"
    user_sub = "test123"

    payload = create_post_payload(content, user_sub)

    assert payload["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"] == content


def test_post_content_length_limit():
    """Test that content length is validated."""
    from agents.linkedin.post import post_to_linkedin

    long_content = "x" * 3001  # Over 3000 char limit

    with pytest.raises(ValueError, match="Content too long"):
        post_to_linkedin(
            content=long_content,
            access_token="dummy",
            user_sub="dummy",
            dry_run=True
        )


def test_dry_run_mode():
    """Test that dry run doesn't make API call."""
    from agents.linkedin.post import post_to_linkedin

    # Should not raise any errors in dry run mode
    post_id = post_to_linkedin(
        content="Test content",
        access_token="dummy_token",
        user_sub="dummy_sub",
        dry_run=True
    )

    assert post_id == "dry-run-post-id"
