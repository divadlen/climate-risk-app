import streamlit as st

import json
import re
import uuid

import pandas as pd
import numpy as np
from collections import Counter

from pydantic import BaseModel, Field
from pydantic import model_validator
from typing import Optional, Dict, Union, Any

from supabase import create_client
from .utility import find_closest_category

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


def get_lookup_from_S1MC(table='s1mc_v2', vehicle_type=None, fuel_type=None):
    # very inefficient query I hate this so much
    
    url = supabase_url 
    key = supabase_anon_key
    supabase = create_client(url, key)
    query_builder = supabase.table(table).select('vehicle_type', 'fuel_type', 'year', 'units', 'kgCO2_km', 'gCH4_km', 'gN2O_km')
    query_builder = query_builder.filter('units', 'eq', 'vehicle-km')
    
    if vehicle_type:
        query_builder = query_builder.filter('vehicle_type', 'eq', vehicle_type)
    if fuel_type:
        query_builder = query_builder.filter('fuel_type', 'eq', fuel_type)
    
    try:
        response = query_builder.execute()
        data = response.data
    except Exception as e:
        raise e
        
    if data == []:
        raise Exception('No data retrieved. Vehicle not supported.')
    # If fuel_type is not provided, find the most common one
    if fuel_type is None and vehicle_type:
        fuel_counter = Counter(i['fuel_type'] for i in data)
        most_common_fuel = fuel_counter.most_common(1)[0][0]
        data = [i for i in data if i['fuel_type'] == most_common_fuel]
        
    # Sort by year and take the latest entry
    data = sorted(data, key=lambda x: x.get('year', 0), reverse=True)
    latest_data = data[0] if data else None
    return latest_data


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
    

def create_vehicle_data(cache, **kwargs):
    """
    cache: S1MC_Lookup_Cache instance
    """
    vehicle_type = kwargs.get('vehicle_type')
    distance_unit = kwargs.get('distance_unit')
    fuel_state = kwargs.get('fuel_state')
    fuel_type = kwargs.get('fuel_type')
    
    # Assume fuel is liquid state if not input
    if fuel_state is None:
        kwargs['fuel_state'] = 'liquid' 
    if distance_unit is None:
        kwargs['distance_unit'] = 'km'
    
    allowed_vehicles = cache.get_allowed_vehicles()
    if vehicle_type is not None and vehicle_type not in allowed_vehicles:
        corrected_vehicle = find_closest_category(vehicle_type, allowed_vehicles)
        if corrected_vehicle is not None:
            print(f'Warning: Input "{vehicle_type}" has been corrected to "{corrected_vehicle}"')
            kwargs['vehicle_type'] = corrected_vehicle
            vehicle_type = corrected_vehicle
        else:
            raise ValueError(f'Invalid vehicle_type. Allowed types in {allowed_vehicles}')
            
    allowed_fuel_types = cache.get_allowed_fuel_types(vehicle_type)
    if fuel_type is not None and fuel_type not in allowed_fuel_types:
        corrected_fuel = find_closest_category(fuel_type, allowed_fuel_types)
        if corrected_fuel is not None:
            print(f'Warning: Input "{fuel_type}" has been corrected to "{corrected_fuel}"')
            kwargs['fuel_type'] = corrected_fuel
            fuel_type = corrected_fuel
        else:
            raise ValueError(f'Invalid fuel type for vehicle "{vehicle_type}". Allowed types in "{allowed_fuel_types}"')
    
    return VehicleData(**kwargs)
    
