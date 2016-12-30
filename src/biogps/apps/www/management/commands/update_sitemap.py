#This command updates WWW_BIOGPSROOTNODE table for sitemap.xml generation.
#from a CouchDB host
#To call this command:
#   python manage.py update_sitemap --settings=settings_dev
#   python manage.py update_sitemap --settings=settings_prod --couch=http://cwu-dev:5984
#
#   When updates on prod DB table, ping_google will be called to notify google for sitemap changes.
from django.conf import settings
from django.db import connection
from django.core.management.base import BaseCommand
from django.contrib.sitemaps import ping_google

from biogps.utils import ask

SITEMAP_TABLE = "WWW_BIOGPSROOTNODE"


class Command(BaseCommand):
    help = "This command updates WWW_BIOGPSROOTNODE table for sitemap.xml generation from a CouchDB host"
    requires_system_checks = True

    def add_arguments(self, parser):
        parser.add_argument(
            "-c", "--couch",
            dest="couch_host",
            default=None,
            help='Specify couchdb host (default taken from settings)'),
        )
        parser.add_argument(
            "-d", "--db",
            dest="dbname",
            default="genedoc",
            help='Specify database name (default "genedoc")',
        )

    def handle(self, **options):
        couch_host = options['couch_host'] or settings.BOCSERVICE_URL.rstrip('/')+':5984'
        dbname=options['dbname']

        update_sitemap(couch_host, dbname)


def update_sitemap(couch_host, dbname):
    import couchdb
    from biogps.www.models import BiogpsRootnode

    server = couchdb.Server(couch_host)
    db = server[dbname]
    total_cnt = len(db)
    assert total_cnt > 0

    print "Updating GeneIDs used for generating sitemap..."
    print "\tSource: %s/%s (%d ids)" % (couch_host, dbname, total_cnt)
    print "\tTarget: Table \"%s\" on %s(%s)" % (SITEMAP_TABLE, settings.DATABASES['default']['NAME'], settings.DATABASES['default']['ENGINE'])
    if ask("Continue?") == 'Y':

        if ask("Delete all records (%d) in existing sitemap Table?" % BiogpsRootnode.objects.count() ) == 'Y':
            print "\tDeleting...",
            #BiogpsRootnode.objects.all().delete()
            cursor = connection.cursor()
#            cursor.execute('DELETE FROM '+SITEMAP_TABLE)
            cursor.execute('TRUNCATE TABLE ' + SITEMAP_TABLE)   #faster version
            cursor.close()
            connection.connection.commit()

            print "Done."
        else:
            return

        #Now insert new records from CouchDB
        print "\tInserting %d new records..." % total_cnt,
        step=10000
        mode='fast'
        for i in range(0, total_cnt, step):
            v_res = db.view('_all_docs', limit=step, skip=i)
            if mode == 'slow':
                for row in v_res.rows:
                    if row.id.startswith('_'):
                        continue
                    try:
                        int(row.id)
                        data_source = 'ncbi'
                    except ValueError:
                        data_source = 'ensembl'
                    node = BiogpsRootnode(id=row.id,
                                          data_source=data_source,
                                          data_source_rank=0,
                                          root_node=0,
                                          flag=0)
                    node.save()
            else:
                data = []
                for row in v_res.rows:
                    if row.id.startswith('_'):
                        continue
                    try:
                        int(row.id)
                        data_source = 'ncbi'
                    except ValueError:
                        data_source = 'ensembl'
                    data.append((row.id, data_source, 0, 0, 0))

                cursor = connection.cursor()
                cursor.executemany('INSERT INTO '+SITEMAP_TABLE+' VALUES (%s,%s,%s,%s,%s)', data)
                cursor.close()
                connection.connection.commit()

            print '%d...' % min(i+step, total_cnt) ,
        print ' Finished!'

        if settings.RELEASE_MODE == 'prod' and settings.SITE_ID == 1:
            print "Ping google for sitemap changes...",
            ping_google()
            print 'Done.'














