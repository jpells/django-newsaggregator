"""
Convenience module for access of custom newsaggregator application settings,
which enforces default settings when the main settings module does not
contain the appropriate settings.
"""
from django.conf import settings

_ = lambda s: s

# The choices for state of a News Entry
STATE_CHOICES = getattr(settings, 'STATE_CHOICES', (
    ('1', _('Draft')),
    ('2', _('Published')),
    ('3', _('Inactive')),
))

# The default state when a News Entry is created
STATE_DEFAULT = getattr(settings, 'STATE_DEFAULT', 3)

# The state of a Published News Entry
STATE_PUBLISHED = getattr(settings, 'STATE_PUBLISHED', 2)