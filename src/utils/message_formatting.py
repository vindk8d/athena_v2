"""
Message Formatting Utilities for Athena Digital Executive Assistant.

Provides helpers for formatting Telegram bot responses safely in Markdown, HTML, or plain text.
"""

import html
import re
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.calendar.google_calendar import CalendarEvent

# Telegram MarkdownV2 special characters that must be escaped
TELEGRAM_MARKDOWN_V2_SPECIALS = r'_\*\[\]\(\)~`>#+\-=|{}.!'


def escape_markdown(text: str) -> str:
    """
    Escape text for Telegram MarkdownV2.
    """
    if not text:
        return ""
    return re.sub(f'([{TELEGRAM_MARKDOWN_V2_SPECIALS}])', r'\\\1', text)


def escape_html(text: str) -> str:
    """
    Escape text for Telegram HTML formatting.
    """
    if not text:
        return ""
    return html.escape(text)


def format_info_message(text: str, markdown: bool = True) -> Dict[str, Any]:
    """
    Format an informational message for Telegram.
    Returns dict with text and parse_mode.
    """
    if markdown:
        return {"text": escape_markdown(text), "parse_mode": "MarkdownV2"}
    else:
        return {"text": escape_html(text), "parse_mode": "HTML"}


def format_error_message(text: str, markdown: bool = True) -> Dict[str, Any]:
    """
    Format an error message for Telegram.
    """
    prefix = "❌ "
    return format_info_message(prefix + text, markdown=markdown)


def format_confirmation_message(text: str, markdown: bool = True) -> Dict[str, Any]:
    """
    Format a confirmation message for Telegram.
    """
    prefix = "✅ "
    return format_info_message(prefix + text, markdown=markdown)


def format_warning_message(text: str, markdown: bool = True) -> Dict[str, Any]:
    """
    Format a warning message for Telegram.
    """
    prefix = "⚠️ "
    return format_info_message(prefix + text, markdown=markdown)


def format_meeting_details(details: Dict[str, Any], markdown: bool = True) -> Dict[str, Any]:
    """
    Format meeting details for Telegram.
    details: dict with keys like title, time, duration, location, attendees
    """
    if markdown:
        lines = [
            f"*Meeting Details*",
            f"*Title:* {escape_markdown(details.get('title', ''))}",
            f"*Time:* {escape_markdown(details.get('time', ''))}",
            f"*Duration:* {escape_markdown(str(details.get('duration', '')))}",
            f"*Location:* {escape_markdown(details.get('location', ''))}",
            f"*Attendees:* {escape_markdown(', '.join(details.get('attendees', [])))}"
        ]
        text = '\n'.join(lines)
        return {"text": text, "parse_mode": "MarkdownV2"}
    else:
        lines = [
            f"<b>Meeting Details</b>",
            f"<b>Title:</b> {escape_html(details.get('title', ''))}",
            f"<b>Time:</b> {escape_html(details.get('time', ''))}",
            f"<b>Duration:</b> {escape_html(str(details.get('duration', '')))}",
            f"<b>Location:</b> {escape_html(details.get('location', ''))}",
            f"<b>Attendees:</b> {escape_html(', '.join(details.get('attendees', [])))}"
        ]
        text = '<br>'.join(lines)
        return {"text": text, "parse_mode": "HTML"}


def format_contact_info(details: Dict[str, Any], markdown: bool = True) -> Dict[str, Any]:
    """
    Format contact info for Telegram.
    details: dict with keys like name, email, telegram_id
    """
    if markdown:
        lines = [
            f"*Contact Info*",
            f"*Name:* {escape_markdown(details.get('name', ''))}",
            f"*Email:* {escape_markdown(details.get('email', ''))}",
            f"*Telegram ID:* {escape_markdown(details.get('telegram_id', ''))}"
        ]
        text = '\n'.join(lines)
        return {"text": text, "parse_mode": "MarkdownV2"}
    else:
        lines = [
            f"<b>Contact Info</b>",
            f"<b>Name:</b> {escape_html(details.get('name', ''))}",
            f"<b>Email:</b> {escape_html(details.get('email', ''))}",
            f"<b>Telegram ID:</b> {escape_html(details.get('telegram_id', ''))}"
        ]
        text = '<br>'.join(lines)
        return {"text": text, "parse_mode": "HTML"}


