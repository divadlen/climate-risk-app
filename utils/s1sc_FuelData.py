import streamlit as st

import json
import re
import uuid

import pandas as pd
import numpy as np

from pydantic import BaseModel, Field, constr
from pydantic import root_validator, field_validator, model_validator
from typing import Optional, Dict, Union, Any

from supabase import create_client


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


def get_lookup_from_supabase(table, fuel_type_col, fuel_type, url, key):
    """
    - table: str
        Name of table in supabase
    - fuel_type_col: str
        Name of column containing fuel type information
    - fuel_type: str
        Name of fuel
    - url, key:
        Supabase url and anon key
    """
    supabase = create_client(url, key)
    query_builder = supabase.table(table).select('*')
    query_builder = query_builder.filter(fuel_type_col, 'eq', fuel_type)
    
    try:
        response = query_builder.execute()
    except Exception as e:
        raise e
    return response.data


def get_emission_factors(table: str, fuel_type: str):
    """Extension for `get_lookup_from_supabase`"""
    row = get_lookup_from_supabase(table, fuel_type_col='fuel_type', fuel_type=fuel_type, url=supabase_url, key=supabase_anon_key)
    return row


def get_relevant_factors(factors, fuel_unit):
    relevant_factors = {}
    chemicals = ['co2', 'ch4', 'n2o'] # expand when needed
    
    # Retrieve all columns with the specified fuel_unit in it
    for key, value in factors.items():
        if re.search(f'_{fuel_unit}', key, re.IGNORECASE):
            
            # Retrieve all remaining columns containing chemicals
            for chem in chemicals:
                if re.search(chem, key, re.IGNORECASE):
                    chemical_name = key
                    relevant_factors[chemical_name] = value
                    break           
    return relevant_factors


def create_fuel_data(cache, **kwargs):
    fuel_state = kwargs.get('fuel_state')
    fuel_type = kwargs.get('fuel_type')

    # Validate fuel state and type using fuel_type_cache
    allowed_fuel_types = cache.get_allowed_fuel_types(fuel_state, lookup=None)
    if fuel_type not in allowed_fuel_types:
        raise ValueError(f'Invalid fuel type for fuel state `{fuel_state}`. Allowed types in `{allowed_fuel_types}`')

    # Create and return a FuelData instance
    return FuelData(**kwargs)


class S1SC_Lookup_Cache(BaseModel):
    from functools import lru_cache
    
    _allowed_fuel_types_cache: dict = {}
    _emission_factors_cache: dict = {}

    def get_allowed_fuel_types(self, fuel_state: str, lookup: Optional[list] = None):
        if fuel_state in self._allowed_fuel_types_cache:
            return self._allowed_fuel_types_cache[fuel_state]
        
        if lookup: # If lookup is provided, no need to query the database, else query supabase
            allowed_fuel_types = [item['fuel_type'] for item in lookup]
        else:
            TABLE = f's1sc_{fuel_state}'
            records = supabase_query(TABLE, supabase_url, supabase_anon_key)
            allowed_fuel_types = [item['fuel_type'] for item in records]

        self._allowed_fuel_types_cache[fuel_state] = allowed_fuel_types
        return allowed_fuel_types  
    
    def get_emission_factors(self, table: str, fuel_type: str):
        cache_key = f"{table}_{fuel_type}"
        if cache_key in self._emission_factors_cache:
            print(f"{cache_key} discovered, skipping database query.") # 
            return self._emission_factors_cache[cache_key]

        row = get_lookup_from_supabase(table, fuel_type_col='fuel_type', fuel_type=fuel_type, url=supabase_url, key=supabase_anon_key)
        self._emission_factors_cache[cache_key] = row
        return row
    
    def to_dict(self):
      return {
        "_allowed_fuel_types_cache": self._allowed_fuel_types_cache,
        "_emission_factors_cache": self._emission_factors_cache,
      }


