"""FinRoute AI — Streamlit entry point."""
from __future__ import annotations
import html
from pathlib import Path
import pandas as pd
import streamlit as st
from modules.chart_selector import select_chart
from modules.classifier import classify
from modules.dashboard_builder import (
    SIDEBAR_BRAND_HTML, SIDEBAR_ICON_DASHBOARD, SIDEBAR_ICON_ENGINE,
    SIDEBAR_ICON_HOME, get_theme_css, build, dimension_pills_html,
)
from modules.indicator_calculator import calculate
from modules.insight_generator import generate

st.set_page_config(page_title="FinRoute AI", layout="wide", initial_sidebar_state="expanded")

if "theme" not in st.session_state:
    st.session_state.theme = "light"

if "fin_view" not in st.session_state:
    st.session_state.fin_view = "home"

st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)

DATA_DIR = Path(__file__).resolve().parent / "data"

# ── 시장 지표 ─────────────────────────────────
@st.cache_data(ttl=300)
def _get_market_data() -> list[dict]:
    try:
        import yfinance as yf
        tickers = {
            "KOSPI": "^KS11", "NASDAQ": "^IXIC", "S&P500": "^GSPC",
            "Gold": "GC=F", "WTI": "CL=F", "USD/KRW": "KRW=X",
        }
        result = []
        for name, sym in tickers.items():
            try:
                hist = yf.Ticker(sym).history(period="5d")
                if len(hist) >= 2:
                    prev = float(hist["Close"].iloc[-2])
                    curr = float(hist["Close"].iloc[-1])
                    chg  = (curr - prev) / prev * 100
                    hist5 = list(hist["Close"].astype(float))
                    result.append({"name": name, "price": curr, "change": chg, "hist": hist5})
                elif len(hist) == 1:
                    curr = float(hist["Close"].iloc[-1])
                    result.append({"name": name, "price": curr, "change": 0.0, "hist": [curr]})
            except Exception:
                result.append({"name": name, "price": None, "change": 0.0, "hist": []})
        return result
    except ImportError:
        return []

# ── 데이터 관리 및 로드 ──────────────────────────
if "df" not in st.session_state:
    st.session_state.df = None
if "fname" not in st.session_state:
    st.session_state.fname = ""

# ── 사이드바 ──────────────────────────────────
with st.sidebar:
    st.markdown(SIDEBAR_BRAND_HTML, unsafe_allow_html=True)
    st.markdown('<div class="sq-nav-label">Menu</div>', unsafe_allow_html=True)

    for key, icon, label in [
        ("home",   SIDEBAR_ICON_HOME,      "Home"),
        ("main",   SIDEBAR_ICON_DASHBOARD, "Dashboard"),
        ("engine", SIDEBAR_ICON_ENGINE,    "Engine"),
    ]:
        row = st.columns([0.22, 0.78])
        with row[0]:
            st.markdown(icon, unsafe_allow_html=True)
        with row[1]:
            btn_type = "primary" if st.session_state.fin_view == key else "secondary"
            if st.button(label, use_container_width=True, key=f"sb_{key}", type=btn_type):
                st.session_state.fin_view = key
                st.rerun()

    dim_section = st.empty()

    st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sq-nav-label">CSV Upload</div>', unsafe_allow_html=True)
    uploaded_sb = st.file_uploader(
        "Upload CSV", type="csv", key="sb_csv_upload", label_visibility="collapsed",
    )

    st.markdown('<div class="sq-nav-label">Settings</div>', unsafe_allow_html=True)
    is_dark = st.toggle("Dark Mode", value=st.session_state.theme == "dark")
    if is_dark and st.session_state.theme != "dark":
        st.session_state.theme = "dark"
        st.rerun()
    elif not is_dark and st.session_state.theme != "light":
        st.session_state.theme = "light"
        st.rerun()

# ── 업로드 데이터 처리 ──────────────────────────
# 홈 업로더(main_csv_upload)와 사이드바 업로더(sb_csv_upload) 감지
uploaded_home = st.session_state.get("main_csv_upload")

# 1. 새로운 파일이 업로드되었는지 확인 (사이드바 또는 홈)
current_upload = uploaded_sb or uploaded_home

if current_upload is not None:
    # A. 파일이 실제로 바뀐 경우 데이터 로드
    if st.session_state.fname != current_upload.name:
        st.session_state.df = pd.read_csv(current_upload)
        st.session_state.fname = current_upload.name
        
        # 홈 화면에서 올렸다면 대시보드로 전환
        if st.session_state.fin_view == "home":
            st.session_state.fin_view = "main"
        st.rerun()
    
    # B. 동일 파일이지만 홈 화면에서 업로드 로직이 수행된 경우 (전환 보장)
    if uploaded_home is not None and st.session_state.fin_view == "home":
        st.session_state.fin_view = "main"
        st.rerun()

# ── 데이터 동기화 ──────────────────────────────
df = st.session_state.df
fname = st.session_state.fname

classify_result: dict | None = None
if df is not None and not df.empty:
    classify_result = classify(df)

with dim_section.container():
    dim = classify_result["dimension"] if classify_result else None
    st.markdown(dimension_pills_html(dim), unsafe_allow_html=True)

# ── 메인 렌더 ─────────────────────────────────
indicator_result = None
chart_result     = None
insight_result   = None
if classify_result is not None and df is not None:
    indicator_result = calculate(df, classify_result)
    chart_result     = select_chart(classify_result)
    insight_result   = generate(classify_result, indicator_result)
    if classify_result:
        st.caption(f"Loaded: **{fname}** · {len(df)} rows")

mkt_data = _get_market_data()
build(
    st.session_state.fin_view,
    classify_result, indicator_result, chart_result, insight_result,
    df, mkt_data,
    theme=st.session_state.theme,
)
