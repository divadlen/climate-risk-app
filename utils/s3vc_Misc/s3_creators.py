import pandas as pd
from pydantic import BaseModel, Field
from typing import Optional, Dict, Union, Tuple, ClassVar, Any

from utils.globals import LOCATION_ABBRV
from utils.utility import find_closest_category, supabase_query_v2
from utils.geolocator import GeoLocator
from utils.s3vc_Misc.s3_models import *


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
def create_s3_data(row, Model, cache=None, **kwargs):
    """ 
    Boilerplate used to create S3 Models from rows of a dataframe. 
    Model( row.to_dict() ) is not reliable as using values from a df directly may not be compatible with Pydantic models

    Params:
    Model: 
      The model that will be using row values to be created under (EG: S3C1, S3C2, ...)

    Recommended new params:
      cache: Lookup cache dictionary to check for dupe entry
      geolocator
    """
    try:
        return Model(**row)
    except Exception as e:
        raise e
    

#---Category 1---#
def create_s3c1_data(row, Model:S3C1_PurchasedGoods, cache=None, **kwargs):
    """ 
    Looks the same for now, but in events we have future tables:
    1. "Supplier name" and their "emission factors"
    2. "Product name" and "emission factors"
    """
    try:
        return Model(**row)
    except Exception as e:
        raise e
    

#---Category 2---#
def create_s3c2_data(row, Model:S3C2_CapitalGoods, cache=None, **kwargs):
    """ 
    Looks the same for now, but in events we have future tables:
    1. "Supplier name" and their "emission factors"
    2. "Product name" and "emission factors"
    """
    try:
        return Model(**row)
    except Exception as e:
        raise e


#---Category 3---#
def create_s3c3_data(row, Model:S3C3_EnergyRelated, cache=None, **kwargs):
    """ 
    Looks the same for now, but in events we have future tables:

    1. "grid_emission_factor" by location
    2. "upstream_emission_factor" by location / provider 
    3. "life_cycle_emission_factor" typically matches value with grid factor (life = grid)
    4. "combustion_emission_factor" factor associated to combustion. (grid - comb = upstream + loss)
    5. "energy_loss_rate"  ratio of energy loss during transporting. (grid - comb - loss = upstream))
    """
    try:
        return Model(**row)
    except Exception as e:
        raise e


#---Category 4---#
def create_s3c4_data(row, Model:S3C4_UpstreamTransport, cache=None, **kwargs):
    """ 

    """
    # fuzzy match might return unintentional results
    abbrv_dict = {
    }

    try:
        # Verify and correct freight_type
        allowed_freight_type = cache.get_allowed_freight_type()
        corrected_freight_type = verify_and_correct(row, 'freight_type', allowed_freight_type, abbrv_dict)
        row['freight_type'] = corrected_freight_type
            
        # Verify and correct fuel_type
        allowed_fuel_type = cache.get_allowed_fuel_type()
        corrected_fuel_type = verify_and_correct(row, 'fuel_type', allowed_fuel_type, abbrv_dict)
        row['fuel_type'] = corrected_fuel_type

        return Model(**row)
    except Exception as e:
        raise e
    

#---Category 5---#
def create_s3c5_data(row, Model:S3C5_WasteGenerated, cache=None, **kwargs):
    """ 
    """
    # fuzzy match might return unintentional results
    abbrv_dict = {
    }

    try:
        # Verify and correct waste_type
        allowed_waste_type = cache.get_allowed_waste_type()
        corrected_waste_type = verify_and_correct(row, 'waste_type', allowed_waste_type, abbrv_dict)
        row['waste_type'] = corrected_waste_type
            
        # Verify and correct waste treatment method based on corrected waste type
        allowed_waste_treatment_method = cache.get_allowed_waste_treatment_method(corrected_waste_type)
        corrected_waste_treatment_method = verify_and_correct(row, 'waste_treatment_method', allowed_waste_treatment_method, abbrv_dict)
        row['waste_treatment_method'] = corrected_waste_treatment_method

        return Model(**row)
    except Exception as e:
        raise e
    