#--Pydantic Models--#
class S1MC_Lookup_Cache(BaseModel):
    from functools import lru_cache
    
    _allowed_fuel_types_cache: dict = {}
    _allowed_vehicles_cache: dict = {}
    _vehicle_emission_factors_cache: dict = {}
        
    def get_allowed_vehicles(self):
        if self._allowed_vehicles_cache != {}:
            return self._allowed_vehicles_cache['vehicles']
        
        # If not in cache, query DB.
        TABLE = f's1mc_v2'
        records = supabase_query(TABLE, supabase_url, supabase_anon_key)
        allowed_vehicles = set(item['vehicle_type'] for item in records)
        allowed_vehicles = sorted(list(allowed_vehicles))
        self._allowed_vehicles_cache['vehicles'] = allowed_vehicles
        return allowed_vehicles
    

    def get_allowed_fuel_types(self, vehicle_type):
        """
        Slight modification from S1SC. Uses vehicle type, not fuel state. 
        """
        if vehicle_type in self._allowed_fuel_types_cache:
            return self._allowed_fuel_types_cache[vehicle_type]
        
        TABLE = f's1mc_v2'
        query_builder = supabase.table(TABLE).select('vehicle_type', 'fuel_type')
        query_builder = query_builder.filter('units', 'eq', 'vehicle-km')
        query_builder = query_builder.filter('vehicle_type', 'eq', vehicle_type)
        response = query_builder.execute()
        records = response.data
        
        if records not in [[], None]:
            allowed_fuel_types = set(item['fuel_type'] for item in records)
            self._allowed_fuel_types_cache[vehicle_type] = allowed_fuel_types
            return allowed_fuel_types
        return None
    
    
    def get_vehicle_emission_factors(self, table: str, vehicle_type: str, fuel_type: str):
        cache_key = f"{table}_{vehicle_type}_{fuel_type}"
        if cache_key in self._vehicle_emission_factors_cache:
            print(f"{cache_key} discovered, skipping database query.") 
            return self._vehicle_emission_factors_cache[cache_key]

        row = get_lookup_from_S1MC(table, vehicle_type=vehicle_type, fuel_type=fuel_type)
        self._vehicle_emission_factors_cache[cache_key] = row
        return row
    
    
    def to_dict(self):
        return {
            "_allowed_fuel_types_cache": self._allowed_fuel_types_cache,
            "_allowed_vehicle_cache": self._allowed_vehicle_cache,
            "_vehicle_emission_factors_cache": self._vehicle_emission_factors_cache,
        }
    

class VehicleData(BaseModel):
    uuid: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = Field(None, max_length=1600)     
        
    vehicle_type: str = Field(default='car')
    distance: Optional[float] = Field(None, ge=0)
    distance_unit: Optional[str] = Field(default='km')
    
    fuel_state: Optional[str] = Field(default='liquid')
    fuel_type: Optional[str] = Field(default='petrol')
    fuel_consumption: Optional[float] = Field(None, ge=0)
    fuel_unit: Optional[str] = Field(default='litre')

    @model_validator(mode='before')
    def validate_vehicle_data(cls, values):
        vehicle_type = values.get('vehicle_type')
        distance = values.get('distance')
        distance_unit = values.get('distance_unit')
        
        fuel_state = values.get('fuel_state')
        fuel_type = values.get('fuel_type')
        fuel_consumption = values.get('fuel_consumption')
        fuel_unit = values.get('fuel_unit')
        
        # validate state
        valid_states = ['gas', 'liquid', 'solid', None]
        if fuel_state is None:
            values['fuel_state'] = 'liquid'
        elif fuel_state not in valid_states:
            raise ValueError(f'Invalid fuel state. Must be within {valid_states}')
            
        # validate distance unit
        supported_distance_unit = ['km']
        if distance_unit is None:
            values['distance_unit'] = 'km'
        elif distance_unit not in supported_distance_unit:
            raise ValueError(f'Invalid distance unit. Supported distance unit {supported_distance_unit}')

        # validate unit
        if fuel_consumption is not None and fuel_consumption > 0 and fuel_unit is not None:
            supported_gas_measurements=['m3', 'mmBtu']
            supported_liquid_measurements=['litre', 'mmBtu']
            supported_solid_measurements=['mton', 'kg', 'mmBtu']

            if fuel_state in ['gas'] and fuel_unit not in supported_gas_measurements:
                raise Exception(f"Fuel unit for gas must be in {supported_gas_measurements}")
            if fuel_state in ['liquid'] and fuel_unit not in supported_liquid_measurements:
                raise Exception(f"Fuel unit for liquid must be in {supported_liquid_measurements}")
            if fuel_state in ['solid'] and fuel_unit not in supported_solid_measurements:
                raise Exception(f"Fuel unit for solid must be in {supported_solid_measurements}")
                            
        return values
    

class EmissionResult(BaseModel):    
    emission_factors: Dict[str, float]  # Example: {'CO2': 53.06, 'NO2': 0.1, ...}
    
    co2_emission: Optional[float] = Field(None)
    ch4_emission: Optional[float] = Field(None)
    n2o_emission: Optional[float] = Field(None)
        
    distance_based_co2e: Optional[float] = Field(None)
    fuel_based_co2e: Optional[float] = Field(None)
    most_reliable_co2e: Optional[float] = Field(None)
        
    validation_score: Optional[int] = Field(None)
    recon_score: Optional[float] = Field(None)


