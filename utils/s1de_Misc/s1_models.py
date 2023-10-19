import uuid

from datetime import datetime
from dateutil import parser

from pydantic import BaseModel, Field
from pydantic import model_validator
from typing import Optional, Dict, List, Union, Tuple, Any


#---------------
# Input Class
#---------------
class S1_BaseModel(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: Optional[Union[datetime, str]] = Field(None) 
    description: Optional[str]= Field(None, max_length=1600)

    @model_validator(mode='before')
    def validate_BaseAsset(cls, values):    
        date = values.get('date')
        if date is None:
            values['date'] = datetime.now().strftime('%Y-%m-%d')
        elif type(date) in [datetime]:
            values['date'] = date.strftime('%Y-%m-%d')
        else:
            try:
                parsed_date = parser.parse(date)
                values['date'] = parsed_date.strftime('%Y-%m-%d')
            except:
                raise ValueError('Invalid date format. Try inputing in YYYY-MM-DD')
        return values
    

#--- Stationary combustion
class S1_StationaryCombustion(S1_BaseModel):
    """ 
    """
    branch: Optional[str] = Field(None, max_length=1600)
    sector: str = Field(default='energy')

    fuel_state: Optional[str] = Field(default='liquid')
    fuel_type: Optional[str] = Field(default='Diesel')
    fuel_use: Optional[float] = Field(None, ge=0)
    fuel_unit: Optional[str] = Field(default='litre')
    
    heating_value: Optional[float] = Field(None)        
    fuel_spend: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(default='USD') 

    @model_validator(mode='before')
    def validate_data(cls, values):
        fuel_state = values.get('fuel_state')

        # validate state
        valid_states = ['gas', 'liquid', 'solid', None]
        if fuel_state is None:
            values['fuel_state'] = 'liquid'
        elif fuel_state.lower() not in valid_states:
            raise ValueError(f'Invalid fuel state. Must be within {valid_states}')
                            
        return values


class S1_MobileCombustion(S1_BaseModel):
    """ 
    """
    branch: Optional[str] = Field(None, max_length=1600)
    sector: str = Field(default='energy')
    vehicle_type: str = Field(default='car')

    fuel_state: Optional[str] = Field(default='liquid')
    fuel_type: Optional[str] = Field(default='Diesel')
    fuel_use: Optional[float] = Field(None, ge=0)
    fuel_unit: Optional[str] = Field(default='litre')

    distance_traveled: Optional[float] = Field(None, ge=0)
    distance_unit: Optional[str] = Field(default='km')


    @model_validator(mode='before')
    def validate_data(cls, values):
        distance_unit = values.get('distance_unit')
        fuel_state = values.get('fuel_state')

        # validate state
        valid_states = ['gas', 'liquid', 'solid', None]
        if fuel_state is None:
            values['fuel_state'] = 'liquid'
        elif fuel_state.lower() not in valid_states:
            raise ValueError(f'Invalid fuel state. Must be within {valid_states}')
            
        # validate distance unit
        supported_distance_unit = ['km']
        if distance_unit is None:
            values['distance_unit'] = 'km'
        elif distance_unit.lower() not in supported_distance_unit:
            raise ValueError(f'Invalid distance unit. Supported distance unit {supported_distance_unit}')
                            
        return values
    

#--- Fugitive Emissions
class S1_FugitiveEmission(S1_BaseModel):
    """ 
    """
    branch: Optional[str] = Field(None, max_length=1600)
    equipment_name: str 

    refrigerant_capacity: Optional[float] = Field(None, ge=0, description='Most machines have their capacity, use that as reference')
    refrigerant_use: Optional[float] = Field(None, ge=0, description='If you know the capacity and loss rate, this will be the number')
    refrigerant_type: Optional[str] = Field(default='R-410A', description='R-410-A is most common refrigerants. In practice, many refrigerants have mixed composites')
    refrigerant_unit: Optional[str] = Field(default='kg', description='GWP for refrigerants are typically measured by mass not volume.')

    install_loss_rate: Optional[float] = Field(None, ge=0, le=1, description='When installing the machine, percentage of refrigerant capacity that was expected to lose. 1-2 percent is a safe assumption')
    annual_leak_rate: Optional[float] = Field(None, ge=0, le=1, description='Percentage of capacity expected to leak/evaporate per year')
    recovery_rate: Optional[float] = Field(None, ge=0, le=1, description='Percentage of remaining capacity after decommissioning')

    number_of_year: Optional[float] = Field(None, ge=0, description='Number of years. Used to be multiplied with annual leak rate')

