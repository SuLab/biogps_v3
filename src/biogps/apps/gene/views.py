from django.http import Http404
from django.shortcuts import render_to_response

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from biogps.utils import log, is_valid_geneid

from .boe import do_query, MyGeneInfo


@api_view(['GET', 'POST'])
def query(request, mobile=False, iphone=False):
    if request.method == 'GET':
        res = do_query(request.query_params)
    else:
        res = do_query(request.data)

    # logging
    _log = {"clientip": request.META.get('REMOTE_ADDR', ''),
            "action": "search"}
    _u = getattr(request.user, 'username', None)
    if _u:
        _log['username'] = _u
    if mobile:
        _log['mobile'] = 1
    if iphone:
        _log['iphone'] = 1

    if '_log' in res:
        _log.update(res['_log'])
        del res['_log']
        log.info(' '.join(['{}={}'.format(*x) for x in _log.items()]))

    return Response(res)


@api_view()
def getgeneidentifiers(request, geneid=None):
    """
    Retrieve all available gene identifiers for given geneid, e.g. ensemblid, refseqid, pdb id.
    URL:          http://biogps.org/boe/getgeneidentifiers
    Parameters:   geneid - Entrez GeneID
    Examples:     http://biogps.org/boe/getgeneidentifiers/?geneid=695
    """
    geneid = geneid or request.GET.get('geneid', '').strip()
    if not is_valid_geneid(geneid):
        content = {'error': "missing or invalid input geneid parameter."}
        return Response(content, status=status.HTTP_404_NOT_FOUND)

    bs = MyGeneInfo()
    gene = bs.get_geneidentifiers(geneid)
    if gene:
        log.info('username=%s clientip=%s action=gene_identifiers id=%s',
                 getattr(request.user, 'username', ''),
                 request.META.get('REMOTE_ADDR', ''), geneid)
        return Response(gene)
    else:
        content = {'error': "input geneid does not match an exist gene."}
        return Response(content, status=status.HTTP_404_NOT_FOUND)


def genereport_for_bot(request, geneid):
    '''The web-crawler (bot) version of gene report page:
        http://biogps.org/gene/1017

       on dev server, the bot page can be accessed direct as:
        http://localhost:8000/gene/bot/1017

    '''
    from biogps.ext_plugins.views import grSymatlasTable
    from django.contrib.sites.models import Site
    from biogps.dataset.views import DatasetBotView

    #retrieve the html content from DatasetBotView
    datachart_content = DatasetBotView().get(request, geneid).content
    #retrieve the html content from SymatlasTable (GeneIdentifiers) plugin
    symtab_data = grSymatlasTable(request, geneid, forbot=True)

    if isinstance(symtab_data, dict) and 'content' in symtab_data:
        symtab_content = symtab_data['content']
        symbol = symtab_data.get('symbol', '')
        desc = symtab_data.get('name', '')
        summary = symtab_data.get('summary', '')

        current_site = Site.objects.get_current()

        return render_to_response('gene/robots.html',
                                  {'geneid': geneid,
                                   'symbol': symbol,
                                   'description': desc,
                                   'summary': summary,
                                   'site': current_site,
                                   'symtab_content': symtab_content,
                                   'datachart_content': datachart_content})
    else:
        raise Http404
