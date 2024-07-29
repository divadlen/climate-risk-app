import streamlit as st
import pandas as pd
import numpy as np
from sklearn.neighbors import KDTree

from supabase import create_client
from utils.utility import supabase_query

""" 
Usage: 
  Gets back row data of state and country that matched with *approximated* lat lon.
  Initialize Geolocator before using it. You will build a map from 5k rows from database (query 2s, build 1s) and store it into memory. 
  This means caching is no longer necessary.

gl = Geolocator()
location_row = gl.get_fields_from_latlon(1, 3)
"""

class GeoLocator:
    def __init__(self, df=None): 
        if df is None:
            print('Building KDTree...')
            try:
                supabase_url= st.secrets['supabase_url']
                supabase_anon_key= st.secrets['supabase_anon_key']
                supabase = create_client(supabase_url, supabase_anon_key)

                TABLE = 'locations_states'
                data = pd.DataFrame(supabase_query(TABLE, supabase_url, supabase_anon_key))
                self.df = data[ data['lat'].notna() & data['lon'].notna() ]
            except Exception as e:
                raise e
            
        else:
            self.df = df[ df['lat'].notna() & df['lon'].notna() ]
        self.kdtree = KDTree(self.df[['lat', 'lon']])
        
    def get_fields_from_latlon(self, lat, lon):
        distance, indices = self.kdtree.query( np.array([[lat, lon]]), k=1 )
        nearest_index = indices[0][0]
        record = self.df.iloc[nearest_index].to_dict()
        return record