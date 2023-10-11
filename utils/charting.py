import streamlit as st

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

import numpy as np
import pandas as pd
import re

from typing import Union
from typing import Optional
from utils.globals import ColorDiscrete

#---
# chart config
#---
def watermark_settings():
    return st.session_state.watermark_settings

def legend_settings_dark(orientation='v', max_per_row=7):
    settings = dict(
        x=0,
        y=1,
        title_text='',
        font=dict(
            family="Times New Roman",
            size=12,
            color="white"
        ),
        bgcolor='rgba(0,75,154,0.3)',
        bordercolor="ivory",
        borderwidth=1,
        orientation=orientation,
    )
    return settings


#---
# Theme config
#---
def initialize_plotly_themes():
    common_layout = {
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'xaxis': {'gridcolor': 'grey'},
        'yaxis': {'gridcolor': 'grey'},
    }

    for name in dir(ColorDiscrete):
        if not name.startswith("__"):  # Skip built-in attributes
            color = getattr(ColorDiscrete, name)
            try:
                pio.templates[name] = go.layout.Template(
                    layout={
                        **common_layout,
                        'colorway': color
                    }
                )
            except Exception as e:
                print(f"Failed to set colorway for {name}: {e}")

#---
# Helper
#---
def sort_str_column_numeric(df, column_name, ascending=True):
    """Sorts a DataFrame based on a string column that contains numeric values."""
    df['SortKey'] = df[column_name].apply(lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
    df.sort_values('SortKey', inplace=True, ascending=ascending)
    df.drop('SortKey', axis=1, inplace=True)
    return df


#---
# Charting
#---
def make_bar_chart(
    df: pd.DataFrame, 
    scope_col: Optional[str] = 'scope', 
    year_col: Optional[str] = 'date', 
    category_col: Optional[str] = 'category', 
    value_col: str = 'financed_emissions', 
    aggregation: str = 'sum', 
    percent: bool = False, 
    theme: Optional[str] = None, 
    title: Optional[str] = 'Bar plot', 
    height: Optional[int] = None, 
    width: Optional[int] = None, 
    watermark=True,
    legend: bool = True,
    legend_dark: bool= False,
    horizontal_legend=False,
    legend_sort_numeric=False,
    auto_adjust_height=False
):
    # Initialize figure
    fig = go.Figure()
    
    # Group and aggregate data
    group_cols = []
    if year_col:
        group_cols.append(year_col)
    if category_col:
        group_cols.append(category_col)
    if group_cols:
        grouped_df = df.groupby(group_cols).agg({value_col: aggregation}).reset_index()
    else:
        grouped_df = df.copy()
    
    # Handle datetime and convert to year if needed
    if year_col and pd.api.types.is_datetime64_any_dtype(df[year_col]):
        grouped_df[year_col] = grouped_df[year_col].dt.year
    
    # Handle percentage calculations
    if percent:
        total_value = grouped_df[value_col].sum()
        grouped_df[value_col] = 100 * grouped_df[value_col] / total_value

    # String columns get sorted weirdly in legend
    if legend_sort_numeric:
        grouped_df = sort_str_column_numeric(grouped_df, category_col, ascending=False)
    
    # Create the plot
    for cat in grouped_df[category_col].unique() if category_col else [None]:
        cat_data = grouped_df[grouped_df[category_col] == cat] if category_col else grouped_df
        
        fig.add_trace(go.Bar(
            y=cat_data[year_col] if year_col else [cat],
            x=cat_data[value_col],
            name=str(cat) if cat else 'Total',
            text=cat_data[value_col].apply(lambda x: f"<b>{cat if cat else 'Total'}</b><br><b>{x:.2f}</b>"),
            textposition='inside',
            orientation='h',
        ))
    
    fig.update_layout(
        title=title,
        title_x = 0.5,
        barmode='stack',
        height=height,
        width=width,
        showlegend=legend,
    )

    # Update datetime axis format
    unique_dates = grouped_df[year_col].nunique() if year_col else 0
    if unique_dates == 1:
        fig.update_yaxes(tickvals=[grouped_df[year_col].iloc[0]], ticktext=['Total'])
    elif unique_dates > 1:
        fig.update_yaxes(tickformat="%d-%m-%Y")

    if watermark:
        fig.update_layout(images= watermark_settings())
    
    if theme:
        fig.update_layout(template=theme)

    if legend_dark:
        fig.update_layout(legend = legend_settings_dark())
    
    if horizontal_legend:
        fig.update_layout(title_y=1, legend=dict(orientation='h', x=0.5, y=1, xanchor='center', yanchor='bottom'))

    if auto_adjust_height:
        height = 300
        nuniq = len( grouped_df[category_col].unique() )
        height += nuniq * 30
        fig.update_layout(height=height)
  
    return fig


def make_donut_chart(
    df, 
    group_col='category', 
    value_col='financed_emissions',
    hole=0.3, 
    percent=False, 
    title='', 
    center_text=None, 
    height=None, 
    width=None, 
    theme=None, 
    watermark=True,
    legend=True,
    legend_dark=False,
    horizontal_legend=False
):
    # Group the data
    grouped_data = df.groupby(group_col).agg({value_col: 'sum'}).reset_index()
    sorted_labels = df[group_col].unique()
    grouped_data.set_index(group_col, inplace=True)
    grouped_data = grouped_data.loc[sorted_labels].reset_index()
    
    total_emissions = grouped_data[value_col].sum()
    grouped_data['percent'] = (grouped_data[value_col] / total_emissions) * 100

    if percent:
        grouped_data.loc[:, value_col] = 100 * grouped_data[value_col] / total_emissions
    
    # Create the figure
    fig = go.Figure(data=[go.Pie(
        labels=grouped_data[group_col],
        values=grouped_data[value_col],
        hole=hole,

        customdata=grouped_data['percent'],
        textinfo='label+percent',
        textfont_size=15,
        insidetextorientation='horizontal',
        texttemplate="<br>%{value:.2f}<br>%{customdata:.2f}%",
        sort=True,
        direction="clockwise",
        hovertemplate="%{label} = %{value} (%{percent})",
    )])
    
    # Update layout
    fig.update_layout(
        title=title,
        title_x=0.5,
        title_font_size=15,
        height=height,
        width=width,
        annotations=[dict(text=center_text, x=0.5, y=0.5, font_size=15, showarrow=False)], 
    )
    fig.update_traces()
    if theme:
        fig.update_layout(template=theme)
    if watermark:
        fig.update_layout(images=watermark_settings())
    if not legend:
        fig.update_layout(showlegend=False)
    if legend_dark:
        fig.update_layout(legend = legend_settings_dark())
    if horizontal_legend:
        fig.update_layout(title_y=1, legend=dict(orientation='h', x=0.5, y=-0.05, xanchor='center', yanchor='top'))

    return fig


def make_grouped_line_chart(
    df, 
    group_col,
    value_col,
    date_col=None,
    percent=False, 
    resample_freq=None,
    stacked=True,
    show_delta=True,
    title='',
    theme=None, 
    watermark=True, 
    legend=True, 
    legend_dark=False, 
    height=None, 
    width=None
):
    # Filter and aggregate data
    temp = df.copy()
    
    # Resampling
    if resample_freq and pd.api.types.is_datetime64_any_dtype(temp[date_col]):
        temp.set_index(date_col, inplace=True)
        temp = temp.groupby([group_col, pd.Grouper(freq=resample_freq)]).sum().reset_index()

    total_emissions_by_time = temp.groupby(date_col)[ value_col ].transform('sum')
    if percent:
        temp.loc[:, value_col] = 100 * temp[value_col] / total_emissions_by_time
    temp = temp.groupby([date_col, group_col]).agg({value_col: 'sum'}).reset_index()

    try:
        temp['category_n'] = temp[group_col].str.extract('(\d+)').astype(int)
        temp = temp.sort_values(['category_n', date_col], ascending=[True, True])
    except Exception as e:
        print(e)

    # Initialize color map
    unique_categories = temp[group_col].unique()
    if theme and theme in pio.templates:
        colors = pio.templates[theme].layout.colorway  # Retrieve color sequence from theme
    else:
        colors = pio.templates['streamlit'].layout.colorway  # Fallback to default colors
    color_map = {cat: colors[i % len(colors)] for i, cat in enumerate(unique_categories)}

    unique_dates = temp[date_col].nunique() if date_col else 0
    if unique_dates < 2:
        fig = go.Figure()
        for cat in unique_categories:
            cat_data = temp[temp[group_col] == cat]
            fig.add_trace(go.Bar(
                x=[cat],
                y=cat_data[value_col],
                name=cat,
                marker=dict(color=color_map[cat])
            ))
            fig.update_layout(barmode='group')
    else:
      if show_delta:
          fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.01, row_heights=[0.7, 0.3])
      else:
          fig = make_subplots(rows=1, cols=1)

      # Line chart
      for cat in unique_categories:
          cat_data = temp[temp[group_col] == cat].sort_values(date_col)
          fig.add_trace(go.Scatter(
              x=cat_data[date_col],
              y=cat_data[value_col],
              mode='lines',
              stackgroup='one' if stacked else None,
              name=cat,
              opacity=0.2 if stacked else None,
              legendgroup=cat,
              line=dict(
                  color=color_map[cat], 
                  width=4 if not stacked else None
              )
          ), row=1, col=1)
      
      if show_delta:
          # Bar chart for YoY / MoM / QoQ change
          temp['interval_change'] = temp.groupby(group_col)[value_col].pct_change() * 100  # Calculate resampled interval change
          for cat in unique_categories:
              cat_data = temp[temp[group_col] == cat].sort_values(date_col)
              fig.add_trace(go.Bar(
                  x=cat_data[date_col],
                  y=cat_data['interval_change'],
                  name=cat,
                  legendgroup=cat,
                  showlegend=False,
                  marker=dict(color=color_map[cat])
              ), row=2, col=1)
        
    # Update layout
    fig.update_layout(
        title=title,
        hovermode="x",
        height=height,
        width=width,
        xaxis_title='',
        yaxis_title='Emissions (%)' if percent else 'Emissions'
    )
    
    if theme:
        fig.update_layout(template=theme)
    if watermark:
        fig.update_layout(images=watermark_settings())
    if not legend:
        fig.update_layout(showlegend=False)
    if legend_dark:
        orientation = 'h'  # or 'v' for vertical
        max_per_row = 7
        fig.update_layout(legend=legend_settings_dark(orientation, max_per_row))

    return fig


