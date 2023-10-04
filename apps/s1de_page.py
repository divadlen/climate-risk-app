import streamlit as st
from st_aggrid import AgGrid, JsCode, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
import streamlit_antd_components as sac

import numpy as np
import pandas as pd
import random
from functools import partial
import json
import logging
from typing import List

import plotly.express as px

from utils.globals import SECTOR_TO_CATEGORY_IDX, IDX_TO_CATEGORY_NAME
from utils.utility import get_dataframe, create_line_simulation
from utils.display_utility import show_example_form, pandas_2_AgGrid
from utils.model_df_utility import df_to_calculator, calculator_to_df
from utils.md_utility import markdown_insert_images
from utils.model_inferencer import ModelInferencer

from utils.s1de_Misc.s1_models import *
from utils.s1de_Misc.s1_calculators import S1_Calculator
from utils.s1de_Misc.s1_creators import *

from utils.s3vc_Misc.s3_cache import S3_Lookup_Cache
from utils.charting import initialize_plotly_themes 


def s1de_Page(): 
  if 'S1SC_Lookup_Cache' not in st.session_state:
    st.session_state['S1SC_Lookup_Cache'] = S3_Lookup_Cache()
  if 's1sc_df' not in st.session_state: 
    st.session_state['s1sc_df'] = None
  if 'validated_s1sc_df' not in st.session_state:
    st.session_state['validated_s1sc_df'] = None
    st.session_state['validated_s1sc_warnings'] = []


  st.title('Stationary Combustion')
  tab1, tab2, tab3 = st.tabs(['Get Forms/Guidelines', 'Submit & Review', 'Analysis'])

  with tab1:
    st.subheader('User Guide')


    download_desc = 'Click on the links in Table of Contents to redirect you to the recommended tables to fill. Download the example forms. Each transaction counts as a row.'
    fill_desc = 'Each form is represented as CSV, each row is one transaction. Example: in "Mobile Combustion" file, each vehicle/machine counts as one row. Details at "More help" and "Visual help"'

    sac.steps(
      items=[
        sac.StepsItem(title='Download relevant forms', subtitle='', description=download_desc),
        sac.StepsItem(title='Fill relevant forms', subtitle='', description=fill_desc),
        sac.StepsItem(title='Upload relevant forms', subtitle='', description='BB'),
        sac.StepsItem(title='Validate & submit forms', subtitle='', description='CC'),
      ], 
      format_func='title',
      direction='vertical',
    )
    
    with st.expander('Show help', expanded=True):
      st.markdown("abc")

    with st.expander('Visual help'):
      with open("resources/mds/s3vc_general_guide.md", "r") as gmd:
        readme = gmd.read()
      readme = markdown_insert_images(readme)
      st.markdown(readme, unsafe_allow_html=True) 

    st.subheader('Table of contents', anchor='s1-toc')
    with st.expander('Show table of contents', expanded=True):
      st.markdown(table_of_contents_md)
    st.divider()

    st.subheader("Mobile Combustion", anchor='S1_MobileCombustion')
    show_example_form(S1_MobileCombustion, key='s1mc', title='Show example form (S1-C0: Mobile Combustion)', button_text='Get example form', filename='s1-c0-mobile-combustion-example.csv', markdown=footer_md, expanded=True)

    st.subheader("Stationary Combustion", anchor='S1_StationaryCombustion') 
    show_example_form(S1_StationaryCombustion, key='s1sc', title='Show example form (S1-C0: Stationary Combustion)', button_text='Get example form', filename='s1-c0-stationary-combustion-example.csv', markdown=footer_md, expanded=True)

    st.subheader("Fugitive Emission", anchor='S1_FugitiveEmission')  
    show_example_form(S1_FugitiveEmission, key='s1fe', title='Show example form (S1-C0: Fugitive Emission)', button_text='Get example form', filename='s1-c0-fugitive-emission-example.csv', markdown=footer_md, expanded=True)


  with tab2:
    t1, t2 = st.tabs(['Upload/Validate', 'Analyze uploads'])

    with t1:        
      st.info('*(For best results, upload only csv files containing matching fields from examples and keep edits to recommended default fields to minimum)*')
      
      # State for clear button
      if 'widget_key' not in st.session_state:
        st.session_state.widget_key = str(random.randint(1000, 100000000))

      # Maximum number of files allowed
      MAX_FILES = 3  

      with st.form('Upload CSV files'):
        uploaded_files = st.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True,  key=st.session_state.widget_key, help='CSV containing any relevant Scope 1 data. Categories are automatically inferred')

        c1,c2 = st.columns([1,1])
        with c1:
          submit_button = st.form_submit_button('Upload')
        # with c2:
        #   clear_button = st.form_submit_button('Clear Files')

        # if clear_button:
        #   # Generate a new random key for the file uploader widget
        #   # https://discuss.streamlit.io/t/are-there-any-ways-to-clear-file-uploader-values-without-using-streamlit-form/40903
        #   st.session_state.widget_key = str(random.randint(1000, 100000000))

          
        if submit_button and uploaded_files:
          if len(uploaded_files) > MAX_FILES:
            st.warning(f"Maximum number of files reached. Only the first {MAX_FILES} will be processed.")
            uploaded_files = uploaded_files[:MAX_FILES]

          # reset everything if button is clicked
          st.session_state['s1de_original_dfs'] = {}
          st.session_state['s1de_result_dfs'] = {}
          st.session_state['s1de_warnings'] = {}
          st.session_state['s1de_calc_results'] = {}

          # Inferencer and df inits
          modinf = ModelInferencer()
          cache = S3_Lookup_Cache()

          s1_models = [
            'S1_FugitiveEmission', 'S1_MobileCombustion', 'S1_StationaryCombustion'
          ]

          # Loop through the uploaded files and convert to models
          progress_bar = st.progress(0)
          nfiles = len(uploaded_files)
          progress_idx = 1
          
          for uploaded_file in uploaded_files:
            data = pd.read_csv(uploaded_file)
            if data is not None:
              df = get_dataframe(data)

              # infer model from df
              inferred_model = modinf.infer_model_from_df(df=df)
              if inferred_model is None:
                st.error(f'Uploaded file "{uploaded_file.name}" with columns {list(df.columns)} has no reliable matches. Please make sure you are submitting a file that closely resemble the examples.')
                continue

              model_name = inferred_model['model']
              Model = modinf.available_models[model_name]    
          
              # Choose calculator based on inferred model
              if model_name not in s1_models:
                st.error(f'Uploaded file "{uploaded_file.name}" with columns {list(df.columns)} has no reliable matches against Scope 1 forms. Skipping...')
                continue

              else:
                CREATOR_FUNCTIONS = {
                  'S1_MobileCombustion': partial( create_s1mc_data, Model=Model, cache=cache ),
                  'S1_StationaryCombustion': partial( create_s1sc_data, Model=Model, cache=cache ),
                  'S1_FugitiveEmission': partial( create_s1fe_data, Model=Model, cache=cache ),
                }
                calc = S1_Calculator(cache=cache)
                creator = CREATOR_FUNCTIONS[model_name]
                
              try:
                calc, warning_list = df_to_calculator(df, calculator=calc, creator=creator, progress_bar=False)
                result_df = calculator_to_df(calc)

                if len(warning_list) > 0:
                  st.session_state['s1de_warnings'][model_name] = warning_list

                st.session_state['s1de_original_dfs'][model_name] = df
                st.session_state['s1de_result_dfs'][model_name] = result_df
                st.session_state['s1de_calc_results'][model_name] = calc
              
              except Exception as e:
                raise
      
              # update progress bar
              progress_pct = progress_idx / nfiles
              progress_bar.progress(progress_pct)
              progress_idx += 1


      with t2:
        with st.expander('Show help'):
          st.markdown('Hi')

        if 's1de_original_dfs' not in st.session_state or st.session_state['s1de_original_dfs'] in [{}]:
          st.info('Please upload at least one valid table at "Upload/Validate" tab to continue')

        if 's1de_original_dfs' in st.session_state and st.session_state['s1de_original_dfs'] not in [{}]:
          with st.expander('Show uploaded table', expanded=True):
            for name, df in st.session_state['s1de_original_dfs'].items():
              pandas_2_AgGrid(df, theme='balham', height=300, key=f's1de_og_{name}_aggrid')

        if 'analyzed_s3vc' not in st.session_state:
          st.session_state['analyzed_s1de'] = False
        
        analyze_button = st.button('Analyze uploaded dataframes', help='Attempts to return calculation results for each row for table. Highly recommended to reupload a validated table before running analysis')
        if analyze_button and st.session_state['s1de_original_dfs'] not in [{}]:
          st.session_state['analyzed_s1de'] = True   
          st.success('Uploaded Scope 3 data tables analyzed!')

          if all(key in st.session_state for key in ['s1de_warnings', 's1de_original_dfs']) and st.session_state.get('analyzed_s1de', True):
            with st.expander('Show warnings'):
              for name, warnings in st.session_state['s1de_warnings'].items():
                for warn in warnings:
                  st.warning(f'{name}: {warn}')
            
            for name, df in st.session_state['s1de_result_dfs'].items(): # might not need this
              with st.expander(f'Show table for analyzed **{name}**'):
                pandas_2_AgGrid(df, theme='balham', height=300, key=f's1de_{name}_aggrid')


    with tab3:
      st.subheader('Executive Insights')

      if 's1de_calc_results' in st.session_state and st.session_state['s1de_calc_results'] != {}:
        res_df = st.session_state['s1de_calc_results'] # key: Model name, val: Calculator
        res_df = calculators_2_df(res_df) # convert each k/v to df

        st.write(res_df) # 



