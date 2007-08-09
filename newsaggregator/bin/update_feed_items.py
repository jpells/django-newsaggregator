import os
import time
import optparse
import datetime
import socket
import traceback
import sys

import feedparser

USER_AGENT = 'Newsaggregator'

def encode(tstr):
    """ Encodes a unicode string in utf-8
    """
    if not tstr:
        return ''
    # this is _not_ pretty, but it works
    try:
        return tstr.encode('utf-8', "xmlcharrefreplace")
    except UnicodeDecodeError:
        # it's already UTF8.. sigh
        return tstr.decode('utf-8').encode('utf-8')

def mtime(ttime):
    """ datetime auxiliar function.
    """
    return datetime.datetime.fromtimestamp(time.mktime(ttime))

def get_tags(entry):
    """ Returns a list of tag objects from an entry.
    """
    from tagging import models

    fcat = []
    if entry.has_key('tags'):
        for tcat in entry.tags:
            if tcat.label != None:
                term = tcat.label
            else:
                term = tcat.term
            qcat = term.strip()
            if ',' in qcat or '/' in qcat:
                qcat = qcat.replace(',', '/').split('/')
            else:
                qcat = [qcat]
            for zcat in qcat:
                tagname = zcat.lower()
                while '  ' in tagname:
                    tagname = tagname.replace('  ', ' ')
                tagname = tagname.strip()
                if not tagname or tagname == ' ':
                    continue
                if not models.Tag.objects.filter(name=tagname):
                    cobj = models.Tag(name=tagname)
                    cobj.save()
                fcat.append(models.Tag.objects.get(name=tagname))
    return fcat

def get_entry_data(entry, feed):
    """ Retrieves data from a entry and returns it in a tuple.
    """
    try:
        link = entry.link
    except AttributeError:
        link = feed.link
    try:
        title = entry.title
    except AttributeError:
        title = link
    guid = entry.get('id', title)

    if entry.has_key('author_detail'):
        author = entry.author_detail.get('name', '')
        author_email = entry.author_detail.get('email', '')
    else:
        author, author_email = '', ''

    if not author:
        author = entry.get('author', entry.get('creator', ''))
    if not author_email:
        author_email = 'nospam@nospam.com'
    
    try:
        content = entry.content[0].value
    except:
        content = entry.get('summary', entry.get('description', ''))
    
    if entry.has_key('modified_parsed'):
        mod_date = mtime(entry.modified_parsed)
    else:
        mod_date = None

    fcat = get_tags(entry)
    comments = entry.get('comments', '')

    return (link, title, guid, author, author_email, content, mod_date, \
      comments, fcat)

def process_entry(entry, fpf, feed, feeditemdict, options):
    """ Process a entry in a feed and saves it in the DB if necessary.
    """
    from newsaggregator import models

    (link, title, guid, author, author_email, content, mod_date, \
      comments, fcat) = get_entry_data(entry, feed)

    if options.verbose:
        print 'entry:'
        print '  title:', title
        print '  link:', link
        print '  guid:', guid
        print '  author:', author
        print '  author_email:', author_email
        print '  tags:', [tcat.name for tcat in fcat]

    if guid in feeditemdict:
        tobj = feeditemdict[guid]
        if options.verbose:
            print '  - Existing previous Feed Item object, updating..'
        feeditemdict[guid] = tobj
        if tobj.content != content or \
          (mod_date and tobj.mod_date != mod_date):
            if options.verbose:
                print '  - Feed Item has changed, updating...'
            if not mod_date:
                # damn non-standard feeds
                mod_date = tobj.mod_date
            tobj.title = title
            tobj.link = link
            tobj.content = content
            tobj.guid = guid
            tobj.mod_date = mod_date
            tobj.author = author
            tobj.author_email = author_email
            tobj.comments = comments
            tags = ''
            for tcat in fcat:
                tags = "%s %s" % (tags, tcat.name)
            tobj.tags = tags
            tobj.save()
        elif options.verbose:
            print '  - Feed Item has not changed, ignoring.'
    else:
        if options.verbose:
            print '  - Creating Feed Item object...'
        if not mod_date:
            # if the feed has no mod_date info, we use the feed mtime or
            # the current time
            if fpf.feed.has_key('modified_parsed'):
                mod_date = mtime(fpf.feed.modified_parsed)
            elif fpf.has_key('modified'):
                mod_date = mtime(fpf.modified)
            else:
                mod_date = datetime.datetime.now()
        tags = ''
        for tcat in fcat:
            tags = "%s %s" % (tags, tcat.name)
        tobj = models.Entry(feed=feed, title=title, link=link,
            content=content, guid=guid, mod_date=mod_date,
            author=author, author_email=author_email,
            comments=comments, tags=tags)
        tobj.save()

