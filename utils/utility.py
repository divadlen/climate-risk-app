import streamlit as st

import pandas as pd
import numpy as np
import math
import random
from datetime import datetime

from PIL import Image
from io import StringIO
import re
from typing import List, Optional, Union, Dict, Any, get_args, get_origin
from fuzzywuzzy import process

import os 
import sys
from supabase import create_client
from supabase.lib.client_options import ClientOptions

from utils.globals import COLUMN_SORT_ORDER

#-----
# Text formatting
#-----
def format_metric(value) -> str:
    if value <= 0:
        return "0 g CO2e"
    elif value < 1:
        return f"{value * 1000:.0f} g CO2e"
    elif value < 1000:  # Less than 1 Ton
        return f"{value:.2f} Kg CO2e"
    elif value < 1e6:  # Less than 1 million
        return f"{value / 1000:.2f} tCO2e"
    elif value < 1e9:  # Less than 1 billion
        return f"{value / 1e6:.2f} ktCO2e"
    elif value < 1e12:  # Less than 1 trillion
        return f"{value / 1e9:.2f} mtCO2e"
    elif value < 1e15:  # Less than 1 quadrillion
        return f"{value / 1e12:.2f} btCO2e"
    else:
        exponent = int(math.log10(value))
        return f"{value / 10**exponent:.2f}e{exponent} tCO2e"


def clamp(n, minn=1, maxn=5):
  return max(min(maxn, n), minn)


def clean_text(text):
  clean_text = re.sub(r'[^a-zA-Z0-9_,.:\s\[\]]', ' ', text)
  return clean_text


def snake_case_to_label(s:str) -> str:
  return ' '.join(word.capitalize() for word in s.split('_'))


def humanize_field(field_name:str, invert=False) -> str:
  if invert:
    # Convert from 'Column Name 1' to 'column_name_1'
    # Strip leading and trailing spaces, replace multiple spaces with one, and convert spaces to underscores
    return re.sub(' +', '_', field_name.strip()).lower()
  else:
    # Convert from 'column_name_1' to 'Column Name 1'
    # Split on underscores and capitalize each word, then join with spaces
    return ' '.join(word.capitalize() for word in field_name.split('_'))
    

#-----
# Theming
#-----
def set_theme():
    if st.session_state.theme_choice == 'Light':
        st.session_state.theme_colors = {
            'primaryColor': "#0b0c0b",
            'backgroundColor': "#f5edec",
            'secondaryBackgroundColor': "#ded2de",
            'textColor':"#202d35"  
        }
    
        watermark_path = "./resources/BlackShortText_Logo_Horizontal-long.png"
        if os.path.exists(watermark_path):
            st.session_state.watermark_settings = [dict(
                source= Image.open(watermark_path),
                xref="paper", yref="paper",
                x=0.98, y=0.02,
                sizex=0.20, sizey=0.20, opacity= 0.25,
                xanchor="right", yanchor="bottom"
            )]
        else:
            st.error(f"File not found: {watermark_path}")     

        st.session_state.sidebar_logo_path = "./resources/BlackText_Logo_Horizontal.png"

    else:
        st.session_state.theme_colors = {
            'primaryColor': '#e5f0d9',
            'backgroundColor': '#000000',
            'secondaryBackgroundColor': '#39393a',
            'textColor': '#ecc0d1'
        }
        st.session_state.sidebar_logo_path = "./resources/BlackText_Logo_Horizontal.png"

        watermark_path = "./resources/WhiteShortText_Logo_Horizontal-long.png"
        if os.path.exists(watermark_path):
            st.session_state.watermark_settings = [dict(
                source= Image.open(watermark_path),
                xref="paper", yref="paper",
                x=0.98, y=0.02,
                sizex=0.20, sizey=0.20, opacity= 0.25,
                xanchor="right", yanchor="bottom"
            )]
        else:
            st.error(f"File not found: {watermark_path}")


