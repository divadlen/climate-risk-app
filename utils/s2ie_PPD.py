import streamlit as st

from datetime import datetime
from dateutil import parser
import pandas as pd
import numpy as np
import re
import uuid

from pydantic import BaseModel, Field
from pydantic import model_validator
from typing import Optional, Dict, Union, Tuple, ClassVar, Any

from supabase import create_client

from .utility import find_closest_category
from .geolocator import GeoLocator

supabase_url= st.secrets['supabase_url']
supabase_anon_key= st.secrets['supabase_anon_key']
supabase = create_client(supabase_url, supabase_anon_key)


def supabase_query(table:str, url:str, key:str, limit: Optional[int]=10000):
    supabase = create_client(url, key)
    query_builder = supabase.table(table).select("*")
    if limit is not None:
        query_builder = query_builder.limit(limit)

    try:
        response = query_builder.execute()
    except Exception as e:
        raise e

    if response.data in ([], None):
        print(f'No data found for `{table}`. Make sure RLS is turned off.')
    return response.data


def get_lookup_from_S2IE(table='s2ie_gef', country='malaysia', state='Peninsular', energy_provider='TNB', default=None):
    url = supabase_url 
    key = supabase_anon_key
    supabase = create_client(url, key)

    if country is None:
        country = 'Malaysia'
        state = 'Peninsular'
    if state is None:
        state = 'Peninsular'
    
    # Fetch unique countries and states for spell check
    unique_countries = [row['country'] for row in supabase.table(table).select('country').execute().data]
    unique_states = [row['state'] for row in supabase.table(table).select('state').execute().data]
    
    # Spell check
    corrected_country = find_closest_category(country, unique_countries)
    corrected_state = find_closest_category(state, unique_states)
    
    query_builder = supabase.table(table).select('*')
    
    if corrected_country:
        query_builder = query_builder.filter('country', 'eq', corrected_country)
    if corrected_state:
        query_builder = query_builder.filter('state', 'eq', corrected_state)
    if energy_provider:
        query_builder = query_builder.filter('energy_provider', 'eq', energy_provider)
    
    try:
        response = query_builder.execute()
        data = response.data
    except Exception as e:
        raise e
    
    if data == []:
        if default is not None:
            return default
        else:
            raise Exception(f'No data retrieved. Query: {corrected_country}, {corrected_state}, {energy_provider}')
    
    # Sort by year and take the latest entry
    data = sorted(data, key=lambda x: x.get('year', 0), reverse=True)
    latest_data = data[0] if data else None
    return latest_data



def get_relevant_factors(factors, unit):
    """
    unit: the suffix for column EG: _kwh, _mton, _litre
    """
    relevant_factors = {}
    chemicals = ['co2', 'ch4', 'n2o'] # expand when needed
    
    # Retrieve all columns with the specified fuel_unit in it
    for key, value in factors.items():
        if re.search(f'_{unit}', key, re.IGNORECASE):
            
            # Retrieve all remaining columns containing chemicals
            for chem in chemicals:
                if re.search(chem, key, re.IGNORECASE):
                    chemical_name = key
                    relevant_factors[chemical_name] = value
                    break           
    return relevant_factors