def process_feed(feed, options):
    """ Downloads and parses a feed.
    """
    from newsaggregator import models

    if options.verbose:
        print '#\n# Processing feed (%d):' % feed.id, feed.feed_url, '\n#'
    else:
        print '# Processing feed (%d):' % feed.id, feed.feed_url
    
    # we check the etag and the modified time to save bandwith and avoid bans
    try:
        fpf = feedparser.parse(feed.feed_url, agent=USER_AGENT,
            etag=feed.etag)
    except:
        print '! ERROR: feed cannot be parsed'
        return 1
    
    if hasattr(fpf, 'status'):
        if options.verbose:
            print 'fpf.status:', fpf.status
        if fpf.status == 304:
            # this means the feed has not changed
            if options.verbose:
                print 'Feed has not changed since last check, ignoring.'
            return 2

        if fpf.status >= 400:
            # http error, ignore
            print '! HTTP ERROR'
            return 3

    if hasattr(fpf, 'bozo') and fpf.bozo and options.verbose:
        print '!BOZO'

    # the feed has changed (or it is the first time we parse it)
    # saving the etag and mod_date fields
    feed.etag = fpf.get('etag', '')
    try:
        feed.mod_date = mtime(fpf.modified)
    except:
        pass
    
    feed.title = fpf.feed.get('title', '')[0:254]
    feed.tagline = fpf.feed.get('tagline', '')
    feed.link = fpf.feed.get('link', '')
    feed.check_date = datetime.datetime.now()

    if options.verbose:
        print 'feed.title', feed.title
        print 'feed.tagline', feed.tagline
        print 'feed.link', feed.link
        print 'feed.check_date', feed.check_date
    guids = []
    for entry in fpf.entries:
        if entry.get('id', ''):
            guids.append(entry.get('id', ''))
        elif entry.title:
            guids.append(entry.title)
        elif entry.link:
            guids.append(entry.link)
    feed.save()
    if guids:
        feeditemdict = dict([(feeditem.guid, feeditem) \
          for feeditem in models.Entry.objects.filter(feed=feed.id).filter(guid__in=guids)])
    else:
        feeditemdict = {}

    for entry in fpf.entries:
        try:
            process_entry(entry, fpf, feed, feeditemdict, options)
        except:
            (etype, eobj, etb) = sys.exc_info()
            print '! -------------------------'
            print traceback.format_exception(etype, eobj, etb)
            traceback.print_exception(etype, eobj, etb)
            print '! -------------------------'

    feed.save()

    return 0

def update_feeds(options):
    """ Updates all active feeds.
    """
    from newsaggregator import models

    #for feed in models.Feed.objects.filter(is_active=True).iterator():
    for feed in models.Feed.objects.all():
        try:
            process_feed(feed, options)
        except:
            (etype, eobj, etb) = sys.exc_info()
            print '! -------------------------'
            print traceback.format_exception(etype, eobj, etb)
            traceback.print_exception(etype, eobj, etb)
            print '! -------------------------'

def main():
    """ Main function. Nothing to see here. Move along.
    """
    parser = optparse.OptionParser(usage='%prog [options]', version=USER_AGENT)
    parser.add_option('--settings', \
      help='Python path to settings module. If this isn\'t provided, the DJANGO_SETTINGS_MODULE enviroment variable will be used.')
    parser.add_option('-f', '--feed', action='append', type='int', \
      help='A feed id to be updated. This option can be given multiple times to update several feeds at the same time (-f 1 -f 4 -f 7).')
#    parser.add_option('-s', '--site', type='int', \
#      help='A site id to update.')
    parser.add_option('-v', '--verbose', action='store_true', dest='verbose', \
      default=False, help='Verbose output.')
    parser.add_option('-t', '--timeout', type='int', default=10, \
      help='Wait timeout in seconds when connecting to feeds.')
    options = parser.parse_args()[0]
    if options.settings:
        os.environ["DJANGO_SETTINGS_MODULE"] = options.settings

    from newsaggregator import models

    # settting socket timeout (default= 10 seconds)
    socket.setdefaulttimeout(options.timeout)
    
    if options.feed:
        for feed in options.feed:
            try:
                process_feed(models.Feed.objects.get(pk=feed), options)
            except  models.Feed.DoesNotExist:
                print '! Unknown feed id: ', feed
#    elif options.site:
#        feeds = [sub.feed \
#          for sub in \
#          models.Site.objects.get(pk=int(options.site)).subscriber_set.all()]
#        for feed in feeds:
#            try:
#                process_feed(feed, options)
#            except  models.Feed.DoesNotExist:
#                print '! Unknown site id: ', feed
    else:
        update_feeds(options)

if __name__ == '__main__':
    main()

#~
