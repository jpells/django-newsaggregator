from newsaggregator.models import Entry
from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed

class RssFeed(Feed):
    title = _("News")
    link = "/news/" 
    description = _("News Entries")
    def items(self):
        return Entry.published_objects.order_by('-pub_date')[:5]

class AtomFeed(RssFeed):
    feed_type = Atom1Feed
