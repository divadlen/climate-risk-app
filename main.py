import streamlit as st
import hydralit as hy
from PIL import Image

from app_config import run_app_config
from utils.utility import get_deep_size, reconcile_theme_config

#Only need to set these here as we are add controls outside of Hydralit, to customise a run Hydralit!
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """

icon = Image.open("./resources/GreenLogo_ico.ico")
st.set_page_config(
  page_title="Gecko Technologies Emission Calculation Service",
  page_icon=icon,
  layout="wide",
  initial_sidebar_state="collapsed",
  menu_items={
    'Get Help': 'https://www.geckointel.com',
    'Report a bug': "https://geckointel.com/contact-us",
    'About': "# Gecko Technologies. GHG Emission Calculation Service",
  }
) # 

sidebar_md = """
## Resources
- [Account verification](https://geckointel.com/contact-us)
- [Submit a bug report](https://geckointel.com/contact-us)
- [Privacy policy](https://neldivad.github.io/climate-risk-app/resources/mds/privacy_policy.html)
- [Terms and condition](https://neldivad.github.io/climate-risk-app/resources/mds/terms.html)

""" #

#---Start app---#
def run_app():
  # Check if user is authenticated
  from apps.auth import AuthApp
  if not st.session_state.get("authenticated"):
    # Run authentication app
    AuthApp()
    return
  
  user_level = st.session_state.get("user_level", 1)

  #---Load states and configurations---#
  run_app_config()
  # st.markdown(hide_st_style, unsafe_allow_html=True)

  #---Start Hydra instance---#
  # hydra_theme = None # init hydra theme
  # navbar_theme_light = {
  #   'txc_inactive': '#FFFFFF',
  #   'txc_active':'grey',
  #   'menu_background':'#05F1E3',
  #   'option_active':'#004457'
  # }
  navbar_theme_dark = {
    'txc_inactive': '#ecc0d1',
    'txc_active': 'black',  
    'menu_background': '#39393a',  
    'option_active': '#C4CEBC' 
  }

  col1, col2, col3 = st.columns([1,2,1])
  with col2:
    pass
  st.image("./resources/imgs/banner.png", use_column_width=True, width=None)

  with st.sidebar:
    if user_level < 2:
      st.info(f"Welcome **{st.session_state.username}**! Your account is not yet verified internally. Please enjoy the demo pages.")

    st.info(sidebar_md) #

    with st.expander('App version'):
      st.write('0.6.2')

    st.markdown('Copyright © 2023 Gecko Technologies')

    # # --- DEBUGGING PURPOSES ---#
    # with st.expander('Show states'): 
    #   size_dict = {}
    #   for key in st.session_state.keys():
    #     size = get_deep_size(st.session_state[key])
    #     size_dict[key] = size

    #   # Sort by size
    #   sorted_items = sorted(size_dict.items(), key=lambda x: x[1], reverse=True)
    #   for key, size in sorted_items:
    #     st.write(f"{key}: {size/1000} kb")

    # for key in st.session_state.keys():
    #   with st.expander(f'Inspect {key}'):
    #     st.write(st.session_state[key])


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
  @app.addapp(is_home=True, title='Home')
  def homeApp():
    from apps.home_page import homePage
    homePage()

  @app.addapp(title='User Manual')
  def usermanualApp():
    from apps.usermanual import main
    main()

  @app.addapp(title='Logout')
  def logout_button():
    from apps.logout import logoutPage
    logoutPage()

  @app.addapp(title='Scope 1: Direct Emissions')
  def s1deApp():
    from apps.s1de_page import s1de_Page
    s1de_Page()

  #--- Level 1 apps ---#
  if user_level < 2: 
    @app.addapp(title='Sample Dashboard')
    def sampleDashApp():
      from apps.sample_dash import dash_Page_v1
      dash_Page_v1()

  #--- Level 2 apps ---#
  if user_level >= 2:
    @app.addapp(title='Scope 2: Indirect Emissions')
    def s2ieApp():
      from apps.s2ie_page import s2ie_Page
      s2ie_Page()

    @app.addapp(title='Scope 3: Value Chain')
    def s3vcApp():
      from apps.s3vc_page import s3vc_Page
      s3vc_Page()

    @app.addapp(title='Overall Dashboard')
    def main_dash():
      from apps.main_dash import main_dash_Page
      main_dash_Page()

    @app.addapp(title='Forms Builder')
    def formsApp():
      from apps.easy_forms import easy_forms_page
      easy_forms_page()


  def build_navigation(user_level=1):
    complex_nav = {}
    
    # Always add Home first
    complex_nav["Home"] = ['Home']
    
    # Conditionally add other navigation items based on user level
    if user_level < 2: 
      complex_nav['Sample Dashboard'] = ['Sample Dashboard']
      complex_nav["Emissions Calculator"] = ['Scope 1: Direct Emissions']

    if user_level >= 2:
      complex_nav["Emissions Calculator"] = ['Scope 1: Direct Emissions', 'Scope 2: Indirect Emissions', 'Scope 3: Value Chain']
      complex_nav["Graphics"] = ["Overall Dashboard"]
      complex_nav["Forms Builder"] = ['Forms Builder']

    # if user_level >=10:
    #   complex_nav["Emissions Calculator"] = ['Scope 1: Direct Emissions', 'Scope 2: Indirect Emissions', 'Scope 3: Value Chain']
    #   complex_nav["Forms Builder"] = ['Forms Builder']
    
    # Always add Logout last
    complex_nav["User Manual"] = ['User Manual']
    complex_nav["logout"] = ['Logout'] # key must be 'logout' idk why 
    return complex_nav
  

  complex_nav = build_navigation(user_level)
  app.run(complex_nav=complex_nav)

if __name__ == '__main__':
  run_app()
