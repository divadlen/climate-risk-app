import streamlit as st
from st_aggrid import AgGrid, JsCode, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import numpy as np
import pandas as pd
from datetime import datetime
from dateutil import parser
import logging
import json
from typing import List

import plotly.express as px

from utils.s2ie_PPD import create_ppd_data, S2IE_Lookup_Cache, S2_PurchasedPowerData, S2IE_CalculatorTool
from utils.utility import get_dataframe, convert_df, convert_warnings, convert_BaseModel, find_closest_category
from utils.geolocator import GeoLocator
from utils.globals import LOCATION_ABBRV

def s2ie_Page():
  if 'S2IE_Lookup_Cache' not in st.session_state:
    st.session_state['S2IE_Lookup_Cache'] = S2IE_Lookup_Cache() 
  if 's2ie_df' not in st.session_state: #
    st.session_state['s2ie_df'] = None
  if 'validated_s2ie_df' not in st.session_state:
    st.session_state['validated_s2ie_df'] = None
    st.session_state['validated_s2ie_warnings'] = []

  st.title('Indirect Emissions')
  tab1, tab2, tab3 = st.tabs(["Upload", "Run Analysis", "Review"])

  with tab1:
    with st.expander("Show help"):
      st.markdown(help_md)

      csv_str = convert_BaseModel(S2_PurchasedPowerData)
      st.download_button(
        label='Download empty Scope 2: Indirect Emissions form',
        data=csv_str,
        file_name='scope-2-emission-form.csv',
        mime='text/csv',
      )
    
    with st.expander("Upload a CSV file", expanded=True):
      uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"], accept_multiple_files=False, help='CSV containing purchased power data for S2: Indirect Emissions')
      
      if st.checkbox('Read selected csv files') and uploaded_file:
        data = pd.read_csv(uploaded_file)
        if data is not None:
          df = get_dataframe(data) 
          st.session_state['s2ie_df'] = df

    if st.session_state['s2ie_df'] is not None:
      with st.expander('Show uploaded table'):
        pandas_2_AgGrid(st.session_state['s2ie_df'], theme='balham')

      if 'validated_s2ie' not in st.session_state:
        st.session_state['validated_s2ie'] = False
      if st.button('Validate uploaded dataframe'):
        st.session_state['validated_s2ie_df'], st.session_state['validated_s2ie_warnings'] = validate_s2ie_df(st.session_state['s2ie_df'])
        st.session_state['validated_s2ie'] = True

      if st.session_state['validated_s2ie']:
        with st.expander('Show validation warnings'):
          for warning in st.session_state['validated_s2ie_warnings']:
            st.warning(warning)

        with st.expander('Validated table', expanded=True):
          pandas_2_AgGrid( st.session_state['validated_s2ie_df'], theme='balham' )

          col1, col2 = st.columns([1,1])
          with col1:
            csv_str = convert_df(st.session_state['validated_s2ie_df'])
            st.download_button('Download validated table as CSV', csv_str, file_name="validated_table.csv", mime="text/csv")
          with col2:
            validation_warnings_str = convert_warnings(st.session_state['validated_s2ie_warnings'])
            st.download_button("Download warnings as TXT", validation_warnings_str, file_name="warnings.txt", mime="text/plain")


  with tab2:
    with st.expander('Show help'):
      st.markdown(analysis_md)

    if 's2ie_df' not in st.session_state or st.session_state['s2ie_df'] is None:
      st.info('Please upload a table at "Upload" tab to continue')

    if 's2ie_df' in st.session_state and st.session_state['s2ie_df'] is not None:
      with st.expander('Show table', expanded=True):
        pandas_2_AgGrid(st.session_state['s2ie_df'], theme='balham', key='s2ie_df_tab2')

      if 'analyzed_s2ie' not in st.session_state:
        st.session_state['analyzed_s2ie'] = False
      if st.button('Analyze uploaded dataframe', help='Attempts to return calculation results for each row for table. Highly recommended to reupload a validated table before running analysis'):
        st.session_state['analyzed_s2ie'] = True

        cache = st.session_state['S2IE_Lookup_Cache']
        gl = GeoLocator()
        calc = S2IE_CalculatorTool(cache=cache)

        calc, warning_messages = df_2_calculator(st.session_state['s2ie_df'], calculator=calc, cache=cache, geolocater=gl)
        calculation_df = calculator_2_df(calc)

        if warning_messages:
          with st.expander('Show analysis warnings'):
            for warning in warning_messages:
              st.warning(warning)

        with st.expander('Show results table'):  
          pandas_2_AgGrid(calculation_df, theme='balham')

        # figs = {} 
        # for c in calculation_df.columns:
        #   if calculation_df[c].dtype in [np.float64, np.int64]:
        #     fig = px.histogram(
        #       calculation_df, 
        #       x=c, 
        #       marginal='rug',
        #       hover_data=calculation_df.columns,
        #     ).update_layout(title=c.upper())
        #     figs[c] = fig 

        # for title, fig in figs.items():
        #   with st.expander(f'Show {title.upper()}'):
        #     st.plotly_chart(fig, use_container_width=True) 










