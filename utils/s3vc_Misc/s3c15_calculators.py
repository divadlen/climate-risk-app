from pydantic import BaseModel, Field
from pydantic import model_validator
from typing import Optional, Dict, List, Union, Tuple, ClassVar, Any
from utils.s3vc_Misc.s3c15_models import *

#----------
# Calculator
#----------
class S3C15_Calculator(BaseModel):    
    cache: Optional[Any] = None # added Any to support streamlit states
    calculated_emissions: Optional[Dict] = None
    best_emissions: Dict[str,float] = {}
    total_emissions: float = 0.0
      
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cache = self.cache or {}
        self.calculated_emissions = self.calculated_emissions or {}

    def add_data(self, asset: S3C15_BaseAsset):
        try:
            if not isinstance(asset, S3C15_BaseAsset):
                raise TypeError('Asset not of expected data type. Expect S3C15_BaseAsset.')
                
            res = self._calculate_emission_result(asset)
            if res is None:
                print('Unable to calculate emissions for asset')
                return
            
            # Create an EmissionResult object
            emission_result = res
            idx = len(self.calculated_emissions)
            self.calculated_emissions[idx] = {'input_data': asset.model_dump(), 'calculated_emissions': emission_result}
            
        except TypeError as te:
            print(te)
        except Exception as e:
            raise e
            
        # Update best_quality_emissions and total_emissions
        self._update_emissions_summary()
            
        
    def _calculate_emission_result(self, asset: S3C15_BaseAsset):
        if isinstance(asset, (S3C15_1A_ListedEquity)):
            res = calc_S3C15_1A_ListedEquity(asset)
            
        elif isinstance(asset, (S3C15_1B_UnlistedEquity, S3C15_1C_CorporateBonds)):
            res = calc_S3C15_1B_1C(asset)
            
        elif isinstance(asset, (S3C15_1D_BusinessLoans)):
            res = calc_S3C15_1D_BusinessLoans(asset)
            
        elif isinstance(asset, (S3C15_1E_CommercialRealEstate, S3C15_2A_Mortgage)):
            res = calc_S3C15_1E_2A(asset)
            
        elif isinstance(asset, (S3C15_2B_VehicleLoans)):
            res = calc_S3C15_2B_VehicleLoans(asset)
            
        elif isinstance(asset, (S3C15_3_ProjectFinance)):
            res = calc_S3C15_3_ProjectFinance(asset)
            
        elif isinstance(asset, (S3C15_4_EmissionRemovals)):
            res = calc_S3C15_4_EmissionRemovals(asset)
            
        elif isinstance(asset, (S3C15_5_SovereignDebt)):
            res = calc_S3C15_5_SovereignDebt(asset)
        else:
            res = None
            print(f'Asset {asset} not in expected data type. Unable to calculate')
        return res

    def _update_emissions_summary(self):
        try:
            asset_uuid = self.calculated_emissions[len(self.calculated_emissions) - 1]['input_data']['uuid']
            metadata = self.calculated_emissions[len(self.calculated_emissions) - 1]['calculated_emissions']['metadata']

            if not metadata:
                raise ValueError("Metadata is empty")
          
            # Extracting the emission with the lowest data quality
            emission_data = min(metadata, key=lambda x: x['data_quality'])
            emissions = emission_data['amount']

            self.best_emissions[asset_uuid] = emissions
            self.total_emissions += emissions

        except ValueError as e:
          print(f"An error occurred: {e}")

    def get_emissions(self) -> Dict[str, float]:
        return self.best_emissions

    def get_total_emissions(self) -> float:
        return self.total_emissions
    

#---
# Helper 
#---
def create_metadata(calculation_name, emission_amount, fields_used, data_quality):
    return {
        'calculation': calculation_name,
        'amount': emission_amount,
        'fields_used': fields_used,
        'data_quality': data_quality
    }

def create_s3c15_data(row, Model):
    """ 
    Boilerplate used to create S3C15 Models from rows of a dataframe. 
    Model( row.to_dict() ) is not reliable as using values from a df directly may not be compatible with Pydantic models

    Params:
    Model: 
      The model that will be using row values to be created under (EG: S3C15_1A, S3C15_2A)

    Recommended new params:
      cache: Lookup cache dictionary to check for dupe entry
      geolocator
    """
    try:
        return Model(**row)
    except Exception as e:
        raise e
    


""" 
Currently no support for verified reported emission auditing and economic-based emissions. 
This is because both are treated the same, and there is no quantitative field to make this distinction.
Physical emissions Will require averaged factors from sector, which is impractical and low score
Client only have 1200 chars to make their case in estimation description.
"""

