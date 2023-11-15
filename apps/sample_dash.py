import streamlit as st
from st_aggrid import AgGrid, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import numpy as np
import pandas as pd
import random
import logging
from typing import Optional, Union
from supabase import create_client

import plotly.express as px
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.io as pio

from utils.globals import ColorDiscrete

def dash_Page_v1():
    st.title('Emissions Executive Summary')

    tab1, tab2 = st.tabs(["Overall Emissions", "Financed Emissions"])

    with tab1:
      tdf = generate_toy_df()

      layout = { # doesnt work streamlit will hijack background settings
          'colorway': ColorDiscrete.gecko_v2,
          'plot_bgcolor': 'rgba(255,255,255,1)',
          'paper_bgcolor': 'rgba(255,255,255,1)',
          'font': {'color': 'black'},
          'xaxis': {'gridcolor': 'grey'},
          'yaxis': {'gridcolor': 'grey'},
      }
      pio.templates["custom"] = go.layout.Template(layout=layout)
      pio.templates.default = "custom"

      col1, col2 = st.columns([1,1])
      with col1:
        display_year = st.selectbox('Display year', [True, False])
        select_year = st.selectbox('Year', list(range(2015, 2025)))
      with col2:
        show_pct = st.selectbox('Show as percent', [False, True])
        scope = st.selectbox("Scope", [None, 1, 2, 3], index=2)

      figs = []
      fig1 = make_bar(tdf, scope=scope, year=display_year, percent=show_pct, theme='custom')
      fig2 = make_line(tdf, scope=scope, percent=show_pct, theme='custom')
      fig3 = make_sunburst(tdf[tdf['year'] == select_year], hierarchy_list=['scope', 'category'], val_col='emissions', root=f'{select_year}', percentage=show_pct, theme='custom')
      fig4 = make_sankey(tdf[tdf['year'] == select_year], theme='custom')
      figs.extend([fig1, fig2, fig3, fig4])

      for fig in figs:
        with st.expander('Show graphic'):  
          c1, c2, c3 = st.columns([1,5,1])
          with c2:
            st.plotly_chart(fig, use_container_width=True)


    with tab2:
      fdf = generate_s3c15_df()

      layout = { # doesnt work streamlit will hijack background settings
          'colorway': ColorDiscrete.gecko_v2,
          'plot_bgcolor': 'rgba(255,255,255,1)',
          'paper_bgcolor': 'rgba(255,255,255,1)',
          'font': {'color': 'black'},
          'xaxis': {'gridcolor': 'grey'},
          'yaxis': {'gridcolor': 'grey'},
      }
      pio.templates["custom"] = go.layout.Template(layout=layout)
      pio.templates.default = "custom"

      figs = []
      fig1 = make_bar_2(fdf, financial_type='investing', theme='custom')
      fig2 = make_sunburst_2(fdf, hierarchy_list=['financial_type', 'asset_class', 'sector'], root='Portfolio', theme='custom')
      fig3 = make_line_2(fdf, financial_type='investing', category='sector', theme='custom')
      fig4 = make_sankey_2(fdf[fdf['year'] == 2020], theme='custom')
      figs.extend([fig1, fig2, fig3, fig4])

      for fig in figs:
        with st.expander('Show graphic'):
          c1, c2, c3 = st.columns([1,5,1])
          with c2:  
            st.plotly_chart(fig, use_container_width=True)









#-- Generate synthetic data --#
def generate_toy_df():
  def generate_data(n, scope, start_year, end_year, category=None, emissions=1):
      years = np.linspace(start_year, end_year, n, endpoint=False).astype(int)
      data = []
      
      for i, year in enumerate(years):
          reduction_factor = 0.995 ** i
          current_emissions = emissions * np.random.power(0.8) * reduction_factor
          data.append([year, f'Scope {scope}', category, current_emissions])
      
      return pd.DataFrame(data, columns=['year', 'scope', 'category', 'emissions'])

  s1mc = generate_data(n=random.randint(30, 50), scope=1, start_year=2015, end_year=2026, category='Mobile Combustion', emissions=3)
  s1sc = generate_data(n=random.randint(30, 50), scope=1, start_year=2015, end_year=2026, category='Stationary Combustion', emissions=3)
  s2ie = generate_data(n=random.randint(30, 45), scope=2, start_year=2015, end_year=2026, category='Indirect Emissions', emissions=5)
  s3c = [generate_data(n=random.randint(50, 100), scope=3, start_year=2015, end_year=2026, category=f'Category {i+1}') for i in range(15)]

  # Combine all data into one DataFrame
  df = pd.concat([s1mc, s1sc, s2ie] + s3c, ignore_index=True)
  df['emissions'] = df['emissions'] * random.randint(1000, 50000)
  return df

