from utils.globals import LOCATION_ABBRV
from utils.utility import find_closest_category
from utils.geolocator import GeoLocator
from utils.s2ie_Misc.s2_models import S2_PurchasedPower


#-------
# Helper 
#-------
def verify_and_correct(row:dict, field_name:str, allowed_values:list, abbrv_dict:dict=None):
    """ 
    Boilerplate for correcting a value in a field, according to a list of available values.
    DOES NOT REPLACE row value, but only returning a corrected value for safety purposes. 

    row: 
      dict object
    
    field_name:
      column name in dict. It is possible to give a name that does not exist in row. 

    allowed_values:
      List object containing all the available values that can be corrected

    abbrv_dict:
      Dict object containing adjustments (US >> United States. Melaka >> Malacca). 
      This is to avoid fuzzy matching to miss "obvious" corrections. 
    """
    value = row.get(field_name)

    if value not in allowed_values:
        corrected_value = find_closest_category(value, allowed_values, abbrv_dict=abbrv_dict)
        if corrected_value is not None:
            print(f'Field "{field_name}" input "{value}" suggested values is "{corrected_value}"')
            return corrected_value
        else:
            raise ValueError(f'Field "{field_name}" input "{value}" and relevant matches not found.')
    
    print(f'Field "{field_name}" input "{value}" has a match!"')
    return value


# -------
# Creator
# ------
def create_s2pp_data(row, Model:S2_PurchasedPower, cache=None, geolocator=None, **kwargs):
    """ 
    Boilerplate used to create S2 Models from rows of a dataframe. 
    Model( row.to_dict() ) is not reliable as using values from a df directly may not be compatible with Pydantic models

    Params:
    Model: 
      The model that will be using row values to be created under (EG: S2_PurchasedPower, ...)

    cache: 
      Lookup cache dictionary to check for dupe entry
    
    geolocator:
      KD tree map
    """
    
    abbrv_map = {
        'usa': 'United States of America',
        'united states': 'United States of America',
        'uk': 'United Kingdom',
        'korea': 'South Korea',
        'my': 'Malaysia',
        'melaka': 'Malacca'
    }

    try:
        # Use lat lon info first if provided
        if geolocator:
            lat = row.get('lat')
            lon = row.get('lon')
            if lat is not None and lon is not None:
                geo_fields = geolocator.get_fields_from_latlon(lat, lon)
                row.update({
                    'state': geo_fields.get('state_name'),
                    'country': geo_fields.get('country_name'),
                })

        # Verify and correct country
        if 'country' in row and row['country'] is not None:
            allowed_countries = cache.get_allowed_countries()
            corrected_country = find_closest_category(row['country'], allowed_countries, abbrv_dict=abbrv_map)
            row['country'] = corrected_country if corrected_country else None

        # Verify and correct state
        if 'state' in row and row['state'] is not None and row['country'] is not None:
            allowed_states = cache.get_allowed_states(country=row['country'])
            corrected_state = find_closest_category(row['state'], allowed_states, abbrv_dict=abbrv_map)
            row['state'] = corrected_state if corrected_state else None

        return Model(**row)

    except Exception as e:
        raise e
