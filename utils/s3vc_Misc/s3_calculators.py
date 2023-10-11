import streamlit as st

import random
from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field
from pydantic import model_validator
from typing import Optional, Dict, Union, Any

from supabase import create_client

from utils.utility import find_closest_category, supabase_query_v2
from utils.ghg_utils import get_relevant_factors, calculate_co2e
from utils.geolocator import GeoLocator
from utils.s3vc_Misc.s3_models import *
from utils.s3vc_Misc.s3_creators import *
from utils.s3vc_Misc.s3_cache import S3_Lookup_Cache

#-------------
# Supabase
#-------------

supabase_url= st.secrets['supabase_url']
supabase_anon_key= st.secrets['supabase_anon_key']
supabase = create_client(supabase_url, supabase_anon_key)

#----------
# Calculator
#----------
class S3_Calculator(BaseModel):    
    cache: Optional[Any] = None # added Any to support streamlit states
    calculated_emissions: Optional[Dict] = None
    best_emissions: Dict[str,float] = {}
    total_emissions: float = 0.0
      
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = self.cache or {}
        self.calculated_emissions = self.calculated_emissions or {}

    def add_data(self, data: S3_BaseModel):
        try:
            if not isinstance(data, S3_BaseModel):
                raise TypeError('Data not of expected data type. Expect S3_BaseModel.')
            
            # Logic to get the required emission factors
            res = self._calculate_emissions(data, cache=self.cache)
            if res is None:
                print('Unable to calculate emissions for data')
                return
            
            # Create emission result dict
            emission_result = res
            idx = len(self.calculated_emissions)
            self.calculated_emissions[idx] = {'input_data': data.model_dump(), 'calculated_emissions': emission_result}
            
        except TypeError as te:
            print(te)
        except Exception as e:
            raise e
            
        # Update best_quality_emissions and total_emissions
        self._update_emissions_summary()
            
        
    def _calculate_emissions(self, data: S3_BaseModel, cache):
        if isinstance(data, (S3C1_PurchasedGoods)):
            res = calc_S3C1_PurchasedGoods(data)
            
        elif isinstance(data, (S3C2_CapitalGoods)):
            res = calc_S3C2_CapitalGoods(data)
            
        elif isinstance(data, (S3C3_EnergyRelated)):
            res = calc_S3C3_EnergyRelated(data)
            
        elif isinstance(data, (S3C4_UpstreamTransport)):
            res = calc_S3C4_UpstreamTransport(data, cache)
            
        elif isinstance(data, (S3C5_WasteGenerated)):
            res = calc_S3C5_WasteGenerated(data, cache)
            
        elif isinstance(data, (S3C6_1_BusinessTravel, S3C6_2_BusinessStay)):
            res = calc_S3C6_BusinessTravel(data, cache)
            
        elif isinstance(data, (S3C7_EmployeeCommute)):
            res = calc_S3C7_EmployeeCommute(data, cache)
            
        elif isinstance(data, (S3C8_1_UpstreamLeasedEstate, S3C8_2_UpstreamLeasedAuto)):
            res = calc_S3C8_UpstreamLeased(data, cache)

        elif isinstance(data, (S3C9_DownstreamTransport)):
            res = calc_S3C9_DownstreamTransport(data, cache)

        elif isinstance(data, (S3C10_ProcessingProducts)):
            res = calc_S3C10_ProcessingProducts(data, cache)

        elif isinstance(data, (S3C11_UseOfSold)):
            res = calc_S3C11_UseOfSold(data, cache)

        elif isinstance(data, (S3C12_EOLTreatment)):
            res = calc_S3C12_EOLTreatment(data, cache)

        elif isinstance(data, (S3C13_1_DownstreamLeasedEstate, S3C13_2_DownstreamLeasedAuto)):
            res = calc_S3C13_DownstreamLeased(data, cache)

        elif isinstance(data, (S3C14_Franchise)):
            res = calc_S3C14_Franchise(data, cache)

        else:
            res = None
            print(f'data {data} not in expected data type. Unable to calculate')
        return res

    def _update_emissions_summary(self):
        try:
            data_uuid = self.calculated_emissions[len(self.calculated_emissions) - 1]['input_data']['uuid']
            metadata = self.calculated_emissions[len(self.calculated_emissions) - 1]['calculated_emissions']['metadata']

            if not metadata:
                raise ValueError("Metadata is empty")
          
            # Extracting the emission with the lowest data quality
            emission_data = min(metadata, key=lambda x: x['data_quality'])
            emissions = emission_data['amount']

            self.best_emissions[data_uuid] = emissions
            self.total_emissions += emissions

        except ValueError as e:
            print(f"An error occurred: {e}")

    def get_emissions(self) -> Dict[str, float]:
        return self.best_emissions

    def get_total_emissions(self) -> float:
        return self.total_emissions



