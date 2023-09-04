import streamlit as st
import pandas as pd
import numpy as np
from sklearn.neighbors import KDTree

from supabase import create_client
from .utility import supabase_query

supabase_url= st.secrets['supabase_url']
supabase_anon_key= st.secrets['supabase_anon_key']
supabase = create_client(supabase_url, supabase_anon_key)


class GeoLocator:
    def __init__(self, df=None): 
        if df is None:
            TABLE = 'locations_states'
            data = pd.DataFrame(supabase_query(TABLE, supabase_url, supabase_anon_key))
            self.df = data[ data['lat'].notna() & data['lon'].notna() ]
        else:
            self.df = df[ df['lat'].notna() & df['lon'].notna() ]
        self.kdtree = KDTree(self.df[['lat', 'lon']])
        
    def get_fields_from_latlon(self, lat, lon):
        distance, indices = self.kdtree.query( np.array([[lat, lon]]), k=1 )
        nearest_index = indices[0][0]
        record = self.df.iloc[nearest_index].to_dict()
        return record