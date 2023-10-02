import streamlit as st
from st_aggrid import AgGrid, JsCode, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder

import numpy as np
import pandas as pd
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

from utils.s3vc_Misc.s3_models import *
from utils.s3vc_Misc.s3_cache import S3_Lookup_Cache
from utils.s3vc_Misc.s3_calculators import S3_Calculator
from utils.s3vc_Misc.s3_creators import *
from utils.charting import initialize_plotly_themes 


def s3vc_Page(): 
  # inits already done in 'app_config()'
  pass