#--------
# Creator
#--------
def create_metadata(calculation_name, emission_amount, fields_used, data_quality):
    return {
        'calculation': calculation_name,
        'amount': emission_amount,
        'fields_used': fields_used,
        'data_quality': data_quality
    }



#---
# Helper 
#---
""" 
Currently no support for verified reported emission auditing and economic-based emissions. 
This is because both are treated the same, and there is no quantitative field to make this distinction.
Physical emissions Will require averaged factors from sector, which is impractical and low score
Client only have 1200 chars to make their case in estimation description.
"""

def calc_S3C1_PurchasedGoods(data: S3C1_PurchasedGoods):
    emission_result={}
    data_quality =5
    metadata=[]

    f1 = ['supplier_incurred_emissions']
    if all(getattr(data, field, None) is not None for field in f1):
        reported_emissions_1 = round(data.supplier_incurred_emissions, 2)
        
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )

    f2 = ['purchased_quantity', 'quantity_emission_factor']
    if all(getattr(data, field, None) is not None for field in f2):
        reported_emissions_2 = round(data.purchased_quantity * data.quantity_emission_factor, 2)
        data_quality -= 2
        
        emission_result['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C2_CapitalGoods(data: S3C2_CapitalGoods):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['supplier_incurred_emissions']
    if all(getattr(data, field, None) is not None for field in f1):
        reported_emissions_1 = round(data.supplier_incurred_emissions, 2)
        
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )

    f2 = ['purchased_quantity', 'quantity_emission_factor']
    if all(getattr(data, field, None) is not None for field in f2):
        reported_emissions_2 = round(data.purchased_quantity * data.quantity_emission_factor, 2)
        data_quality -= 1
        
        emission_result['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )
        
    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C3_EnergyRelated(data: S3C3_EnergyRelated):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['upstream_emission_factor', 'electric_use']
    if all(getattr(data, field, None) is not None for field in f1):
        reported_emissions_1 = round(data.upstream_emission_factor * data.electric_use, 2)
        data_quality -= 1.5
        
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )

    f2 = ['electric_use', 'lifecycle_emission_factor', 'combustion_emission_factor', 'energy_loss_rate']
    if all(getattr(data, field, None) is not None for field in f2):
        cost_inflation =  1 - ( 1/ (1-data.energy_loss_rate) ) # percent increase to factor due to loss
        peak_efficient_factor = data.life_cycle_emission_factor * (1 - cost_inflation) # real factor after removing percent increase to loss
        upstream = peak_efficient_factor - data.combustion_emission_factor # real factor minus combustion factor to find remaining upstream

        reported_emissions_2 = round( data.electric_use * upstream, 2)
        data_quality -= 1.5
            
        emission_result['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C4_UpstreamTransport(data: S3C4_UpstreamTransport, cache):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['distance_traveled', 'distance_unit', 'freight_type']
    if all(getattr(data, field, None) is not None for field in f1): 
        # Retrieve the emission factors from the cache
        factors = cache.get_freight_emission_factors(freight_type=data.freight_type)

        # Determine which factors to use based on the presence of weight
        if getattr(data, 'freight_weight', None) and factors.get('units') == 'mton-km':
            f1.append('freight_weight')
            unit_value = data.distance_traveled * data.freight_weight
        else:
            unit_value = data.distance_traveled
        if factors is None:
            raise ValueError("Appropriate emission factors not found.")
        
        relevant_factors =  get_relevant_factors(factors, unit='unit')
        total_co2e = calculate_co2e(relevant_factors, unit_value=unit_value)
        
        emission_result['distance_based_emissions'] = total_co2e
        data_quality -= 1
        metadata.append( create_metadata('distance_based_emissions', total_co2e, f1, data_quality) )    

    f2 = ['fuel_use', 'fuel_type', 'fuel_unit']
    if all(getattr(data, field, None) is not None for field in f2): 
        factors = cache.get_fuel_emission_factors(fuel_type=data.fuel_type)
        relevant_factors =  get_relevant_factors(factors, unit=data.fuel_unit)
        total_co2e = calculate_co2e(relevant_factors, unit_value=data.fuel_use, unit_of_interest=data.fuel_unit)    

        emission_result['use_based_emissions'] = total_co2e
        data_quality -= 2
        metadata.append( create_metadata('use_based_emissions', total_co2e, f2, data_quality) )
        
    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}

    
