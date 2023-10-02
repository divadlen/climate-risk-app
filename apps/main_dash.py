import streamlit as st
from streamlit_extras.metric_cards import style_metric_cards
from st_aggrid import AgGrid, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import math
import numpy as np
import pandas as pd
import json
import re

import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.io as pio

from utils.charting import initialize_plotly_themes \
    ,make_bar_chart, make_donut_chart, make_grouped_line_chart, make_sankey_chart, make_sunburst_chart



def main_dash_Page():
  
  # Global styling
  style_metric_cards(background_color='#D6D6D6', border_left_color='#28104E', border_radius_px=60)

  st.title('Emissions Executive Summary')
  tab1, tab2 = st.tabs(["Overall Emissions", "Financed Emissions"])

  with tab1:
    dfs_to_concat = []

    if 's1de_calc_results' in st.session_state and st.session_state['s1de_calc_results'] != {}:
      s1_res = st.session_state['s1de_calc_results']
      s1_df = calculators_2_df(s1_res)
      s1_df['data_quality'] = 4
      dfs_to_concat.append(s1_df)
    else:
      st.error('Calculated results for Scope 1 not yet retrieved. Have you already uploaded and analyzed the necessary files for calculation?')

    if 's2ie_calc_results' in st.session_state and st.session_state['s2ie_calc_results'] != {}:
      s2_res = st.session_state['s2ie_calc_results']     
      s2_df = calculators_2_df(s2_res)
      s2_df['data_quality'] = 4
      dfs_to_concat.append(s2_df)
    else:
      st.error('Calculated results for Scope 2 not yet retrieved. Have you already uploaded and analyzed the necessary files for calculation?')

    if 's3vc_calc_results' in st.session_state and st.session_state['s3vc_calc_results'] != {}:
      s3_res = st.session_state['s3vc_calc_results'] # key: Model name, val: Calculator
      s3_df = calculators_2_df(s3_res) # convert each k/v to df
      dfs_to_concat.append(s3_df)
    else:
      st.error('Calculated results for Scope 3 not yet retrieved. Have you already uploaded and analyzed the necessary files for calculation?')

    # st.write(pd.concat(dfs_to_concat, ignore_index=True)) # 

    standardized_dfs = [standardize_scope_df(df) for df in dfs_to_concat]
    if standardized_dfs:
      

      df = pd.concat(standardized_dfs, ignore_index=True)
      df = standardize_merged_df(df)

      st.write(df.head().to_dict(orient='records')) # 

      with st.expander('Expand'):
        st.subheader('Overall')

        c1, c2, c3 = st.columns([1,2,1])
        with c1:
          with st.container():
            st.metric(label="Emissions Overview Total", value=df['emission_result'].sum(), delta=53)
            
          

        with c2:
          bar1 = make_bar_chart(df, scope_col=None, category_col='category_name', year_col=None, value_col='emission_result', theme='google', title='YEs')
          st.plotly_chart(bar1, use_container_width=True)

        with c3:
          pass

      # Emissions Overview
      emissionOverviewPart(df)

      # Category Performance
      with st.expander('Category Performance'):
        c1,c2 = st.columns([1,1])
        with c2:
          show_percent = st.selectbox('Show as percent (%)', options=[False, True])

        categories = df['category_name'].unique()
        for scope in [1, 2, 3]:
          scope_df = df[df['scope'] == scope]
          fig = make_bar_chart(
            scope_df, scope_col=None, category_col='category_name', year_col=None, value_col='emission_result', percent=show_percent,
            theme='google', title=f'Scope {scope}', horizontal_legend=True, legend_sort_numeric=True, auto_adjust_height=True
          )
          st.plotly_chart(fig, use_container_width=True)


      # Contributor Analysis
      contributorAnalysisPart(df)






      # # create bar chart
      # fig1 = make_bar_chart(df, scope_col='scope', value_col='emission_result', theme='google')
      # st.plotly_chart(fig1, use_container_width=True)

      # # create donut chart 
      # fig2 = make_donut_chart(df, group_col='scope', value_col='emission_result', hole=0.5, center_text='Emission Result', theme='gecko_v2')
      # st.plotly_chart(fig2, use_container_width=True)




      # # create sunburst chart
      # hierarchy_list = ['scope', 'category_name']
      # fig = make_sunburst_chart(df, hierarchy_list=hierarchy_list, value_col='emission_result')
      # st.plotly_chart(fig, use_container_width=True)



    else:
      st.error('No data available.')



  with tab2:
    pass






