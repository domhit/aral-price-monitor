TANK_TYPES={0:'Ungültig',1:'Vollbetankung',2:'Teilbetankung',3:'Erstbetankung'}
TIRES={1:'Sommerreifen',2:'Winterreifen',3:'Ganzjahresreifen'}
DRIVING_STYLES={1:'Bewusst sparsam',2:'Normal',3:'Flott'}
ROUTE_BITS={2:'Autobahn',4:'Stadt',8:'Landstraße'}
FUELS={1:'Diesel',2:'Biodiesel',3:'Pflanzenöl',4:'Premium Diesel',6:'Normalbenzin',7:'Super',8:'SuperPlus',9:'Premium Benzin 100',12:'LPG',13:'CNG H',14:'CNG L',15:'Bioethanol',16:'Zweitakt-Gemisch',18:'Premium Benzin 95',19:'Elektrizität',20:'E10',21:'AdBlue',22:'Premium Benzin 100+',23:'Wasserstoff',24:'Ökostrom',25:'GTL Diesel',26:'HVO100'}
def decode_route(value):
    value=int(value or 0);return [name for bit,name in ROUTE_BITS.items() if value & bit]