#---Category 6---#
def create_s3c6_1_data(row, Model:S3C6_1_BusinessTravel, cache=None, **kwargs):
    """ 
    """
    abbrv_dict = {
    }
    try:
        # Verify and correct vehicle type
        allowed_vehicle_type = cache.get_allowed_vehicle_type( table='s3c6_travel_factors' )
        corrected_vehicle_type = verify_and_correct(row, 'vehicle_type', allowed_vehicle_type, abbrv_dict)
        row['vehicle_type'] = corrected_vehicle_type

        # Verify and correct fuel type
        allowed_fuel_type = cache.get_allowed_fuel_type(fuel_state='liquid')
        corrected_fuel_type = verify_and_correct(row, 'fuel_type', allowed_fuel_type, abbrv_dict)
        row['fuel_type'] = corrected_fuel_type

        return Model(**row)
    except Exception as e:
        raise e
    

def create_s3c6_2_data(row, Model:S3C6_2_BusinessStay, cache=None, **kwargs):
    try:
        return Model(**row)
    except Exception as e:
        raise e
    

#---Category 7---#
def create_s3c7_data(row, Model:S3C7_EmployeeCommute, cache=None, **kwargs):
    """ 
    """
    abbrv_dict = {
    }
    try:
        # Verify and correct vehicle type
        allowed_vehicle_type = cache.get_allowed_vehicle_type( table='s3c6_travel_factors' )
        corrected_vehicle_type = verify_and_correct(row, 'vehicle_type', allowed_vehicle_type, abbrv_dict)
        row['vehicle_type'] = corrected_vehicle_type

        return Model(**row)
    except Exception as e:
        raise e
    

#---Category 8---#
def create_s3c8_1_data(row, Model:S3C8_1_UpstreamLeasedEstate, geolocator=None, cache=None, **kwargs):
    abbrv_dict = {
        'r433': 'R-433A',
    }
    try:
        # Use lat lon info first if provided 
        if geolocator:
            if 'lat' not in [None] and 'lon' not in [None]:
                try:
                    geo_fields = geolocator.get_fields_from_latlon(row['lat'], row['lon'])
                    inferred_state = geo_fields.get('state_name')
                    inferred_country = geo_fields.get('country_name')    
                    row['state'] = inferred_state
                    row['country'] = inferred_country

                except Exception as e:
                    print(e)

        # Correct country and state using abbreviation mapping and fuzzy matching
        if 'country' in row and row['country'] is not None:
            corrected_country = find_closest_category(row['country'], cache.get_allowed_countries(), abbrv_dict=LOCATION_ABBRV)
            row['country'] = corrected_country if corrected_country else None

        if 'state' in row and row['state'] is not None:
            valid_states = cache.get_allowed_states(country=row['country'])
            corrected_state = find_closest_category(row['state'], valid_states, abbrv_dict=LOCATION_ABBRV)
            row['state'] = corrected_state if corrected_state else None

        
        # Verify and correct refrigerant type
        allowed_refrigerant_type = cache.get_allowed_refrigerants()
        corrected_refrigerant_type = verify_and_correct(row, 'refrigerant_type', allowed_refrigerant_type, abbrv_dict)
        row['refrigerant_type'] = corrected_refrigerant_type
            
        return Model(**row)
    
    except Exception as e:
        raise e
    

def create_s3c8_2_data(row, Model:S3C8_2_UpstreamLeasedAuto, cache=None, **kwargs):
    abbrv_dict = {
    }
    try:
        # Verify and correct fuel type
        allowed_fuel_type = cache.get_allowed_fuel_type(fuel_state='liquid')
        corrected_fuel_type = verify_and_correct(row, 'fuel_type', allowed_fuel_type, abbrv_dict)
        row['fuel_type'] = corrected_fuel_type
        
        # Verify and correct refrigerant type
        allowed_refrigerant_type = cache.get_allowed_refrigerants()
        corrected_refrigerant_type = verify_and_correct(row, 'refrigerant_type', allowed_refrigerant_type, abbrv_dict)
        row['refrigerant_type'] = corrected_refrigerant_type
            
        return Model(**row)
    
    except Exception as e:
        raise e
    

