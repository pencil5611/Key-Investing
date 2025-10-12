import pandas as pd
import streamlit as st
import yfinance as yf
from supabase import create_client, Client
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict
import numpy as np
import time
from features.portfolio_insight import show_insights
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)


def show_port_manager():
    tab1, tab2, tab3, tab4 = st.tabs(["Portfolio Management", "Transaction History", 'Portfolio Risk Analysis', 'AI Analysis'])

    def retry_if_fail(ticker, start_date=None, end_date=None, max_retries=10, sleep_sec=0.5):
        for attempt in range(max_retries):
            try:
                data = yf.download(
                    tickers=ticker,
                    start=start_date,
                    end=end_date,
                    auto_adjust=True,
                    progress=False
                )
                if not data.empty and "Close" in data.columns:
                    return data["Close"]
            except (KeyError, IndexError, ValueError, TypeError, AttributeError,
                    ConnectionError, TimeoutError, OSError, Exception):
                pass
            time.sleep(sleep_sec)
        return pd.Series(dtype=float)

    def port_manager_tab():
        stored_id = st.session_state.get("user_id")
        if not stored_id:
            st.error("No user ID found. Please log in again.")
            return

        def log_transaction(stored_id, date, txn_type, ticker, shares, price_per_share, total_value, notes=''):
            if hasattr(date, 'isoformat'):
                date = date.isoformat()
            transaction_data = {'user_id': stored_id,
                                'txn_date': date,
                                'txn_type': txn_type,
                                'ticker_symbol': ticker,
                                'shares': shares,
                                'price_per_share': price_per_share,
                                'total_value': total_value,
                                'notes': notes}
            try:
                supabase.table('user_transactions').insert(transaction_data).execute()
            except Exception as e:
                st.error(f"Failed to log transaction: {e}")

        def save_cash(amount):
            try:
                existing_cash = supabase.table("user_cash").select("*").eq("user_id", stored_id).execute()

                if existing_cash.data:
                    supabase.table("user_cash").update({"cash_amount": amount}).eq("user_id", stored_id).execute()
                else:
                    supabase.table("user_cash").insert({"user_id": stored_id, "cash_amount": amount}).execute()

            except Exception as e:
                st.error(f"Failed to save cash assets: {e}")


        st.title('📊Portfolio Management📈')

        with st.form(key='stock_form', clear_on_submit=True):
            ticker = st.text_input('Ticker:').upper()
            s_count = st.number_input('Shares:', max_value=(10.0 ** 7), min_value=0.0001, step=0.0001, format="%.4f", value=None)
            notes = st.text_input('Notes:')
            submitted_add = st.form_submit_button(label='Add to Portfolio')
            submitted_remove = st.form_submit_button(label='Remove from Portfolio')
            refresh_button = st.form_submit_button(label='Refresh Data')

            st.divider()
            cash_response = supabase.table('user_cash').select('cash_amount').eq('user_id', stored_id).execute()
            current_cash = cash_response.data[0]['cash_amount'] if cash_response.data else 0
            cash_amount = st.number_input(
                'Cash Assets ($)',
                min_value=0.0,
                step=0.01,
                format="%.2f",
                value=float(current_cash)
            )
            saved_cash = st.form_submit_button(label='Save Cash')

            if saved_cash:
                if cash_amount >= 0:
                    save_cash(cash_amount)
                    st.success(f'Saved ${cash_amount} to your Portfolio')
                else:
                    st.warning('Cash must be at least zero.')

            if submitted_add:
                try:
                    if ticker == '':
                        st.warning('Please enter a ticker symbol.')
                    else:
                        yf_ticker = yf.Ticker(ticker)
                        price_per_share = yf_ticker.info.get('regularMarketPrice')
                        last_close = yf_ticker.info.get('previousClose')
                        if not notes:
                            notes = 'N/A'
                        if yf_ticker and price_per_share and last_close and float(s_count) > 0:
                            try:
                                now = datetime.now()
                                txn_type = 'Buy'
                                existing_response = supabase.table('user_portfolio').select('*').eq('user_id',
                                                                                                    stored_id).eq(
                                    'ticker_symbol', ticker).execute()
                                if existing_response.data:

                                    existing_record = existing_response.data[0]
                                    existing_shares = float(existing_record['share_count'])
                                    new_total_shares = existing_shares + float(s_count)

                                    update_data = {
                                        'share_count': str(new_total_shares),

                                    }

                                    result = supabase.table('user_portfolio').update(update_data).eq('user_id',
                                                                                                     stored_id).eq(
                                        'ticker_symbol', ticker).execute()

                                    if result.data:
                                        total_value = float(price_per_share) * float(s_count)
                                        log_transaction(stored_id, now, txn_type, ticker, s_count, price_per_share,
                                                        total_value,
                                                        notes)
                                        st.success(
                                            f'Updated {ticker}: Added {s_count} shares. New total: {new_total_shares} shares.')
                                    else:
                                        st.error(f'Failed to update {ticker} in Portfolio.')

                                else:
                                    data_to_save = {
                                        'user_id': stored_id,
                                        'ticker_symbol': ticker,
                                        'share_count': s_count
                                    }

                                    result = supabase.table('user_portfolio').insert(data_to_save).execute()
                                    if result.data:
                                        total_value = float(price_per_share) * float(s_count)
                                        log_transaction(stored_id, now, txn_type, ticker, s_count, price_per_share,
                                                        total_value,
                                                        notes)
                                        st.success(f'Added {s_count} shares of {ticker} to Portfolio.')
                                    else:
                                        st.error(f'Failed to add {ticker} to Portfolio.')

                            except Exception as e:
                                st.error(f'Failed to add {ticker} to Portfolio. Error: {e}')

                        else:
                            st.warning(f'Could not fetch data for {ticker}.')
                except Exception as e:
                    st.error(f'Failed to fetch data for {ticker}. Error: {e}')

            if submitted_remove:
                try:
                    if ticker == '':
                        st.warning('Please enter a ticker symbol.')
                    else:
                        yf_ticker = yf.Ticker(ticker)
                        price_per_share = yf_ticker.info.get('regularMarketPrice')
                        now = datetime.now()
                        total_value = float(price_per_share) * float(s_count)
                        if not notes:
                            notes = 'N/A'
                        if yf_ticker and price_per_share and float(s_count) > 0 and notes:
                            try:
                                existing_response = supabase.table('user_portfolio').select('*').eq('user_id',
                                                                                                    stored_id).eq(
                                    'ticker_symbol', ticker).execute()
                                if existing_response.data:
                                    txn_type = 'Sell'
                                    existing_record = existing_response.data[0]
                                    existing_shares = float(existing_record['share_count'])
                                    new_total_shares = existing_shares - float(s_count)
                                    if new_total_shares > 0:
                                        update_data = {'share_count': str(new_total_shares)}
                                        result = supabase.table('user_portfolio').update(update_data).eq('user_id',
                                                                                                         stored_id).eq(
                                            'ticker_symbol', ticker).execute()
                                        if result.data:
                                            log_transaction(stored_id, now, txn_type, ticker, s_count, price_per_share,
                                                            total_value, notes)
                                            st.success(f'Removed {s_count} shares of {ticker} from Portfolio.')
                                    elif new_total_shares == 0:
                                        supabase.table('user_portfolio').delete() \
                                            .eq('user_id', stored_id).eq('ticker_symbol', ticker).execute()
                                        st.success(f'Removed all shares of {ticker} from your portfolio.')
                                        log_transaction(stored_id, now, txn_type, ticker, s_count, price_per_share,
                                                        total_value,
                                                        notes)
                                    else:
                                        st.error(
                                            f'You are trying to remove more shares of {ticker} than you currently own.')

                                else:
                                    st.warning(f'You do not own any shares of {ticker}.')
                            except Exception as e:
                                st.error(f'Error removing {s_count} shares of {ticker}. Error: {e}')
                except Exception as e:
                    st.error(f'Failed to remove {s_count} shares of {ticker}. Error: {e}')

            if refresh_button:
                with st.spinner('Refreshing...'):
                    st.rerun()

        st.subheader('Current Portfolio')

        try:
            response = supabase.table('user_portfolio').select('ticker_symbol', 'share_count').eq('user_id',
                                                                                                  stored_id).execute()
            rows = response.data

            if not rows:
                st.info('Portfolio not found.')

            df = pd.DataFrame(rows)

            if all(col in df.columns for col in ['ticker_symbol', 'share_count']):
                tickers = df['ticker_symbol'].tolist()
                tickers_data = yf.download(tickers=tickers, period='5d', interval='1m', auto_adjust=True, progress=False)['Close'].ffill().bfill()
                latest_prices = tickers_data.iloc[-1]
                df['current_price'] = df['ticker_symbol'].map(latest_prices)
                for index, row in df.iterrows():
                    if pd.isna(row['current_price']):
                        retry_price = retry_if_fail(row['ticker_symbol'], start_date=datetime.now() - timedelta(days=1), end_date=datetime.now())
                        df.at[index, 'current_price'] = retry_price
                df['total_value'] = df['share_count'].astype(float) * df['current_price'].astype(float)
                for _, row in df.iterrows():
                    ticker = row['ticker_symbol']
                    price = row['current_price']
                    last_close = yf.Ticker(ticker).info['previousClose']
                    day_change = price - last_close
                    total_change = day_change * float(row['share_count'])
                    df.loc[row.name, 'day_change'] = day_change
                    df.loc[row.name, 'total_change'] = total_change
                df = df.rename(columns={
                    'ticker_symbol': 'Ticker',
                    'share_count': 'Shares',
                    'current_price': 'Current Price ($)',
                    'total_value': 'Total Value ($)',
                    'day_change': 'Day Change Per Share ($)',
                    'total_change': 'Total Day Change ($)',
                })
                st.dataframe(df, hide_index=True)

                st.subheader('Portfolio Summary')
                stock_port_value = df['Total Value ($)'].sum() if not df.empty else 0
                cash_response = supabase.table('user_cash').select('cash_amount').eq('user_id',
                                                                                     stored_id).execute() if not df.empty else 0
                cash_assets = cash_response.data[0]['cash_amount'] if cash_response.data else 0
                port_value = float(cash_assets) + float(stock_port_value) if not df.empty else 0
                port_change = df['Total Day Change ($)'].sum() if not df.empty else 0
                port_pct_change = (port_change / port_value) * 100 if port_value > 0 else 0

                port_summary = pd.DataFrame({
                    "Metric": [
                        "Cash Assets",
                        "Total Stock Value",
                        "Total Portfolio Value",
                        "Portfolio Change ($)",
                        "Portfolio Change (%)"
                    ],
                    'Value': [
                        f'${cash_assets:,.2f}',
                        f'${stock_port_value:,.2f}',
                        f'${port_value:,.2f}',
                        f'${port_change:,.2f}',
                        f'{port_pct_change:,.2f}%'
                    ]})

                st.dataframe(port_summary, hide_index=True)

                st.subheader('Portfolio Performance vs S&P 500')

                time_options = {
                    "1 Month": 30,
                    "3 Months": 90,
                    "6 Months": 180,
                    "1 Year": 365,
                    "3 Years": 365 * 3,
                    "5 Years": 365 * 5
                }
                time_choice = st.selectbox("Select Time Range", list(time_options.keys()), index=1)
                days = time_options[time_choice]

                if not df.empty:
                    tickers = df['Ticker'].tolist()
                    shares = df.set_index('Ticker')['Shares'].to_dict()
                    start_date = datetime.today() - timedelta(days=days)

                    portfolio_prices = yf.download(tickers, start=start_date, auto_adjust=True, progress=False)['Close'].ffill().bfill()

                    if isinstance(portfolio_prices, pd.Series):
                        portfolio_prices = portfolio_prices.to_frame()

                    valid_tickers = [t for t in tickers if
                                     t in portfolio_prices.columns and not portfolio_prices[t].isnull().all()]
                    shares = {t: shares[t] for t in valid_tickers}

                    portfolio_value = portfolio_prices.multiply([shares[t] for t in portfolio_prices.columns],
                                                                axis=1).sum(axis=1)
                    portfolio_value = portfolio_value.dropna()
                    portfolio_value = portfolio_value[portfolio_value > 0]

                    sp500 = yf.download("^GSPC", start=start_date, auto_adjust=True, progress=False)['Close'].ffill().bfill()

                    if portfolio_value.empty or pd.isna(portfolio_value.iloc[0]) or portfolio_value.iloc[0] == 0:
                        st.warning(
                            "Portfolio price data incomplete or zero on first day; cannot display performance graph.")
                    else:
                        portfolio_norm = portfolio_value / portfolio_value.iloc[0] * 100
                        sp500_norm = sp500 / sp500.iloc[0] * 100

                        comparison_df = pd.DataFrame({
                            "Date": portfolio_norm.index,
                            "Portfolio": pd.Series(portfolio_norm.values.ravel(), index=portfolio_norm.index),
                            "S&P 500": pd.Series(sp500_norm.values.ravel(), index=sp500_norm.index)
                        })

                        fig = px.line(comparison_df, x="Date", y=["Portfolio", "S&P 500"],
                                      labels={"value": "Normalized Value"},
                                      title=f"Portfolio vs S&P 500 ({time_choice})")
                        st.plotly_chart(fig)
                else:
                    st.warning('No Portfolio Data; cannot display performance graph.')

                st.subheader('Portfolio Allocation by Sector')
                sector_totals = defaultdict(float)

                if not df.empty:
                    for _, row in df.iterrows():
                        ticker = row['Ticker']
                        value = row['Total Value ($)']

                        sector_response = supabase.table("ticker_info").select("sector").eq("ticker", ticker).execute()
                        if sector_response.data:
                            sector = sector_response.data[0]['sector']
                        else:
                            sector = yf.Ticker(ticker).info.get('sector', 'N/A')
                            supabase.table("ticker_info").insert({
                                "ticker": ticker,
                                "sector": sector
                            }).execute()

                        sector_totals[sector] += value

                    sector_df = pd.DataFrame(list(sector_totals.items()), columns=['Sector', 'Value'])
                    if not sector_df.empty:
                        fig = px.pie(sector_df, values='Value', names='Sector', title='Sector Allocation')
                        st.plotly_chart(fig)


        except Exception as e:
            st.warning(f'Failed to display Portfolio. Check your internet connection and try again. Error: {e}')

    def transaction_history_tab():
        stored_id = st.session_state.get("user_id")
        if not stored_id:
            st.error("No user ID found. Please log in again.")
            return

        st.title('📜Transaction History')

        try:
            response = (supabase.table('user_transactions').select('id',
                                                                   'txn_date',
                                                                   'txn_type',
                                                                   'ticker_symbol',
                                                                   'shares',
                                                                   'price_per_share',
                                                                   'total_value',
                                                                   'notes'
                                                                   ).eq('user_id', stored_id).execute())
            rows = response.data

            if not rows:
                st.warning("No transactions found. Buy or Sell stock to see transactions here.")

            df = pd.DataFrame(rows)
            df = df.rename(columns={
                'txn_date': 'Date',
                'txn_type': 'Type',
                'ticker_symbol': 'Ticker',
                'shares': 'Shares',
                'price_per_share': 'Price per Share',
                'total_value': 'Total Value',
                'notes': 'Notes'
            })

            df['Date'] = pd.to_datetime(df['Date'])

            min_date, max_date = df['Date'].min(), df['Date'].max()
            date_range = st.date_input(
                "Filter by Date Range:",
                [min_date, max_date],
                min_value=min_date,
                max_value=max_date
            )
            if len(date_range) == 2:
                start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
                df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

            txn_types = df['Type'].unique().tolist()
            selected_types = st.multiselect(
                "Filter by Transaction Type:",
                options=txn_types,
                default=txn_types
            )
            if selected_types:
                df = df[df['Type'].isin(selected_types)]

            tickers = sorted(df['Ticker'].unique().tolist())
            selected_tickers = st.multiselect(
                "Filter by Ticker:",
                options=tickers,
                default=tickers
            )

            if selected_tickers:
                df = df[df['Ticker'].isin(selected_tickers)]

            st.dataframe(df.drop(columns=['id']), hide_index=True)

            st.subheader("🗑️ Delete a Transaction")

            if not df.empty:
                txn_to_delete = st.selectbox(
                    "Select a transaction to delete:",
                    options=df.apply(lambda
                                         row: f"ID {row['id']} | {row['Date'].date()} | {row['Type']} {row['Ticker']} | ${row['Total Value']:.2f}",
                                     axis=1),
                )

                if st.button("Delete Selected Transaction"):

                    txn_id = txn_to_delete.split()[1]
                    try:
                        supabase.table('user_transactions').delete().eq('id', txn_id).execute()
                        st.success(f"Transaction {txn_id} deleted successfully.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to delete transaction. Error: {e}")

        except Exception as e:
            st.error(f'Failed to display Transaction History. Error: {e}')



    def portfolio_risk():
        stored_id = st.session_state.get("user_id")
        if not stored_id:
            st.error("No user ID found. Please log in again.")
            return

        st.title("📉 Portfolio Risk Analysis (Historical VaR)")

        try:
            response = supabase.table('user_portfolio').select('ticker_symbol', 'share_count').eq('user_id',
                                                                                                  stored_id).execute()
            rows = response.data

            if not rows:
                st.warning("No portfolio data found for risk analysis.")
                return

            df = pd.DataFrame(rows)
            tickers = df['ticker_symbol'].tolist()
            shares_dict = df.set_index('ticker_symbol')['share_count'].astype(float).to_dict()

            latest_prices = yf.download(tickers=tickers, period='5d', interval='5m', auto_adjust=True, progress=False)['Close'].ffill().bfill().iloc[-1]
            failures = latest_prices[latest_prices.isna()].index.tolist()
            for ticker in failures:
                retry_price = retry_if_fail(ticker, start_date=datetime.now() - timedelta(days=10), end_date=datetime.now())
                latest_prices[ticker] = retry_price.iloc[-1] if not retry_price.empty else np.nan

            portfolio_value = sum(latest_prices[t] * shares_dict[t] for t in tickers)

            years = 10
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            close_df = pd.DataFrame()
            data = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)
            close_df[tickers] = data['Close']
            for ticker in close_df:
                if close_df[ticker].isna().all():
                    retry_prices = retry_if_fail(ticker, start_date=start_date, end_date=end_date)
                    close_df[ticker] = retry_prices

            if close_df.empty:
                st.warning("Failed to fetch historical price data for selected tickers.")
                return

            log_returns = np.log(close_df / close_df.shift(1)).dropna()

            weights = np.array([shares_dict[t] * close_df[t].iloc[-1] / portfolio_value for t in tickers])

            portfolio_returns = (log_returns * weights).sum(axis=1)

            days = st.number_input('Days', value=5, min_value=1, max_value=10, step=1)
            confidence = st.slider('Confidence', min_value=70.0, max_value=99.99, value=95.0, step=0.1)

            range_returns = portfolio_returns.rolling(window=days).sum().dropna()
            range_returns_pct = np.exp(range_returns) - 1
            range_returns_dollar = range_returns_pct * portfolio_value
            VaR = -np.percentile(range_returns_dollar, 100 - confidence)

            st.metric(label=f"{days}-Day Historical VaR at {confidence}% Confidence", value=f"${VaR:,.2f}")

            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=range_returns_dollar,
                nbinsx=50,
                name='Portfolio Returns',
                opacity=0.75
            ))
            fig.add_vline(
                x=-VaR,
                line=dict(color='red', width=2, dash='dash'),
                annotation_text=f"VaR: ${VaR:,.2f}",
                annotation_position="top right"
            )
            fig.update_layout(
                title=f"{days}-Day Portfolio Returns Distribution",
                xaxis_title="Portfolio Returns ($)",
                yaxis_title="Frequency",
                bargap=0.1,
                template="plotly_white"
            )

            st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error computing portfolio risk: {e}")


    with tab1:
        port_manager_tab()
    with tab2:
        transaction_history_tab()
    with tab3:
        portfolio_risk()
    with tab4:
        show_insights()