def calc_S3C5_WasteGenerated(data:S3C5_WasteGenerated, cache):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['waste_type', 'waste_quantity']
    if all(getattr(data, field, None) is not None for field in f1): 
        if getattr(data, 'waste_treatment_method', None):
            f1.append('waste_treatment_method')
            data_quality -= 1
            factors = cache.get_waste_emission_factors(waste_type=data.waste_type, waste_treatment_method=data.waste_treatment_method)
        else:
            factors = cache.get_waste_emission_factors(waste_type=data.waste_type) # get the first viable waste treatment method

        if factors is None:
            total_co2e = 0
        else:
            relevant_factors =  get_relevant_factors(factors, unit='unit')        
            total_co2e = calculate_co2e(relevant_factors, unit_value=data.waste_quantity)

        emission_result['physical_emissions'] = total_co2e
        data_quality -= 1
        metadata.append( create_metadata('physical_emissions', total_co2e, f1, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C6_BusinessTravel(data: Union[S3C6_1_BusinessTravel, S3C6_2_BusinessStay], cache):
    emission_result={}
    data_quality=5
    metadata=[]

    if isinstance(data, S3C6_2_BusinessStay):
        try:
            f1 = ['no_of_nights', 'hotel_emission_factor']
            total_co2e = data.no_of_nights * data.hotel_emission_factor
            emission_result['reported_emissions_1'] = total_co2e
            metadata.append( create_metadata('reported_emissions_1', total_co2e, f1, data_quality) )
            return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}
        except:
            raise
    
    else:
        f1 = ['vehicle_type', 'distance_traveled']    
        if all(getattr(data, field, None) is not None for field in f1): 
            # Retrieve the emission factors from the cache
            TABLE = 's3c6_travel_factors'
            factors = cache.get_vehicle_emission_factors(table=TABLE, vehicle_type=data.vehicle_type)
            relevant_factors =  get_relevant_factors(factors, unit='unit')
            total_co2e = calculate_co2e(relevant_factors, unit_value=data.distance_traveled)
        
            emission_result['distance_based_emissions'] = total_co2e
            data_quality -= 1
            metadata.append( create_metadata('distance_based_emissions', total_co2e, f1, data_quality) )    

        f2 = ['fuel_use', 'fuel_type', 'fuel_unit']
        if all(getattr(data, field, None) is not None for field in f2): 
            factors = cache.get_fuel_emission_factors(fuel_type=data.fuel_type)
            relevant_factors =  get_relevant_factors(factors, unit=data.fuel_unit)
            total_co2e = calculate_co2e(relevant_factors, unit_value=data.fuel_use, unit_of_interest=data.fuel_unit)    

            emission_result['use_based_emissions'] = total_co2e
            data_quality -= 1
            metadata.append( create_metadata('use_based_emissions', total_co2e, f2, data_quality) )

        return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}

 