#---Category 9---#
def create_s3c9_data(row, Model:S3C9_DownstreamTransport, cache=None, **kwargs):
    abbrv_dict = {
    }
    try:
        # Verify and correct freight_type
        allowed_freight_type = cache.get_allowed_freight_type()
        corrected_freight_type = verify_and_correct(row, 'freight_type', allowed_freight_type, abbrv_dict)
        row['freight_type'] = corrected_freight_type
            
        # Verify and correct fuel_type
        allowed_fuel_type = cache.get_allowed_fuel_type()
        corrected_fuel_type = verify_and_correct(row, 'fuel_type', allowed_fuel_type, abbrv_dict)
        row['fuel_type'] = corrected_fuel_type
            
        return Model(**row)
    
    except Exception as e:
        raise e


#---Category 10---#
def create_s3c10_data(row, Model:S3C10_ProcessingProducts, cache=None, **kwargs):
    abbrv_dict = {
    }
    try:
        # Verify and correct fuel type
        fuel_state = row['fuel_state']
        if fuel_state is not None:
            allowed_fuel_type = cache.get_allowed_fuel_type(fuel_state=fuel_state)
        else:
            allowed_fuel_type = cache.get_allowed_fuel_type(fuel_state='liquid')
        corrected_fuel_type = verify_and_correct(row, 'fuel_type', allowed_fuel_type, abbrv_dict)
        row['fuel_type'] = corrected_fuel_type        

        # Verify and correct refrigerant type
        allowed_refrigerant_type = cache.get_allowed_refrigerants()
        corrected_refrigerant_type = verify_and_correct(row, 'refrigerant_type', allowed_refrigerant_type, abbrv_dict)
        row['refrigerant_type'] = corrected_refrigerant_type

        return Model(**row)
    
    except Exception as e:
        raise e


#---Category 11---#
def create_s3c11_data(row, Model:S3C11_UseOfSold, cache=None, **kwargs):
    abbrv_dict = {
    }
    try:
        # Verify and correct fuel type if fuel state provided
        fuel_state = row['fuel_state']
        if fuel_state is not None:
            allowed_fuel_type = cache.get_allowed_fuel_type(fuel_state=fuel_state)
            corrected_fuel_type = verify_and_correct(row, 'fuel_type', allowed_fuel_type, abbrv_dict)
            row['fuel_type'] = corrected_fuel_type        
        else:
            pass
        
        # Verify and correct refrigerant type
        allowed_refrigerant_type = cache.get_allowed_refrigerants()
        corrected_refrigerant_type = verify_and_correct(row, 'refrigerant_type', allowed_refrigerant_type, abbrv_dict)
        row['refrigerant_type'] = corrected_refrigerant_type

        return Model(**row)
    
    except Exception as e:
        raise e   


#---Category 12---#
def create_s3c12_data(row, Model:S3C12_EOLTreatment, cache=None, **kwargs):
    abbrv_dict = {
    }
    try:
        # Verify and correct waste_type
        allowed_waste_type = cache.get_allowed_waste_type()
        corrected_waste_type = verify_and_correct(row, 'waste_type', allowed_waste_type, abbrv_dict)
        row['waste_type'] = corrected_waste_type
            
        # Verify and correct waste treatment method based on corrected waste type
        allowed_waste_treatment_method = cache.get_allowed_waste_treatment_method(corrected_waste_type)
        corrected_waste_treatment_method = verify_and_correct(row, 'waste_treatment_method', allowed_waste_treatment_method, abbrv_dict)
        row['waste_treatment_method'] = corrected_waste_treatment_method

        return Model(**row)
    
    except Exception as e:
        raise e