def generate_s3c15_df():
  def generate_financed_data(n, start_year, end_year, financial_type, asset_class, sector, emissions=1):
      years = np.linspace(start_year, end_year, n, endpoint=False).astype(int)
      data = []
      
      for i, year in enumerate(years):
          reduction_factor = 0.995 ** i
          current_emissions = emissions * np.random.power(0.8) * reduction_factor
          data.append([year, financial_type, asset_class, sector, current_emissions])
      
      return pd.DataFrame(data, columns=['year', 'financial_type', 'asset_class', 'sector', 'emissions'])

  # Define asset classes and sectors
  asset_classes = ['business loans', 'commercial real estate', 'mortgages', 'listed equity & bond', 'unlisted equity']
  sectors = ['oil & gas', 'power & utilities', 'real estate & construction', 'agriculture', 'cement', 'coal', 'transportation']

  # Generate data
  data_frames = []
  scaling_factor = 0.7

  n_records = random.randint(40, 180)
  for i, financial_type in enumerate(['lending', 'investing']):
      n_financial = int(n_records * (scaling_factor ** (i+1)))
      
      for j, asset_class in enumerate(asset_classes):
          n_asset = int(n_financial * (scaling_factor ** (j+1)))
          
          for k, sector in enumerate(sectors):
              n_sector = int(n_asset * (scaling_factor ** (k+1)))
              
              if n_sector <1:
                  n_sector = 1 # ensure at least one record
                  
              emissions_factor = random.uniform(0.1, 3)
              dfs = generate_financed_data(n=n_sector, start_year=2015, end_year=2026, financial_type=financial_type, asset_class=asset_class, sector=sector, emissions=emissions_factor)
              data_frames.append(dfs)

  # Combine all data into one DataFrame
  fdf = pd.concat(data_frames, ignore_index=True)
  fdf['emissions'] = fdf['emissions'] * random.randint(1000, 50000)
  return fdf



#-- Charting --#
def make_bar(df, scope:Union[int, None], year=False, percent=False, theme=None):
    if type(scope) == int:
      temp = df[df['scope'] == f'Scope {scope}']
    
      if year:
          total_emissions_per_year = temp.groupby('year')['emissions'].transform('sum')
      
          if percent:
              temp.loc[:, 'emissions'] = 100 * temp['emissions'] / total_emissions_per_year
              
          temp = temp.groupby(['year', 'category']).agg({'emissions': 'sum'}).reset_index()
          try:
              temp['category_n'] = temp['category'].str.extract('(\d+)').astype(int)
              temp = temp.sort_values('category_n', ascending=False)
          except Exception as e:
              print(e)
          
          fig = go.Figure()
          for cat in temp['category'].unique():
              cat_data = temp[temp['category'] == cat]
              fig.add_trace(go.Bar(
                  y=cat_data['year'],
                  x=cat_data['emissions'],
                  orientation='h',
                  name=cat
              ))
          fig.update_layout(
              barmode='stack',
              title=f'Scope {scope} Emissions by Year and Category',
              xaxis_title='Emissions (%)' if percent else 'Emissions',
              yaxis_title='Year',
              yaxis= dict(tickfont = dict(size=12))
          )
          
      else:
          temp = temp.groupby('category').agg({'emissions': 'sum'}).reset_index()
          
          try:
              temp['category_n'] = temp['category'].str.extract('(\d+)').astype(int)
              temp = temp.sort_values('category_n', ascending=False)
          except Exception as e:
              print(e)
              
          if percent:
              total = temp['emissions'].sum()
              temp['emissions'] = 100 * temp['emissions'] / total
          
          fig = go.Figure()
          for cat in temp['category']:
            fig.add_trace(go.Bar(
              x=[temp[temp['category'] == cat]['emissions'].values[0]], 
              y=['Total'],  # Single y-tick lab
              name=cat,
              orientation='h'
          ))
          fig.update_layout(
              title=f'Scope {scope} Emissions by Category',
              barmode='stack',
              xaxis_title='Emissions (%)' if percent else 'Emissions',
              yaxis_title='Category',
              yaxis= dict(tickfont = dict(size=12))
          )
          
    else:
      temp = df
      temp = temp.groupby(['scope']).agg({'emissions': 'sum'}).reset_index()
      total_emissions = temp['emissions'].sum()

      if percent:
        temp['emissions'] = (temp['emissions'] / total_emissions) * 100

      # Create the bar chart
      fig = go.Figure()
      for scope in temp['scope']:
        fig.add_trace(go.Bar(
          x=[temp[temp['scope'] == scope]['emissions'].values[0]], 
          y=['Total'],  # Single y-tick label
          name=scope,
          orientation='h'
      ))
      fig.update_layout(barmode='stack')

    try:
      unique_years = len(temp['year'].unique())
      height = 80 * unique_years
    except:
      height = 500
    fig.update_layout(height=height)
        
    if theme:
        fig.update_layout(template=theme)
        fig.update_layout(colorscale=dict())
    return fig