def calc_S3C7_EmployeeCommute(data:S3C7_EmployeeCommute, cache):
    emission_result={}
    data_quality=5
    metadata=[]

    f1 = ['vehicle_type', 'distance_traveled']    
    if all(getattr(data, field, None) is not None for field in f1): 
        # Retrieve the emission factors from the cache
        TABLE = 's3c6_travel_factors'
        factors = cache.get_vehicle_emission_factors(table=TABLE, vehicle_type=data.vehicle_type)
        relevant_factors =  get_relevant_factors(factors, unit='unit')
        total_co2e = calculate_co2e(relevant_factors, unit_value=data.distance_traveled)
    
        emission_result['distance_based_emissions'] = total_co2e
        data_quality -= 1
        metadata.append( create_metadata('distance_based_emissions', total_co2e, f1, data_quality) )    

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C8_UpstreamLeased(data: Union[S3C8_1_UpstreamLeasedEstate, S3C8_2_UpstreamLeasedAuto], cache):
    emission_result={}
    data_quality=5
    metadata=[]

    if isinstance(data, S3C8_1_UpstreamLeasedEstate):  
        if getattr(data, 'electric_use', None) is not None:
            # Step 1: Check for grid_emission_factor
            grid_emission_factor = getattr(data, 'grid_emission_factor', None)
            
            # Step 2: If grid_emission_factor is None, query the cache
            if grid_emission_factor is None:
                if all(getattr(data, field, None) is not None for field in ['country']):
                    TABLE = 's2ie_gef'
                    factors = cache.get_grid_emission_factors(table=TABLE, country=data.country, state=data.state)
                    relevant_factors = get_relevant_factors(factors, unit='kwh')
                    grid_emission_factor = list(relevant_factors.values())[0]
                    data.grid_emission_factor = grid_emission_factor  # Update the data object
            
            # Step 3: Perform the calculation
            if grid_emission_factor is not None:
                total_co2e = data.electric_use * grid_emission_factor
                
                # Additional calculations for refrigerant, if applicable
                if all(getattr(data, field, None) is not None for field in ['refrigerant_use', 'refrigerant_type']):
                    factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
                    refrigerant_gwp = factors['gwp_100yr']
                    refrigerant_co2e = data.refrigerant_use * refrigerant_gwp
                    total_co2e += refrigerant_co2e
                
                # Update results
                emission_result['physical_emissions'] = total_co2e
                data_quality -= 2
                metadata.append(create_metadata('physical_emissions', total_co2e, ['electric_use', 'grid_emission_factor'], data_quality))

        f2 = ['reported_emissions']
        if all(getattr(data, field, None) is not None for field in f2): 
            total_co2e = data.reported_emissions
            
            emission_result['reported_emissions'] = total_co2e
            data_quality = 1.5
            metadata.append( create_metadata('reported_emissions', total_co2e, f2, data_quality) )            

    else:
        fields = []
        total_co2e = 0
        physical_available = False

        f1 = ['fuel_use', 'fuel_type', 'fuel_unit']
        if all(getattr(data, field, None) is not None for field in f1): 
            physical_available = True
            factors = cache.get_fuel_emission_factors(fuel_type=data.fuel_type)
            relevant_factors =  get_relevant_factors(factors, unit=data.fuel_unit)
            co2e = calculate_co2e(relevant_factors, unit_value=data.fuel_use, unit_of_interest=data.fuel_unit)
            fields += f1
            total_co2e += co2e

        f2 = ['refrigerant_use',  'refrigerant_type']
        if all(getattr(data, field, None) is not None for field in f2): 
            physical_available = True
            factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
            refrigerant_gwp = factors['gwp_100yr']
            refrigerant_co2e = data.refrigerant_use * refrigerant_gwp
            fields += f2
            total_co2e += refrigerant_co2e

        if physical_available:
            emission_result['physical_emissions'] = total_co2e
            data_quality -= 2
            metadata.append( create_metadata('physical_emissions', total_co2e, fields, data_quality) )

        f3 = ['reported_emissions']
        if all(getattr(data, field, None) is not None for field in f2): 
            total_co2e = data.reported_emissions
            
            emission_result['reported_emissions'] = total_co2e
            data_quality = 1.5
            metadata.append( create_metadata('reported_emissions', total_co2e, f3, data_quality) )  

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C9_DownstreamTransport(data: S3C9_DownstreamTransport, cache):
    emission_result={}
    data_quality=5
    metadata=[]

    f1 = ['distance_traveled', 'distance_unit', 'freight_type']
    if all(getattr(data, field, None) is not None for field in f1): 
        factors = cache.get_freight_emission_factors(freight_type=data.freight_type)

        # Determine which factors to use based on the presence of weight
        if getattr(data, 'freight_weight', None) and factors.get('units') == 'mton-km':
            f1.append('freight_weight')
            unit_value = data.distance_traveled * data.freight_weight
        else:
            unit_value = data.distance_traveled
        if factors is None:
            raise ValueError("Appropriate emission factors not found.")
        
        relevant_factors =  get_relevant_factors(factors, unit='unit')
        total_co2e = calculate_co2e(relevant_factors, unit_value=unit_value)
        
        emission_result['distance_based_emissions'] = total_co2e
        data_quality -= 1
        metadata.append( create_metadata('distance_based_emissions', total_co2e, f1, data_quality) )    

    f2 = ['fuel_use', 'fuel_type', 'fuel_unit']
    if all(getattr(data, field, None) is not None for field in f2): 
        factors = cache.get_fuel_emission_factors(fuel_type=data.fuel_type)
        relevant_factors =  get_relevant_factors(factors, unit=data.fuel_unit)
        total_co2e = calculate_co2e(relevant_factors, unit_value=data.fuel_use, unit_of_interest=data.fuel_unit)    

        emission_result['use_based_emissions'] = total_co2e
        data_quality -= 2
        metadata.append( create_metadata('use_based_emissions', total_co2e, f2, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C10_ProcessingProducts(data: S3C10_ProcessingProducts, cache):
    emission_result={}
    data_quality=5
    metadata=[]

    fields = []
    total_co2e = 0
    physical_available = False

    f1 = ['fuel_use', 'fuel_type', 'fuel_unit']
    if all(getattr(data, field, None) is not None for field in f1): 
        physical_available = True
        factors = cache.get_fuel_emission_factors(fuel_type=data.fuel_type)
        relevant_factors =  get_relevant_factors(factors, unit=data.fuel_unit)
        co2e = calculate_co2e(relevant_factors, unit_value=data.fuel_use, unit_of_interest=data.fuel_unit)
        fields += f1
        total_co2e += co2e

    f2 = ['refrigerant_use',  'refrigerant_type']
    if all(getattr(data, field, None) is not None for field in f2): 
        physical_available = True
        factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
        refrigerant_gwp = factors['gwp_100yr']
        refrigerant_co2e = data.refrigerant_use * refrigerant_gwp
        fields += f2
        total_co2e += refrigerant_co2e

    f3 = ['grid_emission_factor', 'electric_use']
    if all(getattr(data, field, None) is not None for field in f3): 
        physical_available = True
        co2e = data.grid_emission_factor * data.electric_use
        fields += f1
        total_co2e += co2e  

    if physical_available:
        emission_result['physical_emissions'] = total_co2e
        data_quality -= 2
        metadata.append( create_metadata('physical_emissions', total_co2e, fields, data_quality) )

    f4 = ['reported_emissions']
    if all(getattr(data, field, None) is not None for field in f2): 
        total_co2e = data.reported_emissions

        emission_result['reported_emissions'] = total_co2e
        data_quality = 1.5
        metadata.append( create_metadata('reported_emissions', total_co2e, f4, data_quality) )  

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C11_UseOfSold(data:S3C11_UseOfSold, cache):
    emission_result={}
    data_quality=5
    metadata=[]

    fields = []
    total_co2e = 0
    physical_available = False

    f1 = ['lifetime_usage_freq', 'number_sold']
    if all(getattr(data, field, None) is not None for field in f1): 
        fields += f1
        sum_use = data.lifetime_usage_freq * data.lifetime_usage_freq
        
        f2 = ['fuel_per_use', 'fuel_type', 'fuel_unit']
        if all(getattr(data, field, None) is not None for field in f2): 
            physical_available = True
            factors = cache.get_fuel_emission_factors(fuel_type=data.fuel_type)
            relevant_factors =  get_relevant_factors(factors, unit=data.fuel_unit)
            co2e = sum_use * calculate_co2e(relevant_factors, unit_value=data.fuel_per_use, unit_of_interest=data.fuel_unit)

            fields += f2
            total_co2e += co2e  
        
        f3 = ['electric_per_use', 'grid_emission_factor']
        if all(getattr(data, field, None) is not None for field in f3): 
            physical_available = True  
            co2e = sum_use * data.electric_per_use * data.grid_emission_factor
            fields += f3
            total_co2e += co2e         
        
        f4 = ['refrigerant_per_use', 'refrigerant_type']
        if all(getattr(data, field, None) is not None for field in f4): 
            physical_available = True
            factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
            refrigerant_gwp = factors['gwp_100yr']
            co2e = sum_use * data.refrigerant_per_use * refrigerant_gwp
            fields += f4
            total_co2e += co2e

    if physical_available:
        emission_result['physical_emissions'] = total_co2e
        data_quality -= 2
        metadata.append( create_metadata('physical_emissions', total_co2e, fields, data_quality) )
  
    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C12_EOLTreatment(data: S3C12_EOLTreatment, cache):
    emission_result={}
    data_quality=5
    metadata=[]

    f1 = ['waste_type', 'waste_quantity']
    if all(getattr(data, field, None) is not None for field in f1): 
        if getattr(data, 'waste_treatment_method', None):
            f1.append('waste_treatment_method')
            data_quality -= 1
            factors = cache.get_waste_emission_factors(waste_type=data.waste_type, waste_treatment_method=data.waste_treatment_method)
        else:
            factors = cache.get_waste_emission_factors(waste_type=data.waste_type) # get the first viable waste treatment method

        relevant_factors =  get_relevant_factors(factors, unit='unit')
        total_co2e = calculate_co2e(relevant_factors, unit_value=data.waste_quantity)

        emission_result['physical_emissions'] = total_co2e
        data_quality -= 1
        metadata.append( create_metadata('physical_emissions', total_co2e, f1, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C13_DownstreamLeased(data: Union[S3C13_1_DownstreamLeasedEstate, S3C13_2_DownstreamLeasedAuto], cache):
    emission_result={}
    data_quality=5
    metadata=[]

    if isinstance(data, S3C13_1_DownstreamLeasedEstate):  
        if getattr(data, 'electric_use', None) is not None:
            # Step 1: Check for grid_emission_factor
            grid_emission_factor = getattr(data, 'grid_emission_factor', None)
            
            # Step 2: If grid_emission_factor is None, query the cache
            if grid_emission_factor is None:
                if all(getattr(data, field, None) is not None for field in ['country']):
                    TABLE = 's2ie_gef'
                    factors = cache.get_grid_emission_factors(table=TABLE, country=data.country, state=data.state)
                    relevant_factors = get_relevant_factors(factors, unit='kwh')
                    grid_emission_factor = list(relevant_factors.values())[0]
                    data.grid_emission_factor = grid_emission_factor  # Update the data object
            
            # Step 3: Perform the calculation
            if grid_emission_factor is not None:
                total_co2e = data.electric_use * grid_emission_factor
                
                # Additional calculations for refrigerant, if applicable
                if all(getattr(data, field, None) is not None for field in ['refrigerant_use', 'refrigerant_type']):
                    factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
                    refrigerant_gwp = factors['gwp_100yr']
                    refrigerant_co2e = data.refrigerant_use * refrigerant_gwp
                    total_co2e += refrigerant_co2e
                
                # Update results
                emission_result['physical_emissions'] = total_co2e
                data_quality -= 2
                metadata.append(create_metadata('physical_emissions', total_co2e, ['electric_use', 'grid_emission_factor'], data_quality))

        f2 = ['reported_emissions']
        if all(getattr(data, field, None) is not None for field in f2): 
            total_co2e = data.reported_emissions
            
            emission_result['reported_emissions'] = total_co2e
            data_quality = 1.5
            metadata.append( create_metadata('reported_emissions', total_co2e, f2, data_quality) )            

    else:
        fields = []
        total_co2e = 0
        physical_available = False

        f1 = ['fuel_use', 'fuel_type', 'fuel_unit']
        if all(getattr(data, field, None) is not None for field in f1): 
            physical_available = True
            factors = cache.get_fuel_emission_factors(fuel_type=data.fuel_type)
            relevant_factors =  get_relevant_factors(factors, unit=data.fuel_unit)
            co2e = calculate_co2e(relevant_factors, unit_value=data.fuel_use, unit_of_interest=data.fuel_unit)
            fields += f1
            total_co2e += co2e

        f2 = ['refrigerant_use',  'refrigerant_type']
        if all(getattr(data, field, None) is not None for field in f2): 
            physical_available = True
            factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
            refrigerant_gwp = factors['gwp_100yr']
            refrigerant_co2e = data.refrigerant_use * refrigerant_gwp
            fields += f2
            total_co2e += refrigerant_co2e

        if physical_available:
            emission_result['physical_emissions'] = total_co2e
            data_quality -= 2
            metadata.append( create_metadata('physical_emissions', total_co2e, fields, data_quality) )

        f3 = ['reported_emissions']
        if all(getattr(data, field, None) is not None for field in f2): 
            total_co2e = data.reported_emissions
            
            emission_result['reported_emissions'] = total_co2e
            data_quality = 1.5
            metadata.append( create_metadata('reported_emissions', total_co2e, f3, data_quality) )  

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C14_Franchise(data: S3C14_Franchise, cache):
    emission_result={}
    data_quality=5
    metadata=[]

    fields = []
    total_co2e = 0
    physical_available = False 

    if getattr(data, 'electric_use', None) is not None:
        # Step 1: Check for grid_emission_factor
        grid_emission_factor = getattr(data, 'grid_emission_factor', None)
        
        # Step 2: If grid_emission_factor is None, query the cache
        if grid_emission_factor is None:
            if all(getattr(data, field, None) is not None for field in ['country']):
                TABLE = 's2ie_gef'
                factors = cache.get_grid_emission_factors(table=TABLE, country=data.country, state=data.state)
                relevant_factors = get_relevant_factors(factors, unit='kwh')
                grid_emission_factor = list(relevant_factors.values())[0]
                data.grid_emission_factor = grid_emission_factor  # Update the data object
        
        # Step 3: Perform the calculation
        if grid_emission_factor is not None:
            total_co2e = data.electric_use * grid_emission_factor
            
            # Additional calculations for refrigerant, if applicable
            if all(getattr(data, field, None) is not None for field in ['refrigerant_use', 'refrigerant_type']):
                factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
                refrigerant_gwp = factors['gwp_100yr']
                refrigerant_co2e = data.refrigerant_use * refrigerant_gwp
                total_co2e += refrigerant_co2e
            
            # Update results
            emission_result['physical_emissions'] = total_co2e
            data_quality -= 2
            metadata.append(create_metadata('physical_emissions', total_co2e, ['electric_use', 'grid_emission_factor'], data_quality))

    f2 = ['refrigerant_use',  'refrigerant_type']
    if all(getattr(data, field, None) is not None for field in f2): 
        factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
        refrigerant_gwp = factors['gwp_100yr']
        co2e = data.refrigerant_use * refrigerant_gwp

        physical_available = True
        fields += f2
        total_co2e += co2e
        
    if physical_available:    
        emission_result['physical_emissions'] = total_co2e
        data_quality -= 2
        metadata.append( create_metadata('physical_emissions', total_co2e, f2, data_quality) )   

    f3 = ['reported_emissions']
    if all(getattr(data, field, None) is not None for field in f3): 
        total_co2e = data.reported_emissions
        
        emission_result['reported_emissions'] = total_co2e
        data_quality = 1.5
        metadata.append( create_metadata('reported_emissions', total_co2e, f3, data_quality) )      

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


#--
# Test
#--
def random_data(cls, cache):
    special_field_generators = {
        'travel_mode': lambda: random.choice(['rail', 'land', 'air', 'water']),
        'distance_unit': lambda: random.choice(['km']),
        'quantity_unit': lambda: random.choice(['kg', 'litre', 'm3', 'count', None]),
        
        'freight_type': lambda: random.choice(cache.get_allowed_freight_type()),
        'vehicle_type': lambda: random.choice(cache.get_allowed_vehicle_type(table='s3c6_travel_factors')),
        
        'fuel_type': lambda: random.choice(cache.get_allowed_fuel_type()),
        'fuel_unit': lambda: random.choice(['litre']),
    
        'waste_state': lambda: random.choice(['solid', 'liquid', 'gas']),
        'waste_type': lambda: random.choice(cache.get_allowed_waste_type()),
        'waste_unit': lambda: random.choice(['kg', 'litre', 'm3']),
        'waste_treatment_method': lambda: random.choice(cache.get_allowed_waste_treatment_method()),
        
        'refrigerant_type': lambda: random.choice(cache.get_allowed_refrigerants()),
        'state': lambda: 'Malacca',
        'country': lambda: 'Malaysia',
    }

    data = {}
    for field, field_info in cls.model_fields.items():
        if field in special_field_generators:
            data[field] = special_field_generators[field]()
            continue

        annotation = field_info.annotation
        is_optional = False

        if annotation:
            if 'Union' in str(annotation) or 'Optional' in str(annotation):
                is_optional = True
                annotation = annotation.__args__[0]  # Take the first type for simplicity
                
        if annotation == str:
            data[field] = f"{field}_{random.randint(1, 100)}"
        elif annotation == int:
            data[field] = random.randint(1, 1)
        elif annotation == float:
            data[field] = random.uniform(0, 1)
        elif annotation == datetime:
            data[field] = datetime.now()
        elif annotation == uuid4:
            data[field] = uuid4()
        elif annotation == bool:
            data[field] = random.choice([True, False])
        else:
            print(f"Unhandled field type: {field} with annotation {annotation}")
            
    return cls(**data)


def calculator_test():
    cache = S3_Lookup_Cache()
    calc = S3_Calculator(cache=cache)


    error_logs = []
    for _ in range(10):
        try:
            calc.add_data(random_data(S3C1_PurchasedGoods, cache))
            calc.add_data(random_data(S3C2_CapitalGoods, cache))
            calc.add_data(random_data(S3C3_EnergyRelated, cache))
            calc.add_data(random_data(S3C4_UpstreamTransport, cache))
            calc.add_data(random_data(S3C5_WasteGenerated, cache))
            calc.add_data(random_data(S3C6_1_BusinessTravel, cache))
            calc.add_data(random_data(S3C6_2_BusinessStay, cache))
            calc.add_data(random_data(S3C7_EmployeeCommute, cache))  
            calc.add_data(random_data(S3C8_1_UpstreamLeasedEstate, cache))
            calc.add_data(random_data(S3C8_2_UpstreamLeasedAuto, cache))
            calc.add_data(random_data(S3C9_DownstreamTransport, cache))
            calc.add_data(random_data(S3C10_ProcessingProducts, cache))
            calc.add_data(random_data(S3C11_UseOfSold, cache))
            calc.add_data(random_data(S3C12_EOLTreatment, cache))
            calc.add_data(random_data(S3C13_1_DownstreamLeasedEstate, cache))
            calc.add_data(random_data(S3C13_2_DownstreamLeasedAuto, cache))
            calc.add_data(random_data(S3C14_Franchise, cache))
        except Exception as e:
            error_logs.append(str(e))
    
    return error_logs


def calculator_test(calc=None, cache=None, count=2):
    if not cache:
        cache = S3_Lookup_Cache()
    if not calc:
        calc = S3_Calculator(cache=cache)

    models = [
        S3C1_PurchasedGoods, 
        S3C2_CapitalGoods, 
        S3C3_EnergyRelated, 
        S3C4_UpstreamTransport, 
        S3C5_WasteGenerated, 
        S3C6_1_BusinessTravel, 
        S3C7_EmployeeCommute,
        S3C8_1_UpstreamLeasedEstate,
        S3C8_2_UpstreamLeasedAuto,
        S3C9_DownstreamTransport,
        S3C10_ProcessingProducts,
        S3C11_UseOfSold,
        S3C12_EOLTreatment,
        S3C13_1_DownstreamLeasedEstate,
        S3C13_2_DownstreamLeasedAuto,
        S3C14_Franchise
    ]
    
    error_logs = []
    success_counter = {model.__name__: 0 for model in models}

    for i in range(count):
        for model in models:
            try:
                data = random_data(model, cache)
                calc.add_data(data)
                success_counter[model.__name__] += 1
            except Exception as e:
                error_logs.append({
                    'iteration': i,
                    'model': model.__name__,
                    'error': str(e),
                    'data': data.model_dump() if 'model_dump' in dir(data) else data
                })

    return {'success_counter': success_counter, 'error_logs': error_logs}