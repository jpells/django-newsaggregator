from django.contrib.auth.models import User
from django.db import models
from newsaggregator import settings
from tagging.fields import TagField
from published_manager.managers import PublishedManager
from django.utils.translation import ugettext as _

class Feed(models.Model):
    title = models.CharField(_("Title"), max_length=200)
    tagline = models.TextField(_('Tagline'), blank=True)
    feed_url = models.URLField(_("Feed Url"), unique=True)
    public_url = models.URLField()
    is_defunct = models.BooleanField()
    tagline = models.TextField(_("Tagline"), blank=True)
    link = models.URLField(_("Link"), blank=True)
    etag = models.CharField(_("Etag"), max_length=50, blank=True)
    mod_date = models.DateTimeField(_("Date Modified"), null=True, blank=True)
    check_date = models.DateTimeField(_("Date Checked"), null=True, blank=True)

    class Admin:
        pass

    def __unicode__(self):
        return _(self.title)

class Entry(models.Model):
    """
    A news entry 
    """
    feed = models.ForeignKey(Feed, null=True, blank=True, verbose_name=_("Source Feed"))
    link = models.URLField(null=True, blank=True, verbose_name=_("Source Link"))
    summary = models.TextField(null=True, blank=True, verbose_name=_("Summary"))
    mod_date = models.DateTimeField(verbose_name=_("Date Modified"), null=True, blank=True, auto_now=True)
    guid = models.CharField(max_length=200, unique=True, db_index=True, verbose_name=_("Globally Unique Identifier"), blank=True, null=True)
    author = models.CharField(_("Author"), max_length=50, null=True, blank=True)
    author_email = models.EmailField(_("Author's Email"), null=True, blank=True)
    comments = models.URLField(_("Comments"), null=True, blank=True)
    title = models.CharField(max_length=255, verbose_name=_("Title"))
    slug = models.SlugField(prepopulate_from=('title',), unique=True, verbose_name=_("Slug Field"), blank=True, null=True)
    content = models.TextField(blank=True, verbose_name=_("Content"))
    pub_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Date Published"))
    user = models.ForeignKey(User, verbose_name=_("User"), null=True, blank=True)
    state = models.CharField(max_length=1, choices=settings.STATE_CHOICES, default=settings.STATE_DEFAULT, verbose_name=_("State of object"))
    ip_address = models.IPAddressField(verbose_name=_("Author's IP Address"), null=True, blank=True)
    tags = TagField(help_text=_("Enter key terms seperated with a space that you want to associate with this Entry"), verbose_name=_("Tags"))
    objects = models.Manager()
    published_objects = PublishedManager()

    def get_absolute_url(self):
        if self.link:
            return self.link
        else:
            return "/news/%s/%s/" % (self.pub_date.strftime("%Y/%b/%d").lower(), self.slug)

    def get_author_str(self):
        if self.user:
            return "<a href=%s>%s</a>" % (self.user.get_absolute_url(), self.user)
        elif self.author:
            if self.author_email:
                if not self.author_email == "nospam@nospam.com":
                    return "<a href=mailto:%s>%s</a>" % (self.author_email, self.author)
                else:
                    return self.author
            else:
                return self.author
        else:
            return ''

    def __unicode__(self):
        return _(self.title)

    class Meta:
        ordering = ['pub_date']
        get_latest_by = "pub_date"
        verbose_name = _("Entry")
        verbose_name_plural = _("Entries")

    class Admin:
        date_hierarchy = 'pub_date'
        list_display = ('title', 'user')
        ordering = ['pub_date']
        search_fields = ['title']
