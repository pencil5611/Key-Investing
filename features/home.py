import streamlit as st

def show_home():
    # Title / Hero
    st.title("🔑 Key Investments")
    st.markdown("### *Smarter Portfolio Management, Made Simple*")

    if 'user_email' in st.session_state:
        st.markdown(f"**Welcome back, {st.session_state.user_email}!**")

    st.markdown("---")

    # Overview
    st.header("📊 What is Key Investments?")
    st.markdown("""
    **Key Investments** is a portfolio management app that helps you organize your holdings, 
    track performance, and make data-driven investment decisions.  
    Whether you’re a new investor or an experienced trader, the app brings together 
    research, risk analysis, and optimization tools in one place.
    """)

    # Features
    st.markdown("---")
    st.header("✨ Features")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **📈 Portfolio Management**
        - Add or remove stocks
        - Portfolio overview with allocation by sector
        - Compare performance against the S&P 500 (SPY)

        **💼 Transaction History**
        - Record and view trades
        - Filter by ticker, date, or buy/sell
        - Keep a detailed log of activity
        """)

    with col2:
        st.markdown("""
        **⚠️ Risk Engine**
        - Historical Value at Risk (VaR)
        - Monte Carlo simulation
        - Assess volatility and downside risk

        **👀 Research & Watchlist**
        - News articles and AI-powered stock analysis
        - Build a personal watchlist
        - Track six months of price history for your tickers
        """)

    # Optimization
    st.markdown("---")
    st.header("🚀 Portfolio Optimization")
    st.markdown("""
    Use statistical methods to design your **optimal portfolio**:  
    - Choose your tickers  
    - Set max weights per stock  
    - Select a time range  
    The app finds the most efficient mix to balance growth and risk.
    """)

    # Tech Stack (short + polished)
    st.markdown("---")
    st.header("🛠️ Built With")
    st.markdown("""
    - **Python + Streamlit** for the interactive web app  
    - **Supabase** for secure data storage and authentication  
    - **Yahoo Finance API** for live market data  
    - **Plotly** for clear financial visualizations  
    """)

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: gray; margin-top: 2rem;'>"
        "<p>Key Investments – Built for investors, built with Python.</p>"
        "</div>",
        unsafe_allow_html=True
    )