class S1MC_CalculatorTool(BaseModel):    
    cache: Union[S1MC_Lookup_Cache, Any] # added Any to support streamlit states
    calculated_emissions: Dict[int, Dict[str, Union[VehicleData, EmissionResult]]] = Field({})
    
    class Config:
        arbitrary_types_allowed = True

    def add_vehicle_data(self, v: VehicleData):
        if not isinstance(v, VehicleData):
            raise ValueError("Expected an VehicleData instance.")
        
        #--Calculate distance-based--#
        try:
            TABLE = f's1mc_v2'
            factors = self.cache.get_vehicle_emission_factors(TABLE, vehicle_type=v.vehicle_type, fuel_type= v.fuel_type)     
            relevant_factors = get_relevant_factors(factors, 'km') # get only GHG columns

            # Update the fuel_type in the VehicleData instance
            v.fuel_type = factors.get('fuel_type', v.fuel_type)
        
            emissions = {}
            for ghg, factor in relevant_factors.items():
                if v.distance is not None:
                    try:
                        emissions[ghg] = self.calculate_distance_based_method(v.distance, factor)
                    except:
                        print(f'Cannot get emission {ghg} for {v.vehicle_type}--{v.fuel_type}') # 
                
            #--Perform calculations for each gas--#
            def get_emission_value(emissions, ghg):
                for key, value in emissions.items():
                    if ghg.lower() in key.lower():
                        return value
                return 0
        
            co2_emission = get_emission_value(emissions, 'CO2')
            ch4_emission = get_emission_value(emissions, 'CH4') /1000 # convert from g to kg
            n2o_emission = get_emission_value(emissions, 'N2O') /1000 # convert from g to kg
        
            # Calculate CO2e
            gwp = {'CH4': 25,'N2O': 298}
            distance_based_co2e = co2_emission + (ch4_emission * gwp['CH4']) + (n2o_emission * gwp['N2O'])
            
            #--Calculate recon score--#
            methods = {
                'distance_based': distance_based_co2e,
                # 'fuel_based': fuel_based_co2e,
            }
            reliability_order = ['distance_based']  # This can be extended in the future

             # Filter out the available methods based on the reliability order
            available_ordered = [(method, methods[method]) for method in reliability_order if methods[method] is not None]        
            most_reliable_val = available_ordered[0][1]

            if len(available_ordered) >=2:
                next_most_reliable_val = available_ordered[1][1]
                if next_most_reliable_val > 0 and most_reliable_val > 0:
                    recon_score = round( 100 - abs((most_reliable_val - next_most_reliable_val)/ most_reliable_val * 100), 2)
                else:
                    recon_score = None
            else:
                recon_score = None

            #--Final result--#            
            calculated_emissions = EmissionResult(
                emission_factors=relevant_factors,
                co2_emission=co2_emission,
                ch4_emission=ch4_emission,
                n2o_emission=n2o_emission,
                distance_based_co2e=distance_based_co2e,
                most_reliable_co2e=most_reliable_val,
                recon_score=recon_score
            )     
            
        except:
            print(f'Cannot retrieve emission factor for {v.vehicle_type}, {v.fuel_type}. Unable to calculate emission score')
            calculated_emissions = EmissionResult(
                emission_factors={},
                co2_emission=None,
                ch4_emission=None,
                n2o_emission=None,
                distance_based_co2e=None,
                most_reliable_co2e=None,
                recon_score=0
            )    

        key = len(self.calculated_emissions)
        self.calculated_emissions[key] = {'vehicle': v, 'calculated_emissions': calculated_emissions}
        
    def calculate_distance_based_method(self, distance:float, distance_emission_factor:float) -> float:
        return distance * distance_emission_factor
        
    def calculate_fuel_based_method(self, fuel_consumption: float, fuel_emission_factor: float) -> float:
        """Calculate emissions using the emission factor method (Eq1)"""
        return fuel_consumption * fuel_emission_factor
    
    def get_total_co2e(self):
        total_co2e = 0
        
        for emission in self.calculated_emissions.values():
            if emission['calculated_emissions'].most_reliable_co2e is not None:
                total_co2e += emission['calculated_emissions'].most_reliable_co2e

        return round(total_co2e, 2)