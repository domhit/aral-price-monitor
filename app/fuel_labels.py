SPRITMONITOR_FUELS={1:'Diesel',7:'Super',8:'SuperPlus',20:'E10',22:'Premium Benzin 100+'}
def fuel_label(code,station_brand='',station_name=''):
    try: code=int(code) if code is not None else None
    except (TypeError,ValueError): pass
    brand=f'{station_brand or ""} {station_name or ""}'.lower()
    if code==22 and 'aral' in brand:return 'Ultimate 102'
    return SPRITMONITOR_FUELS.get(code,str(code) if code not in (None,'') else '–')