def format_meeting_confirmation(
    event: CalendarEvent,
    timezone: str = 'UTC',
    include_attendees: bool = True
) -> str:
    """
    Format a meeting confirmation message for Telegram delivery.
    
    Args:
        event: Calendar event details
        timezone: Timezone for displaying times
        include_attendees: Whether to include attendee list
        
    Returns:
        Formatted message string
    """
    # Format times in the specified timezone
    start_time = event.start.strftime('%I:%M %p')
    end_time = event.end.strftime('%I:%M %p')
    date = event.start.strftime('%A, %B %d, %Y')
    
    # Build message
    message = [
        f"✅ Meeting Scheduled Successfully!",
        f"\n📅 {date}",
        f"⏰ {start_time} - {end_time}",
        f"📝 {event.summary}"
    ]
    
    if event.description:
        message.append(f"\n📋 {event.description}")
    
    if event.location:
        message.append(f"\n📍 {event.location}")
    
    if include_attendees and event.attendees:
        message.append("\n👥 Attendees:")
        for attendee in event.attendees:
            message.append(f"• {attendee}")
    
    message.append(f"\n\n🔗 View in Calendar: {event.html_link}")
    
    return "\n".join(message)


def format_meeting_suggestions(
    slots: List[CalendarEvent],
    timezone: str = 'UTC'
) -> str:
    """
    Format meeting slot suggestions for Telegram delivery.
    
    Args:
        slots: List of available time slots
        timezone: Timezone for displaying times
        
    Returns:
        Formatted message string
    """
    if not slots:
        return "❌ No available time slots found in the specified range."
    
    message = ["📅 Available Time Slots:"]
    
    for i, slot in enumerate(slots, 1):
        start_time = slot.start.strftime('%I:%M %p')
        end_time = slot.end.strftime('%I:%M %p')
        date = slot.start.strftime('%A, %B %d')
        
        message.append(f"\n{i}. {date} at {start_time} - {end_time}")
    
    message.append("\nPlease select a time slot by replying with the number.")
    
    return "\n".join(message)


def format_meeting_cancellation(
    event: CalendarEvent,
    timezone: str = 'UTC'
) -> str:
    """
    Format a meeting cancellation message for Telegram delivery.
    
    Args:
        event: Calendar event details
        timezone: Timezone for displaying times
        
    Returns:
        Formatted message string
    """
    start_time = event.start.strftime('%I:%M %p')
    end_time = event.end.strftime('%I:%M %p')
    date = event.start.strftime('%A, %B %d, %Y')
    
    message = [
        "❌ Meeting Cancelled",
        f"\n📅 {date}",
        f"⏰ {start_time} - {end_time}",
        f"📝 {event.summary}"
    ]
    
    if event.description:
        message.append(f"\n📋 {event.description}")
    
    return "\n".join(message)


def format_meeting_update(
    event: CalendarEvent,
    timezone: str = 'UTC',
    include_attendees: bool = True
) -> str:
    """
    Format a meeting update message for Telegram delivery.
    
    Args:
        event: Calendar event details
        timezone: Timezone for displaying times
        include_attendees: Whether to include attendee list
        
    Returns:
        Formatted message string
    """
    start_time = event.start.strftime('%I:%M %p')
    end_time = event.end.strftime('%I:%M %p')
    date = event.start.strftime('%A, %B %d, %Y')
    
    message = [
        "🔄 Meeting Updated",
        f"\n📅 {date}",
        f"⏰ {start_time} - {end_time}",
        f"📝 {event.summary}"
    ]
    
    if event.description:
        message.append(f"\n📋 {event.description}")
    
    if event.location:
        message.append(f"\n📍 {event.location}")
    
    if include_attendees and event.attendees:
        message.append("\n👥 Attendees:")
        for attendee in event.attendees:
            message.append(f"• {attendee}")
    
    message.append(f"\n\n🔗 View in Calendar: {event.html_link}")
    
    return "\n".join(message)


# Exported functions
__all__ = [
    'escape_markdown',
    'escape_html',
    'format_info_message',
    'format_error_message',
    'format_confirmation_message',
    'format_warning_message',
    'format_meeting_details',
    'format_contact_info',
    'format_meeting_confirmation',
    'format_meeting_suggestions',
    'format_meeting_cancellation',
    'format_meeting_update',
] 