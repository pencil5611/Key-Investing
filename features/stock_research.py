import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
import yfinance as yf
import requests
from groq import Groq
from supabase import Client, create_client
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)


API_KEY = st.secrets['FIN_API_KEY']
groq_key = st.secrets['API_KEY']

groq_client = Groq(api_key=groq_key)


def get_price_on_or_before(hist, date):
    if hist.empty:
        return None
    date_str = date.strftime("%Y-%m-%d")
    if date_str in hist.index:
        return hist.loc[date_str]["Close"]
    hist_dates = pd.to_datetime([d.split()[0] for d in hist.index.astype(str)])
    target_date = pd.to_datetime(date_str)
    if target_date < hist_dates.min():
        first_date = hist_dates.min().strftime("%Y-%m-%d")
        return hist.loc[first_date]["Close"]
    valid_dates = hist_dates[hist_dates <= target_date]
    if len(valid_dates) > 0:
        closest_date = valid_dates.max().strftime("%Y-%m-%d")
        return hist.loc[closest_date]["Close"]
    return None

def show_research_watchlist_page():

    tab1, tab2 = st.tabs(['Research', 'Your Watchlist'])

    def show_research():


        stored_id = st.session_state.get("user_id")
        if not stored_id:
            st.error("No user ID found. Please log in again.")
            return

        st.title('Stock Research')

        with st.form('ticker_form', clear_on_submit=False):
            ticker = st.text_input('Ticker Symbol').upper()
            submitted = st.form_submit_button('Fetch Data')
            submitted_add = st.form_submit_button('Add To Watchlist')

        if submitted_add:
            if ticker == "":
                st.warning("Please enter a ticker symbol")
            else:
                notes = 'N/A'
                if not yf.Ticker(ticker).info.get('regularMarketPrice'):
                    st.warning('Invalid ticker symbol')
                else:
                    response = supabase.table('user_watchlist').select('ticker_symbol').eq('user_id', stored_id).eq(
                        'ticker_symbol', ticker).execute()
                    if response.data:
                        st.warning(f'{ticker} already exists in your watchlist')
                    else:
                        supabase.table("user_watchlist").insert({
                            "user_id": stored_id,
                            "ticker_symbol": ticker,
                            "notes": notes
                        }).execute()
                        st.success(f"{ticker} has been added to your watchlist")


        if 'metrics_df' not in st.session_state:
            st.session_state.metrics_df = pd.DataFrame()
        if 'ticker_prices_df' not in st.session_state:
            st.session_state.ticker_prices_df = pd.DataFrame()

        if submitted and ticker:

            st.session_state['ticker'] = ticker

            yf_ticker = yf.Ticker(ticker)
            hist = yf_ticker.history(period="7d")
            if hist.empty:
                st.warning(f'Could not fetch price data for specified ticker')
                st.stop()
            else:
                st.session_state.ticker_prices_df = hist[['Close']].copy()

                info = yf_ticker.info
                metrics = {
                    'Current Price': info.get('regularMarketPrice'),
                    'Previous Close': info.get('previousClose'),
                    'Open': info.get('open'),
                    'Days Low': info.get('dayLow'),
                    'Days High': info.get('dayHigh'),
                    'Fifty Two Week Low': info.get('fiftyTwoWeekLow'),
                    'Fifty Two Week High': info.get('fiftyTwoWeekHigh'),
                    'Volume': info.get('volume'),
                    'Average Volume': info.get('averageVolume'),
                    'Market Cap': info.get('marketCap'),
                    'Beta': info.get('beta'),
                    'PE Ratio': info.get('trailingPE'),
                    'EPS': info.get('trailingEps'),
                    'Target Price': info.get('targetMeanPrice'),
                }

                def format_value(val):
                    if val is None:
                        return 'N/A'
                    if isinstance(val, (int, float)):
                        return f"{val:,.2f}"
                    if isinstance(val, datetime):
                        return val.strftime('%b %d, %Y')
                    return str(val)

                metrics_formatted = {k: format_value(v) for k, v in metrics.items()}
                st.session_state.metrics_df = pd.DataFrame([metrics_formatted])

        if 'ticker' in st.session_state:
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
            start_date = datetime.today() - timedelta(days=days)

            ticker_prices = yf.download(st.session_state['ticker'], start=start_date, auto_adjust=True)['Close'].ffill()

            st.session_state.ticker_prices_df = pd.DataFrame(
                {'Date': ticker_prices.index.ravel(), 'Close': ticker_prices.values.ravel()})

            if not st.session_state.ticker_prices_df.empty:
                df = st.session_state.ticker_prices_df.set_index('Date')
                st.line_chart(df['Close'])

            if not st.session_state.metrics_df.empty:
                st.subheader('Important Metrics')
                metrics_dict = st.session_state.metrics_df.iloc[0].to_dict()

                formatted_lines = []
                for key, value in metrics_dict.items():
                    formatted_lines.append(f"**{key}** {'.' * 20} <span style='color: #00cc44;'>{value}</span>")

                st.markdown('<br>'.join(formatted_lines), unsafe_allow_html=True)

            if 'show_news' not in st.session_state:
                st.session_state.show_news = False
            if 'show_ai' not in st.session_state:
                st.session_state.show_ai = False

            stored_ticker = st.session_state['ticker']
            col1, col2 = st.columns(2)

            with col1:
                if st.button(f'{stored_ticker} News') and yf.Ticker(stored_ticker).info.get('regularMarketPrice'):
                    st.session_state.show_news = True
                    st.session_state.show_ai = False

            with col2:
                if st.button(f'{stored_ticker} AI Overview') and yf.Ticker(stored_ticker).info.get('regularMarketPrice'):
                    st.session_state.show_ai = True
                    st.session_state.show_news = False

            if st.session_state.show_news:
                try:
                    if stored_ticker == '':
                        st.warning('Please enter a ticker symbol')
                    else:
                        two_months_ago = (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d')
                        today = datetime.now().strftime('%Y-%m-%d')
                        url = f"https://finnhub.io/api/v1/company-news?symbol={stored_ticker}&from={two_months_ago}&to={today}&token={API_KEY}"
                        response = requests.get(url)
                        news_data = response.json()
                        if response.status_code == 200:
                            with st.container():
                                for article in news_data:
                                    st.markdown(f"### [{article['headline']}]({article['url']})")
                                    col1, col2, col3 = st.columns(3)
                                    with col1:
                                        readable_date = datetime.fromtimestamp(article['datetime']).strftime(
                                            '%B %d, %Y at %I:%M %p')
                                        st.caption(f"📅 {readable_date}")
                                    with col2:
                                        st.caption(f"📰 {article['source']}")
                                    with col3:
                                        st.caption(f"📊 Sentiment: {article.get('sentiment', 'N/A')}")


                                    st.markdown(article['summary'])
                                    st.divider()
                except Exception as e:
                    st.warning(e)

            if st.session_state.show_ai:
                try:
                    if stored_ticker == '':
                        st.warning('Please enter a ticker symbol')
                    else:
                        yf_ticker = yf.Ticker(stored_ticker)
                        info = yf_ticker.info


                        prompt = f"""
                        Analyze {stored_ticker} using these grouped financial metrics:
    
                        
                        TICKER INFO: {info}
    
                        Provide a professional IN DETAIL investment analysis covering company overview, financial health, valuation, and outlook. Separate numbers from text except for when required, like a comma.
                         ONLY USE THE GIVEN INFORMATION IN YOUR ANALYSIS.
                         DO NOT use the '$' symbol in your analysis.
                         Clearly format your analysis so that the user can easily read it. (Bullet points are acceptable)
                         NEVER MAKE UP INFORMATION.
                         Abbreviate large numbers when necessary (e.g. 1,500,000 as 1.5M or 1.5 million).
                         NEVER refer to a user directly. Always keep the analysis objective and data-driven. Don't reference "the given data" only say "the data".
                        """

                        try:
                            # noinspection PyTypeChecker
                            response = groq_client.chat.completions.create(
                                model="llama-3.1-8b-instant",
                                messages=[
                                    {"role": "system",
                                     "content": """You are a financial analyst. When given stock data, provide a clear, detailed, and professional summary of the company's financial condition and investment analysis.
    
                        Instructions for your analysis:
                        1. **Company Overview** — Briefly describe what the company does
                        2. **Financial Health** — Discuss profitability, liquidity, leverage, and efficiency 
                        3. **Growth & Trends** — Identify trends and growth patterns
                        4. **Valuation** — Analyze if the stock might be overvalued or undervalued
                        5. **Risks & Concerns** — Highlight any red flags or concerning ratios
                        6. **Investment Outlook** — Provide a reasoned investment outlook
    
                        CRITICAL: Always use proper spacing between words. Never concatenate words together. Each word should be separated by exactly one space.
    
                        Keep your tone objective and data driven.
                        CRITICAL FORMATTING: Write each word separately. For example, write "the company is profitable" NOT "thecompanyisprofitable". Always put spaces between words."""},
                                    {"role": "user", "content": prompt}
                                ],
                                temperature=0.0
                            )
                            analysis = response.choices[0].message.content.strip()

                            st.subheader('**🤖 AI Analysis**')
                            st.write(analysis)
                        except Exception as e:
                            st.warning(f"AI request failed: {e}")
                except Exception as e:
                    st.warning(f"AI request failed: {e}")


    def show_watchlist():
        stored_id = st.session_state.get("user_id")
        if not stored_id:
            st.error("No user ID found. Please log in again.")
            return

        st.title("🔍Your Watchlist")

        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🔄 Refresh All Data"):
                st.rerun()

        with st.form(key="watchlist_form", clear_on_submit=True):
            ticker = st.text_input("Ticker Symbol").upper()
            notes = st.text_input("Notes")
            submitted_add = st.form_submit_button("Add to Watchlist")
            submitted_remove = st.form_submit_button("Remove from Watchlist")

            if submitted_add:
                if ticker == "":
                    st.warning("Please enter a ticker symbol")
                else:
                    if not notes:
                        notes = "N/A"
                    if not yf.Ticker(ticker).info.get('regularMarketPrice'):
                        st.warning('Invalid ticker symbol')
                    else:
                        response = supabase.table('user_watchlist').select('ticker_symbol').eq('user_id', stored_id).eq(
                            'ticker_symbol', ticker).execute()
                        if response.data:
                            st.warning(f'{ticker} already exists in your watchlist')
                        else:
                            supabase.table("user_watchlist").insert({
                                "user_id": stored_id,
                                "ticker_symbol": ticker,
                                "notes": notes
                            }).execute()
                            st.success(f"{ticker} has been added to your watchlist")
                            st.rerun()

            if submitted_remove:
                if ticker == "":
                    st.warning("Please enter a ticker symbol")
                else:
                    response = supabase.table('user_watchlist').select('ticker_symbol').eq('user_id', stored_id).eq(
                        'ticker_symbol', ticker).execute()
                    if not response.data:
                        st.warning(f'{ticker} does not exist in your watchlist')
                    else:
                        supabase.table("user_watchlist").delete().eq("user_id", stored_id).eq("ticker_symbol",
                                                                                              ticker).execute()
                        st.success(f"{ticker} removed from your watchlist")
                        st.rerun()

        response = supabase.table("user_watchlist").select("ticker_symbol, notes").eq("user_id", stored_id).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            updated_rows = []
            today = datetime.now(timezone.utc)
            one_month_ago = today - timedelta(days=30)
            three_months_ago = today - timedelta(days=90)
            six_months_ago = today - timedelta(days=182)

            for _, row in df.iterrows():
                ticker = row["ticker_symbol"]
                notes = row["notes"]
                try:
                    ticker_yf = yf.Ticker(ticker)
                    hist = ticker_yf.history(start=six_months_ago.strftime("%Y-%m-%d"), end=today.strftime("%Y-%m-%d"))
                    price_1m = get_price_on_or_before(hist, one_month_ago)
                    price_3m = get_price_on_or_before(hist, three_months_ago)
                    price_6m = get_price_on_or_before(hist, six_months_ago)
                    share_price = ticker_yf.info.get("regularMarketPrice")
                    last_close = ticker_yf.info.get("previousClose")

                    if any(v is None for v in [price_1m, price_3m, price_6m, share_price, last_close]):
                        continue

                    day_change = share_price - last_close
                    month_change = share_price - price_1m
                    threeM_change = share_price - price_3m
                    sixM_change = share_price - price_6m
                    day_pct = (day_change / last_close) * 100 if last_close else None
                    month_pct = (month_change / price_1m) * 100 if price_1m else None
                    threeM_pct = (threeM_change / price_3m) * 100 if price_3m else None
                    sixM_pct = (sixM_change / price_6m) * 100 if price_6m else None

                    updated_rows.append([
                        ticker, notes, share_price, price_1m, price_3m, price_6m,
                        day_pct, month_pct, threeM_pct, sixM_pct
                    ])
                except Exception:
                    continue

            display_df = pd.DataFrame(updated_rows, columns=[
                "Ticker", "Notes", "Price Now", "Price 1M Ago", "Price 3M Ago", "Price 6M Ago",
                "Day % Change", "1M % Change", "3M % Change", "6M % Change"
            ])
            display_df = display_df.fillna("N/A")
            st.dataframe(display_df, hide_index=True)
        else:
            st.info("No tickers in your watchlist yet.")


    with tab1:
        show_research()

    with tab2:
        show_watchlist()