def reconcile_theme_config():
    set_theme()
    
    keys = ['primaryColor', 'backgroundColor', 'secondaryBackgroundColor', 'textColor']
    for key in keys:
        if st._config.get_option(f'theme.{key}') != st.session_state.theme_colors.get(key, ''):
            st._config.set_option(f'theme.{key}', st.session_state.theme_colors.get(key, ''))

        

#-----------------------
# Helper functions
#-----------------------
def supabase_query(table:str, url:str, key:str,  schema: Optional[str]=None, limit: Optional[int]=10000):
    if schema:
        opts = ClientOptions().replace(schema=schema)
        supabase = create_client(url, key, options=opts)
    else:
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


def supabase_query_v2(table, schema: Optional[str]=None, limit: Optional[int]=10000, **kwargs):
    """ 
    v2 lets you pass "column_name" = "value" as kwargs to filter

    Example:
      TABLE = 's1mc_gas'
      kwargs= {'fuel_type': 'natural gas'} # search "natural gas" from column "fuel_type"
    
    supabase_query_v2(TABLE, **kwargs)
    """
    supabase_url= st.secrets['supabase_url']
    supabase_anon_key= st.secrets['supabase_anon_key']

    url = supabase_url
    key = supabase_anon_key
    
    if schema:
        opts = ClientOptions().replace(schema=schema)
        supabase = create_client(url, key, options=opts)
    else:
        supabase = create_client(url, key)
    
    query_builder = supabase.table(table).select('*')
    for key, value in kwargs.items():
        if value is not None:  # Only add filter if value is not None
            query_builder = query_builder.filter(key, 'eq', value)
            
    if limit is not None:
        query_builder = query_builder.limit(limit)
    
    try:
        response = query_builder.execute()
        return response.data
    except Exception as e:
        raise e

    
def get_lookup(
    table: str, 
    filters: Optional[Dict[str, Any]]=None, 
    distinct: Optional[str]=None
):
    """
    Get back a row from supabase or a list of unique values. 
    table: Supabase table name. Note the global anon key is loaded inside. 
    filters: column equals value dict pair. DOES NOT SUPPORT LIST VALUE. 

    Usage: 
      get_lookup(table='s1mc_v2', filters={'id': 38}) >> [{'id': '38', ... ]
      get_lookup(table='s1mc_v2', distinct='year) >> [2020, 2019...]
    """
    supabase_url= st.secrets['supabase_url']
    supabase_anon_key= st.secrets['supabase_anon_key']
    url = supabase_url
    key = supabase_anon_key
    supabase = create_client(url, key)
    
    if distinct:
        query_builder = supabase.table(table).select(distinct)
    else:
        query_builder = supabase.table(table).select('*')
        
    if filters:
        for column, value in filters.items():
            query_builder = query_builder.filter(column, 'eq', value)
    
    try:
        response = query_builder.execute()
        data = response.data
        if distinct:
            unique_values = list(set(row[distinct] for row in data))
            return unique_values
        return data
    
    except Exception as e:
        raise e
    

@st.cache_data
def get_dataframe(data):
  return pd.DataFrame(data)


def find_closest_category(input_str, allowed_list:list, threshold=80, abbrv_dict: dict={}):
    """
    Autocorrect for a list of options
    abbrv_dict: 
      Dictionary containing custom pairs. EG: 'usa': 'United States of America'
      Useful if fuzzy matching is returning unintentional results
    """
    if input_str in [None, '']:
        return None

    if abbrv_dict not in [None, {}]:
        input_str = abbrv_dict.get(input_str.strip().lower(), input_str)
    
    closest_match, score = process.extractOne(input_str, allowed_list)
    if score >= threshold:
        return closest_match
    else:
        return None 
    

def get_deep_size(obj):
    """Get the size of each object"""
    size = sys.getsizeof(obj)
    if isinstance(obj, dict):
        size += sum([get_deep_size(v) for v in obj.values()])
        size += sum([get_deep_size(k) for k in obj.keys()])
    elif isinstance(obj, list):
        size += sum([get_deep_size(v) for v in obj])
    return size


#-------
# Helper for download export
#---------
@st.cache_data
def convert_df(df):
  return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def convert_warnings(warnings: List):
  warnings_str = "\n".join(warnings)
  return warnings_str

