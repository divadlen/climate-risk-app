import streamlit as st
from st_aggrid import AgGrid, JsCode, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import numpy as np
import pandas as pd
import json
import logging
from typing import List
from supabase import create_client

import plotly.express as px

from utils.globals import SECTOR_TO_CATEGORY_IDX, IDX_TO_CATEGORY_NAME
from utils.utility import convert_BaseModel

from utils.s3vc_Misc.s3c15_models import *
 


def s3vc_Page(): 
  st.title('Scope 3: Value Chain') 
 
  if not st.session_state.get('s3_settings'):
    with st.form(key='scope_3_config'):
      valid_sectors = list(SECTOR_TO_CATEGORY_IDX.keys())
      sector = st.selectbox('Select Sector', options=valid_sectors)
      
      if st.form_submit_button('Confirm settings'):
        with st.spinner():
          st.session_state["s3_settings"] = True
          st.session_state['s3_sector'] = sector
          st.experimental_rerun()

  if 's3_settings' in st.session_state and st.session_state['s3_settings'] == True:
    tab1, tab2, tab3, tab4 = st.tabs(['Settings', 'Get Forms/Guidelines', 'Submit & Review', 'Analysis'])
    applicable_indices = SECTOR_TO_CATEGORY_IDX.get(st.session_state['s3_sector'], None)
    
    try:
      sorted_applicable_indices = sorted(list(set(applicable_indices)))
      applicable_bools = [i in sorted_applicable_indices for i in range(1, 16)]        
    except:
      sorted_applicable_indices = None
      applicable_bools = [False] * 15

    with tab1:
      with st.form(key='scope_3_reset'):
        st.info(f"Current sector: {st.session_state['s3_sector']}")

        df = pd.DataFrame({
          'Category': [IDX_TO_CATEGORY_NAME[i] for i in range(1,16)],
          'Applicable': applicable_bools
        })

        cellstyle_jscode = JsCode("""
        function(params){
            if (params.data.Applicable === true) {
                return {
                    'backgroundColor': 'lightblue',
                }
            } else {
                return {
                    'color': 'black',
                    'backgroundColor': 'white',
                }
            }
        }
        """)
        pandas_2_AgGrid(df, cellstyle_jscode=cellstyle_jscode, height=None, pagination=None)

        if st.form_submit_button('Reset settings'):
          del st.session_state['s3_settings']
          st.experimental_rerun()


    with tab2:
      footer_md = """*(Highlighted columns with <Blank> are optional. Blue column indicates recommended default values*"""
      
      st.subheader('User Guide')
      with st.expander('Show help', expanded=True):
        st.markdown(general_guide_md)

      st.subheader('Table of contents', anchor='s3-toc')
      with st.expander('Show table of contents'):
        st.markdown(table_of_contents_md)
      st.divider()

        1: 'Category 1 : Purchased goods & services',
  2: 'Category 2 : Capital goods',
  3: 'Category 3 : Fuel- & energy-related activities (excluded in Scope 1 & 2)',
  4: 'Category 4 : Upstream transportation & distribution',
  5: 'Category 5 : Waste generated in operations',
  6: 'Category 6 : Business and air travel',
  7: 'Category 7 : Employee commuting',
  8: 'Category 8 : Upstream leased assets',
  9: 'Category 9 : Transportation & distribution of sold products',
  10: 'Category 10 : Processing of sold products',
  11: 'Category 11 : Use of sold products',
  12: 'Category 12 : End-of-life treatment of sold products',
  13: 'Category 13 : Downstream leased assets',
  14: 'Category 14 : Franchises',
  15: 'Category 15 : Investments',

      st.subheader("Category 1 : Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')




      st.subheader("Category 15-1A: Investment-Listed Equity", anchor='S3C15_1A_ListedEquity')
      show_example_form(S3C15_1A_ListedEquity, title='Show example form (S3-C15-1A Listed Equity)', button_text='Get example form', filename='s3-c15-1a-listed_equity-example.csv', markdown=footer_md)
        

      # with st.expander(f'Show guidelines for **Scope 3: {IDX_TO_CATEGORY_NAME[1]}**'):
      #   example_df = convert_BaseModel( S3C15_2B_VehicleLoans, examples=True, return_as_string=False)
      #   csv_str = convert_BaseModel( S3C15_2B_VehicleLoans, examples=True ) # replace "category" with name of class


      #   cellstyle_jscode = JsCode("""
      #   function(params){
      #       if (params.value === '<Blank>') {
      #           return {
      #               'backgroundColor': 'teal',
      #               'color': 'white'
      #           }
      #       } else {
      #           return {
      #               'color': 'black',
      #               'backgroundColor': 'white',
      #           }
      #       }
      #   }
      #   """)
      #   pandas_2_AgGrid(example_df, cellstyle_jscode=cellstyle_jscode, height=None)


      #   st.download_button(
      #     label=f'Get example Scope 3: Category 1 form',
      #     data=csv_str,
      #     file_name=f'scope-3-category-1-form.csv',
      #     mime='text/csv'
      #   )


      # uploaded_files = st.file_uploader("Choose a CSV file", type="csv", accept_multiple_files=True)

      # st.write(applicable_indices) # 
      
      # Track categories
      # uploaded_categories = set()
      # applicable_categories = set(applicable_indices)

      # for uploaded_file in uploaded_files:
      #   def infer_category():
      #     pass 

      #   inferred_category  = infer_category(uploaded_file)
      #   if inferred_category in uploaded_categories:
      #     st.warning(f'Multiple files for category {inferred_category} uploaded! Only the first will be used.')
      #   else:
      #     uploaded_categories.add(inferred_category)

      #   if inferred_category in applicable_categories:
      #     applicable_categories.remove(inferred_category)

      # for remaining_category in applicable_categories:
      #   with st.expander(f'Inputs for {IDX_TO_CATEGORY_NAME[remaining_category]}'):
      #     st.write(f'{IDX_TO_CATEGORY_NAME[remaining_category]}')



      




def pandas_2_AgGrid(df: pd.DataFrame, cellstyle_jscode=None, theme:str='streamlit', height=600, pagination=True, key=None) -> AgGrid:
  if not cellstyle_jscode:
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

  if pagination == True:
    custom_css={"#gridToolBar": {"padding-bottom": "0px !important"}} # allows page arrows to be shown
  else:
    custom_css=None

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
  gd.configure_pagination(enabled=pagination)
  
  grid_options = gd.build()
  grid_response = AgGrid(
    df, 
    gridOptions=grid_options,
    custom_css=custom_css,
    height=height, 
    theme=theme,
    reload_data=True,
    allow_unsafe_jscode=True,
    key=key,
  )
  return grid_response['data']


















def show_sector_md(settings):
  if settings not in SECTOR_TO_CATEGORY_IDX.keys():
    raise ValueError(f'{settings} not in {list(SECTOR_TO_CATEGORY_IDX.keys())}')

  if settings == 'Banking and Finance':
    return md_banking
  
  if settings == 'Energy':
    return md_energy
  

def show_guidelines_md(category):
  pass


md_banking = """
### Banking and Finance

#### Required forms for
- Scope 15: Investments
"""

md_energy= """
### Energy 

#### Required forms for 
- Scope 7
"""

md_c9="""
abc
"""

md_c15="""
Form options: 

1. Corporate Finance:
- 1A ListedEquity
- 1B UnlistedEquity
- 1C CorporateBonds
- 1D BusinessLoans
- 1E CommercialRealEstate

2. Consumer Finance:
- 2A Mortgage
- 2B VehicleLoans

3. Project Finance
4. Emission Removals
5. Sovereign Debt (government bonds)
"""

general_guide_md = """
- Get the recommended scopes for your sector. **:blue["Settings" >> "Show highlighted rows"]**
- Click on the links in **[:green[Table of Contents]](#s3-toc)** to redirect you to the recommended tables to fill. 
- Download the example forms. Each transaction counts as a row.
- Unless the default information conflicts with what you have, you are **:green[strongly advised]** to not edit default values for columns. 
- Cells shown as **<Blank>** indicates the field is optional, but inputting them will result in greater accuracy and reconcilation efforts.
"""

table_of_contents_md="""
- **Category 1 : Purchased goods & services**
- **Category 2 : Capital goods**
- **Category 3 : Fuel- & energy-related activities (excluded in Scope 1 & 2)**
- **Category 4 : Upstream transportation & distribution**
- **Category 5 : Waste generated in operations**
- **Category 6 : Business and air travel**
- **Category 7 : Employee commuting**
- **Category 8 : Upstream leased assets**
- **Category 9 : Transportation & distribution of sold products**
- **Category 10 : Processing of sold products**
- **Category 11 : Use of sold products**
- **Category 12 : End-of-life treatment of sold products**
- **Category 13 : Downstream leased assets**
- **Category 14 : Franchises**
- **Category 15 : Investments**
  - 1. Corporate Finance
    - [A: Listed Equity](#S3C15_1A_ListedEquity)
    - [B: Unlisted Equity](#S3C15_1B_UnlistedEquity)
    - [C: Corporate Bonds](#S3C15_1C_CorporateBonds)
    - [D: Business Loans](#S3C15_1D_BusinessLoans)
    - [E: Commercial Real Estate](#S3C15_1E_CommercialRealEstate)
  - 2. Consumer Finance
    - [A: Mortgage](#S3C15_2A_Mortgage)
    - [B: Vehicle Loans](#S3C15_2B_VehicleLoans)
  - [3. Project Finance](#S3C15_3_ProjectFinance)
  - [4. Emission Removals](#S3C15_4_EmissionRemovals)
  - [5. Sovereign Debt / Government Bonds](#S3C15_5_SovereignDebt)
"""



def display_c1_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 1 : Purchased goods & services**'):
    pass

def display_c2_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 2 : Capital goods**'):
    pass

def display_c3_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 3 : Fuel- & energy-related activities (excluded in Scope 1 & 2)**'):
    pass

def display_c4_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 4 : Upstream transportation & distribution**'):
    pass

def display_c5_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 5 : Waste generated in operations**'):
    pass

def display_c6_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 6 : Business and air travel**'):
    pass

def display_c7_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 7 : Employee commuting**'):
    pass

def display_c8_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 8 : Upstream leased assets**'):
    pass

def display_c9_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 9 : Transportation & distribution of sold products**'):
    pass

def display_c10_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 10 : Processing of sold products**'):
    pass

def display_c11_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 11 : Use of sold products**'):
    pass

def display_c12_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 12 : End-of-life treatment of sold products**'):
    pass

def display_c13_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 13 : Downstream leased assets**'):
    pass

def display_c14_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 14 : Franchises**'):
    pass

def display_c15_guidelines():
  with st.expander('Show guidelines for **Scope 3: Category 15 : Investments**'):
    st.markdown(md_c15)

    csv_str = convert_BaseModel( S3C15_2B_VehicleLoans, examples=True ) 
    example_df = convert_BaseModel( S3C15_2B_VehicleLoans, examples=True, return_as_string=False)
    
    cellstyle_jscode = JsCode("""
    function(params){
        if (params.value === '<Blank>') {
            return {
                'backgroundColor': 'teal',
                'color': 'white'
            }
        } else {
            return {
                'color': 'black',
                'backgroundColor': 'white',
            }
        }
    }
    """)
    pandas_2_AgGrid(example_df, cellstyle_jscode=cellstyle_jscode, height=None)

    st.download_button(
      label=f'Get example Scope 3: Category 1 form',
      data=csv_str,
      file_name=f'scope-3-category-1-form.csv',
      mime='text/csv'
    )
    


def show_example_form(BaseModelCls, title:str, button_text: str, filename: str, markdown:str=None):
    """ 
    BaseModelCls: 
      Pydantic BaseModel
    
    title: 
      Title displayed on expander
    
    button_text: 
      Text for download button WITHOUT csv extension
    
    filename: 
      Default downloaded filename
    
    markdown: 
      Optional, extra markdown to include below forms. 
    """

    with st.expander(title):
        csv_str = convert_BaseModel(BaseModelCls, examples=True)
        example_df = convert_BaseModel(BaseModelCls, examples=True, return_as_string=False)

        cellstyle_jscode = JsCode("""
        function(params){
            if (params.value === '<Blank>') {
                return {
                    'backgroundColor': 'teal',
                    'color': 'white'
                }
            } else if (typeof params.value === 'string' && !params.value.includes('EXAMPLE')) {
                return {
                    'backgroundColor': 'paleturquoise',
                    'color': 'black'
                }
            } else {
                return {
                    'color': 'black',
                    'backgroundColor': 'white',
                }
            }
        }
        """)
        pandas_2_AgGrid(example_df, cellstyle_jscode=cellstyle_jscode, height=None)

        st.download_button(
            label=button_text,
            data=csv_str,
            file_name=f'{filename}.csv',
            mime='text/csv'
        )

        if markdown:
          st.markdown(markdown)