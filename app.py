import streamlit as st
from supabase import create_client, Client
from features.portfolio_management import show_port_manager
from features.stock_research import show_research_watchlist_page
from features.optimize import portfolio_page
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]

supabase: Client = create_client(supabase_url, supabase_key)



if 'user_email' not in st.session_state:
    st.session_state.user_email = None
    st.session_state.user_id = None

    if st.query_params:
        stored_user = st.query_params.get('u')
        stored_id = st.query_params.get('d')
        if stored_user and stored_id:
            st.session_state.user_email = stored_user
            st.session_state.user_id = stored_id


def sign_up(email, password):
    try:
        user = supabase.auth.sign_up({'email': email, 'password': password})
        return user
    except Exception as e:
        st.error(f'Registration failed: {e}')


def sign_in(email, password):
    try:
        user = supabase.auth.sign_in_with_password({'email': email, 'password': password})
        if user and user.user:
            st.session_state.user_email = user.user.email
            st.session_state.user_id = user.user.id
            # Add to URL to persist
            st.query_params.u = user.user.email
            st.query_params.d = user.user.id
            st.success(f'Welcome back, {email}')
            st.rerun()
        return user
    except Exception as e:
        st.error(f'Sign in failed: {e}')


def sign_out():
    try:
        supabase.auth.sign_out()
        st.session_state.user_email = None
        st.query_params.clear()
        st.rerun()

    except Exception as e:
        st.error(f'Sign out failed: {e}')


def main_app():
    page = st.sidebar.selectbox('Select Page', [ 'Portfolio Management',
                                                'Research and Watchlist',
                                                'Portfolio Optimization'])
    content = st.empty()

    if page == 'Portfolio Management':
        with content:
            show_port_manager()

    if page == 'Research and Watchlist':
        with content:
            show_research_watchlist_page()


    if page == 'Portfolio Optimization':
        with content:
            portfolio_page()

    st.divider()

    if st.button('Logout'):
        sign_out()


def auth_screen():
    st.title('Key Investing Login/Sign Up Page')
    option = st.selectbox('Choose an Action:', ['Login', 'Sign Up'])
    email = st.text_input('Email')
    password = st.text_input('Password', type='password')

    if option == 'Sign Up' and st.button('Register'):
        user = sign_up(email, password)
        if user and user.user:
            st.success('Registration successful. You may log in.')


    if option == 'Login' and st.button('Login'):
        user = sign_in(email, password)
        if user and user.user:
            st.session_state.user_email = user.user.email
            st.success(f'Welcome back, {email}')
            st.rerun()


if st.session_state.user_email:
    main_app()
else:
    auth_screen()


