import streamlit as st
import numpy as np
import pandas as pd
from fredapi import Fred
import yfinance as yf
import plotly.express as px
from datetime import datetime, date, timedelta
from scipy.optimize import minimize
import ssl
import certifi
from supabase import Client, create_client

ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)
FED_API_KEY = st.secrets["FED_API_KEY"]
fred = Fred(api_key=FED_API_KEY)


def save_optimal_port(stored_id, tickers, weights, metrics, timestamp, name):
    data = {
        'user_id': stored_id,
        'tickers': tickers,
        'weights': weights.tolist(),
        'metrics': metrics,
        'created_at': timestamp.isoformat(),
        'port_name': name,
    }

    response = supabase.table('saved_optimized_ports').insert([data]).execute()
    if response.data:
        st.success('Portfolio Saved!')
    else:
        st.error('Error saving portfolio. Please try again later.')

def standard_deviation(weights, cov_matrix):
    variance = weights.T @ cov_matrix @ weights
    return np.sqrt(variance)

def expected_return(weights, log_returns):
    mean_returns = log_returns.mean().values
    return np.dot(weights, mean_returns) * 252

def sharpe_ratio(weights, log_returns, cov_matrix, risk_free_rate):
    return (expected_return(weights, log_returns) - risk_free_rate) / standard_deviation(weights, cov_matrix)

def neg_sharpe_ratio(weights, log_returns, cov_matrix, risk_free_rate):
    return -sharpe_ratio(weights, log_returns, cov_matrix, risk_free_rate)