def calculators_2_df(calculators):
  """ 
  calculators: dictionary of calculators
    Example: 
    calculators = {
      'Scope1_MobileCombustion': calculator1,
      'Scope2_IndirectEmissions': calculator2,
      # ...
    }
  """
  def get_first_number(d):
    if isinstance(d, dict):
      for value in d.values():
        if isinstance(value, (int, float)):
          return value
    return np.nan

  rows = []
  for name, calculator in calculators.items():
    scope = name.split('_')[0]  # Assuming the scope is the first part of the name
    category = name.split('_')[-1]

    if hasattr(calculator, 'calculated_emissions'):
      for key, value in calculator.calculated_emissions.items():

        # Initialize row
        row = {
          'scope': scope,
          'category': category,
        }
        input_data = value.get('input_data', {})

        for k, v in input_data.items():
          if 'description' not in k.lower() and 'uuid' not in k.lower():
            row[k] = v

        emission_data = value.get('calculated_emissions', {})

        for k, v in emission_data.items():
          if isinstance( v, (int, float, str, bool)):
            row[k] = v
          elif isinstance( v, (dict)):
            row[k] = get_first_number(v)
          elif isinstance( v, list ):
            try:
              row[k] = v[0]
            except:
              row[k] = {}
          else:
            print(f'Column {k} unable to retrieve valid value. {v} as {type(v)}')

        rows.append(row)
  
  df = pd.DataFrame(rows)
  for col in df.columns:
    if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
      df[col] = df[col].apply(json.dumps)

  return df






## Markdowns
general_guide_md = """
- Get the recommended scopes for your sector. **:blue["Settings" >> "Show highlighted rows"]**
- Click on the links in **[:green[Table of Contents]](#s3-toc)** to redirect you to the recommended tables to fill. 
- Download the example forms. Each transaction counts as a row.
- Unless the default information conflicts with what you have, you are **:green[strongly advised]** to not edit default values for columns. 
- Cells shown as **<Blank>** indicates the field is optional, but inputting them will result in greater accuracy and reconcilation efforts.
"""

table_of_contents_md="""
- [**Mobile Combustion**](#S1_MobileCombustion)
- [**Stationary Combustion**](#S1_StationaryCombustion)
- [**Fugitive Emission**](#S1_FugitiveEmission)
"""

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

footer_md = """*(Highlighted columns with <Blank> are optional. Blue column indicates recommended default values)*"""