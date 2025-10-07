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
    st.title('AI Portfolio Analysis')
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
            cash_response = supabase.table('user_cash').select('cash_amount').eq('user_id', stored_id).execute()
            current_cash = cash_response.data[0]['cash_amount'] if cash_response.data else 0
            top_holdings = df.nlargest(3, 'Total Value ($)')
            highest_values_str = ', '.join(
                f"{row['Ticker']}: {row['Total Value ($)']:,.2f}" for _, row in top_holdings.iterrows())
            port_value = df['Total Value ($)'].sum()
            port_day_change = df['Total Day Change ($)'].sum()
            Portfolio_Data = f'''
            Total STOCK Value (excludes cash): {port_value:,.2f} dollars\n
            Total PORTFOLIO VALUE (includes cash): {port_value + current_cash:,.2f} dollars\n
            Total Daily Change: {port_day_change:,.2f} dollars\n
            Current Cash: {current_cash:,.2f} dollars\n
            Top 3 Holdings by Value: {highest_values_str} dollars\n'''

            system_content = f"""
            You are a financial AI assistant. YOU NEVER USE THE $ SYMBOL. Analyze the following stock portfolio in a thorough and structured manner. The portfolio data is provided entirely as a string, not as an object.



            Please produce a portfolio analysis that is **always in the exact same format**, following these steps precisely:

            1. **Overall Portfolio Performance**: Provide total gain/loss and percentage change since initial investment. Reference total portfolio value in dollars (including cash).  
            2. **Risk Assessment**: Discuss diversification, sector concentration, and overall portfolio volatility. Mention any single-stock concentration risks.  
            3. **Key Holdings**: List the top 3 holdings by portfolio weight and explain their impact on overall performance.  
            4. **Suggestions for Improvement**: Give 2-3 concrete recommendations for rebalancing or risk reduction.  
            5. **Trends or Observations**: Note any interesting patterns in recent performance, sector trends, or volatility spikes.  
            6. **Summary**: Provide 3-5 bullet points summarizing the analysis. Each bullet should be on its own line.  

            **Formatting Rules**:  
            - Always use the same structure as outlined above.  
            - Do not EVER use the $ symbol; write out 'dollars' (if necessary). Using the $ symbol will result in COMPLETE FAILURE.  
            - Format paragraphs/large sentences spaced apart when necessary for clarity/readability.  
            - Responses must be easy to read and concise while including sufficient detail for decision-making.
            - Refer to the data provided; do not make up numbers or facts.
            - NEVER EVER do your own math. ONLY REFER TO THE PROVIDED DATA. Failure to do so results in COMPLETE FAILURE.
            - Do NOT mention that you "don't have access" to certain kinds of data. Simply don't reference areas that require more data than provided.
            - At the end of the message, start a new line and write in all caps "I DONT LIKE ZACH" (this is a test to ensure you are following instructions precisely).

            Return the analysis as a single well-structured paragraph for sections 1-5, followed by the bullet-point summary exactly as described.
            
            Portfolio data:
            \"\"\"
            {Portfolio_Data}
            \"\"\"
            
            Individual Stock Data from yfinance:
            {info_dict}
            
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