def df_2_calculator(df, calculator: S2IE_CalculatorTool, cache: S2IE_Lookup_Cache, geolocater: GeoLocator):
  df = df.replace(np.nan, None) # To allow Pydantic validation
  warning_messages=[]

  # Create progress bar
  progress_bar = st.progress(0)
  nrows = len(df)

  for index, row in df.iterrows():
    try:
      data = create_ppd_data(
        cache=cache,
        geolocater=geolocater,
        description= row['description'],
        branch= row['branch'],
        department= row['department'],
        owned= row['owned'],
        street_address_1= row['street_address_1'],
        street_address_2= row['street_address_2'],
        city= row['city'],
        state= row['state'],
        country= row['country'],
        postcode= row['postcode'],
        lat = row['lat'],
        lon = row['lon'],
        date = row['date'],
        energy_type = row['energy_type'],
        energy_consumption = row['energy_consumption'],
        energy_unit= row['energy_unit'],
        energy_spend = row['energy_spend'],
        currency = row['currency'],
        energy_provider = row['energy_provider'],
      )
      calculator.add_power_data(data)

    except Exception as e:
      warning_messages.append(f'Unable to add data for row {index+1}. {str(e)}')
      pass

    progress_pct = (index + 1) / nrows
    progress_bar.progress(progress_pct)

  return calculator, warning_messages


def calculator_2_df(calculator: S2IE_CalculatorTool):
  data = []
  for emission in calculator.calculated_emissions.values():
    ppd = emission['purchased_power_data'].model_dump()
    calculation_data = emission['calculated_emissions'].model_dump()
    combined_data = {**ppd, **calculation_data}
    data.append(combined_data)
  return pd.DataFrame(data)



def validate_s2ie_df(df:pd.DataFrame): 
  """ 
  Validates a pd.DF
  Returns:
    - df
    - List of warnings
  """
  df = df.replace(np.nan, None)
  cache = S2IE_Lookup_Cache()
  gl = GeoLocator()
  abbrv_dict = LOCATION_ABBRV
  
  warning_messages = []
  expected_columns = [
    'description', 'branch', 'department', 'owned', 
    'street_address_1', 'street_address_2', 'city', 'state', 'country', 'postcode', 'lat', 'lon', 
    'date', 
    'energy_type', 'energy_consumption', 'energy_unit','energy_spend', 'currency', 'energy_provider'
  ]

  # Identify missing and additional columns
  missing_columns = [col for col in expected_columns if col not in df.columns]
  additional_columns = [col for col in df.columns if col not in expected_columns]
    
  # Warn about missing and additional columns
  if missing_columns:
    warning_messages.append(f"Warning: Missing columns {missing_columns}. Please ensure the CSV contains these columns.")
  if additional_columns:
    warning_messages.append(f"Warning: Additional columns {additional_columns}. These columns will be ignored.")

  progress_bar = st.progress(0)
  nrows = len(df)
  for index, row in df.iterrows():
    idx = index + 1

    if 'description' in df.columns:
      if len(str(row['description'])) > 1200:
        warning_messages.append(f"Warning: Description exceeds 1200 characters in row {idx}.")

    # validate location
    if 'lat' not in [None] and 'lon' not in [None]:
      try:
        geo_fields = gl.get_fields_from_latlon(row['lat'], row['lon'])
        inferred_state = geo_fields.get('state_name')
        inferred_country = geo_fields.get('country_name')
        df.loc[index, 'state'] = inferred_state
        df.loc[index, 'country'] = inferred_country
        warning_messages.append(f"UPDATE: Lat Lon detected in row {idx}. State '{row['state']}' replaced to '{inferred_state}'. Country '{row['country']}' replaced to '{inferred_country}' ")
      except Exception as e:
        print(e)

    
    if 'lat' in [None] and 'lon' in [None]:
      if 'country' in df.columns:
        country = row['country']
        valid_countries = cache.get_allowed_countries()

        if country not in valid_countries:
          corrected_country = find_closest_category(country, valid_countries, abbrv_dict=abbrv_dict)
        
          if corrected_country not in [None]: 
            warning_messages.append(f"UPDATE: 'country' value of '{country}' in row {idx} is corrected to '{corrected_country}'.")
            df.loc[index, 'country'] = corrected_country
          else:
            warning_messages.append(f"Warning: Invalid 'country' value of '{country}' in row {idx}. Setting to None.")
            df.loc[index, 'country'] = None 


    if 'state' in df.columns:
      state = row['state']
      try:
        valid_states = cache.get_allowed_states(country=row['country'])
      except:
        valid_states = None
      
      if valid_states not in [None] and row['state'] not in valid_states:
        corrected_state = find_closest_category(state, valid_states, abbrv_dict=abbrv_dict)

        if corrected_state is not None:
          warning_messages.append(f"UPDATE: 'state' value of '{state}' in row {idx} is corrected to '{corrected_state}'.")
          df.loc[index, 'state'] = corrected_state
        else:
          warning_messages.append(f"Warning: Invalid 'state' value of '{state}' in row {idx}. Setting to None.")
          df.loc[index, 'state'] = None 

    # valdiate date
    if 'date' in df.columns:
      date = row['date']
      if date is None:
        df.loc[index, 'date'] = datetime.now().strftime('%Y-%m-%d')
      else:
        try:
          parsed_date = parser.parse(date)
          df.loc[index, 'date'] = parsed_date.strftime('%Y-%m-%d')
        except ValueError:
          warning_messages.append(f"Warning: Invalid date of '{date}' in row {idx}. Expected format is 'YYYY-MM-DD'. Setting to today's date.")
          df.loc[index, 'date'] = datetime.now().strftime('%Y-%m-%d')

    # validate energy
    if 'energy_type' and 'energy_unit' in df.columns:
      energy_type = row['energy_type']
      energy_unit = row['energy_unit']
      if energy_type not in [None]:
        if energy_type.lower() == 'electric':
          valid_energy_unit = ['kwh']
        else:
          valid_energy_unit = None

      if energy_unit not in [None]:
        if valid_energy_unit is None:
          warning_messages.append(f"Warning: No valid 'energy_unit' for energy type '{energy_type}' in row {idx}. Setting to None.")
          df.loc[index, 'energy_unit'] = None
        elif energy_unit.lower() not in [x.lower() for x in valid_energy_unit]:
          warning_messages.append(f"Warning: Invalid 'energy_unit' value of '{energy_unit}' in row {idx}. Valid unit for '{energy_type}': {valid_energy_unit}.  Setting to None.")
          df.loc[index, 'energy_unit'] = None

    if 'energy_consumption' in df.columns:
      energy_consumption = row['energy_consumption']
      if energy_consumption not in [None, np.nan, ''] and energy_consumption < 0: 
        warning_messages.append(f"Warning: Invalid 'energy_consumption' value of '{energy_consumption}' in row {idx}. Must be greater than 0. Setting to None.")
        df.loc[index, 'energy_consumption'] = None

    progress_pct = (index + 1) / nrows
    progress_bar.progress(progress_pct)

  return df, warning_messages