class S2IE_Lookup_Cache(BaseModel):
    from functools import lru_cache

    _allowed_countries_cache: dict = {}
    _allowed_states_cache: dict = {}
    _grid_emission_factors_cache: dict = {}

    def get_allowed_countries(self):
        if 'countries' in self._allowed_countries_cache:
            return self._allowed_countries_cache['countries']
        
        TABLE = 'locations_country_code'
        records = supabase_query(TABLE, supabase_url, supabase_anon_key)
        allowed_countries = set(item['name'] for item in records)
        allowed_countries = sorted(list(allowed_countries))
        
        self._allowed_countries_cache['countries'] = allowed_countries
        return allowed_countries
    
    
    def get_allowed_states(self, country):
        if country in self._allowed_states_cache:
            return self._allowed_states_cache[country]
        
        if country not in [None, [], np.nan]:
          TABLE = 'locations_states'
          query_builder = supabase.table(TABLE).select('state_name', 'country_name')
          query_builder = query_builder.filter('country_name', 'eq', country)
          response = query_builder.execute()
          records = response.data
          
          if records not in [[], None]:
              allowed_states = list(set(item['state_name'] for item in records))
              self._allowed_states_cache[country] = allowed_states
              return allowed_states
          return None
        return None
    
    
    def get_grid_emission_factors(self, table='s2ie_gef', country='my', state='Peninsular', energy_provider=None):
        cache_key = f"{table}_{country}_{state}_{energy_provider}"
        if cache_key in self._grid_emission_factors_cache:
            print(f"{cache_key} discovered, skipping database query.") # 
            return self._grid_emission_factors_cache[cache_key]

        try:
            row = get_lookup_from_S2IE(table, country, state, energy_provider)
            if row in [None, {}]:
                self._grid_emission_factors_cache[cache_key] = {}
                raise Exception(f'No data retrieved. Query: {cache_key}')  
            self._grid_emission_factors_cache[cache_key] = row
            return row

        except Exception as e:
            self._grid_emission_factors_cache[cache_key] = {}
            raise e
          
    
    def to_dict(self):
        return {
            "_allowed_countries_cache": self._allowed_countries_cache,
            "_allowed_states_cache": self._allowed_states_cache,
            "_grid_emission_factors_cache": self._grid_emission_factors_cache,
        }
    