class FuelData(BaseModel):
    uuid: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique identifier for the fuel data")
    description: Optional[str] = Field(None, max_length=255)        
    sector: str
    fuel_state: str  
    fuel_type: str
    fuel_consumption: Optional[float] = Field(None, ge=0)
    fuel_unit: Optional[str] = Field(None)
    heating_value: Optional[str] = Field(None)        
    fuel_spend: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(None)    

    @model_validator(mode='before')
    def validate_fuel_data(cls, values):
        fuel_state = values.get('fuel_state')
        fuel_type = values.get('fuel_type')
        fuel_consumption = values.get('fuel_consumption')
        fuel_unit = values.get('fuel_unit')
        heating_value = values.get('heating_value')
        fuel_spend = values.get('fuel_spend')
        currency = values.get('currency')

        # validate state
        valid_states = ['gas', 'liquid', 'solid']
        if fuel_state not in valid_states:
            raise ValueError(f'Invalid fuel state. Must be within {valid_states}')

        # validate unit
        if fuel_consumption is not None and fuel_consumption > 0:
            supported_gas_measurements=['m3', 'mmBtu']
            supported_liquid_measurements=['litre', 'mmBtu']
            supported_solid_measurements=['mton', 'kg', 'lb', 'mmBtu']

            if fuel_state in ['gas'] and fuel_unit not in supported_gas_measurements:
                raise Exception(f"Fuel unit for gas must be in {supported_gas_measurements}")
            if fuel_state in ['liquid'] and fuel_unit not in supported_liquid_measurements:
                raise Exception(f"Fuel unit for liquid must be in {supported_liquid_measurements}")
            if fuel_state in ['solid'] and fuel_unit not in supported_solid_measurements:
                raise Exception(f"Fuel unit for solid must be in {supported_solid_measurements}")
            
        # validate heating_value
        supported_heating_value = ['high', 'low']
        if heating_value is None:
            values['heating_value'] = 'low'
        elif heating_value not in supported_heating_value:
            raise Exception(f"Heating value must be in {supported_heating_value}. Default 'low'.")
            
        # validate currency
        supported_currency = ['USD', 'MYR', 'SGD']
        if fuel_spend is not None and fuel_spend > 0:
            if currency is None:
                values['currency'] = 'USD'
            elif currency not in supported_currency:
                raise Exception(f"Currency must be in {supported_currency}")
                
        return values
    

class FuelDataCalculation(BaseModel):    
    emission_factors: Dict[str, float]  # Example: {'CO2': 53.06, 'NO2': 0.1, ...}
    
    co2_emission: Optional[float] = Field(None)
    ch4_emission: Optional[float] = Field(None)
    n2o_emission: Optional[float] = Field(None)
        
    fuel_based_co2e: Optional[float] = Field(None)
    spend_based_co2e: Optional[float] = Field(None)
    most_reliable_co2e: Optional[float] = Field(None)
        
    validation_score: Optional[int] = Field(None)
    recon_score: Optional[float] = Field(None)


class FuelCalculatorTool(BaseModel):    
    cache: Union[S1SC_Lookup_Cache, Any] # added Any to support streamlit states
    calculated_emissions: Dict[int, Dict[str, Union[FuelData, FuelDataCalculation]]] = Field({})
    
    class Config:
        arbitrary_types_allowed = True

    def add_fuel_data(self, fuel: FuelData):
        if not isinstance(fuel, FuelData):
            raise ValueError("Expected an FuelData instance.")
        
        #--Calculate fuel-based--#
        table = f's1sc_{fuel.fuel_state}'
        # factors = get_emission_factors(table, fuel.fuel_type)[0] # no cache support
        factors = self.cache.get_emission_factors(table, fuel.fuel_type)[0] # cache support
        relevant_factors = get_relevant_factors(factors, fuel.fuel_unit) # get relevant columns
        
        emissions = {}
        for ghg, factor in relevant_factors.items():
            if fuel.fuel_consumption is not None:
                try:
                    emissions[ghg] = self.calculate_fuel_based_method(fuel.fuel_consumption, factor)
                except:
                
                    #-----------
                    print(f'Cannot get emission {ghg} for {fuel}') # 
                    #--------
                
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
        fuel_based_co2e = co2_emission + (ch4_emission * gwp['CH4']) + (n2o_emission * gwp['N2O'])
        spend_based_co2e = self.calculate_fuel_spend_method(fuel.fuel_spend, 0.2)
        
        #--Calculate recon score--#
        methods = {
            'fuel_based': fuel_based_co2e,
            'spend_based': spend_based_co2e
        }
        reliability_order = ['fuel_based', 'spend_based']  # This can be extended in the future
        
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
        calculation_result = FuelDataCalculation(
            fuel_data=fuel,
            emission_factors=relevant_factors,
            co2_emission=co2_emission,
            ch4_emission=ch4_emission,
            n2o_emission=n2o_emission,
            fuel_based_co2e=fuel_based_co2e,
            spend_based_co2e=spend_based_co2e,
            most_reliable_co2e=most_reliable_val,
            recon_score=recon_score
        )     
        
        key = len(self.calculated_emissions)
        self.calculated_emissions[key] = {'fuel': fuel, 'calculation_result': calculation_result}
        
    def calculate_fuel_based_method(self, fuel_consumption: float, fuel_emission_factor: float) -> float:
        """Calculate emissions using the emission factor method (Eq1)"""
        return fuel_consumption * fuel_emission_factor
    
    def calculate_fuel_spend_method(self, fuel_spend, spend_emission_factor: float=0.2) -> float:
        """Calculate the amount of fuel cost by price (Eq4)"""
        if fuel_spend is not None:
            return fuel_spend * spend_emission_factor
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
            calculation_data = emission['calculation_result'].model_dump()
            merged_data = {**fuel_data, **calculation_data}
            data.append(merged_data)
        return pd.DataFrame(data)