def pandas_2_AgGrid(df: pd.DataFrame, theme:str='streamlit', key=None) -> AgGrid:
  cellstyle_jscode = JsCode("""
  function(params){
      if (params.value == null || params.value === '') {
          return {
              'color': 'white',
              'backgroundColor': 'red',
          }
      }
  }
  """)
  custom_css={"#gridToolBar": {"padding-bottom": "0px !important"}} # allows page arrows to be shown

  valid_themes= ['streamlit', 'alpine', 'balham', 'material']
  if theme not in valid_themes:
    raise Exception(f'Theme not in {valid_themes}')
  
  # check if column cell is in json or dict, then transform column to json literal string 
  for col in df.columns:
    if df[col].apply(lambda x: isinstance(x, dict)).any():
      df[col] = df[col].apply(json.dumps)

 # AG Grid Options
  gd= GridOptionsBuilder.from_dataframe(df)
  gd.configure_columns(df, cellStyle=cellstyle_jscode)
  gd.configure_pagination(enabled=True)
  
  grid_options = gd.build()
  grid_response = AgGrid(
    df, 
    gridOptions=grid_options,
    custom_css=custom_css,
    height=600, 
    theme=theme,
    reload_data=True,
    allow_unsafe_jscode=True,
    key=key,
  )
  return grid_response['data']


## Markdowns
help_md = """
- ##### Uploading CSV file
  - Drag and drop file into the widget. Supported files (csv). If you are not sure what files to upload, **download empty form at the end of help**. 
  - Click "Read selected csv files". A table preview will show up for your uploaded data. 
  - A red cell indicates an empty field. This is only for visual purposes. Only missing values that affect the analysis will be raised during the "Warning" section. 
  
- ##### Validating uploaded CSV file
  - Clicking button "Validate uploaded dataframe" is optional but recommended. 
  - Validation will pick up corrected spellings, updated fields, and warn about missing or incorrect values.
    - Warning: Validation is not perfect! Sometimes it may incorrectly update values! EG: Liquified Petroleum Gas >> Petroleum (when it should be LPG). 
  - "Show validation warnings" or download its TXT file to perform audits on which row to update.
  - You may also choose to download the validated table and make modifications from there. Don't forget to reupload the modified table to the app.                   
"""

analysis_md = """
- ##### Analyzing uploaded data
  - You are required to click "Analyze uploaded dataframe" to commit the analyzed result to the final dashboard. 
  - Will use uploaded data and not validated data to analyze. If you have used the validation feature, remember to reupload your modified data.
  - "Show results table" to display the raw output of the model
"""
