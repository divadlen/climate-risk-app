import streamlit as st
import hydralit as hy

from app_config import run_app_config
from utils.utility import get_deep_size, reconcile_theme_config


st.set_page_config(
  page_title="Gecko Technologies Emission Calculation Service",
  page_icon="🧊",
  layout="wide",
  initial_sidebar_state="expanded",
  menu_items={
    'Get Help': 'https://www.geckointel.com',
    'Report a bug': "https://geckointel.com/contact-us",
    'About': "# Gecko Technologies. GHG Emission Calculation Service",
  }
)

#---Start app---#
def run_app():
  # Check if user is authenticated
  from apps.auth import AuthApp
  if not st.session_state.get("authenticated"):
    # Run authentication app
    AuthApp()
    return

  #---Load states and configurations---#
  run_app_config()

  #---Start Hydra instance---#
  hydra_theme = None # init hydra theme
  navbar_theme_light = {
    'txc_inactive': '#FFFFFF',
    'txc_active':'grey',
    'menu_background':'#05F1E3',
    'option_active':'#004457'
  }
  navbar_theme_dark = {
    'txc_inactive': '#ecc0d1',
    'txc_active': 'black',  
    'menu_background': '#39393a',  
    'option_active': '#C4CEBC' 
  }

  col1, col2, col3 = st.columns([1,2,1])
  with col2:
    st.image("./resources/G1-long.png", use_column_width=True, width=None)




  with st.sidebar:
    qwe = st.text_input('QWE') # 

    with st.form(key='theme_form'):
      st.session_state['theme_choice'] = st.radio('Choose theme', ['Dark', 'Light'], horizontal=True)  
      submit_button = st.form_submit_button('Double click to apply theme')

    if submit_button:
      reconcile_theme_config()  # Apply the theme

    with st.expander('Show states'):
      size_dict = {}
      for key in st.session_state.keys():
        size = get_deep_size(st.session_state[key])
        size_dict[key] = size

      # Sort by size
      sorted_items = sorted(size_dict.items(), key=lambda x: x[1], reverse=True)
      for key, size in sorted_items:
        st.write(f"{key}: {size/1000} kb")


  app = hy.HydraApp(
    hide_streamlit_markers=False,
    use_navbar=True, 
    navbar_sticky=False,
    navbar_animation=True,
    navbar_theme=navbar_theme_dark,
  )

  #specify a custom loading app for a custom transition between apps, this includes a nice custom spinner
  from apps._loading import MyLoadingApp
  app.add_loader_app(MyLoadingApp(delay=0))

  #---Add apps from folder---#
  @app.addapp(is_home=True)
  def my_home(title='home'):
    hy.info('Hello from Home!')

  # @app.addapp(title='from app folderr')
  # def app4():
  #   from apps.home2 import main
  #   main()

  @app.addapp(title='Logout')
  def logout_button():
    from apps.logout import logoutPage
    logoutPage()

  @app.addapp(title='Scope 1: Direct Emissions')
  def s1deApp():
    from apps.s1de_page import s1de_Page
    s1de_Page()

  @app.addapp(title='Scope 2: Indirect Emissions')
  def s2ieApp():
    from apps.s2ie_page import s2ie_Page_v2
    s2ie_Page_v2()

  @app.addapp(title='Scope 3: Value Chain')
  def s3vcApp():
    from apps.s3vc_page import s3vc_Page
    s3vc_Page()

  @app.addapp(title='Overall Dashboard')
  def main_dash():
    from apps.main_dash import main_dash_Page
    main_dash_Page()


    
  #---Optional, if you want to nest navigations---#
  complex_nav = {
    "Home": ['home'],
    "Emissions Calculator": ['Scope 1: Direct Emissions', 'Scope 2: Indirect Emissions', 'Scope 3: Value Chain'],
    # "heat": ['Risk Heatmap'], 
    "Graphics": ["Overall Dashboard"],
    "logout": ['Logout'],
  }

  app.run(complex_nav=complex_nav)

if __name__ == '__main__':
  run_app()