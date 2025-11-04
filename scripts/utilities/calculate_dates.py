#!/usr/bin/env python3
from datetime import datetime, timedelta

# Get today's date
today = datetime.now().date()

# Calculate current week (Monday - Sunday)
# weekday() returns 0=Monday, 6=Sunday
current_weekday = today.weekday()

# Calculate this week's Monday and Sunday
this_week_monday = today - timedelta(days=current_weekday)
this_week_sunday = this_week_monday + timedelta(days=6)

# Calculate next week's Monday and Sunday
next_week_monday = this_week_sunday + timedelta(days=1)
next_week_sunday = next_week_monday + timedelta(days=6)

# Calculate remaining days this week (tomorrow through Sunday)
tomorrow = today + timedelta(days=1)
days_until_sunday = 6 - current_weekday

print(f"Today: {today.strftime('%A, %B %d, %Y')} ({today})")
print()
print(f"This Week:")
print(f"  Monday:    {this_week_monday}")
print(f"  Sunday:    {this_week_sunday}")
print(f"  Tomorrow:  {tomorrow}")
print(f"  Days until Sunday: {days_until_sunday}")
print()
print(f"Next Week:")
print(f"  Monday:    {next_week_monday}")
print(f"  Sunday:    {next_week_sunday}")