def emissionOverviewPart(df):      
    def format_metric(value):
      weight_denominator = 'Kg'

      if value <= 0:
        return f"0 ({weight_denominator} CO2e)"
      
      exponent = math.floor(math.log10(abs(value)))
      mantissa = value / 10**exponent

      if value > 1000:
        weight_denominator = 'Gg'
    
      if weight_denominator == 'Gg':
        mantissa -= 3

      return f"{mantissa:.4f}e{exponent} ({weight_denominator} CO2e)"

    with st.expander('Emissions Overview'):
      c1, c2, c3 = st.columns([1, 1, 1])
      
      with c1:
          total_scope1 = df[df['scope'] == 1]['emission_result'].sum()
          st.metric(label="Scope 1 Emissions", value=format_metric(total_scope1))

      with c2:
          total_scope2 = df[df['scope'] == 2]['emission_result'].sum()
          st.metric(label="Scope 2 Emissions", value=format_metric(total_scope2))

      with c3:
          total_scope3 = df[df['scope'] == 3]['emission_result'].sum()
          st.metric(label="Scope 3 Emissions", value=format_metric(total_scope3))
              
      # Upstream and Downstream percentages
      total_current = df[df['stream'] == 'Current']['emission_result'].sum()
      total_upstream = df[df['stream'] == 'Upstream']['emission_result'].sum()
      total_downstream = df[df['stream'] == 'Downstream']['emission_result'].sum()

      total = total_upstream + total_downstream
      upstream_percent = (total_upstream / total) * 100
      downstream_percent = (total_downstream / total) * 100

      # Create a DataFrame for the bar chart
      bar_df = pd.DataFrame({
          'Stream': ['Upstream', 'Downstream'],
          'Percentage': [upstream_percent, downstream_percent]
      })

      # Initialize the figure
      fig = go.Figure()

      # Add traces
      for index, row in bar_df.iterrows():
          fig.add_trace(go.Bar(
              x=[row['Percentage']],
              name=row['Stream'],
              orientation='h'
          ))

      # Update layout
      fig.update_layout(
          title='Upstream vs Downstream Emissions',
          xaxis=dict(title='Percentage'),
          yaxis=dict(title='', tickvals=[]),
          barmode='stack',
          height=250,
          template='gecko3',
          legend=dict(
            orientation='h',
            x=0.5,
            y=1,
            xanchor='center',
            yanchor='bottom'
          )
      )
      st.plotly_chart(fig, use_container_width=True)


def contributorAnalysisPart(df):
    with st.expander('Contributor Analysis'):
        # Get only categorical or object columns
        categorical_columns = set(df.select_dtypes(include=['category', 'object']).columns)
        exclude_columns = {'uuid', 'date'}
        categorical_columns = list(categorical_columns - exclude_columns)

        # Select category
        c1,c2 = st.columns([1,1])
        with c1:
          selected_option = st.selectbox('Select category', categorical_columns)

        # Group DataFrame by selected option and sum the emission_result
        grouped_df = df.groupby(selected_option)['emission_result'].sum().reset_index()

        # Sort DataFrame by emission_result
        sorted_df = grouped_df.sort_values('emission_result', ascending=False)

        # Vertical Bar Chart with Cumulative Sum
        total_emission = sorted_df['emission_result'].sum()
        sorted_df['cum_sum'] = sorted_df['emission_result'].cumsum()
        sorted_df['cum_sum_percent'] = (sorted_df['cum_sum'] / total_emission) * 100

        fig_v = go.Figure()

        # Emission Result Bar
        for index, row in sorted_df.iterrows():
            fig_v.add_trace(go.Bar(
                x=[row[selected_option]],  # x should be a list or array
                y=[row['emission_result']],  # y should also be a list or array
                name=str(row[selected_option]),
                yaxis='y1'
            ))

        # Cumulative Sum Line
        fig_v.add_trace(go.Scatter(
            x=sorted_df[selected_option],
            y=sorted_df['cum_sum_percent'],
            mode='lines+markers',
            name='Cumulative Sum (%)',
            yaxis='y2'
        ))

        # Update layout
        fig_v.update_layout(
            title='Vertical Bar Chart with Cumulative Sum',
            xaxis_title=selected_option,
            yaxis=dict(
                title='Emission Result',
                titlefont=dict(
                    color="#1f77b4"
                ),
                tickfont=dict(
                    color="#1f77b4"
                )
            ),
            yaxis2=dict(
                title='Cumulative Sum (%)',
                overlaying='y',
                side='right',
                range=[0, 100]
            ),
            height=600,
            template='google',
        )
        st.plotly_chart(fig_v, use_container_width=True)






































