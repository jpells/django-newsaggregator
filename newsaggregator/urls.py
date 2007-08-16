from django.conf.urls.defaults import *
from newsaggregator.models import Entry
from newsaggregator.feeds import RssFeed, AtomFeed
from django.conf import settings

feeds = { 
    'rss': RssFeed,
    'atom': AtomFeed,
}

entry_dict = {
    'queryset': Entry.objects.all(),
    'date_field': 'pub_date',
    'allow_empty': 'true',
}

entry_dict_detail = {
    'queryset': Entry.objects.all(),
    'date_field': 'pub_date',
}

entry_dict_year = {
    'queryset': Entry.objects.all(),
    'date_field': 'pub_date',
    'make_object_list': 'True',
    'allow_empty': 'true',
}

urlpatterns = patterns('',
    (r'^rss/$', 'django.contrib.syndication.views.feed', {'feed_dict': feeds, 'url': 'rss'}),
    (r'^atom/$', 'django.contrib.syndication.views.feed', {'feed_dict': feeds, 'url': 'atom'}),
)

urlpatterns += patterns('django.views.generic.create_update',
    (r'^create/$', 'create_object', dict(model=Entry, login_required=True, extra_context={'STATE_DEFAULT': settings.STATE_DEFAULT})),
)

urlpatterns += patterns('django.views.generic.date_based',
    (r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/(?P<slug>[0-9A-Za-z-]+)/$', 'object_detail', dict(entry_dict_detail, slug_field='slug')),
    (r'^$', 'archive_index', entry_dict),
    (r'^(?P<year>\d{4})/$', 'archive_year',  entry_dict_year),
    (r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/(?P<day>\w{1,2})/$',  'archive_day', entry_dict),
    (r'^(?P<year>\d{4})/(?P<month>[a-z]{3})/$',  'archive_month', entry_dict),
)
