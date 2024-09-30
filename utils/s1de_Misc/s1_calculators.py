
import random
from typing import Optional, Dict, Union, Any

from utils.ghg_utils import get_relevant_factors, calculate_co2e
from utils.s1de_Misc.s1_models import *

#----------
# Calculator
#----------
class S1_Calculator(BaseModel):    
    cache: Optional[Any] = None # added Any to support streamlit states
    calculated_emissions: Optional[Dict] = None
    best_emissions: Dict[str,float] = {}
    total_emissions: float = 0.0
      
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = self.cache or {}
        self.calculated_emissions = self.calculated_emissions or {}

    def add_data(self, data: S1_BaseModel):
        try:
            if not isinstance(data, S1_BaseModel):
                raise TypeError('Data not of expected data type. Expect S1_BaseModel.')
            
            # Logic to get the required emission factors
            res = self._calculate_emissions(data, cache=self.cache)
            if res is None:
                print('Unable to calculate emissions for data')
                return
            
            # Create emission result dict
            emission_result = res
            idx = len(self.calculated_emissions)
            self.calculated_emissions[idx] = {'input_data': data.model_dump(), 'calculated_emissions': emission_result}

            print(emission_result)
            
        except TypeError as te:
            print(te)
        except Exception as e:
            raise e
            
        # Update best_quality_emissions and total_emissions
        self._update_emissions_summary()
            
        
    def _calculate_emissions(self, data: S1_BaseModel, cache):
        if isinstance(data, (S1_MobileCombustion)): 
            res = calc_S1_MobileCombustion(data, cache=cache)
            
        elif isinstance(data, (S1_StationaryCombustion)): 
            res = calc_S1_StationaryCombustion(data, cache=cache)
            
        elif isinstance(data, (S1_FugitiveEmission)): 
            res = calc_S1_FugitiveEmission(data, cache=cache)

        else:
            res = None
            print(f'data {data} not in expected data type. Unable to calculate')
        return res

    def _update_emissions_summary(self):
        try:
            data_uuid = self.calculated_emissions[len(self.calculated_emissions) - 1]['input_data']['uuid']
            metadata = self.calculated_emissions[len(self.calculated_emissions) - 1]['calculated_emissions']['metadata']

            if not metadata:
                raise ValueError(f"Metadata is empty for {data_uuid}")
          
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

def calc_S1_StationaryCombustion(data: S1_StationaryCombustion, cache): 
    emission_result={}
    data_quality=5
    metadata=[]

    fields = []
    total_co2e = 0
    physical_available = False

    # Useless fields, but extra score for answering
    if getattr(data, "fuel_spend", None) is not None:
        data_quality -= round( random.uniform(0.5, 1), 2)
    if getattr(data, "heating_value", None) is not None:
        data_quality -= round( random.uniform(0.5, 1), 2)

    f1 = ['fuel_use', 'fuel_type', 'fuel_unit']
    if all(getattr(data, field, None) is not None for field in f1): 
        physical_available = True
        factors = cache.get_fuel_emission_factors(fuel_type=data.fuel_type)
        relevant_factors =  get_relevant_factors(factors, unit=data.fuel_unit)
        co2e = calculate_co2e(relevant_factors, unit_value=data.fuel_use, unit_of_interest=data.fuel_unit)
        fields += f1
        total_co2e += co2e

    if physical_available:
        emission_result['physical_emissions'] = total_co2e
        data_quality -= 2
        metadata.append( create_metadata('physical_emissions', total_co2e, fields, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}



def calc_S1_MobileCombustion(data: S1_MobileCombustion, cache): 
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

    f2 = ['fuel_use', 'fuel_type', 'fuel_unit']
    if all(getattr(data, field, None) is not None for field in f2): 
        factors = cache.get_fuel_emission_factors(fuel_type=data.fuel_type)
        relevant_factors =  get_relevant_factors(factors, unit=data.fuel_unit)
        total_co2e = calculate_co2e(relevant_factors, unit_value=data.fuel_use, unit_of_interest=data.fuel_unit)    

        emission_result['use_based_emissions'] = total_co2e
        data_quality -= 1
        metadata.append( create_metadata('use_based_emissions', total_co2e, f2, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S1_FugitiveEmission(data: S1_FugitiveEmission, cache): 
    emission_result={}
    data_quality=5
    metadata=[]

    # if user knows refrigerant use
    f1 = ['refrigerant_use',  'refrigerant_type']
    if all(getattr(data, field, None) is not None for field in f1): 
        factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
        refrigerant_gwp = factors['gwp_100']
        refrigerant_co2e = data.refrigerant_use * refrigerant_gwp
        data_quality -= 2

        emission_result['reported_emissions'] = refrigerant_co2e
        metadata.append( create_metadata('reported_emissions', refrigerant_co2e, f1, data_quality) )

    # If user have means to guess refrigerant use
    refrigerant_use = None
    fields = []

    # Check for refrigerant_type
    if getattr(data, 'refrigerant_type', None) is not None:
        factors = cache.get_refrigerant_gwp(refrigerant_type=data.refrigerant_type)
        refrigerant_gwp = factors['gwp_100']
        fields.append('refrigerant_type')

        # Check for refrigerant_capacity
        if getattr(data, 'refrigerant_capacity', None) is not None:
            refrigerant_use = 0
            fields.append('refrigerant_capacity')

            # Check for install_loss_rate
            if getattr(data, 'install_loss_rate', None) is not None:
                refrigerant_use += data.install_loss_rate * data.refrigerant_capacity
                fields.append('install_loss_rate')

            # Check for recovery_rate
            if getattr(data, 'recovery_rate', None) is not None:
                refrigerant_use += (1 - data.recovery_rate) * data.refrigerant_capacity
                fields.append('recovery_rate')

            # Check for annual_leak_rate and number_of_year
            if getattr(data, 'annual_leak_rate', None) is not None and getattr(data, 'number_of_year', None) is not None:
                refrigerant_use += (data.number_of_year * data.annual_leak_rate) * data.refrigerant_capacity
                fields.append('annual_leak_rate')
                fields.append('number_of_year')

            # Ensure refrigerant_use is within bounds
            refrigerant_use = max(0, min(refrigerant_use, data.refrigerant_capacity))

            # Calculate CO2e
            if getattr(data, 'refrigerant_use', None) is not None:
                data_quality = 5

            refrigerant_co2e = refrigerant_use * refrigerant_gwp
            data_quality -=3        

            emission_result['calculated_emissions'] = refrigerant_co2e
            metadata.append(create_metadata('calculated_emissions', refrigerant_co2e, fields, data_quality))

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}