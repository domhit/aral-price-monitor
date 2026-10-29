TANK_TYPES={0:'Ungültig',1:'Vollbetankung',2:'Teilbetankung',3:'Erstbetankung'}
TIRES={1:'Sommerreifen',2:'Winterreifen',3:'Ganzjahresreifen'}
DRIVING={1:'Bewusst sparsam',2:'Normal',3:'Flott'}
FUELS={1:'Diesel',7:'Super',8:'SuperPlus',20:'E10',22:'Premium Benzin 100+'}
def route_name(value):
 names=[];v=int(value or 0)
 if v&2:names.append('Autobahn')
 if v&4:names.append('Stadt')
 if v&8:names.append('Landstraße')
 return ' + '.join(names) if names else '–'