def make_sunburst(df, hierarchy_list=[], val_col=None, root:str='Placeholder', percentage=False, theme=None):
    df = df.copy()
    df['root'] = root
    
    if percentage:
        total = df[val_col].sum()
        df['percentage'] = round(100 * df[val_col] / total, 2)
        val_col = 'percentage'
    
    fig = px.sunburst(
        df, 
        path=['root'] + hierarchy_list, 
        values=val_col
    )
    if theme:
        fig.update_layout(template=theme)
    return fig


def make_line(df, scope:int, percent=False, theme=None):
    # filter
    temp = df[df['scope'] == f'Scope {scope}']
    total_emissions_per_year = temp.groupby('year')['emissions'].transform('sum')
    
    if percent:
        temp.loc[:, 'emissions'] = 100 * temp['emissions'] / total_emissions_per_year
    
    temp = temp.groupby(['year', 'category']).agg({'emissions': 'sum'}).reset_index()
    try:
        temp['category_n'] = temp['category'].str.extract('(\d+)').astype(int)
        temp = temp.sort_values(['category_n', 'year'], ascending=[True, True])
    except Exception as e:
        print(e)
    
    # Charting
    color_map = {}
    unique_categories = temp['category'].unique()
    colors = ColorDiscrete.gecko_v1 # Add more colors as needed

    for i, cat in enumerate(unique_categories):
        color_map[cat] = colors[i % len(colors)]
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.01, row_heights=[0.8, 0.2])
        
    # Line chart
    for cat in unique_categories:
        cat_data = temp[temp['category'] == cat].sort_values('year')
        fig.add_trace(go.Scatter(
            x=cat_data['year'],
            y=cat_data['emissions'],
            mode='lines',
            stackgroup='one',
            name=cat,
            opacity=0.2,
            legendgroup=cat,
            line=dict(color=color_map[cat])
        ), row=1, col=1)
        
    # Bar chart for YoY change
    temp['yoy_change'] = temp.groupby('category')['emissions'].pct_change() * 100  # Calculate YoY change
    for cat in unique_categories:
        cat_data = temp[temp['category'] == cat].sort_values('year')
        fig.add_trace(go.Bar(
            x=cat_data['year'],
            y=cat_data['yoy_change'],
            name=cat,
            legendgroup=cat,
            showlegend=False,
            marker=dict(color=color_map[cat])
        ), row=2, col=1)
        
    fig.update_layout(
        title=f'Scope {scope} Emissions by Year and Category',
        hovermode="x",
        height=600,
        xaxis_title='Year',
        yaxis_title='Emissions (%)' if percent else 'Emissions'
    )
    if theme:
        fig.update_layout(template=theme)
    return fig


def make_sankey(df, title='Emissions Flow by Scope, and Category', height=800, width=1000, theme=None):
    # Create unique lists for each hierarchy level
    years = df['year'].astype(str).unique().tolist()
    scopes = df['scope'].unique().tolist()
    categories = df['category'].unique().tolist()
    
    # Combine all labels and create an index mapping
    all_labels = years + scopes + categories
    label_idx = {label: i for i, label in enumerate(all_labels)}
    
    # Initialize source, target, and value lists for Sankey links
    sources = []
    targets = []
    values = []
    
    # Populate source, target, and value lists
    for _, row in df.iterrows():
        year = str(row['year'])
        scope = row['scope']
        category = row['category']
        emissions = row['emissions']
        
        sources.append(label_idx[year])
        targets.append(label_idx[scope])
        values.append(emissions)
        
        sources.append(label_idx[scope])
        targets.append(label_idx[category])
        values.append(emissions)
    
    # Create the Sankey diagram
    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=all_labels
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values
        )
    ))
    fig.update_layout(title_text=title, font_size=10, height=height, width=width)
    if theme:
        fig.update_layout(template=theme)
    return fig


