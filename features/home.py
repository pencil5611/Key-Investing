import streamlit as st

def show_home():
    st.title("🌟 Key Investing Streamlit App")

    st.markdown("""
    Key Investing is a **Streamlit-based web application** for individual investors to manage portfolios, conduct stock research, and perform portfolio optimization and risk analysis. The app integrates **real-time market data**, **AI-driven insights**, and a **Supabase backend** for secure user management and data storage.
    """)

    st.header("✨ Features")

    st.subheader("1. Portfolio Management 💼")
    st.markdown("""
    - Add, remove, and track shares of stocks.
    - Log all transactions with details such as date, ticker, shares, price per share, total value, and notes.
    - Manage cash assets.
    - Visualize current portfolio holdings with up-to-date prices.
    - Compare portfolio performance against the S&P 500 over multiple time frames.
    - Sector allocation breakdown via interactive pie charts.
    """)

    st.subheader("2. Transaction History 📝")
    st.markdown("""
    - View all past transactions in a tabular format.
    - Filter transactions by date, type (buy/sell), or ticker.
    - Delete individual transactions.
    """)

    st.subheader("3. Research and Watchlist 🔍")
    st.markdown("""
    - Fetch real-time stock data including price, volume, 52-week high/low, market cap, PE ratio, EPS, beta, and analyst target prices.
    - Maintain a personal watchlist with notes.
    - Track historical price changes over 1, 3, and 6 months.
    - View company news sourced from Finnhub.
    - AI-driven analysis of financial metrics using Groq API for investment insights.
    """)

    st.subheader("4. Portfolio Risk Analysis ⚠️")
    st.markdown("""
    - Historical Value at Risk (VaR) calculation over customizable periods and confidence levels.
    - Visualize portfolio return distributions and risk metrics.
    """)

    st.subheader("5. Portfolio Optimization 🚀")
    st.markdown("""
    - Advanced optimization tools to help identify efficient portfolio allocations.
    - Integration with historical returns and risk metrics.
    """)

    st.subheader("6. User Authentication 🔐")
    st.markdown("""
    - Sign up, log in, and log out with secure credentials using Supabase Auth.
    - Persist user sessions and synchronize data with Supabase database.
    """)

    st.header("📊 Data Sources")
    st.markdown("""
    - **Yahoo Finance (yfinance)**: Real-time and historical stock prices.
    - **Finnhub API**: Company news and sentiment data.
    - **Supabase**: Backend database for user information, portfolios, transactions, and watchlists.
    - **Groq API**: AI-powered financial analysis.
    """)

    st.header("🏗 Architecture")
    st.markdown("""
    - **Frontend**: Streamlit for interactive dashboards and UI.
    - **Backend**: Supabase for authentication and data storage.
    - **Data Processing**: Pandas, NumPy, and yfinance for stock calculations.
    - **Visualization**: Plotly for charts and portfolio performance graphs.
    - **AI Integration**: Groq API for detailed stock analysis.
    """)

    st.header("🛠 Usage Overview")
    st.markdown("""
    1. **Authentication**: Users register or log in via the app. Session data is maintained for portfolio and watchlist management.
    2. **Portfolio Management**: Add or remove stocks, update cash holdings, and track performance against S&P 500.
    3. **Research**: Fetch real-time metrics, explore news, and generate AI-driven analyses for selected tickers.
    4. **Watchlist**: Add tickers to watchlist, monitor recent price changes, and track notes.
    5. **Portfolio Risk Analysis**: Evaluate historical VaR and visualize risk distribution.
    6. **Portfolio Optimization**: Access optimization tools for better portfolio allocation.
    """)

    st.header("💡 Notes")
    st.markdown("""
    - All monetary values are displayed in USD.
    - AI analysis strictly uses provided data; no external assumptions are included.
    - Portfolio calculations use adjusted closing prices for accuracy.
    - App is optimized for Streamlit Cloud deployment.
    """)

    st.header("🔒 Security & Privacy")
    st.markdown("""
    - User credentials and session data are securely managed via Supabase.
    - Financial data is retrieved in real-time from trusted APIs and stored only for authenticated users.
    """)

