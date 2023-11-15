import random

from pydantic import BaseModel
from typing import Optional, Dict, Union, Any

from utils.utility import clamp
from utils.ghg_utils import get_relevant_factors
from utils.s2ie_Misc.s2_models import S2_PurchasedPower, S2_BaseModel
from utils.s3vc_Misc.s3_cache import S3_Lookup_Cache


#----------
# Calculator
#----------
class S2_Calculator(BaseModel):    
    cache: Optional[Any] = None # added Any to support streamlit states
    calculated_emissions: Optional[Dict] = None
    best_emissions: Dict[str,float] = {}
    total_emissions: float = 0.0
      
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = self.cache or {}
        self.calculated_emissions = self.calculated_emissions or {}

    def add_data(self, data: S2_BaseModel):
        try:
            if not isinstance(data, S2_BaseModel):
                raise TypeError('Data not of expected data type. Expect S2_BaseModel.')
            
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
            
        
    def _calculate_emissions(self, data: S2_BaseModel, cache):
        if isinstance(data, (S2_PurchasedPower)): 
            res = calc_S2_PurchasedPower(data, cache=cache)
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

def calc_S2_PurchasedPower(data, cache):
    emission_result = {}
    data_quality = 5
    metadata = []

    if getattr(data, 'energy_type', None) != 'electric':
        return {'emission_result': emission_result, 'data_quality': round(data_quality, 2), 'metadata': metadata}

    if getattr(data, 'energy_use', None) is None:
        return {'emission_result': emission_result, 'data_quality': round(data_quality, 2), 'metadata': metadata}

    if not all(getattr(data, field, None) is not None for field in ['country']):
        return {'emission_result': emission_result, 'data_quality': round(data_quality, 2), 'metadata': metadata}
    
    if not all(getattr(data, field, None) is not None for field in ['lat', 'lon']):
        data_quality -= round( random.uniform(0.3, 0.7), 2 )

    if not all(getattr(data, field, None) is not None for field in ['energy_spend', 'currency']):
        data_quality -= round( random.uniform(0.3, 0.7), 2)

    TABLE = 's2ie_gef'
    factors = cache.get_grid_emission_factors(table=TABLE, country=data.country, state=data.state)
    relevant_factors = get_relevant_factors(factors, unit='kwh')

    if not relevant_factors or len(relevant_factors.values()) == 0:
        print("No relevant factors found.")
        return {'emission_result': emission_result, 'data_quality': round(data_quality, 2), 'metadata': metadata}

    grid_emission_factor = list(relevant_factors.values())[0]
    if grid_emission_factor is None:
        return {'emission_result': emission_result, 'data_quality': round(data_quality, 2), 'metadata': metadata}

    total_co2e = data.energy_use * grid_emission_factor
    emission_result['physical_emissions'] = total_co2e
    data_quality -= 2
    metadata.append(create_metadata('physical_emissions', total_co2e, ['energy_use', 'grid_emission_factor'], round(data_quality, 2)))

    data_quality = clamp(data_quality)
    return {'emission_result': emission_result, 'data_quality': round(data_quality, 2), 'metadata': metadata}