#-- Charting 2 --#
def make_bar_2(df, financial_type=False, year=False, percent=False, theme=None):
    temp = df[df['financial_type'] == financial_type]
    
    if year:
        total_emissions_per_year = temp.groupby('year')['emissions'].transform('sum')
    
        if percent:
            temp.loc[:, 'emissions'] = 100 * temp['emissions'] / total_emissions_per_year
            
        temp = temp.groupby(['year', 'sector']).agg({'emissions': 'sum'}).reset_index()
        
        fig = go.Figure()
        for sector in temp['sector'].unique():
            sector_data = temp[temp['sector'] == sector]
            fig.add_trace(go.Bar(
                y=sector_data['year'],
                x=sector_data['emissions'],
                orientation='h',
                name=sector
            ))
        fig.update_layout(
            barmode='stack',
            title=f'{financial_type} Emissions by Year and Sector',
            xaxis_title='Emissions (%)' if percent else 'Emissions',
            yaxis_title='Year',
            height=80 * len(temp['year'].unique()),
            yaxis=dict(tickfont=dict(size=12))
        )
    else:
        temp = temp.groupby('sector').agg({'emissions': 'sum'}).reset_index()
        
        if percent:
            total = temp['emissions'].sum()
            temp['emissions'] = 100 * temp['emissions'] / total
        
        fig = go.Figure(data=[
            go.Bar(y=temp['sector'], x=temp['emissions'], orientation='h')
        ])
        
        fig.update_layout(
            title=f'{financial_type} Emissions by Sector',
            xaxis_title='Emissions (%)' if percent else 'Emissions',
            yaxis_title='Sector',
            yaxis=dict(tickfont=dict(size=12))
        )
    if theme:
        fig.update_layout(template=theme)
    return fig


def make_sunburst_2(df, hierarchy_list=[], val_col=None, root:str='Placeholder', percentage=False, theme=None):
    df = df.copy()
    df['root'] = root
    
    if percentage:
        total = df[val_col].sum()
        df['percentage'] = round(100 * df[val_col] / total, 2)
        val_col = 'percentage'
    
    fig = px.sunburst(
        df, 
        path=['root'] + hierarchy_list, 
        values=val_col
    )
    if theme:
        fig.update_layout(template=theme)
    return fig


def make_line_2(df, financial_type:str, category='sector', percent=False, theme=None):
    temp = df[df['financial_type'] == financial_type]
    total_emissions_per_year = temp.groupby('year')['emissions'].transform('sum')
    
    if percent:
        temp.loc[:, 'emissions'] = 100 * temp['emissions'] / total_emissions_per_year
    
    temp = temp.groupby(['year', category]).agg({'emissions': 'sum'}).reset_index()
    
    # Charting
    color_map = {}
    unique_categories = temp[category].unique()
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']  # Add more colors as needed

    for i, cat in enumerate(unique_categories):
        color_map[cat] = colors[i % len(colors)]
    
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.01)    
    for cat in unique_categories:
        cat_data = temp[temp[category] == cat].sort_values('year')
        fig.add_trace(go.Scatter(
            x=cat_data['year'],
            y=cat_data['emissions'],
            mode='lines',
            stackgroup='one',
            opacity=0.2,
            name=cat,
            legendgroup=cat,
            line=dict(color=color_map[cat])
        ))
        
    temp['yoy_change'] = temp.groupby(category)['emissions'].pct_change() * 100  # Calculate YoY change
    for cat in unique_categories:
        cat_data = temp[temp[category] == cat].sort_values('year')
        fig.add_trace(go.Bar(
            x=cat_data['year'],
            y=cat_data['yoy_change'],
            name=cat,
            legendgroup=cat,
            showlegend=False,
            marker=dict(color=color_map[cat])
        ), row=2, col=1)
        
    fig.update_layout(
        title=f'Emissions by Year and Sector',
        xaxis_title='Year',
        yaxis_title='Emissions (%)' if percent else 'Emissions',
        hovermode="x",
    )
    if theme:
        fig.update_layout(template=theme)
    return fig


def make_sankey_2(df, height=800, width=1000, theme=None):
    # Create unique lists for each hierarchy level
    financial_types = df['financial_type'].unique().tolist()
    asset_classes = df['asset_class'].unique().tolist()
    sectors = df['sector'].unique().tolist()
    
    # Combine all labels and create an index mapping
    all_labels = financial_types + asset_classes + sectors
    label_idx = {label: i for i, label in enumerate(all_labels)}
    
    # Initialize source, target, and value lists for Sankey links
    sources = []
    targets = []
    values = []
    
    # Populate source, target, and value lists
    for _, row in df.iterrows():
        financial_type = row['financial_type']
        asset_class = row['asset_class']
        sector = row['sector']
        emissions = row['emissions']
        
        sources.append(label_idx[financial_type])
        targets.append(label_idx[asset_class])
        values.append(emissions)
        
        sources.append(label_idx[asset_class])
        targets.append(label_idx[sector])
        values.append(emissions)
    
    # Create the Sankey diagram
    fig = go.Figure(go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=all_labels
        ),
        link=dict(
            source=sources,
            target=targets,
            value=values
        )
    ))
    
    fig.update_layout(title_text='Financial Emissions Flow', font_size=10, height=height, width=width)
    if theme:
        fig.update_layout(template=theme)
    return fig