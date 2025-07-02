from utils import is_pi
from skyfield.api import wgs84, load

if is_pi():
    ephemeris = "/home/owen/astroflo/de440s.bsp"
else:
    ephemeris = 'de440s.bsp'
planets = load(ephemeris)
earth = planets["EARTH"]
location = wgs84.latlon(43.1566, -77.6088, 100) # TODO: sync with other location, customize

def get_planet(planet_name: str):
    if f'{planet_name.upper()} BARYCENTER' in planets:
        return planets[f'{planet_name.upper()} BARYCENTER']
    return planets[planet_name.upper()]

def observe(self, target):
        target = get_planet(target)
        if target is None:
            raise ValueError(f"Target {target} not found in ephemeris")
        topocentric = earth + location
        geocentric = topocentric.at(self.get_time()).observe(target).apparent()

        ra, dec, dist = geocentric.radec() # TODO: Analyze whether using time is more accurate
        # If so, implement a system that manually marks planets
        # Starplots current system plots J2000 coordinates, but are slightly off for planets

        #local = CelestialObject("Planet", 0, "Planet", "", ra.degrees, dec.degrees, "", False)
        return None