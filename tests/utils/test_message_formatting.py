"""Tests for message formatting utilities."""

import pytest
from datetime import datetime, timedelta, UTC
from src.calendar.google_calendar import CalendarEvent
from src.utils.message_formatting import (
    format_meeting_confirmation,
    format_meeting_suggestions,
    format_meeting_cancellation,
    format_meeting_update
)


@pytest.fixture
def sample_event():
    """Create a sample calendar event for testing."""
    start = datetime.now(UTC)
    end = start + timedelta(hours=1)
    
    return CalendarEvent(
        id="test_event_123",
        summary="Test Meeting",
        start=start,
        end=end,
        description="Test meeting description",
        attendees=["test1@example.com", "test2@example.com"],
        location="Test Location",
        html_link="https://calendar.google.com/event?eid=test"
    )


def test_format_meeting_confirmation(sample_event):
    """Test meeting confirmation message formatting."""
    message = format_meeting_confirmation(sample_event)
    
    assert "✅ Meeting Scheduled Successfully!" in message
    assert sample_event.summary in message
    assert sample_event.description in message
    assert sample_event.location in message
    assert "👥 Attendees:" in message
    assert "test1@example.com" in message
    assert "test2@example.com" in message
    assert sample_event.html_link in message


def test_format_meeting_confirmation_no_optional_fields():
    """Test meeting confirmation with minimal event details."""
    event = CalendarEvent(
        id="test_event_123",
        summary="Test Meeting",
        start=datetime.now(UTC),
        end=datetime.now(UTC) + timedelta(hours=1),
        description=None,
        attendees=None,
        location=None,
        html_link="https://calendar.google.com/event?eid=test"
    )
    
    message = format_meeting_confirmation(event)
    
    assert "✅ Meeting Scheduled Successfully!" in message
    assert event.summary in message
    assert "👥 Attendees:" not in message
    assert "📋" not in message
    assert "📍" not in message


def test_format_meeting_suggestions(sample_event):
    """Test meeting suggestions message formatting."""
    slots = [sample_event]
    message = format_meeting_suggestions(slots)
    
    assert "📅 Available Time Slots:" in message
    assert "1." in message
    assert sample_event.summary in message
    assert "Please select a time slot" in message


def test_format_meeting_suggestions_empty():
    """Test meeting suggestions with no slots."""
    message = format_meeting_suggestions([])
    
    assert "❌ No available time slots found" in message


def test_format_meeting_cancellation(sample_event):
    """Test meeting cancellation message formatting."""
    message = format_meeting_cancellation(sample_event)
    
    assert "❌ Meeting Cancelled" in message
    assert sample_event.summary in message
    assert sample_event.description in message


def test_format_meeting_update(sample_event):
    """Test meeting update message formatting."""
    message = format_meeting_update(sample_event)
    
    assert "🔄 Meeting Updated" in message
    assert sample_event.summary in message
    assert sample_event.description in message
    assert sample_event.location in message
    assert "👥 Attendees:" in message
    assert "test1@example.com" in message
    assert "test2@example.com" in message
    assert sample_event.html_link in message


def test_format_meeting_update_no_optional_fields():
    """Test meeting update with minimal event details."""
    event = CalendarEvent(
        id="test_event_123",
        summary="Test Meeting",
        start=datetime.now(UTC),
        end=datetime.now(UTC) + timedelta(hours=1),
        description=None,
        attendees=None,
        location=None,
        html_link="https://calendar.google.com/event?eid=test"
    )
    
    message = format_meeting_update(event)
    
    assert "🔄 Meeting Updated" in message
    assert event.summary in message
    assert "👥 Attendees:" not in message
    assert "📋" not in message
    assert "📍" not in message 