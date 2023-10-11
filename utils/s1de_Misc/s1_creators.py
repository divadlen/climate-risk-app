from utils.utility import find_closest_category
from utils.s1de_Misc.s1_models import *


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
def create_s1_data(row, Model, cache=None, **kwargs):
    """ 
    Boilerplate used to create S1 Models from rows of a dataframe. 
    Model( row.to_dict() ) is not reliable as using values from a df directly may not be compatible with Pydantic models

    Params:
    Model: 
      The model that will be using row values to be created under (EG: S1, ...)

    Recommended new params:
      cache: Lookup cache dictionary to check for dupe entry
      geolocator
    """
    try:
        return Model(**row)
    except Exception as e:
        raise e
    

#---Category 1---#
def create_s1mc_data(row, Model:S1_MobileCombustion, cache=None, **kwargs): 
    """ 
    """
    # fuzzy match might return unintentional results
    abbrv_dict = {
    }

    try:            
        # Verify and correct fuel_type
        allowed_fuel_type = cache.get_allowed_fuel_type()
        corrected_fuel_type = verify_and_correct(row, 'fuel_type', allowed_fuel_type, abbrv_dict)
        row['fuel_type'] = corrected_fuel_type
          
        # Verify and correct vehicle type
        allowed_vehicle_type = cache.get_allowed_vehicle_type( table='s3c6_travel_factors' )
        corrected_vehicle_type = verify_and_correct(row, 'vehicle_type', allowed_vehicle_type, abbrv_dict)
        row['vehicle_type'] = corrected_vehicle_type

        return Model(**row)
  
    except Exception as e:
        raise e
    

def create_s1sc_data(row, Model:S1_StationaryCombustion, cache=None, **kwargs):
    # fuzzy match might return unintentional results
    abbrv_dict = {
    }

    try:            
        # Verify and correct fuel_type
        allowed_fuel_type = cache.get_allowed_fuel_type()
        corrected_fuel_type = verify_and_correct(row, 'fuel_type', allowed_fuel_type, abbrv_dict)
        row['fuel_type'] = corrected_fuel_type
          
        return Model(**row)
  
    except Exception as e:
        raise e


def create_s1fe_data(row, Model:S1_FugitiveEmission, cache=None, **kwargs):
    # fuzzy match might return unintentional results
    abbrv_dict = {
    }

    try: 
        # Verify and correct refrigerant type
        allowed_refrigerant_type = cache.get_allowed_refrigerants()
        corrected_refrigerant_type = verify_and_correct(row, 'refrigerant_type', allowed_refrigerant_type, abbrv_dict)
        row['refrigerant_type'] = corrected_refrigerant_type

        return Model(**row)
    
    except Exception as e:
        raise e