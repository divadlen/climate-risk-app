import streamlit as st
from st_aggrid import AgGrid, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import pandas as pd
import uuid
import json

from utils.utility import convert_BaseModel, get_cached_df

#---
# Streamlit Displays
#---
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
  
  # check if column cell is in list, json or dict, then transform column to json literal string 
  for col in df.columns:
    if df[col].apply(lambda x: isinstance(x, (dict, list))).any():
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
    enable_enterprise_modules=False # 
  )
  return grid_response['data']

def show_example_form(BaseModelCls, title:str, button_text: str, filename: str, markdown:str=None, key=None, expanded=False):
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

    with st.expander(title, expanded=expanded):
        csv_str = convert_BaseModel(BaseModelCls, examples=True)
        # example_df = convert_BaseModel(BaseModelCls, examples=True, return_as_string=False)
        example_df = get_cached_df(BaseModelCls) # cache doesnt work with aggrid

        cellstyle_jscode = JsCode("""
        function(params){
            if (params.value === '<Blank>') {
                return {
                    'backgroundColor': 'teal',
                    'color': 'white'
                }
            } else if (params.value === '<To fill>') {
                return {
                    'backgroundColor': 'orange',
                    'color': 'black'
                }
            } else if (typeof params.value === 'string' && !params.value.includes('EXAMPLE')) {
                return {
                    'backgroundColor': 'turquoise',
                    'color': 'black'
                }
            } else {
                return {
                    'backgroundColor': 'darkorange',
                    'color': 'black'
                }
            }
        }
        """)
        pandas_2_AgGrid(example_df, cellstyle_jscode=cellstyle_jscode, height=None, key=f'{str(uuid.uuid4())}')

        st.download_button(
            label=button_text,
            data=csv_str,
            file_name=f'{filename}',
            mime='text/csv'
        )

        if markdown:
          st.markdown(markdown)

