from datetime import datetime
from dateutil import parser
import uuid

from pydantic import BaseModel, Field
from pydantic import model_validator
from typing import Optional, Dict, Union, Tuple, ClassVar, Any

from supabase import create_client


#---------------
# Input Class
#---------------
class S2_BaseModel(BaseModel):
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: Optional[Union[datetime, str]] = Field(None) 
    description: Optional[str]= Field(None, max_length=1600)

    @model_validator(mode='before')
    def validate_BaseModel(cls, values):    
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


class S2_PurchasedPower(S2_BaseModel):    
    lat: Optional[float] = Field(None, ge=-90, le=90)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    state: Optional[str] = Field(None, max_length=99)
    country: Optional[str] = Field(None, max_length=35)

    branch: Optional[str] = Field(None, max_length=1600)
    department: Optional[str] = Field(None, max_length=255)    
    street_address_1: Optional[str] = Field(None, max_length=35)
    street_address_2: Optional[str] = Field(None, max_length=35)
    city: Optional[str] = Field(None, max_length=35)
    postcode: Optional[Union[str, int]] = Field(None)    

    owned: Optional[bool] = Field(default=True)
    
    energy_provider: Optional[str] = Field(None, max_length=99)
    energy_type: Optional[str] = Field(default='electric')
    energy_use: Optional[float] = Field(None, ge=0)
    energy_unit: Optional[str] = Field(default='kwh')
    energy_spend: Optional[float] = Field(None, ge=0)
    currency: Optional[str] = Field(default='MYR')
        
    @model_validator(mode='before')
    def validate_PPD(cls, values):
        owned = values.get('owned')
        state = values.get('state')
        country = values.get('country')
        lat = values.get('lat')
        lon = values.get('lon')

        energy_type = values.get('energy_type')
        energy_use = values.get('energy_use')
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
        if energy_spend is not None and float(energy_spend) > 0:
            if currency is None:
                values['currency'] = 'myr'
            else:
                currency_lower = currency.lower()
                if currency_lower not in supported_currency:
                    raise ValueError(f'Currency must be in {supported_currency}')
                values['currency'] = currency_lower
                
        return values
