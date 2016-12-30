from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "A weekly clean-up utility for BioGPS app. It cleans both expired session data and httplib2 cache files."

    requires_system_checks = True

    def handle(self, **options):
        from django.conf import settings
        cleanupSession()
        res = cleanupHttplib2Cache()
        if res:
            removed_cnt, file_cnt = res
        import os.path, time
        log_f = file(os.path.join(settings.ROOT_PATH, 'biogps_cleanup.log'),'w')
        log_f.write('Last ran=%s\n' % time.ctime())
        if res:
            log_f.write('.cache folder: #before=%d; #removed=%d; #after=%d' % (file_cnt, removed_cnt, file_cnt-removed_cnt))
        log_f.close()


def cleanupSession():
    """Clean up expired sessions."""
    from django.contrib.sessions.models import Session
    from django.db import transaction
    from django.utils import timezone

    print "Cleaning expired sessions...",
    with transaction.atomic():
        Session.objects.filter(expire_date__lt=timezone.now()).delete()
    print 'Done!'


def cleanupHttplib2Cache():
    '''clean up old (by default 1 week older) cached httplib2 requests.'''
    from django.conf import settings
    import time, os, os.path

    cache_folder = settings.HTTPLIB2_CACHE
    if not cache_folder: return

    print 'Cleaning old cache files ("%s")...' % cache_folder,
    now = time.time()
    removed_cnt = 0
    file_cnt = 0
    for f in os.listdir(cache_folder):
        _f = os.path.join(cache_folder, f)
        if os.path.isfile(_f) and (now-os.path.getmtime(_f))>604800: #604800 is 1 week; 1209600 is 2 weeks
            os.remove(_f)
            removed_cnt += 1
        file_cnt += 1
    print 'Done! [%d/%d cleaned]' % (removed_cnt, file_cnt)
    return removed_cnt, file_cnt
