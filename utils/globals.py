LOCATION_ABBRV = {
  'usa': 'United States of America',
  'united states': 'united of america',
  'uk': 'United Kingdom',
  'korea': 'south korea',
  'my': 'malaysia',
  'melaka': 'malacca',
  'pineng': 'Penang',
}

COLUMN_SORT_ORDER = [
  # Universal
  'uuid', 'date', 'description',

  # location
  'country_code', 'country', 
  'address', 'lat', 'lon',  
  'branch', 'department', 'street_address_1', 'street_address_2', 'city', 'state', 'postcode',

  # Company descriptions
  'financial_type', 'company_name', 'sector', 'asset_class', 'is_listed', 'owned',

  # vehicle descriptions
  'vehicle_type',

  # fuel descriptions
  'fuel_state', 'fuel_type', 'fuel_unit', 'fuel_consumption',  'heating_value', 'fuel_spend',

  # energy descriptions
  'energy_provider', 'energy_type', 'energy_unit', 'energy_consumption', 'energy_spend',

  # distance descriptions
  'distance_traveled', 'distance', 'distance_unit', 'distance_emission_factor', 

  # building descriptions
  'building_energy_use', 'building_emission_factor', 'year_constructed',

  # finances
  'currency', 'outstanding_amount', 'enterprise_value', 'total_equity', 'total_debt', 'total_government_debt', 'PPP_adj_GDP', 'property_value', 'value_at_origin', 
  
  # emissions
  'attribution_share', 'reported_emissions', 'project_emissions', 'emissions_removed', 'production_emissions', 'consumption_emissions', 'emission_estimation_description',
]


#--- USED BY S3VC --#
# Mapping sectors to applicable categories by index
SECTOR_TO_CATEGORY_IDX = {
  'Energy': [1, 4, 9, 11],
  'Industrial': [1, 3, 4, 5, 6, 7, 9, 10, 11],
  'Construction': [1, 3, 4, 5, 6, 7, 9, 10, 11],
  'Telecommunication': [5, 6, 7, 9],
  'Transportation': [3, 5, 6, 7],
  'Automobile': [1, 2, 3, 4, 5, 6, 7, 9, 10, 11, 12],
  'Real Estate': [5, 6, 7, 13],
  'Banking and Finance': [6, 7, 15],
}

IDX_TO_CATEGORY_NAME = {
  1: 'Category 1 : Purchased goods & services',
  2: 'Category 2 : Capital goods',
  3: 'Category 3 : Fuel- & energy-related activities (excluded in Scope 1 & 2)',
  4: 'Category 4 : Upstream transportation & distribution',
  5: 'Category 5 : Waste generated in operations',
  6: 'Category 6 : Business and air travel',
  7: 'Category 7 : Employee commuting',
  8: 'Category 8 : Upstream leased assets',
  9: 'Category 9 : Downstream distribution of sold products',
  10: 'Category 10 : Processing of sold products',
  11: 'Category 11 : Use of sold products',
  12: 'Category 12 : End-of-life treatment of sold products',
  13: 'Category 13 : Downstream leased assets',
  14: 'Category 14 : Franchises',
  15: 'Category 15 : Investments',
}


class ColorDiscrete:
  tableau = ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F', '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC']
  colorbrewer = ['#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00', '#FFFF33', '#A65628', '#F781BF', '#999999']
  google = ['#F44336', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#03A9F4', '#00BCD4', '#009688', '#4CAF50', '#8BC34A', '#CDDC39', '#FFEB3B', '#FFC107', '#FF9800', '#FF5722'] 
  d3 = ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2', '#7F7F7F', '#BCBD22', '#17BECF']
  ilo = ['#0094D2', '#E6007E', '#F47D30', '#212121', '#F0F0F0'] 
  okabe_ito = ['#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7', '#000000', '#F0E442', '#D55E00']
  economist = ['#E3120B', '#4C4C4C', '#6D6E71', '#8E8D8F', '#AAAAB2', '#B6B4B5', '#C1BDBA', '#C9C5B6', '#D2CDC2', '#D9D5CD']
  mckinsey = ['#4A90E2', '#F5A623', '#7ED321', '#D0021B', '#417505', '#BD10E0', '#50E3C2', '#F8E71C', '#F78B00', '#000000']
  deloitte = ['#00A5DC', '#49276D', '#8A0000', '#007681', '#9A7227', '#84BE41', '#7C7474', '#D12F2F', '#F8931D', '#000000']
  nhk_jp = ['#E60012', '#579D1C', '#4B1E66', '#1B255E', '#1E4896', '#00A0E9', '#009944', '#6CBB5A', '#D1C000', '#E39800']
  abc_aus = ['#E14100', '#008C45', '#00AEEF', '#7600A1', '#80C342', '#005BB5', '#93C6E0', '#F15A29', '#DF7C00', '#00B5E2']
  gecko_v1 = gecko_v1 = ['#D4B7CB',"#004457","#cc5a29", '#FFEB3B', "#53c6bb","#753c9c","#56e199","#857ca0","#edc49d", '#B97C68', "#6D3837", '#E3120B']