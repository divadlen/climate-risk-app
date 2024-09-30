from pydantic import BaseModel, Field
from utils.utility import find_closest_category, supabase_query_v2


#-----
# Cache
#-----
class S3_Lookup_Cache(BaseModel):
    from functools import lru_cache
    cache: dict = {}
        
    #--Helper--#
    def __repr__(self):
        return f"<S3_Lookup_Cache: {len(self.cache)} items>"
    
    def _generate_cache_key(self, table, **kwargs):
        sorted_items = sorted(kwargs.items())
        return f"{table}_{'_'.join([f'{k}_{v}' for k, v in sorted_items])}"
    
    def _query_and_cache_uniques(self, cache_key, table, column, additional_filters=None):
        """ 
        1. Search cache for key. If key, return result. 
        2. If key not found, use QueryV2 to search TABLE, then COL. 
        3. From column, sort and filter all available values and return as result. 
        """
        if cache_key in self.cache:
            return self.cache[cache_key]

        if additional_filters:
            records = supabase_query_v2(table=table, **additional_filters)
        else:
            records = supabase_query_v2(table=table)

        if records not in [[], None]:
            allowed_values = sorted(list(set(item[column] for item in records)))
            
             # Handle edge case where all values are None
            if allowed_values == [None]:
                self.cache[cache_key] = None
                return None
        
            self.cache[cache_key] = allowed_values
            return allowed_values
        return None
    

    #--- Get allowed options from column from table
    def get_allowed_countries(self):
        CACHE_KEY = 'allowed_countries'
        TABLE = 'locations_country_code'
        COUNTRY_COL = 'name'
        
        result = self._query_and_cache_uniques(cache_key=CACHE_KEY, table=TABLE, column=COUNTRY_COL, additional_filters=None)
        return result
    
    
    def get_allowed_states(self, country=None):
        CACHE_KEY = f'allowed_states_{country}'
        TABLE = 'locations_states'
        STATE_COL = 'state_name'
        ADDITIONAL_FILTERS = {'country_name': country}
        
        result = self._query_and_cache_uniques(CACHE_KEY, TABLE, STATE_COL, ADDITIONAL_FILTERS)
        return result
        
    
    def get_allowed_fuel_type(self, fuel_state='liquid'):
        CACHE_KEY = f'allowed_fuel_{fuel_state}'
        TABLE = f's1sc_{fuel_state}'
        FUEL_COL = 'fuel_type'
        ADDITIONAL_FILTERS = {}
        
        result = self._query_and_cache_uniques(CACHE_KEY, TABLE, FUEL_COL, ADDITIONAL_FILTERS)
        return result
        
    
    def get_allowed_vehicle_type(self, table='s1mc_v2'):
        CACHE_KEY = f'allowed_vehicle_type_{table}'
        TABLE = table
        VEHICLE_COL = 'vehicle_type'
        
        result = self._query_and_cache_uniques(CACHE_KEY, TABLE, VEHICLE_COL)
        return result
    
    
    def get_allowed_freight_type(self):
        CACHE_KEY = 'allowed_freight_type'
        TABLE = 's3c4_freight_factors'
        FREIGHT_COL = 'freight_type'

        result = self._query_and_cache_uniques(CACHE_KEY, TABLE, FREIGHT_COL)
        return result
    
    
    def get_allowed_waste_type(self):
        CACHE_KEY = 'allowed_waste_type'
        TABLE = 's3c5_waste_factors'
        MATERIAL_COL = 'waste_type'
        
        result = self._query_and_cache_uniques(CACHE_KEY, TABLE, MATERIAL_COL)
        return result
        
    
    def get_allowed_waste_treatment_method(self, waste_type=None):
        CACHE_KEY = f'allowed_waste_treatment_method_{waste_type}' if waste_type else 'allowed_waste_treatment_method'
        TABLE = 's3c5_waste_factors'
        TREATMENT_COL = 'waste_treatment_method'

        ADDITIONAL_FILTERS = {}
        if waste_type:
            ADDITIONAL_FILTERS['waste_type'] = waste_type

        result = self._query_and_cache_uniques(CACHE_KEY, TABLE, TREATMENT_COL, ADDITIONAL_FILTERS)
        return result
    
    
    def get_allowed_refrigerants(self):
        CACHE_KEY = 'allowed_refrigerants'
        TABLE = 'ghg_refrigerants_gwp_v2'
        REFRIGERANT_COL = 'ashrae_number'
        
        result = self._query_and_cache_uniques(CACHE_KEY, TABLE, REFRIGERANT_COL)
        return result
    
    
    #--- Get emission factors ---#
    def get_freight_emission_factors(self, **kwargs):
        TABLE = 's3c4_freight_factors'
        CACHE_KEY = self._generate_cache_key(table=TABLE, **kwargs)
        
        if CACHE_KEY in self.cache:
            print(f"{CACHE_KEY} discovered, skipping database query")
            return self.cache[CACHE_KEY]
        
        else:
            records = supabase_query_v2(table=TABLE, **kwargs)
            first_record = records[0]
            self.cache[CACHE_KEY] = first_record
            return first_record


    def get_fuel_emission_factors(self, fuel_state='liquid', fuel_type='Petroleum'):
        TABLE = f's1sc_{fuel_state}'
        CACHE_KEY = self._generate_cache_key(table=TABLE, fuel_type=fuel_type)
        
        if CACHE_KEY in self.cache:
            print(f"{CACHE_KEY} discovered, skipping database query")
            return self.cache[CACHE_KEY]
            
        else:
            records = supabase_query_v2(table=TABLE, fuel_type=fuel_type)
            first_record = records[0]
            self.cache[CACHE_KEY] = first_record
            return first_record
  
    
    def get_grid_emission_factors(self, table='s2ie_gef', country='malaysia', state=None, energy_provider=None):
        CACHE_KEY = self._generate_cache_key(table=table, country=country, state=state, energy_provider=energy_provider)
        UNIQUE_COUNTRIES_KEY = f"{table}_unique_countries"
        UNIQUE_STATES_KEY = f"{table}_unique_states"

        if CACHE_KEY in self.cache:
            print(f"{CACHE_KEY} discovered, skipping database query.")
            return self.cache[CACHE_KEY]

        try:
            # Fetch unique countries and states for spell check
            if UNIQUE_COUNTRIES_KEY not in self.cache:
                self.cache[UNIQUE_COUNTRIES_KEY] = list(set(row['country'] for row in supabase_query_v2(table=table, select='country')))

            if UNIQUE_STATES_KEY not in self.cache:
                self.cache[UNIQUE_STATES_KEY] = list(set(row['state'] for row in supabase_query_v2(table=table, select='state')))

            unique_countries = self.cache[UNIQUE_COUNTRIES_KEY]
            unique_states = self.cache[UNIQUE_STATES_KEY]
            
            # Spell check
            corrected_country = find_closest_category(country, unique_countries)
            corrected_state = find_closest_category(state, unique_states)

            # Query the database
            records = supabase_query_v2(table=table, country=corrected_country, state=corrected_state, energy_provider=energy_provider)

            if not records:
                self.cache[CACHE_KEY] = {}
                raise Exception(f'No data retrieved. Query: {CACHE_KEY}')

            # Sort by year and take the latest entry
            records = sorted(records, key=lambda x: x.get('year', 0) or 0, reverse=True)
            latest_data = records[0] if records else None

            self.cache[CACHE_KEY] = latest_data
            return latest_data

        except Exception as e:
            self.cache[CACHE_KEY] = {}
            raise e
        
          
    def get_waste_emission_factors(self, waste_type='Aluminum Cans', **kwargs):
        TABLE = f's3c5_waste_factors'
        CACHE_KEY = self._generate_cache_key(table=TABLE, waste_type=waste_type, **kwargs)
        
        if CACHE_KEY in self.cache:
            print(f"{CACHE_KEY} discovered, skipping database query")
            return self.cache[CACHE_KEY]
        
        else:
            records = supabase_query_v2(table=TABLE, waste_type=waste_type, **kwargs)
            filtered_records = [record for record in records if record.get('kgCO2_unit') is not None]
            
            if not filtered_records:
                return None
            
            first_record = filtered_records[0]
            self.cache[CACHE_KEY] = first_record
            return first_record
        

    def get_vehicle_emission_factors(self, table='s3c6_travel_factors', **kwargs):
        """ 
        There are lots of different tables you can get vehicle travel factors from.
        Default s3c6. 
        """
        TABLE = table
        CACHE_KEY = self._generate_cache_key(table=TABLE, **kwargs)
        
        if CACHE_KEY in self.cache:
            print(f"{CACHE_KEY} discovered, skipping database query")
            return self.cache[CACHE_KEY]
        
        else:
            records = supabase_query_v2(table=TABLE, **kwargs)
            first_record = records[0]
            self.cache[CACHE_KEY] = first_record
            return first_record   
        

    def get_refrigerant_gwp(self, refrigerant_type, **kwargs):
        """
        Not the best implementation. 
        Refrigerants are often mixture of gases. 
        ASHRAE is also not intuitive for lay people. 
        """
        TABLE='ghg_refrigerants_gwp_v2'
        CACHE_KEY = self._generate_cache_key(table=TABLE, ashrae_number=refrigerant_type, **kwargs)
        
        if CACHE_KEY in self.cache:
            print(f"{CACHE_KEY} discovered, skipping database query")
            return self.cache[CACHE_KEY]
        
        else:
            records = supabase_query_v2(table=TABLE, ashrae_number=refrigerant_type, **kwargs)
            first_record = records[0]
            self.cache[CACHE_KEY] = first_record
            return first_record
        
        