import streamlit as st
from streamlit import session_state as state
import streamlit_antd_components as sac
from streamlit_extras.metric_cards import style_metric_cards
    

import numpy as np
import pandas as pd
import random
from functools import partial
from typing import List

import plotly.express as px
import plotly.graph_objects as go

from utils.utility import get_dataframe, format_metric
from utils.display_utility import show_example_form, pandas_2_AgGrid
from utils.model_df_utility import df_to_calculator, calculator_to_df, calculators_2_df
from utils.md_utility import markdown_insert_images
from utils.model_inferencer import ModelInferencer

from utils.s1de_Misc.s1_models import *
from utils.s1de_Misc.s1_calculators import S1_Calculator
from utils.s1de_Misc.s1_creators import *

from utils.s3vc_Misc.s3_cache import S3_Lookup_Cache


def s1de_Page(): 
  user_level = state.get("user_level", 1)
  state['S1SC_Lookup_Cache'] = state.get('S1SC_Lookup_Cache', S3_Lookup_Cache())
  state['s1sc_df'] = state.get('s1sc_df', None)
  state['validated_s1sc_df'] = state.get('validated_s1sc_df', None)
  state['validated_s1sc_warnings'] = state.get('validated_s1sc_warnings', [])

  st.title('Scope 1: Direct Emissions')
  tab1, tab2, tab3 = st.tabs(['Get Forms/Guidelines', 'Submit & Review', 'Analysis'])

  with tab1:
    st.subheader('User Guide')

    with st.expander('Show help', expanded=True):
      download_desc = 'Click on the links in Table of Contents to redirect you to the recommended tables to fill. Download the example forms. Each transaction counts as a row.'
      fill_desc = 'Each form is represented as CSV, each row is one transaction. Example: in "Mobile Combustion" file, each vehicle/machine counts as one row. Details at "More help" and "Visual help"'
      upload_desc = 'In "Submit & Review" tab, drag and drop your csv files in the upload window.'
      validate_desc = 'In "Submit & Review" tab, go to "Analyze uploads" to verify your uploaded files. From there, our AI validator will simulate the results of your submitted files.'

      sac.steps(
        items=[
          sac.StepsItem(title='Download relevant forms', subtitle='', description=download_desc),
          sac.StepsItem(title='Fill relevant forms', subtitle='', description=fill_desc),
          sac.StepsItem(title='Upload relevant forms', subtitle='', description=upload_desc),
          sac.StepsItem(title='Validate & submit forms', subtitle='', description=validate_desc),
        ], 
        format_func='title',
        direction='vertical',
      )
    

    with st.expander('Visual help'):
      with open("resources/mds/s1sc-general-guide-1.md", "r") as gmd:
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
      state.get('widget_key', str(random.randint(1000, 100000000)))

      if user_level >=10:
        st.error('File upload feature not available for demo accounts')
      else:
        # Maximum number of files allowed
        MAX_FILES = 3  
        with st.form('Upload CSV files'):
          uploaded_files = st.file_uploader("Upload CSV files (accepts only up to 3 files)", type=["csv"], accept_multiple_files=True,  key=state.widget_key, help='CSV containing any relevant Scope 1 data. Categories are automatically inferred')

          c1,c2 = st.columns([1,1])
          with c1:
            submit_button = st.form_submit_button('Upload')

          if submit_button and uploaded_files:
            if len(uploaded_files) > MAX_FILES:
              st.warning(f"Maximum number of files reached. Only the first {MAX_FILES} will be processed.")
              uploaded_files = uploaded_files[:MAX_FILES]

            s1_inits = {
              's1de_warnings': {},
              's1de_invalid_indices': {},
              's1de_original_dfs': {},
              's1de_result_dfs': {},
              's1de_calc_results': {},
            }

            # Loop to initialize variables in state if not present
            for var_name, default_value in s1_inits.items(): 
              state[var_name] = default_value # reset everything if button is clicked

            # Inferencer and df inits
            modinf = ModelInferencer()
            cache = state['S1SC_Lookup_Cache']

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
                
                # Store the filename with the model name
                if 'model_filenames' not in state:
                  state['model_filenames'] = {}
                state['model_filenames'][model_name] = uploaded_file.name
            
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
                  calc, warning_list, invalid_indices = df_to_calculator(df, calculator=calc, creator=creator, progress_bar=False, return_invalid_indices=True)
                  result_df = calculator_to_df(calc)

                  if len(warning_list) > 0:
                    state['s1de_warnings'][model_name] = warning_list
                    state['s1de_invalid_indices'][model_name] = invalid_indices
                  state['s1de_original_dfs'][model_name] = df
                  state['s1de_result_dfs'][model_name] = result_df
                  state['s1de_calc_results'][model_name] = calc
                
                except Exception as e:
                  raise
        
                # update progress bar
                progress_pct = progress_idx / nfiles
                progress_bar.progress(progress_pct)
                progress_idx += 1 


    with t2:
      with st.expander('Show help', expanded=False):
        with open("resources/mds/s1sc-validation-guide-1.md", "r") as gmd:
          readme = gmd.read()
        readme = markdown_insert_images(readme) 
        st.markdown(readme, unsafe_allow_html=True) 

      if 's1de_original_dfs' not in state or state['s1de_original_dfs'] in [{}]:
        st.info('Please upload at least one valid table at "Upload/Validate" tab to continue')

      if 's1de_original_dfs' in state and state['s1de_original_dfs'] not in [{}]:
        with st.expander('Show uploaded table', expanded=True):
          for name, df in state['s1de_original_dfs'].items():
            pandas_2_AgGrid(df.head(20), theme='balham', height=300, key=f's1de_og_{name}_aggrid')

      if 'analyzed_s1de' not in state:
        state['analyzed_s1de'] = False
      
      analyze_button = st.button('Validate uploaded dataframes', help='Attempts to return calculation results for each row for table.')
      if analyze_button and state['s1de_original_dfs'] not in [{}]:
        state['analyzed_s1de'] = True   
        st.success('Uploaded Scope 1 data tables analyzed!')
        
        st.divider()
        st.subheader('Validation Results')

        if all(key in state for key in ['s1de_warnings', 's1de_original_dfs']) and state.get('analyzed_s1de', True):
          with st.expander('Show warnings'):
            for name, warnings in state['s1de_warnings'].items():
              for warn in warnings:
                st.warning(f'{name}: {warn}')
            
            for name, df in state['s1de_original_dfs'].items():
              df = df.replace('<Blank>', None)
              df = df.replace('<To fill>', None)
              df = df.replace(np.nan, None)
              pandas_2_AgGrid(
                df, theme='balham', height=300, key=f's1de_warn_{name}_aggrid', 
                highlighted_rows=state['s1de_invalid_indices'].get(name, [])  # Returns an empty list if 'name' is not in the dictionary
              )
          
          for name, df in state['s1de_result_dfs'].items():
            with st.expander(f'Show table for analyzed **{name}**'):
              pandas_2_AgGrid(df, theme='balham', height=300, key=f's1de_{name}_aggrid')


  with tab3:
    st.subheader('Executive Insights')
    if 's1de_calc_results' not in state or state['s1de_calc_results'] == {}:
      st.error('Nothing to display here. Have you uploaded or analyzed your uploaded files?')

    if 's1de_calc_results' in state and state['s1de_calc_results'] != {}:
      res_df = state['s1de_calc_results'] # key: Model name, val: Calculator
      res_df = calculators_2_df(res_df) # convert each k/v to df

      emissionOverviewPart(df=res_df)

      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')
      st.write('')


        