def portfolio_page():
    tab1, tab2 = st.tabs(["Optimize Portfolio", "Saved Portfolios"])

    def show_optimize():
        stored_id = st.session_state.get("user_id")
        if not stored_id:
            st.error("No user ID found. Please log in again.")
            return

        if "tickers" not in st.session_state:
            st.session_state["tickers"] = []

        if "weight" not in st.session_state:
            st.session_state["weight"] = None

        if "port_name" not in st.session_state:
            st.session_state["port_name"] = None

        st.header("Portfolio Optimization Tool")

        with st.form(key="ticker_form", clear_on_submit=True):
            ticker_input = st.text_input("Enter Ticker").upper()
            add_ticker = st.form_submit_button("Add Ticker")
            if add_ticker and yf.Ticker(ticker_input).info.get('regularMarketPrice'):
                try:
                    if ticker_input not in st.session_state.tickers:
                            if len(st.session_state.tickers) < 50:
                                st.session_state.tickers.append(ticker_input)
                                st.success(f"Ticker added: {ticker_input}")
                            else:
                                st.warning("Maximum number of tickers reached.")
                    else:
                        st.warning("Ticker already registered.")
                except (ValueError, TypeError):
                    st.warning("Error retrieving ticker info.")

            st.subheader("Current Tickers")
            write_list = []
            if st.session_state.tickers:
                for t in st.session_state.tickers:
                    write_list.append(t)
                to_write = ", ".join(write_list)
                st.write(to_write)
            else:
                st.write("N/A")

        with st.form(key="weight_form", clear_on_submit=True):
            max_weight_input = st.number_input("Maximum Portfolio Weight by Ticker (%)", step=1.0)
            set_weight = st.form_submit_button("Set Maximum Weight")
            if set_weight:
                if max_weight_input > 100:
                    st.warning("Weight cannot exceed 100%.")
                elif max_weight_input < 0:
                    st.warning('Weight cannot be less than zero.')
                elif max_weight_input < (100 / len(st.session_state.tickers)):
                    st.warning('Please input a high enough weight to account for 100% of your portfolio.')
                else:
                    st.session_state.weight = max_weight_input / 100
                    st.success(f"Maximum weight set to {st.session_state.weight:.2f}")

        with st.form(key='name_form', clear_on_submit=True):
            port_name = st.text_input('Name Portfolio')
            save_name = st.form_submit_button('Save Name')
            if save_name:
                if port_name:
                    st.session_state.port_name = port_name
                    st.success(f"Portfolio name set to {port_name}")
                else:
                    st.warning('Please enter a name for your portfolio.')


        if st.session_state.weight is not None:
            st.write(f"Current Maximum Weight: {st.session_state.weight:.2f}")

        if st.session_state.port_name is not None:
            st.write(f"Current Portfolio Name: {st.session_state.port_name}")

        today = datetime.now()
        one_month_ago = today - timedelta(days=31)
        min_date = date(today.year - 20, today.month, today.day)
        start_date = st.date_input("Start Date", min_value=min_date, max_value=one_month_ago)

        if st.button("Run Portfolio Optimization"):
            if not st.session_state.tickers:
                st.warning("Add at least one ticker first.")
            elif st.session_state.weight is None:
                st.warning("Set maximum weight first.")
            elif st.session_state.port_name is None:
                st.warning("Set Portfolio Name first.")
            else:
                adj_close_df = pd.DataFrame()
                for t in st.session_state.tickers:
                    data = yf.download(t, start=start_date, end=today, auto_adjust=True)
                    if "Close" in data.columns:
                        adj_close_df[t] = data["Close"]

                log_returns = np.log(adj_close_df / adj_close_df.shift(1)).dropna()
                cov_matrix = log_returns.cov() * 252

                ten_year_treasury_rate = fred.get_series_latest_release("GS10") / 100
                risk_free_rate = ten_year_treasury_rate.iloc[-1]

                constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1}
                bounds = [(0, st.session_state.weight) for _ in st.session_state.tickers]
                initial_weights = np.array([1 / len(st.session_state.tickers)] * len(st.session_state.tickers))

                optimize_results = minimize(
                    neg_sharpe_ratio,
                    initial_weights,
                    args=(log_returns, cov_matrix, risk_free_rate),
                    method="SLSQP",
                    constraints=constraints,
                    bounds=bounds
                )

                optimal_weights = optimize_results.x
                optimal_portfolio_return = expected_return(optimal_weights, log_returns)
                optimal_portfolio_volatility = standard_deviation(optimal_weights, cov_matrix)
                optimal_sharpe_ratio = sharpe_ratio(optimal_weights, log_returns, cov_matrix, risk_free_rate)

                metrics = {
                    "expected_return": float(optimal_portfolio_return),
                    "volatility": float(optimal_portfolio_volatility),
                    "sharpe_ratio": float(optimal_sharpe_ratio),
                }

                st.session_state['optimal_weights'] = optimal_weights # Saves weights and metrics to session state for later function call
                st.session_state['metrics'] = metrics

                fig = px.bar(
                    x=st.session_state.tickers,
                    y=optimal_weights,
                    labels={"x": "Ticker", "y": "Optimal Weight"},
                    title=f'Optimal Weights by Ticker for Portfolio "{st.session_state.port_name}"'
                )
                st.plotly_chart(fig, use_container_width=True)

                st.markdown(f"""
                Expected Annual Return: {optimal_portfolio_return:.4f}  
                Expected Volatility: {optimal_portfolio_volatility:.4f}  
                Sharpe Ratio: {optimal_sharpe_ratio:.4f}
                """)

                st.info("""
                Disclaimer:
                This portfolio analysis is based on historical data
                and statistical models. Past performance does not guarantee future results,
                and the optimization does not account for all risks or personal circumstances.
                Use this tool for educational and exploratory purposes only, not as financial advice.
                """)

        if 'optimal_weights' in st.session_state:
            if st.button("Save Optimized Portfolio"):
                save_optimal_port(
                    stored_id=stored_id,
                    tickers=st.session_state.tickers,
                    weights=st.session_state.optimal_weights,
                    metrics=st.session_state.metrics,
                    timestamp=datetime.now(),
                    name=st.session_state.port_name,
                )

    def show_saved_tab():
        stored_id = st.session_state.get("user_id")
        if not stored_id:
            st.error("No user ID found. Please log in again.")
            return

        st.header("Saved Portfolios")

        response = supabase.table('saved_optimized_ports').select("*").eq("user_id", stored_id).execute()
        saved_ports = response.data or []

        if saved_ports:
            portfolio_options = [f'{p["port_name"]}' for p in saved_ports]
            selected_port = st.selectbox("Select a saved portfolio to display", portfolio_options)


            port = next(
                (p for p in saved_ports if f'{p["port_name"]}' == selected_port),
                None
            )

            if port is not None:
                st.markdown(f"**Portfolio Name: {port['port_name']}**")
                date_only = port["created_at"].split("T")[0]
                st.write(f'Date Saved: {date_only}')
                for key, value in port['metrics'].items():
                    if key == 'volatility':
                        key = 'Volatility'
                    elif key == 'sharpe_ratio':
                        key = 'Sharpe Ratio'
                    elif key == 'expected_return':
                        key = 'Expected Annual Return'
                    if key != 'Sharpe Ratio':
                        st.write(f'{key}: {value*100:.4f}%')
                    else:
                        st.write(f'{key}: {value:.4f}')
                fig = px.bar(
                    x=port["tickers"],
                    y=port["weights"],
                    labels={"x": "Ticker", "y": "Weight"},
                    title="Portfolio Weights"
                )
                st.plotly_chart(fig, use_container_width=True)

                if fig:
                    if st.button('Delete Saved Portfolio'):
                        supabase.table('saved_optimized_ports').delete().eq("user_id", stored_id).eq('port_name', selected_port).execute()
                        st.rerun()
            else:
                st.warning("No matching portfolio found.")

    with tab1:
        show_optimize()

    with tab2:
        show_saved_tab()












