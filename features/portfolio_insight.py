import streamlit as st
from groq import Groq
import pandas as pd
from supabase import Client, create_client
import yfinance as yf

supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)
groq_key = st.secrets['API_KEY']

groq_client = Groq(api_key=groq_key)

def show_insights():
    stored_id = st.session_state.get("user_id")
    if not stored_id:
        st.error("No user ID found. Please log in again.")
        return
    st.title('Insights into your Portfolio')
    try:
        response = supabase.table('user_portfolio').select('ticker_symbol', 'share_count').eq('user_id',stored_id).execute()
        rows = response.data

        if not rows:
            st.error('Portfolio not found.')

        df = pd.DataFrame(rows)

        if all(col in df.columns for col in ['ticker_symbol', 'share_count']):
            tickers = df['ticker_symbol'].tolist()
            info_dict = {}
            keys_to_keep = [
                "symbol",
                "shortName",
                "regularMarketPrice",
                "previousClose",
                "open",
                "dayHigh",
                "dayLow",
                "fiftyTwoWeekHigh",
                "fiftyTwoWeekLow",
                "marketCap",
                "volume",
                "averageVolume",
                "trailingPE",
                "forwardPE",
                "dividendYield"
            ]

            def filter_info(info: dict, keys_to_keep: list) -> dict:
                return {k: info.get(k) for k in keys_to_keep if k in info}
            for ticker in tickers:
                info = yf.Ticker(ticker).info
                info_dict[ticker] = filter_info(info, keys_to_keep)
            tickers_data = yf.download(tickers=tickers, period='1d', interval='1m', auto_adjust=True)['Close'].iloc[-1]
            df['current_price'] = df['ticker_symbol'].map(tickers_data)
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
            cash = supabase.table('user_cash').select('cash_amount').eq('user_id', stored_id).execute()
            port_value = df['Total Value ($)'].sum()
            port_day_change = df['Total Day Change ($)'].sum()
            if cash.data:
                cash_amount = cash.data[0]['cash_amount']
                Portfolio_Data = f'Total Portfolio Value: {port_value:,.2f} dollars\nTotal Daily Change: {port_day_change:,.2f} dollars\nCash Amount: {cash_amount:,.2f} dollars\n'
            else:
                Portfolio_Data = f'Total Portfolio Value: {port_value:,.2f} dollars\nTotal Daily Change: {port_day_change:,.2f} dollars\n'






            system_content = f"""
            You are a financial AI assistant. Analyze the following stock portfolio. The portfolio data is provided entirely as a string, not as an object.

            Portfolio data:
            \"\"\"
            {Portfolio_Data}
            \"\"\"
            
            Individual Stock Data from yfinance:
            {info_dict}

            Please provide:
            1. Overall portfolio performance and total gain/loss.
            2. Risk assessment (diversification, sector concentration, volatility).
            3. Key holdings and their impact on performance.
            4. Suggestions for improvement or rebalancing.
            5. Any notable trends or observations.
            6. Summarize in 3-5 bullet points, new-line separated.

            Return your answer as a well-structured paragraph that is easy for users to read.
            DO NOT use the '$' Symbol in your response. Instead, use the word 'dollars'.
            """

            try:
                # noinspection PyTypeChecker
                response = groq_client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": "Please analyze this portfolio and provide your summary."}
                    ],
                    temperature=0.0
                )

                analysis = response.choices[0].message.content.strip()

                st.write(f'{analysis}')
            except Exception as e:
                print("Groq API error:", e)




    except Exception as e:
        st.error(e)