#---Category 13---#
def create_s3c13_1_data(row, Model:S3C13_1_DownstreamLeasedEstate, geolocator:GeoLocator=None, cache=None, **kwargs):
    abbrv_dict = {
        'r433': 'R-433A',
    }
    try:
        # Use lat lon info first if provided 
        if geolocator:
            if 'lat' not in [None] and 'lon' not in [None]:
                try:
                    geo_fields = geolocator.get_fields_from_latlon(row['lat'], row['lon'])
                    inferred_state = geo_fields.get('state_name')
                    inferred_country = geo_fields.get('country_name')    
                    row['state'] = inferred_state
                    row['country'] = inferred_country

                except Exception as e:
                    print(e)

        # Correct country and state using abbreviation mapping and fuzzy matching
        if 'country' in row and row['country'] is not None:
            corrected_country = find_closest_category(row['country'], cache.get_allowed_countries(), abbrv_dict=LOCATION_ABBRV)
            row['country'] = corrected_country if corrected_country else None

        if 'state' in row and row['state'] is not None:
            valid_states = cache.get_allowed_states(country=row['country'])
            corrected_state = find_closest_category(row['state'], valid_states, abbrv_dict=LOCATION_ABBRV)
            row['state'] = corrected_state if corrected_state else None

        
        # Verify and correct refrigerant type
        allowed_refrigerant_type = cache.get_allowed_refrigerants()
        corrected_refrigerant_type = verify_and_correct(row, 'refrigerant_type', allowed_refrigerant_type, abbrv_dict)
        row['refrigerant_type'] = corrected_refrigerant_type

        return Model(**row)
    
    except Exception as e:
        raise e


def create_s3c13_2_data(row, Model:S3C13_2_DownstreamLeasedAuto, cache=None, **kwargs):
    abbrv_dict = {
    }
    try:
        # Verify and correct fuel type
        allowed_fuel_type = cache.get_allowed_fuel_type(fuel_state='liquid')
        corrected_fuel_type = verify_and_correct(row, 'fuel_type', allowed_fuel_type, abbrv_dict)
        row['fuel_type'] = corrected_fuel_type
        
        # Verify and correct refrigerant type
        allowed_refrigerant_type = cache.get_allowed_refrigerants()
        corrected_refrigerant_type = verify_and_correct(row, 'refrigerant_type', allowed_refrigerant_type, abbrv_dict)
        row['refrigerant_type'] = corrected_refrigerant_type
            
        return Model(**row)
    
    except Exception as e:
        raise e


#---Category 14---#
def create_s3c14_data(row, Model:S3C14_Franchise, geolocator=None, cache=None, **kwargs):
    abbrv_dict = {
        'r433': 'R-433A',
    }
    try:
        # Use lat lon info first if provided 
        if geolocator:
            if 'lat' not in [None] and 'lon' not in [None]:
                try:
                    geo_fields = geolocator.get_fields_from_latlon(row['lat'], row['lon'])
                    inferred_state = geo_fields.get('state_name')
                    inferred_country = geo_fields.get('country_name')    
                    row['state'] = inferred_state
                    row['country'] = inferred_country

                except Exception as e:
                    print(e)

        # Correct country and state using abbreviation mapping and fuzzy matching
        if 'country' in row and row['country'] is not None:
            corrected_country = find_closest_category(row['country'], cache.get_allowed_countries(), abbrv_dict=LOCATION_ABBRV)
            row['country'] = corrected_country if corrected_country else None

        if 'state' in row and row['state'] is not None:
            valid_states = cache.get_allowed_states(country=row['country'])
            corrected_state = find_closest_category(row['state'], valid_states, abbrv_dict=LOCATION_ABBRV)
            row['state'] = corrected_state if corrected_state else None

        
        # Verify and correct refrigerant type
        allowed_refrigerant_type = cache.get_allowed_refrigerants()
        corrected_refrigerant_type = verify_and_correct(row, 'refrigerant_type', allowed_refrigerant_type, abbrv_dict)
        row['refrigerant_type'] = corrected_refrigerant_type
            
        return Model(**row)
    
    except Exception as e:
        raise e

#
