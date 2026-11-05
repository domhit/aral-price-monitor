from datetime import date

def active_in_season(vehicle,day=None):
    if not vehicle or not int(vehicle.get('active',1) or 0):return False
    day=day or date.today();md=day.strftime('%m-%d')
    start=str(vehicle.get('season_start') or '01-01');end=str(vehicle.get('season_end') or '12-31')
    # Any full-year representation is always active.
    if (start,end) in {('01-01','12-31'),('01-01','01-01'),('','')}:return True
    return start<=md<=end if start<=end else md>=start or md<=end

def seasonal_vehicles(vehicles,day=None):return [v for v in vehicles if active_in_season(v,day)]
