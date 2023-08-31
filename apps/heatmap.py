import streamlit as st
from st_aggrid import AgGrid, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import numpy as np
import pandas as pd
import logging
from typing import Optional
from supabase import create_client

import plotly.express as px
import plotly.graph_objs as go

def heatmapPage():
  url = st.secrets['supabase_url']
  key = st.secrets['supabase_anon_key']
  supabase = create_client(url, key)

  TABLE = 'climate_risk-climate_simulation_v2'

  data = supabase_query(table=TABLE, url=url, key=key, limit=None)
  df = pd.DataFrame(data)
  if 'id' in df.columns:
    df = df.drop('id', axis=1)

  mapbox_token = st.secrets['mapbox_token']
  px.set_mapbox_access_token(mapbox_token)

  col1, col2 = st.columns([1,1])
  with col1:
    sel_year = st.selectbox('Select Scenario', df['Year'].unique())
  with col2:
    sel_scenario = st.selectbox('Select Scenario', df['Scenario'].unique())

  hdata=['Country', 'Latitude', 'Longtitude', 'Exposure', 'Rating Grade', 'PD', 'Balance', 'LTV', 'Vulnerability', 'Year', 'Scenario']
  temp = df[hdata]
  temp = temp[temp['Scenario'] == sel_scenario]
  temp = temp[temp['Year'] == sel_year]

  fig = px.density_mapbox(
      temp,
      lat='Latitude',
      lon='Longtitude',
      z='Exposure',
      radius=5,
      color_continuous_scale= px.colors.diverging.RdYlGn_r,
      hover_data=hdata
  )
  fig.update_layout(title='', height=600, template='presentation')

  with st.expander('Flood Risk Heatmap'):
    st.plotly_chart(fig, use_container_width=True)

  with st.expander('Show Table'):
    pandas_2_AgGrid(df, theme='streamlit')



#---Helper---#
@st.cache_data()
def show_columns(table:str, url:str, key:str):
  supabase = create_client(url, key)
  response = supabase.table(table).select("*").execute()
  data = response.data
  return list(data[0].keys()) if data else []

@st.cache_data(show_spinner=True)
def supabase_query(table:str, url:str, key:str, limit: Optional[int]=10000):
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
    logging.info(f'No data found for `{table}`. Make sure RLS is turned off.')
  return response.data


def pandas_2_AgGrid(df: pd.DataFrame, theme:str='streamlit') -> AgGrid:
  cellstyle_jscode = JsCode("""
  function(params){
    if (params.value == '0') {
      return {
        'color': 'black', 
        'backgroundColor': 'orange',
      }
    }
    if (params.value < '0') {
      return{
        'color': 'white',
        'backgroundColor': 'red',
      }
    }
    if (params.value > '0') {
      return{
          'color': 'white',
          'backgroundColor': 'green',
      }
    }
  }
  """)
  custom_css={"#gridToolBar": {"padding-bottom": "0px !important"}} # allows page arrows to be shown

  valid_themes= ['streamlit', 'alpine', 'balham', 'material']
  if theme not in valid_themes:
    raise Exception(f'Theme not in {valid_themes}')

 # AG Grid Options
  gd  = GridOptionsBuilder.from_dataframe(df)
  gd.configure_columns(
    df, 
    # cellStyle=cellstyle_jscode
  )
  gd.configure_default_column(floatingFilter=True, selectable=False)
  gd.configure_pagination(enabled=True)
  grid_options = gd.build()

  grid_response = AgGrid(
    df, 
    gridOptions=grid_options,
    custom_css=custom_css,
    height=600, 
    theme=theme,
    reload_data=True,
    allow_unsafe_jscode=True
  )
  return grid_response
