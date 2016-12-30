import os.path, time

from django.core.management.base import BaseCommand
from django.conf import settings
from biogps.plugin.models import BiogpsPlugin, BiogpsPluginPopularity


class Command(BaseCommand):
    help = "A daily utility to update plugin's popularity scores for BioGPS app. It should be scheduled as a daily job."
    requires_system_checks = True

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch', '-b',
            action='store_true',
            dest='batch',
            help='Run in batch mode without confirmation.',
        )

    def handle(self, **options):
        target_DB = settings.DATABASES['default']['NAME']

        if options.get("batch", False):
            ans = 'Y'
        else:
            ans = ask("Update popularity scores on DB \"%s\"?" % target_DB)
        if ans=='Y':
            print 'Calculating popularity scores...',

            score_d = dict([(p, [p.usage.count()]) for p in BiogpsPlugin.objects.all()])
            cnt_1 = len(score_d)
            print 'Done. [%d, %d]' % (len(score_d), cnt_1)

            log_f = file(os.path.join(settings.ROOT_PATH, 'biogps_updatepopscores.log'),'w')

            # Plugin list of lists [layout count, plugin]
            plugin_rank = list([[score_d[p][0], p] for p in score_d])

            # Sort by usage
            plugin_rank.sort(reverse=True)

            # Assign rank
            prev_rank, prev_rank_val, ranking, rank_count = 0,0,0,0
            for p in plugin_rank:
                rank_count += 1
                if p[0] != prev_rank_val:
                    ranking = rank_count
                    prev_rank = ranking
                    prev_rank_val = p[0]
                else:
                    # Same value as previous, use same rank
                    ranking = prev_rank

                # Get plugin from score_d, assign rank
                if p[1] in score_d:
                    score_d[p[1]].append(ranking)

            print 'Updating scores into "BiogpsPluginPopularity" table...',
            cnt_2 = 0

            for plugin in BiogpsPlugin.objects.all():
                try:
                    pop = BiogpsPluginPopularity.objects.get(plugin=plugin)
                except BiogpsPluginPopularity.DoesNotExist:
                    # If cannot find associated entry in BiogpsPluginPopularity model
                    # create one on the fly
                    pop = BiogpsPluginPopularity(plugin=plugin)

                pop.score, pop.rank = score_d.get(plugin, (0, 0))

                try:
                    pop.users_count = plugin.usage_users()
                except:
                    pop.users_count = 0

                # Calculate 'commonly used with this plugin' statistics
                layouts_using = plugin.usage

                # All plugins used with this plugin {plugin id: [title, count, url]}
                used_with = dict()

                for layout in layouts_using:
                    # Get each plugin used with current plugin
                    for p in layout.plugins.all():
                        if plugin.id != p.id and p.is_public:
                            if p.id in used_with:
                                # Plugin already entered, update count
                                used_with[p.id][1] += 1
                            else:
                                used_with[p.id] = [p.title, 1, p.get_absolute_url()]

                # Create [count, ID, title, url] list of total used_with plugin stats, then sort
                used_with_totals = [[item[1][1], item[0], item[1][0], item[1][2]] for item in used_with.iteritems()]
                used_with_totals.sort(reverse=True)

                # Grab top 5 plugins
                most_common = used_with_totals[:5]

                # Create related plugins list of dictionaries [{plugin ID, count, title, url}]
                pop.related_plugins = [{'id': i[1], 'title': i[2], 'count': i[0], 'url': i[3]} for i in most_common]

                pop.save()
                cnt_2 += 1

            print 'Done. [%d]' % cnt_2
            log_f.write('Last ran=%s\n' % time.ctime())
            log_f.write('Target_DB=%s\n' % target_DB)
            log_f.write('Stats=%s, %s, %s' % (len(score_d), cnt_1, cnt_2))
            log_f.close()


def ask(prompt,options='YN'):
    '''Prompt Yes or No,return the upper case 'Y' or 'N'.'''
    options=options.upper()
    while 1:
        s=raw_input(prompt+'[%s]' % '|'.join(list(options))).strip().upper()
        if s in options: break
    return s
