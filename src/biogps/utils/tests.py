from django.test import Client
from biogps.test.utils import *
from models import *
#==============================================================================
# To run this test file, use the command:
#   python manage.py test -- biogps.utils.tests
#
# Or to run a specific test, use:
#   python manage.py test -- biogps.utils.tests:test_species_list
#==============================================================================


#==============================================================================
# test functions starts here
#==============================================================================
def test_species_list():
    sl = BiogpsSpeciesList()
    eq_( len(sl), 8 )   # Update this number as the species count increases.
    eq_( sl['human'].taxid, 9606 )
    eq_( sl['human']['taxid'], 9606 )
    eq_( sl['mouse'].prefix, 'Mm' )
    eq_( sl['rat'].assembly, 'rn4' )
    eq_( sl['fruitfly'].genus, 'Drosophila melanogaster' )
    eq_( sl['nematode'].sample_gene, 172677 )
    eq_( sl[7955].name, 'zebrafish' )