#---
# Model Helpers
#---
def convert_BaseModel(cls, examples:bool=False, return_as_string:bool=True):
  """ 
  cls: Must be pydantic basemodel class
  examples: If True, return header + 5 rows of examples. If False, return only header row
  get_as_string: If True, return str representation of csv. If False, return pd DataFrame.
  """
  if not examples:
    field_names = list(cls.model_fields.keys())
    if 'uuid' in field_names:
       field_names.remove('uuid')
    df = pd.DataFrame(columns=field_names)
  
  else:
    def random_value_for_type(field_type):
      if field_type == str:
        return 'EXAMPLE_' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz1234567890', k=5))
      elif field_type == float:
        return random.uniform(1, 100)
      elif field_type == int:
        return random.randint(1, 100)
      elif field_type == bool:
        return random.choice(['True', 'False'])
      elif field_type == datetime:
        return datetime.now().strftime('%Y-%m-%d')
      else:
        return '<Blank>'
      
    def get_default_value(field_type, default_value):
      if get_origin(field_type) in (Optional, Union):
        actual_types = get_args(field_type)
        if float in actual_types or int in actual_types:
          return '<To fill>'
        return '<Blank>'
      return random_value_for_type(field_type) if default_value in ['None', 'PydanticUndefined'] else '<Blank>'
    
    def create_random_row(cls):
      non_calculation_fields = [
        'lat', 'lon', 'postcode', 'employee_id', 
        'reported_emissions', 'estimated_emissions',
        'energy_spend', # 
      ]

      row = {}
      for field_name, field_info in cls.model_fields.items():  # pydantic only
        field_type = field_info.annotation
        default_value = str(field_info.default) # str representation to catch PydanticUndefined
        
        if field_name == 'uuid':  # Skip uuid field
          continue

        if default_value not in ['None', 'PydanticUndefined']:
          row[field_name] = default_value
          continue

        if field_name in non_calculation_fields:
          row[field_name] = '<Blank>'
        else:
          row[field_name] = get_default_value(field_type, default_value)

      return row

    NUM_ROWS = 5
    field_names = list(cls.model_fields.keys())
    if 'uuid' in field_names:
      field_names.remove('uuid')    
    df = pd.DataFrame(index=range(NUM_ROWS), columns=field_names)
    
    # Add example rows
    for i in range(NUM_ROWS):
      example_row = create_random_row(cls)
      df.loc[i] = example_row # avoid pandas complaining about all-NA entries concat
      # df = pd.concat([df, pd.DataFrame([example_row])], axis=0, ignore_index=True)


  # Sort columns according to globals
  df = df[[col for col in COLUMN_SORT_ORDER if col in df.columns]] 

  # Humanize all field names in the DataFrame
  df.columns = [humanize_field(col) for col in df.columns]
     
    
  if return_as_string:
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_str = csv_buffer.getvalue()
    return csv_str
  return df

@st.cache_data 
def get_cached_df(BaseModelCls): # cache still doesnt work with aggrid
  return convert_BaseModel(BaseModelCls, examples=True, return_as_string=False)


#---
# Simulator
#----
def create_line_simulation():
    def random_timeseries(initial_value: float, volatility: float, count: int, trend: float = 0.0) -> list:
        time_series = [initial_value]
        for _ in range(count - 1):
            next_value = time_series[-1] + initial_value * random.gauss(0.2, 0.4) * volatility + trend
            time_series.append(next_value)
        return time_series

    
    months = pd.date_range(start='2019-01-01', end='2021-12-01', freq='MS')
    categories = [f'Category_{i+1}' for i in range(12)]
    
    values = []
    for _ in categories:
        cat_values = random_timeseries(initial_value=random.uniform(100,100), volatility=0.2, count=len(months), trend=2)
        values.extend(cat_values)

    data = {
        'date': np.tile(months, len(categories)),
        'category': np.repeat(categories, len(months)),
        'value': values
    }
    df = pd.DataFrame(data)
    return df
