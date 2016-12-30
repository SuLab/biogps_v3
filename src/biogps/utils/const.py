MAX_QUERY_LENGTH = 10*1000       # A rough upper limit for length of input gene query.

SPECIES_LIST = [
    dict(name='human',
         taxid=9606,
         prefix='Hs',
         assembly='hg19',
         genus='Homo sapiens',
         sample_gene=1017),    # CDK2
    dict(name='mouse',
         taxid=10090,
         prefix='Mm',
         assembly='mm9',
         genus='Mus musculus',
         sample_gene=12566),   # CDK2
    dict(name='rat',
         taxid=10116,
         prefix='Rn',
         assembly='rn4',
         genus='Rattus norvegicus',
         sample_gene=362817),  # CDK2
    dict(name='fruitfly',
         taxid=7227,
         prefix='Dm',
         assembly='dm3',
         genus='Drosophila melanogaster',
         sample_gene=42453),   # CDK2
    dict(name='nematode',
         taxid=6239,
         prefix='Ce',
         assembly='ce7',
         genus='Caenorhabditis elegans',
         sample_gene=172677),  # CDK8
    dict(name='zebrafish',
         taxid=7955,
         prefix='Dr',
         assembly='danRer6',
         genus='Danio rerio',
         sample_gene=406715),  # CDK2
    dict(name='thale-cress',
         taxid=3702,
         prefix='At',
         assembly='',          # we don't have genomic data for arabidopsis right now
         genus='Arabidopsis thaliana',
         sample_gene=837405),  # CSD1
    dict(name='frog',
         taxid=8364,
         prefix='Xt',
         assembly='xenTro2',
         genus='Xenopus tropicalis',
         sample_gene=493498),  # cdk2
    dict(name='pig',
         taxid=9823,
         prefix='Ss',
         assembly='susScr2',
         genus='Sus scrofa',
         # sample_gene=100127490),  # CDK2
         sample_gene=397593),     # AMBP (CDK2 does not have data in pigatlas dataset)
]

AVAILABLE_SPECIES = [s['name'] for s in SPECIES_LIST]
assembly_d = dict([(s['name'], s['assembly']) for s in SPECIES_LIST])
taxid_d = dict([(s['name'], s['taxid']) for s in SPECIES_LIST])
species_d = dict([(s['taxid'], s['name']) for s in SPECIES_LIST])
genus_d = dict([(s['name'], s['genus']) for s in SPECIES_LIST])
sample_gene = dict([(s['name'], s['sample_gene']) for s in SPECIES_LIST])

MIMETYPE = {
    'json': 'application/json',
    'myjson': 'application/json',
    'plainjson': 'text/plain',
    'xml': 'application/xml',
}

GO_CATEGORY = {"MF": 'Molecular Function',
               "BP": 'Biological Process',
               "CC": 'Cellular Component'}

ROLEPERMISSION_VALUES = {'myself': None,
                         'gnfusers': 'GNF Users',
                         'novartisusers': 'Novartis Users',
                         'biogpsusers': 'BioGPS Users'}
ROLEPERMISSION_SHORTNAMES = dict([reversed(x) for x in ROLEPERMISSION_VALUES.items()])
VALID_ROLE_LIST = [r for r in ROLEPERMISSION_VALUES.values() if r]

STD_FORMAT = {'plainjson': 'json'}

ANONYMOUS_USER_ERROR = {'success': False,
                        'error': 'Login required for accessing this service. (It could be your session has expired. <a href="javascript:biogps.usrMgr.gotoLoginPage()">Click here to login again.)</a>'}
