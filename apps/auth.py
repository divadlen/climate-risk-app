import streamlit as st
import streamlit_authenticator as stauth

import bcrypt
import re

from supabase import create_client
import pandas as pd


supabase_url = st.secrets['supabase_url']
supabase_anon_key = st.secrets['supabase_anon_key']
supabase = create_client(supabase_url, supabase_anon_key)

# Load the configuration file
def AuthApp():
  col1, col2, col3 = st.columns([1,2,1])
  with col2:
    st.image("./resources/G1-long.png", use_column_width=True, width=None)

  tab1, tab2, tab3 = st.tabs(["Login", "Sign Up", "Forgot Password"])

  with tab1:
    with st.form(key='Username'):
      username = st.text_input('Username/Email')
      password = st.text_input('Password', type='password')
    
      if st.form_submit_button('Login'):
        with st.spinner():
          user = check_credentials(username, password)
        
          if user:
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.experimental_rerun()
            return
          else:
            st.error('Username/password is incorrect')
    
    

  with tab2:
    with st.form(key='Sign up'):
      email_address = st.text_input('Email Address')
      username = st.text_input('Username')
      password = st.text_input('Password', type='password')
    
      if st.form_submit_button('Register'):
        with st.spinner():
          if register_user(username, password, email_address):
            st.success('User registered successfully')
          else:
            st.error('Registration failed')


  with tab3:
    with st.form(key='Forgot password'):
      identifier = st.text_input('Email')
    
      if st.form_submit_button('Reset Password'):
        with st.spinner():
          if '@' not in identifier or '.com' not in identifier[-4:] or identifier in [None, '']:
            st.error('Email not valid')
            return

          # new_password = forgot_password(identifier)
          new_password = reset_password_insecure(identifier)
          if new_password:
            st.success('Password reset! Please check your email for the new password.')
          else:
            st.error('Email not found')


#------------------------------#

def check_credentials(identifier, password):
  user = None
  if '@' in identifier:
    result = supabase.table('user_creds').select("*").eq('email', identifier).execute()
  else:
    result = supabase.table('user_creds').select("*").eq('username', identifier).execute()
  user = result.data[0] if result.data else None

  if user and bcrypt.checkpw(password.encode(), user['password'].encode()):
    return user
  return None


def register_user(username, password, email):
  # Check if every field is filled
  if not username or not password or not email:
    st.error('All fields must be filled.')
    return False
    
  # Check if email is legit
  if '@' not in email or '.com' not in email[-4:]:
    st.error('Not a valid email address')
    return False
  
  # Check if only alphanumeric characters are included within username
  if not re.match("^[a-zA-Z0-9]+$", username):
    st.error('Username can only contain alphanumeric characters.')
    return False
  
  # Check if username length is less than or equal to 50
  if len(username) > 50:
    st.error('Username must be 50 characters or less.')
    return False
  
  # Check if password length is at least 6 characters long
  if len(password) < 6:
    st.error('Password must be at least 6 characters long.')
    return False
  
  # Check for duplicate username or email
  existing_email = supabase.table('user_creds').select('*').eq('email', email).execute()
  existing_username = supabase.table('user_creds').select('*').eq('username', username).execute()

  if existing_username.data or existing_email.data:
    st.error('Username or email already exists.')
    return False
  
  try:
    hashed_password = stauth.Hasher([password]).generate()[0]
    result = supabase.table('user_creds').insert([
      {'username': username, 'password': hashed_password, 'email': email}
    ]).execute()
    return result
  except Exception as e:
    raise e

#---Reset Password helpers---#
def forgot_password(identifier):
  import smtplib
  import secrets
  from email.mime.text import MIMEText

  def generate_reset_token(user):
    token = secrets.token_urlsafe(32)
    return token

  # Determine whether the identifier is a username or email
  user = None
  if '@' in identifier:
    result = supabase.table('user_creds').select("*").eq('email', identifier).execute()
  else:
    result = supabase.table('user_creds').select("*").eq('username', identifier).execute()
  user = result.data[0] if result.data else None

  print('\n', user, '\n') # 

  if user:
    # Generate a unique reset token and URL
    reset_token = generate_reset_token(user)
    reset_url = f"https://your-app.com/reset-password?token={reset_token}"

    # Create the email message
    msg = MIMEText(f'''
    Hi {user['username']},

    You requested a password reset. Click the link below to reset your password:

    {reset_url}

    If you did not request this, please ignore this email.

    Thanks,
    Gecko Technologies
    ''')

    msg['From'] = 'noreply@geckointel.com'
    msg['To'] = user['email']
    msg['Subject'] = 'Gecko Technologies - Password Reset Request'

    try:
      #---Send the email---#
      # server = smtplib.SMTP('smtpout.secureserver.net', 465, timeout=10) # From godaddy, SSL Port: 465 or 587
      # server.ehlo()
      # server.starttls() # Remove this line if using SSL (port 465)

      server = smtplib.SMTP_SSL('smtpout.secureserver.net', 465, timeout=10)
      server.login(st.secrets['anon_email'], st.secrets['anon_email_pw']) # your business email and pw
      server.sendmail('noreply@geckointel.com', user['email'], msg.as_string()) 
      server.quit()
      return True
    
    except Exception as e:
      print(f"Error sending email: {e}")
      return False
  
  else:
    return False


def reset_password_insecure(identifier):
  """ 
  NOT A GOOD PRACTICE. AVOID USING IN PRODUCTION. 
  Resets password immediately and emailed to user. Risk interception
  """
  import smtplib
  import secrets
  from email.mime.text import MIMEText

  # Generate a new random password
  new_password = secrets.token_urlsafe(10) 

  # Determine whether the identifier is a username or email
  user = None
  if not '@' in identifier:
    return
  
  result = supabase.table('user_creds').select("*").eq('email', identifier).execute()
  user = result.data[0] if result.data else None

  if user:
    # Hash and update the new password
    hashed_password = stauth.Hasher([new_password]).generate()[0]

    # Create the email message
    msg = MIMEText(f'''
    Hi {user['username']},

    Your password has been reset. Your new password is:

    {new_password}

    Thanks,
    Gecko Technologies
    ''')

    # ... rest of the email sending code ...
    msg['From'] = 'noreply@geckointel.com'
    msg['To'] = user['email']
    msg['Subject'] = 'Gecko Technologies - Password Reset Request'

    try:
      server = smtplib.SMTP_SSL('smtpout.secureserver.net', 465, timeout=10)
      server.login(st.secrets['anon_email'], st.secrets['anon_email_pw']) # your business email and pw
      server.sendmail('noreply@geckointel.com', user['email'], msg.as_string()) 
      server.quit()

      # Update only after mail is successfully sent
      supabase.table('user_creds').update({'password': hashed_password}).eq('email', user['email']).execute()
      return True
    
    except Exception as e:
      print(f"Error sending email: {e}")
      return False
  
  else:
    return False