def make_sankey_chart(
    df, 
    hierarchy_col_list: list = ['financial_type', 'asset_class', 'sector'],
    value_col: str = 'financed_emissions',
    title='',
    height=800, 
    width=1000, 
    theme=None, 
    watermark=True,
    legend=True,
    legend_dark=False
):
    # Create unique lists for each hierarchy level and combine them
    all_labels = []
    for col in hierarchy_col_list:
        unique_labels = df[col].unique().tolist()
        all_labels += unique_labels

    # Create an index mapping for all labels
    label_idx = {label: i for i, label in enumerate(all_labels)}
    
    # Initialize source, target, and value lists for Sankey links
    sources = []
    targets = []
    values = []
    
    # Populate source, target, and value lists
    for _, row in df.iterrows():
        for i in range(len(hierarchy_col_list) - 1):
            source_col = hierarchy_col_list[i]
            target_col = hierarchy_col_list[i + 1]
            value = row[value_col]
            
            sources.append(label_idx[row[source_col]])
            targets.append(label_idx[row[target_col]])
            values.append(value)
    
    # Create the Sankey diagram
    fig = go.Figure(go.Sankey(
        node=dict(
            pad=20,
            thickness=20,
            line=dict(color='black', width=1),
            label=all_labels
        ),
        link=dict(
            # arrowlen=15,
            source=sources,
            target=targets,
            value=values,
            color='lightgrey'
        )
    ))
    
    fig.update_layout(title_text=title, title_x=0.5, font_size=10, height=height, width=width)
    if theme:
        fig.update_layout(template=theme)
    if watermark:
        fig.update_layout(images=watermark_settings())
    if not legend:
        fig.update_layout(showlegend=False)
    if legend_dark:
        fig.update_layout(legend = legend_settings_dark())
    
    return fig


def make_sunburst_chart(
    df, 
    hierarchy_list: list = [], 
    value_col: str = None, 
    root: str = 'Placeholder', 
    percentage: bool = False, 
    theme: str = None,
    watermark = True,
):
    # Create a copy of the DataFrame to avoid modifying the original
    df = df.copy()
    
    # Add a root node to the DataFrame
    df['root'] = root
    
    # If percentage is True, calculate the percentage values
    if percentage:
        total = df[value_col].sum()
        df['percentage'] = round(100 * df[value_col] / total, 2)
        value_col = 'percentage'
    
    # Create the sunburst chart
    fig = px.sunburst(
        df, 
        path=['root'] + hierarchy_list,  # Add the root to the hierarchy list
        values=value_col
    )
    
    # Apply the theme if specified
    if theme:
        fig.update_layout(template=theme)
    if watermark:
        fig.update_layout(images=watermark_settings())
    
    return fig