#---
# Helpers
#---
def standardize_scope_df(df):
  """ 
  df: 
    Merged df from s1, s2, s3 calculation results.
  """
  cols = [
    'uuid', 'date',
    'scope', 'category', 'category_name', 'stream',
    'emission_result', 'most_reliable_co2e', 'financed_emissions', 'emission_removals',
    'data_quality',

    # name
    'product_name', 'distributor_name', 'process_name', 'supplier_name',

    # asset status
    'ownership_status', 'ownership_share',

    # location
    'country', 'state', 'company_name', 'asset_class'  

    # types
    'refrigerant_type', 'vehicle_type', 'freight_type', 'fuel_type', 'waste_type'
  ]

  selected_cols = [col for col in cols if col in df.columns]
  df = df[selected_cols]
  return df



def standardize_merged_df(df):
  """ 
  Different dfs soured from s1, s2, s3 may have different names given for their emission column. 
  This function tries to standardize them into a same column name,
  """
  def standardize_emission_results(df, alt_col_name:str):
    df['emission_result'] = df.apply(
      lambda row: row[alt_col_name] if pd.isna(row['emission_result']) and not pd.isna(row[alt_col_name]) else row['emission_result'],
      axis=1
    )
    df = df.drop(alt_col_name, axis=1)
    return df
  
  alt_col_names = ['most_reliable_co2e', 'financed_emissions', 'emission_removals']
  for name in alt_col_names:
    if name in df.columns:
      df = standardize_emission_results(df, alt_col_name=name)

  return df



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
  def camel_case_to_natural(camel_case_str):
    return re.sub('([a-z0-9])([A-Z])', r'\1 \2', camel_case_str)


  def extract_scope_and_category(name):
      scope_match = re.search(r'S(\d+)', name)
      category_match = re.search(r'C(\d+)', name)
      
      scope = int(scope_match.group(1)) if scope_match else None
      category = int(category_match.group(1)) if category_match else None
      category_name = camel_case_to_natural(name.split('_')[-1])
      return scope, category, category_name
  

  def get_stream_status(scope, category):
      if scope in [1, 2]:
          return "Current"
      if category in [None, np.nan]:
          return None
      if category < 9:
          return "Upstream"
      return "Downstream"
  

  def get_first_number(d):
    if isinstance(d, dict):
      for value in d.values():
        if isinstance(value, (int, float)):
          return value
    return np.nan

  rows = []
  for name, calculator in calculators.items():
    scope, category, category_name = extract_scope_and_category(name)    
    stream = get_stream_status(scope=scope, category=category)

    if hasattr(calculator, 'calculated_emissions'):
      for key, value in calculator.calculated_emissions.items():

        # Initialize row
        row = {
          'scope': scope,
          'category': category,
          'category_name': f"C{category}: {category_name}",
          'stream': stream
        }
        input_data = value.get('input_data', {})

        for k, v in input_data.items():
          if 'description' not in k.lower(): # get rid of description cols
            row[k] = v
          # if 'uuid' not in k.lower():
          #   row[k] = v

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