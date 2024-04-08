import streamlit as st
from streamlit import session_state as state

import numpy as np
import pandas as pd
from datetime import datetime
from functools import partial
from typing import Union, get_args, get_origin

from utils.utility import find_closest_category, snake_case_to_label
from utils.globals import ABBRV_IDX_TO_CATEGORY_NAME, COLUMN_SORT_ORDER
from utils.model_inferencer import ModelInferencer
from utils.display_utility import show_example_form, pandas_2_AgGrid
from utils.s3vc_Misc.s3_cache import S3_Lookup_Cache
from utils.geolocator import GeoLocator

def easy_forms_page():
  if 'S3VC_Lookup_Cache' not in state:
    state['S3VC_Lookup_Cache'] = S3_Lookup_Cache()

  st.subheader('Form Builder')
  c1, c2 = st.columns([1,1])
  with c1:
    selected_scope = st.selectbox('Select scope', options=[1,2,3])
    if selected_scope == 1:
      state['form_builder_allowed_categories'] = ['Stationary Combustion', 'Mobile Combustion', 'Fugitive Emission']
    elif selected_scope == 2:
      state['form_builder_allowed_categories'] = ['Purchased Power']
    elif selected_scope == 3:
      state['form_builder_allowed_categories'] = list(ABBRV_IDX_TO_CATEGORY_NAME.values())
  with c2:
    selected_category = st.selectbox('Select category', options=state['form_builder_allowed_categories'])
  
  ##
  cache = state['S3VC_Lookup_Cache']
  field_to_cache_func ={
    'fuel_type': cache.get_allowed_fuel_type,
    'refrigerant_type': cache.get_allowed_refrigerants, 
    'freight_type': cache.get_allowed_freight_type,
    'vehicle_type': cache.get_allowed_vehicle_type, 
    'waste_type': cache.get_allowed_waste_type,
    'waste_treatment_method': cache.get_allowed_waste_treatment_method,
    'country': cache.get_allowed_countries, 
    'state': cache.get_allowed_states, 
  }

  modinf = ModelInferencer()
  available_models = modinf.available_models.keys()
  selected_form = find_closest_category(selected_category, allowed_list=list(available_models), threshold=40) # Front end displayed names differ from backend keys
  model = modinf.available_models[selected_form]

  show_example_form(model, title=f'Selected form: {selected_form}', button_text='Download table', filename=f'{selected_form}-example-form.csv', expanded=True, download_button=False)

  build_dynamic_forms(model, cache, field_to_cache_func)


      
def build_dynamic_forms(model, cache, field_to_cache_func):
  # Initialize the state variables if not already done
  if 'country' not in state:
    state['country'] = 'Select country'
  if 'state' not in state:
    state['state'] = 'Select state'
  if 'fuel_state' not in state:
    state['fuel_state'] = 'Select fuel state'
  if 'fuel_type' not in state:
    state['fuel_type'] = 'Select fuel type'

  # Init lists
  country_list = cache.get_allowed_countries() # pointless to save these into session. You need to write a lot of lines to save a few ms of API call
  state_list = []
  fuel_list = []

  if state['country'] != 'Select country':
    state_list = cache.get_allowed_states(country=state['country'])
  if state['fuel_state'] != 'Select fuel state':
    fuel_list = cache.get_allowed_fuel_type(fuel_state=state['fuel_state'])
  
  # Create an expander for the dynamic form
  with st.expander('Form content preview', expanded=True):
    # Loop based on the custom sort order
    for field_name in COLUMN_SORT_ORDER:
      if field_name not in model.model_fields:
        continue  # Skip fields not in the model
    
      # retrieve metadata for field
      field_info = model.model_fields[field_name]
      field_type = field_info.annotation
      origin = get_origin(field_type)
      args = get_args(field_type)
      
      placeholder = None
      if str(field_info.default) not in ['None', 'PydanticUndefined']: # str to catch pydantic undefined
        placeholder = str(field_info.default)
    
      # check if field fits condition
      if field_name in ['uuid', 'description']:
        continue
      
      elif field_name in ['lat']:
        st.slider(label=snake_case_to_label(field_name), min_value=float(-90), max_value=float(90), value=0.000, step=0.001)

      elif field_name in ['lon']:
        st.slider(label=snake_case_to_label(field_name), min_value=float(-180), max_value=float(180), value=0.000, step=0.001)

      elif field_name in ['attribution_share', 'install_loss_rate', 'annual_leak_rate', 'recovery_rate', 'ownership_share']:
        st.slider(label=snake_case_to_label(field_name), min_value=float(0), max_value=float(1), value=0.1, step=0.01)

      elif field_name in ['waste_state']:
        st.selectbox(label=snake_case_to_label(field_name), options=['solid', 'liquid', 'gas'], index=1)

      elif field_name in ['fuel_state']:
        state['fuel_state'] = st.selectbox(label=snake_case_to_label(field_name), options=['solid', 'liquid', 'gas'], index=1)

      elif field_name in ['travel_mode']:
        state['travel_mode'] = st.selectbox(label=snake_case_to_label(field_name), options=['Rail', 'Air', 'Land', 'Water', None], index=1)

      # if field name has dynamic option select
      elif field_name in field_to_cache_func:
        if field_name == 'country':
          selected_country = st.selectbox(label=snake_case_to_label(field_name), options=country_list if country_list else [None])
          # refresh state if country input is updated
          if selected_country != state['country']:
            state['country'] = selected_country
            state['state'] = 'Select state'
            
        elif field_name == 'state':
          if state['country'] != 'Select country':
            options = state_list
            selected_state = st.selectbox(label=snake_case_to_label(field_name), options=options if options else [None])
            if selected_state != state['state']:
              state['state'] = selected_state

        elif field_name == 'fuel_type':
          if state['fuel_state'] != 'Select fuel state':
            options = fuel_list
            selected_fuel_type = st.selectbox(label=snake_case_to_label(field_name), options=options if options else [None])
            if selected_fuel_type != state['fuel_type']:
              state['fuel_type'] = selected_fuel_type

        else:
          options = field_to_cache_func[field_name]()  # Run the function to get the list of allowed fields
          st.selectbox(label=snake_case_to_label(field_name), options=options)
            
      elif origin == None: # if origin has only one type
        if field_type == str:
          st.text_input(label=snake_case_to_label(field_name), placeholder=placeholder)
        elif field_type == float:
          st.number_input(label=snake_case_to_label(field_name))
        elif field_type == int:
          st.number_input(label=snake_case_to_label(field_name), step=1)
        elif field_type == bool:
          st.selectbox(label=snake_case_to_label(field_name), options=[True, False])
        elif field_type == datetime:
          st.date_input(label=field_name)

      elif origin == Union:
        valid_types = [arg for arg in args if arg != type(None)] # Skip NoneType when unpacking Union args
        actual_type = valid_types[0] # get the first accepted type for field that is not None

        if actual_type == str:
          st.text_input(label=snake_case_to_label(field_name), placeholder=placeholder)
        elif actual_type == float:
          st.number_input(label=snake_case_to_label(field_name))
        elif actual_type == int:
          st.number_input(label=snake_case_to_label(field_name), step=1)
        elif actual_type == datetime:
          st.date_input(label=snake_case_to_label(field_name))
        elif actual_type == bool:
          st.selectbox(label=snake_case_to_label(field_name), options=[True, False])





  