def emissionOverviewPart(df):      
    # Global styling
    style_metric_cards(background_color='#D6D6D6', border_left_color='#28104E', border_radius_px=60)

    c1,c2,c3 = st.columns([1,1,1])
    with c1: 
      total_mc = df[df['category_name'] == 'C0: Mobile Combustion']['emission_result'].sum()
      st.metric(label="Mobile Combustion", value=format_metric(total_mc))
    with c2:
      total_sc = df[df['category_name'] == 'C0: Stationary Combustion']['emission_result'].sum()
      st.metric(label="Stationary Combustion", value=format_metric(total_sc))
    with c3:
      total_fe = df[df['category_name'] == 'C0: Fugitive Emission']['emission_result'].sum()
      st.metric(label="Fugitive Emissions", value=format_metric(total_fe))
    st.divider()

    st.subheader('Top contributors')
    
    # Allowed columns for groupby selection
    potential_columns = ['fuel_type', 'vehicle_type', 'refrigerant_type']

    # Filter out the columns that actually exist in the DataFrame
    available_columns = [col for col in potential_columns if col in df.columns]

    c1, c2 = st.columns([1, 3])
    with c1:
      selected_group = st.selectbox('Select group', options=available_columns)

    # Group DataFrame by selected option, sum, then sort
    grouped_df = df.groupby(selected_group)['emission_result'].sum().reset_index()
    sorted_df = grouped_df.sort_values('emission_result', ascending=False)
    sorted_df['delta'] = round( sorted_df['emission_result'].pct_change(-1).fillna(0) * 100, 2)

    # Limit to top 10 and combine the rest as 'Others'
    top_10_df = sorted_df.head(10)
    others_sum = sorted_df.iloc[10:]['emission_result'].sum()
    others_delta = sorted_df.iloc[9]['emission_result'] - others_sum if len(sorted_df) > 10 else 0
    others_df = pd.DataFrame({selected_group: ['Others'], 'emission_result': [others_sum], 'delta': [others_delta]})
    top_10_df = pd.concat([top_10_df, others_df], ignore_index=True)

    with c1:
      for index, row in top_10_df.head(5).iterrows():
        st.metric(label=f"{row[selected_group]} Emissions", value=format_metric(row['emission_result']), delta=f"{row['delta']}%")

    # Vertical Bar Chart with Cumulative Sum
    total_emission = top_10_df['emission_result'].sum()
    top_10_df['cum_sum'] = top_10_df['emission_result'].cumsum()
    top_10_df['cum_sum_percent'] = (top_10_df['cum_sum'] / total_emission) * 100

    fig = go.Figure()
    for index, row in top_10_df.iterrows():
      fig.add_trace(go.Bar(
        x=[row[selected_group]],  # x should be a list or array
        y=[row['emission_result']],  # y should also be a list or array
        name=str(row[selected_group]),
        yaxis='y1',
        hovertemplate=f"%{{value:.2f}} kg"
      ))

    # Cumulative Sum Line
    fig.add_trace(go.Scatter(
      x=top_10_df[selected_group],
      y=top_10_df['cum_sum_percent'],
      mode='lines+markers',
      name='Cumulative Sum (%)',
      yaxis='y2',
      hovertemplate ='%{y:.2f} %',
    ))

    # Update layout
    fig.update_layout(
      title='',
      xaxis_title=f'<b>{selected_group}</b>',
      yaxis=dict(title='<b>Emission Result</b>'),
      yaxis2=dict(
        title='<b>Cumulative Sum (%)</b>',
        overlaying='y',
        side='right',
        range=[0, 100]
      ),
      height=800,
      template='google',
      legend=dict(
        orientation='h', title=None,
        x=0.5, y=1, xanchor='center', yanchor='bottom'
      ),
      showlegend=True,
      hovermode="x",
      hoverlabel=dict(font_size=18),
    )
    
    with c2:
      st.plotly_chart(fig, use_container_width=True)

          






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

footer_md = """*(<Blank> and <To fill> are optional. <To fill> indicates optional fields that can affect calculations. Blue indicates REQUIRED fields with recommended default values. Orange indicates REQUIRED fields.)*"""




# def MaterialUIPart(df):
#   """ 
#   Material UI not supporting streamlit local elements.
#   """
#   from streamlit_elements import elements, sync, event
#   from types import SimpleNamespace
#   from mui_elements.dashboard import Dashboard
#   from mui_elements.player import Player
#   from mui_elements.data_grid import DataGrid
#   from mui_elements.charting import Pie
  
#   if 'w' not in state:
#     board = Dashboard()
#     w = SimpleNamespace(
#       dashboard= board,
#       player = Player(board, x=1, y=30, w=5, h=5, minW=3, minH=3),
#       table = DataGrid(board, 1,2,3,4, df=df),
#       pie = Pie(board, 1,2,3,4, fig=None),
#     )
#     state.w = w
#   else:
#     w = state.w


#   with elements('ABC'):
#     event.Hotkey("ctrl+s", sync(), bindInputs=True, overrideDefault=True)

#     with w.dashboard(rowHeight=57):
#       w.player()
#       w.table()
#       w.pie()