def calc_S3C15_1A_ListedEquity(asset: S3C15_1A_ListedEquity):
    emission_result={}
    data_quality =5
    metadata=[]

    f1 = ['attribution_share', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f1):
        reported_emissions_1 = round(asset.attribution_share * asset.reported_emissions, 2)
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )

    f2 = ['outstanding_amount', 'enterprise_value', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f2):
        reported_emissions_2 = round( (asset.outstanding_amount / asset.enterprise_value) * asset.reported_emissions, 2)
        data_quality -= 1
        emission_result['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )

    # When you must estimate emissions
    if getattr(asset, 'reported_emissions', None) is None:
        ef1 = ['estimated_emissions']
        if all(getattr(asset, field, None) is not None for field in ef1):
            estimated_emissions = asset.estimated_emissions
            emission_result['estimated_emissions'] = estimated_emissions
            metadata.append( create_metadata('estimated_emissions', estimated_emissions, ef1, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C15_1B_1C(asset: Union[S3C15_1B_UnlistedEquity, S3C15_1C_CorporateBonds]):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['attribution_share', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f1):
        reported_emissions_1 = round(asset.attribution_share * asset.reported_emissions, 2)
        
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )

    f2 = ['outstanding_amount', 'total_equity', 'total_debt', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f2):
        EV = asset.total_equity + asset.total_debt
        reported_emissions_2 = round( (asset.outstanding_amount / EV) * asset.reported_emissions, 2)
        data_quality -= 1
        
        emission_result['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )

    # When you must estimate emissions
    if getattr(asset, 'reported_emissions', None) is None:
        ef1 = ['estimated_emissions']
        if all(getattr(asset, field, None) is not None for field in ef1):
            estimated_emissions = asset.estimated_emissions
            emission_result['estimated_emissions'] = estimated_emissions
            metadata.append( create_metadata('estimated_emissions', estimated_emissions, ef1, data_quality) )
        
    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C15_1D_BusinessLoans(asset: S3C15_BaseAsset):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['attribution_share', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f1):
        reported_emissions_1 = round(asset.attribution_share * asset.reported_emissions, 2)
        
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )

    if asset.is_listed == False:
        f2 = ['outstanding_amount', 'total_equity', 'total_debt', 'reported_emissions']
        if all(getattr(asset, field, None) is not None for field in f2):
            EV = asset.total_equity + asset.total_debt
            reported_emissions_2 = round( (asset.outstanding_amount / EV) * asset.reported_emissions, 2)
            data_quality -= 1
            
            emission_result['reported_emissions_2'] = reported_emissions_2
            metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )
            
    elif asset.is_listed == True:
        f2 = ['outstanding_amount', 'enterprise_value', 'reported_emissions']
        if all(getattr(asset, field, None) is not None for field in f2):
            reported_emissions_2 = round( (asset.outstanding_amount / asset.enterprise_value) * asset.reported_emissions, 2)
            data_quality -= 1
      
            emission_result['reported_emissions_2'] = reported_emissions_2
            metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )

    # When you must estimate emissions
    if getattr(asset, 'reported_emissions', None) is None:
        ef1 = ['estimated_emissions']
        if all(getattr(asset, field, None) is not None for field in ef1):
            estimated_emissions = asset.estimated_emissions
            emission_result['estimated_emissions'] = estimated_emissions
            metadata.append( create_metadata('estimated_emissions', estimated_emissions, ef1, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C15_1E_2A(asset: S3C15_BaseAsset):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['attribution_share', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f1):
        reported_emissions_1 = round(asset.attribution_share * asset.reported_emissions, 2)
        
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )
        
    f2 = ['outstanding_amount', 'property_value', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f2):
        reported_emissions_2 = round( (asset.outstanding_amount / asset.property_value) * asset.reported_emissions, 2)
        data_quality -= 1
        
        if asset.value_at_origin == True:
            data_quality -= 0.5
            
        emission_result['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )
        
    f3 = ['building_energy_use', 'building_emission_factor', 'reported_emissions', 'outstanding_amount', 'property_value']
    if all(getattr(asset, field, None) is not None for field in f3):
        building_emissions = asset.building_energy_use * asset.building_emission_factor
        physical_emissions = round( (asset.outstanding_amount / asset.property_value) * building_emissions, 2)
        data_quality -= 2
        
        emission_result['physical_emissions'] = physical_emissions
        metadata.append( create_metadata('physical_emissions', physical_emissions, f3, data_quality) )

    # When you must estimate emissions
    if getattr(asset, 'reported_emissions', None) is None:
        ef1 = ['estimated_emissions']
        if all(getattr(asset, field, None) is not None for field in ef1):
            estimated_emissions = asset.estimated_emissions
            emission_result['estimated_emissions'] = estimated_emissions
            metadata.append( create_metadata('estimated_emissions', estimated_emissions, ef1, data_quality) )
    
    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C15_2B_VehicleLoans(asset: S3C15_BaseAsset):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['attribution_share', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f1):
        reported_emissions_1 = round(asset.attribution_share * asset.reported_emissions, 2)
        
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )
        
    f2 = ['outstanding_amount', 'vehicle_value', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f2):
        reported_emissions_2 = round( (asset.outstanding_amount / asset.vehicle_value) * asset.reported_emissions, 2)
        data_quality -= 1
        
        if asset.value_at_origin == True:
            data_quality -= 0.5
        
        emission_result['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )      
            
    f3 = ['distance_traveled', 'distance_emission_factor', 'reported_emissions', 'outstanding_amount', 'vehicle_value']
    if all(getattr(asset, field, None) is not None for field in f3):
        vehicle_emissions = asset.distance_traveled * asset.distance_emission_factor
        physical_emissions = round( (asset.outstanding_amount / asset.vehicle_value) * vehicle_emissions, 2)
        data_quality -= 2
        
        emission_result['physical_emissions'] = physical_emissions
        metadata.append( create_metadata('physical_emissions', physical_emissions, f3, data_quality) )
    
    # When you must estimate emissions
    if getattr(asset, 'reported_emissions', None) is None:
        ef1 = ['estimated_emissions']
        if all(getattr(asset, field, None) is not None for field in ef1):
            estimated_emissions = asset.estimated_emissions
            emission_result['estimated_emissions'] = estimated_emissions
            metadata.append( create_metadata('estimated_emissions', estimated_emissions, ef1, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}

    
def calc_S3C15_3_ProjectFinance(asset: S3C15_BaseAsset):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['attribution_share', 'project_emissions']
    if all(getattr(asset, field, None) is not None for field in f1):
        reported_emissions_1 = round(asset.attribution_share * asset.project_emissions, 2)
        
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )
        
    f2 = ['outstanding_amount', 'total_equity', 'total_debt', 'project_emissions']
    if all(getattr(asset, field, None) is not None for field in f2):
        EV = asset.total_equity + asset.total_debt
        reported_emissions_2 = round( (asset.outstanding_amount / EV) * asset.project_emissions, 2)
        data_quality -= 1
        
        emission_result['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )

    # When you must estimate emissions
    if getattr(asset, 'project_emissions', None) is None:
        ef1 = ['estimated_emissions']
        if all(getattr(asset, field, None) is not None for field in ef1):
            estimated_emissions = asset.estimated_emissions
            emission_result['estimated_emissions'] = estimated_emissions
            metadata.append( create_metadata('estimated_emissions', estimated_emissions, ef1, data_quality) )
        
    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C15_4_EmissionRemovals(asset: S3C15_BaseAsset):
    emission_removals={}
    data_quality=5 # not required by PCAF
    metadata=[]
 
    f1 = ['attribution_share', 'emissions_removed']
    if all(getattr(asset, field, None) is not None for field in f1):
        reported_emissions_1 = round(asset.attribution_share * asset.emissions_removed, 2)
        
        emission_removals['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )
        
    f2 = ['outstanding_amount', 'enterprise_value', 'emissions_removed']
    if all(getattr(asset, field, None) is not None for field in f2):
        reported_emissions_2 = round( (asset.outstanding_amount / asset.enterprise_value) * asset.emissions_removed, 2)
        data_quality -= 1
        
        emission_removals['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )

    # When you must estimate emissions
    if getattr(asset, 'emissions_removed', None) is None:
        ef1 = ['estimated_emissions']
        if all(getattr(asset, field, None) is not None for field in ef1):
            estimated_emissions = asset.estimated_emissions
            emission_removals['estimated_emissions'] = estimated_emissions
            metadata.append( create_metadata('estimated_emissions', estimated_emissions, ef1, data_quality) )

    return {'emission_removals': emission_removals, 'data_quality': data_quality, 'metadata': metadata}


def calc_S3C15_5_SovereignDebt(asset: S3C15_BaseAsset):
    emission_result={}
    data_quality=5
    metadata=[]
    
    f1 = ['attribution_share', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f1):
        reported_emissions_1 = round(asset.attribution_share * asset.reported_emissions, 2)
        
        emission_result['reported_emissions_1'] = reported_emissions_1
        metadata.append( create_metadata('reported_emissions_1', reported_emissions_1, f1, data_quality) )
         
    f2 = ['outstanding_amount', 'PPP_adj_GDP', 'reported_emissions']
    if all(getattr(asset, field, None) is not None for field in f2):
        reported_emissions_2 = round( (asset.outstanding_amount / asset.PPP_adj_GDP) * asset.reported_emissions, 2)
        data_quality -=1
        
        emission_result['reported_emissions_2'] = reported_emissions_2
        metadata.append( create_metadata('reported_emissions_2', reported_emissions_2, f2, data_quality) )

    f3 = ['attribution_share', 'consumption_emissions']
    if all(getattr(asset, field, None) is not None for field in f3):
        physical_emissions = round(asset.attribution_share * asset.consumption_emissions, 2)
        data_quality -= 2
        
        emission_result['physical_emissions'] = physical_emissions
        metadata.append( create_metadata('physical_emissions', physical_emissions, f3, data_quality) )

    # When you must estimate emissions
    if getattr(asset, 'reported_emissions', None) is None:
        ef1 = ['estimated_emissions']
        if all(getattr(asset, field, None) is not None for field in ef1):
            estimated_emissions = asset.estimated_emissions
            emission_result['estimated_emissions'] = estimated_emissions
            metadata.append( create_metadata('estimated_emissions', estimated_emissions, ef1, data_quality) )

    return {'emission_result': emission_result, 'data_quality': data_quality, 'metadata': metadata}


#--
# Test
#--
def calculator_test():
  import random
  from datetime import datetime
  from uuid import uuid4
    
  def random_asset(cls):
      asset = {}    
      if 'company_name' in cls.model_fields:
          asset['company_name'] = f"Company_{random.randint(1, 100)}"
          
      if 'sector' in cls.model_fields:
          asset['sector'] = f"Sector_{random.randint(1, 10)}"
          
      if 'outstanding_amount' in cls.model_fields:
          asset['outstanding_amount'] = random.uniform(100, 1000)
          
      if 'attribution_share' in cls.model_fields:
          asset['attribution_share'] = random.uniform(0, 1)
          
      if 'reported_emissions' in cls.model_fields:
          asset['reported_emissions'] = random.uniform(100, 500)
          
      if 'enterprise_value' in cls.model_fields:
          asset['enterprise_value'] = random.uniform(100, 1000)
          
      if 'total_equity' in cls.model_fields:
          asset['total_equity'] = random.uniform(100, 1000)
          
      if 'total_debt' in cls.model_fields:
          asset['total_debt'] = random.uniform(100, 1000)
          
      if 'project_emissions' in cls.model_fields:
          asset['project_emissions'] = random.uniform(100, 1000)
      
      if 'value_at_origin' in cls.model_fields:
          asset['value_at_origin'] = random.choice([True, False])
      
      if 'property_value' in cls.model_fields:
          asset['property_value'] = random.uniform(100000, 200000)
      
      if 'building_energy_use' in cls.model_fields:
          asset['building_energy_use'] = random.uniform(1000, 10000)
          
      if 'building_emission_factor' in cls.model_fields:
          asset['building_emission_factor'] = random.uniform(0.2, 0.9)
          
      if 'vehicle_value' in cls.model_fields:
          asset['vehicle_value'] = random.uniform(10000, 50000)
          
      if 'distance_traveled' in cls.model_fields:
          asset['distance_traveled'] = random.uniform(10000, 100000)
          
      if 'distance_emission_factor' in cls.model_fields:
          asset['distance_emission_factor'] = random.uniform(0.2, 0.9)
      
      if 'emissions_removed' in cls.model_fields:
          asset['emissions_removed'] = random.uniform(10000, 100000)
      
      if 'country_code' in cls.model_fields:
          asset['country_code'] = random.choice(['MY', 'sg', 'uK'])
      
      if 'total_government_debt' in cls.model_fields:
          asset['total_government_debt'] = random.uniform(10000000000, 50000000000)
      
      if 'PPP_adj_GDP' in cls.model_fields:
          asset['PPP_adj_GDP'] = random.uniform(1000000000, 5000000000)
      
      if 'consumption_emissions' in cls.model_fields:
          asset['consumption_emissions'] = random.uniform(444444444444, 777777777777)
      
      return cls(**asset)
  
  try:
    calc = S3C15_Calculator()

    for _ in range(10):
      calc.add_data(random_asset(S3C15_1A_ListedEquity))
      calc.add_data(random_asset(S3C15_1B_UnlistedEquity))
      calc.add_data(random_asset(S3C15_1C_CorporateBonds))
      calc.add_data(random_asset(S3C15_1D_BusinessLoans))
      calc.add_data(random_asset(S3C15_1E_CommercialRealEstate))
      calc.add_data(random_asset(S3C15_2A_Mortgage))
      calc.add_data(random_asset(S3C15_2B_VehicleLoans))
      calc.add_data(random_asset(S3C15_3_ProjectFinance))
      calc.add_data(random_asset(S3C15_4_EmissionRemovals))
      calc.add_data(random_asset(S3C15_5_SovereignDebt))

    return calc
  
  except Exception as e:
    raise e