class S2_PurchasedPowerData(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = Field(None, max_length=1600)
        
    branch: Optional[str] = Field(None, max_length=1600)
    department: Optional[str] = Field(None, max_length=255)    
    owned: Optional[bool] = Field(default=True)
        
    street_address_1: Optional[str] = Field(None, max_length=35)
    street_address_2: Optional[str] = Field(None, max_length=35)
    city: Optional[str] = Field(None, max_length=35)
    state: Optional[str] = Field(None, max_length=99)
    country: Optional[str] = Field(None, max_length=35)
    postcode: Optional[Union[str, int]] = Field(None)    
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    
    date: Optional[Union[str, datetime]] = Field(None) 
    
    energy_type: Optional[str] = Field(default='electric')
    energy_consumption: Optional[float] = Field(None, ge=0)
    energy_unit: Optional[str] = Field(default='kwh')
    energy_spend: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(default='USD')
    energy_provider: Optional[str] = Field(None, max_length=99)
        
    @model_validator(mode='before')
    def validate_PPD(cls, values):
        owned = values.get('owned')
        city = values.get('city')
        state = values.get('state')
        country = values.get('country')
        postcode = values.get('postcode')
        lat = values.get('lat')
        lon = values.get('lon')
    
        date = values.get('date')
        energy_type = values.get('energy_type')
        energy_consumption = values.get('energy_consumption')
        energy_unit = values.get('energy_unit')
        energy_spend = values.get('energy_spend')
        currency = values.get('currency')
        
        # Set defaults
        if owned is None:
            values['owned'] = True
        if energy_type is None:
            values['energy_type'] = 'electric'
        if energy_unit is None:
            values['energy_unit'] = 'kwh'
            
            
        # validate location
        if country is None and state is None:
            if lat is None or lon is None:
                raise ValueError('Unable to verify address. Must fill at least one field: "country", "state". Or provide values for both "lat" and "lon"!')
            
        # # validate postcode len (cannot do this during pydantic bc int/str union)
        # if len(str(postcode)) > 6:
        #     raise ValueError('Postcode too long. Commonly 5-6 digits. EG:46000, "46000"')
            
            
        # validate_date
        if date is None:
            values['date'] = datetime.now().strftime('%Y-%m-%d')
        else:
            try:
                parsed_date = parser.parse(date)
                values['date'] = parsed_date.strftime('%Y-%m-%d')
            except:
                raise ValueError('Invalid date format. Try inputing in YYYY-MM-DD')
        
        # validate energy type
        supported_types = ['electric'] # steam, heat, cool
        if energy_type not in [None, '']:
            energy_type_lower = energy_type.lower()
            if energy_type_lower not in supported_types:
                raise ValueError(f'Invalid "energy_type", must be in {supported_types}')
            values['energy_type'] = energy_type_lower
            
        # validate unit
        supported_units = ['kwh'] # GWh, kJ
        if energy_unit not in [None, '']:
            energy_unit_lower = energy_unit.lower()
            if energy_unit_lower not in supported_units:
                raise ValueError(f'Invalid "energy_unit", must be in {supported_units}. To gain support for a new unit measurement, please send a ticker request.')
            values['energy_unit'] = energy_unit_lower
        
        # validate currency
        supported_currency = ['usd', 'myr', 'sgd']
        if energy_spend is not None and energy_spend > 0:
            if currency is None:
                values['currency'] = 'myr'
            else:
                currency_lower = currency.lower()
                if currency_lower not in supported_currency:
                    raise ValueError(f'Currency must be in {supported_currency}')
                values['currency'] = currency_lower
                
        return values
    

class S2IE_EmissionResult(BaseModel):    
    emission_factors: Dict[str, float]  # Example: {'CO2': 53.06, 'NO2': 0.1, ...}
    
    co2_emission: Optional[float] = Field(None)
    ch4_emission: Optional[float] = Field(None)
    n2o_emission: Optional[float] = Field(None)
        
    use_based_co2e: Optional[float] = Field(None)
    spend_based_co2e: Optional[float] = Field(None)
    most_reliable_co2e: Optional[float] = Field(None)
        
    validation_score: Optional[int] = Field(None)
    recon_score: Optional[float] = Field(None)


class S2IE_CalculatorTool(BaseModel):    
    cache: Union[S2IE_Lookup_Cache, Any] # added Any to support streamlit states
    calculated_emissions: Dict[int, Dict[str, Union[S2_PurchasedPowerData, S2IE_EmissionResult]]] = Field({})
    
    class Config:
        arbitrary_types_allowed = True

    def add_power_data(self, ppd: S2_PurchasedPowerData):
        if not isinstance(ppd, S2_PurchasedPowerData):
            raise ValueError("Expected a S2_PurchasedPowerData instance.")
        
        #--Calculate use-based--#
        TABLE = f's2ie_gef'
        country = ppd.country
        state = ppd.state 
        energy_provider = None # ppd.energy_provider # not supported for now

        # conditional states
        if country not in [None] and country.lower() in ['malaysia']:
            if state not in [None] and state.lower() not in ['sabah', 'sarawak']:
                state = 'Peninsular'
        
        factors = self.cache.get_grid_emission_factors(TABLE, country, state, energy_provider)
        relevant_factors = get_relevant_factors(factors, unit='kwh')
        
        # grid has no ch4 or n2o measurements for now
        emissions = {}
        for ghg, factor in relevant_factors.items():
            if ppd.energy_consumption is not None:
                try:
                    emissions[ghg] = self.calculate_use_based_method(ppd.energy_consumption, factor)
                except:                    
                    print(f'Cannot get emission {ghg} for {ppd}') # 

                
        #--Perform calculations for each gas--#
        def get_emission_value(emissions, ghg): 
            for key, value in emissions.items():
                if ghg.lower() in key.lower():
                    return value
            return 0
        
        co2_emission = get_emission_value(emissions, 'CO2')
        ch4_emission = get_emission_value(emissions, 'CH4') /1000 # convert from g to kg
        n2o_emission = get_emission_value(emissions, 'N2O') /1000 # convert from g to kg
        
        # GWP dictionary
        gwp = {
            'CH4': 25,
            'N2O': 298,
        }
        
        #--Calculate CO2e--#
        use_based_co2e = co2_emission + (ch4_emission * gwp['CH4']) + (n2o_emission * gwp['N2O'])
        spend_based_co2e = self.calculate_spend_based_method(ppd.energy_spend, 0)
        
        #--Calculate recon score--#
        methods = {
            'use_based': use_based_co2e,
            'spend_based': spend_based_co2e
        }
        reliability_order = ['use_based', 'spend_based']  # This can be extended in the future
        
         # Filter out the available methods based on the reliability order
        available_ordered = [(method, methods[method]) for method in reliability_order if methods[method] is not None]        
        most_reliable_val = available_ordered[0][1]
        
        if len(available_ordered) >=2:
            next_most_reliable_val = available_ordered[1][1]
            if next_most_reliable_val > 0 and most_reliable_val > 0:
                r = abs(most_reliable_val - next_most_reliable_val)
                adj_r = min( r/most_reliable_val, r/next_most_reliable_val )
                recon_score = round( 100*(1-adj_r), 2)
            else:
                recon_score = None
        else:
            recon_score = None
        
        #--Final result--#            
        calculated_emissions = S2IE_EmissionResult(
            emission_factors=relevant_factors,
            co2_emission=co2_emission,
            ch4_emission=ch4_emission,
            n2o_emission=n2o_emission,
            use_based_co2e=use_based_co2e,
            spend_based_co2e=spend_based_co2e,
            most_reliable_co2e=most_reliable_val,
            recon_score=recon_score
        )     
        
        key = len(self.calculated_emissions)
        self.calculated_emissions[key] = {'purchased_power_data': ppd, 'calculated_emissions': calculated_emissions}
        
    def calculate_use_based_method(self, consumption: float, emission_factor: float) -> float:
        """Calculate emissions using the emission factor method (Eq1)"""
        return consumption * emission_factor
    
    def calculate_spend_based_method(self, spend, spend_emission_factor: float=0.2) -> float:
        """Calculate emissions by price (Eq4)"""
        if spend is not None:
            return spend * spend_emission_factor
        return None
    
    def get_total_co2e(self):
        total_co2e = 0
        for emission in self.calculated_emissions.values():
            total_co2e += emission['calculated_emissions'].most_reliable_co2e
        
        return round(total_co2e, 2)
    
    def to_df(self) -> pd.DataFrame:
        data = []
        for emission in self.calculated_emissions.values():
            fuel_data = emission['fuel'].model_dump()
            calculation_data = emission['calculated_emissions'].model_dump()
            merged_data = {**fuel_data, **calculation_data}
            data.append(merged_data)
        return pd.DataFrame(data)
    

def create_ppd_data(cache: S2IE_Lookup_Cache, geolocater: GeoLocator, **kwargs):
    lat = kwargs.get('lat')
    lon = kwargs.get('lon')
    
    # If lat and lon are provided, update kwargs with the values from get_fields_from_latlon
    if lat is not None and lon is not None:
        print(f'Lat lon values discovered. Will replace state and country values to the matching lat lon.')
        geo_fields = geolocater.get_fields_from_latlon(lat, lon)
        kwargs.update({
            'state': geo_fields.get('state_name'),
            'country': geo_fields.get('country_name'),
        })
    
    city = kwargs.get('city')
    state = kwargs.get('state')
    country = kwargs.get('country')
    postcode = kwargs.get('postcode')
    
    # fuzzy match might return unintentional results
    abbrv_map = {
        'usa': 'United States of America',
        'united states': 'united of america',
        'uk': 'United Kingdom',
        'korea': 'south korea',
        'my': 'malaysia',
        'melaka': 'malacca'
    }
        
    # Verify country
    if country not in [None, '']:
        allowed_countries = cache.get_allowed_countries()
              
        if country not in allowed_countries:
            corrected_country = find_closest_category(country, allowed_countries, abbrv_dict=abbrv_map) 
        
            if corrected_country not in [None]:
                print(f'Country input "{country}" has been corrected to "{corrected_country}"')
                kwargs['country'] = corrected_country
                country = corrected_country
            else:
                raise ValueError(f"Country {country} not found. Try using the full name of the country instead of alpha-2 or alpha-3 codes.")
    
    # verify state
    if country not in [None, '']:
        allowed_states = cache.get_allowed_states(country=country)
        
        if state not in [None, '']:
            if allowed_states not in [None] and state not in allowed_states:    
                corrected_state = find_closest_category(state, allowed_states, abbrv_dict=abbrv_map)
        
                if corrected_state not in [None]:
                    print(f'State input "{state}" has been corrected to "{corrected_state}"')
                    kwargs['state'] = corrected_state
                    state = corrected_state
                else:
                    raise ValueError(f"State {state} not found for {country}. Allowed states in {allowed_states}")
        
    return S2_PurchasedPowerData(**kwargs)