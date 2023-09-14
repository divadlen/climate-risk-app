import logging
import json
import re
import uuid

from datetime import datetime
from dateutil import parser

import pandas as pd
import numpy as np

from pydantic import BaseModel, Field
from pydantic import model_validator
from pydantic_core.core_schema import FieldValidationInfo
from typing import Optional, Dict, List, Union, Tuple, ClassVar, Any


#---------------
# Input Class
#---------------
class S3_BaseAsset(BaseModel):
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