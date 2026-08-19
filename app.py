import base64
import io
import os
import re
import pandas as pd
import streamlit as st

# 1. SAYFA YAPILANDIRMASI
st.set_page_config(
    page_title="Görükle Acente - Kurye Performans",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. OTURUM DURUMU (Session State)
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Ana Panel"
if "perf_df" not in st.session_state:
    st.session_state.perf_df = None
if "raw_df" not in st.session_state:
    st.session_state.raw_df = None

KULLANICI_ISIM = "Celal ŞENOL"
KULLANICI_GOREV = "Şube Şefi"

# ==========================================
# CSS VE MODERN GÖRSEL BİLEŞEN TASARIMLARI
# ==========================================
custom_css = """
<style>
    .notranslate {
        translate: no !important;
    }
    .stApp {
        background-color: #0B192C !important;
        color: #FFFFFF !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #FFFFFF !important;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    [data-testid="stSidebar"] {
        background-color: #1E3E62 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }
    [data-testid="stSidebar"] div.stButton > button {
        width: 100% !important;
        height: 48px !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        background: linear-gradient(135deg, #00B4D8 0%, #0077B6 100%) !important;
        color: #FFFFFF !important;
        border: 1px solid #90E0EF !important;
        box-shadow: 0 6px 0 #03045E, 0 8px 10px rgba(0, 0, 0, 0.4) !important;
        margin-bottom: 10px !important;
        text-align: left !important;
        padding-left: 15px !important;
    }
    [data-testid="stSidebar"] div.stButton > button:hover {
        background: linear-gradient(135deg, #48CAE4 0%, #00B4D8 100%) !important;
    }
    
    /* "AT Zimmet Raporu Yükle" Alanı Sarı Tasarım */
    [data-testid="stFileUploader"] section {
        background: linear-gradient(135deg, #FFD166 0%, #FFB703) !important;
        border: 2px dashed #FB8500 !important;
        border-radius: 12px !important;
    }
    [data-testid="stFileUploader"] section * {
        color: #000000 !important;
    }
    [data-testid="stFileUploader"] button {
        background: linear-gradient(135deg, #FFB703 0%, #FB8500) !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        box-shadow: 0 4px 0 #9E2A2B, 0 6px 8px rgba(0,0,0,0.3) !important;
    }

    .person-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    .profile-section {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .avatar-circle {
        width: 62px;
        height: 62px;
        border-radius: 50%;
        border: 2px solid #FFB703;
        object-fit: cover;
        background-color: #1E3E62;
    }
    .person-name {
        font-size: 15px;
        font-weight: 700;
        color: #FFFFFF !important;
    }
    .metric-title {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.6) !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .metric-value {
        font-size: 19px;
        font-weight: 700;
    }
    .channel-badge {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 6px;
        padding: 4px 10px;
        font-size: 12px;
        display: inline-block;
        margin-right: 8px;
        margin-top: 8px;
    }
    .badge-val {
        font-weight: 700;
        color: #FFB703 !important;
    }
    
    /* Dashboard Kartları */
    .dashboard-card {
        background: linear-gradient(135deg, #162A45 0%, #0B192C 100%);
        border: 1px solid rgba(255, 183, 3, 0.3);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }
    .stat-label {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.5);
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 4px;
    }
    
    /* İlerleme Çubukları */
    .progress-container {
        background: rgba(255, 255, 255, 0.07);
        border-radius: 8px;
        padding: 12px 15px;
        margin-bottom: 10px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .progress-bar-bg {
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 6px;
        height: 10px;
        width: 100%;
        margin-top: 6px;
        overflow: hidden;
    }
    .progress-bar-fill-orange {
        background: linear-gradient(90deg, #FB8500 0%, #FFB703 100%);
        height: 100%;
        border-radius: 6px;
    }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)


# ==========================================
# İSİM TEMİZLEME VE NORMALİZASYON
# ==========================================
def clean_string(text):
    if pd.isna(text) or not text:
        return ""
    text = str(text).upper().strip()
    replacements = {
        "İ": "I",
        "I": "I",
        "Ş": "S",
        "Ğ": "G",
        "Ü": "U",
        "Ö": "O",
        "Ç": "C",
    }
    for search, replace in replacements.items():
        text = text.replace(search, replace)
    text = re.sub(r"[^A-Z0-9]", "", text)
    return text


def norm_name(val):
    if pd.isna(val) or not val:
        return ""
    val_str = str(val).strip()
    if val_str.upper() in ["NAN", "NONE", "-", ""]:
        return ""
    return " ".join(val_str.upper().split())


# ==========================================
# OTOMATİK KURYE FOTOĞRAFI ALMA
# ==========================================
def get_courier_photo(courier_name):
    clean_courier = clean_string(courier_name)
    search_dirs = []
    if os.path.exists("kuryeler"):
        search_dirs.append("kuryeler")
    search_dirs.append(".")

    for target_dir in search_dirs:
        try:
            files = os.listdir(target_dir)
            for file in files:
                file_path = os.path.join(target_dir, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower().replace(".", "")
                    if ext in ["png", "jpg", "jpeg", "webp"]:
                        file_name_clean = clean_string(os.path.splitext(file)[0])
                        if file_name_clean == clean_courier:
                            try:
                                with open(file_path, "rb") as image_file:
                                    encoded_string = base64.b64encode(image_file.read()).decode()
                                    mime_type = "image/png" if ext == "png" else f"image/{ext}"
                                    return f"data:{mime_type};base64,{encoded_string}"
                            except Exception:
                                pass

            for file in files:
                file_path = os.path.join(target_dir, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower().replace(".", "")
                    if ext in ["png", "jpg", "jpeg", "webp"]:
                        file_name_clean = clean_string(os.path.splitext(file)[0])
                        if (
                            file_name_clean
                            and clean_courier
                            and (
                                file_name_clean in clean_courier
                                or clean_courier in file_name_clean
                            )
                        ):
                            try:
                                with open(file_path, "rb") as image_file:
                                    encoded_string = base64.b64encode(image_file.read()).decode()
                                    mime_type = "image/png" if ext == "png" else f"image/{ext}"
                                    return f"data:{mime_type};base64,{encoded_string}"
                            except Exception:
                                pass
        except Exception:
            continue

    return f"https://ui-avatars.com/api/?name={courier_name.replace(' ', '+')}&background=1E3E62&color=FFB703&bold=true&size=150"


# ==========================================
# AKILLI DOSYA OKUMA MOTORU
# ==========================================
def smart_read_file(uploaded_file):
    file_bytes = uploaded_file.getvalue()
    encodings = ["cp1254", "iso-8859-9", "utf-8-sig", "utf-8", "latin1"]
    separators = [";", ",", "\t", None]

    for enc in encodings:
        for sep in separators:
            try:
                engine_type = "python" if sep is None else None
                df = pd.read_csv(
                    io.BytesIO(file_bytes),
                    sep=sep,
                    encoding=enc,
                    engine=engine_type,
                    on_bad_lines="skip",
                )
                if df is not None and len(df.columns) > 1 and len(df) > 0:
                    return df
            except Exception:
                continue

    try:
        return pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    except Exception:
        pass

    try:
        return pd.read_excel(io.BytesIO(file_bytes), engine="xlrd")
    except Exception:
        pass

    for enc in ["utf-8", "cp1254", "latin1"]:
        try:
            dfs = pd.read_html(io.BytesIO(file_bytes), encoding=enc)
            if dfs and len(dfs) > 0:
                return dfs[0]
        except Exception:
            continue

    raise Exception(
        "Dosya yapısı çözümlenemedi. Lütfen dosyanın bozuk olmadığını kontrol edin."
    )


# ==========================================
# AT ZİMMET İZLEME TAM UYUMLU İŞLEME MOTORU
# ==========================================
def process_excel_data(df):
    df.columns = df.columns.astype(str).str.strip()
    req_cols = ["AT Zimmet Personel Adı", "Teslim Eden Personel"]
    missing_cols = [col for col in req_cols if col not in df.columns]

    if missing_cols:
        return None, missing_cols

    valid_df = df[
        df["AT Zimmet Personel Adı"].notna()
        & (df["AT Zimmet Personel Adı"].astype(str).str.strip() != "")
        & (
            df["AT Zimmet Personel Adı"].astype(str).str.strip().str.upper()
            != "NAN"
        )
        & (
            df["AT Zimmet Personel Adı"].astype(str).str.strip().str.upper()
            != "NONE"
        )
    ].copy()

    valid_df["Norm_Zimmet"] = valid_df["AT Zimmet Personel Adı"].apply(norm_name)
    valid_df["Norm_Teslim"] = valid_df["Teslim Eden Personel"].apply(norm_name)

    has_kanali = "Kargo Teslimat Kanalı" in valid_df.columns
    has_aciklama = "Açıklama" in valid_df.columns

    def evaluate_row(row):
        z = row["Norm_Zimmet"]
        t = row["Norm_Teslim"]

        if t == "" or t != z:
            return "DEVİR", ""

        kanali = str(row["Kargo Teslimat Kanalı"]).strip().upper() if has_kanali else ""
        aciklama = str(row["Açıklama"]).strip().upper() if has_aciklama else ""

        if "İMZA" in kanali or "IMZA" in kanali:
            return "TESLİM", "İMZA"
        elif "SMS" in kanali:
            return "TESLİM", "SMS"
        elif "KAPIYA BIRAKILDI" in kanali or "KAPIYA" in kanali:
            return "TESLİM", "KS"
        elif (
            kanali == "" or kanali == "NAN" or kanali == "-"
        ) and "POS ENTEGRASYON" in aciklama:
            return "TESLİM", "KS-PE"

        return "TESLİM", "DİĞER"

    results = valid_df.apply(evaluate_row, axis=1)
    valid_df["Durum"] = [r[0] for r in results]
    valid_df["Kanal"] = [r[1] for r in results]

    personnel_groups = valid_df.groupby("Norm_Zimmet")

    summary = []
    for norm_p, p_df in personnel_groups:
        p_name = (
            p_df["AT Zimmet Personel Adı"].mode()[0]
            if not p_df["AT Zimmet Personel Adı"].mode().empty
            else norm_p
        )
        p_name = " ".join(str(p_name).split())

        zimmet_cnt = len(p_df)
        devir_df = p_df[p_df["Durum"] == "DEVİR"]
        teslim_edilemeyen_cnt = len(devir_df)
        teslim_df = p_df[p_df["Durum"] == "TESLİM"]
        teslim_cnt = len(teslim_df)

        success_rate = (
            round((teslim_cnt / zimmet_cnt) * 100, 1) if zimmet_cnt > 0 else 0.0
        )

        imza_cnt = len(teslim_df[teslim_df["Kanal"] == "İMZA"])
        sms_cnt = len(teslim_df[teslim_df["Kanal"] == "SMS"])
        ks_cnt = len(teslim_df[teslim_df["Kanal"] == "KS"])
        ks_pe_cnt = len(teslim_df[teslim_df["Kanal"] == "KS-PE"])

        summary.append({
            "Personel": p_name,
            "Zimmet": zimmet_cnt,
            "Teslim Edilen": teslim_cnt,
            "Teslim Edilemeyen": teslim_edilemeyen_cnt,
            "Başarı Oranı": success_rate,
            "İMZA": imza_cnt,
            "SMS": sms_cnt,
            "KS": ks_cnt,
            "KS-PE": ks_pe_cnt,
        })

    res_df = pd.DataFrame(summary)
    if not res_df.empty:
        res_df.index = range(1, len(res_df) + 1)

    return res_df, None


# ==========================================
# SIDEBAR VE GEZİNTİ MENÜSÜ
# ==========================================
with st.sidebar:
    st.markdown(
        """
    <div class="notranslate" style="text-align: center; padding-bottom: 10px;">
        <h2 style="margin: 0; color: #FFFFFF;">Yurtiçi Kargo</h2>
        <h4 style="margin: 0; color: #00B4D8;">Görükle Acente KOYS</h4>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "<hr style='border: 1px solid rgba(255,255,255,0.1);'>",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
    <div class="notranslate" style="background: linear-gradient(135deg, #FF7B00 0%, #FF5400 100%); border-radius: 12px; padding: 12px; margin-bottom: 15px; border: 1px solid #FFA200; box-shadow: 0 4px 8px rgba(255,123,0,0.3);">
        <small style="color: #FFFFFF; font-weight: 600;">Aktif Kullanıcı:</small><br>
        <strong style="color: #FFFFFF; font-size: 15px;">{KULLANICI_ISIM}</strong><br>
        <span style="color: #FFFFFF; font-size: 13px; font-weight: bold;">({KULLANICI_GOREV})</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "📂 AT Zimmet Raporu Yükle", type=["csv", "xlsx", "xls", "html"]
    )

    st.markdown(
        "<hr style='border: 1px solid rgba(255,255,255,0.1);'>",
        unsafe_allow_html=True,
    )

    if st.button("📊 Ana Panel"):
        st.session_state.active_tab = "Ana Panel"
    if st.button("🏃‍♂️ Kurye Performans"):
        st.session_state.active_tab = "Kurye Performans"

# ==========================================
# AKILLI VERİ YÖNETİMİ
# ==========================================
if uploaded_file is not None:
    try:
        raw_df = smart_read_file(uploaded_file)
        st.session_state.raw_df = raw_df

        perf_res, err = process_excel_data(raw_df)
        if err:
            st.error(f"❌ Eksik Sütunlar: {err}")
        else:
            st.session_state.perf_df = perf_res
    except Exception as e:
        st.error(f"❌ Dosya Okuma/İşleme Hatası: {e}")

# ==========================================
# TAB 1: ANA PANEL
# ==========================================
if st.session_state.active_tab == "Ana Panel":
    st.title("📊 Görükle Acente - Genel Performans Özeti")

    perf_df = st.session_state.perf_df
    if perf_df is not None and not perf_df.empty:
        total_zimmet = perf_df["Zimmet"].sum()
        total_teslim = perf_df["Teslim Edilen"].sum()
        total_devir = perf_df["Teslim Edilemeyen"].sum()
        avg_rate = (
            round((total_teslim / total_zimmet) * 100, 1) if total_zimmet > 0 else 0
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📦 Toplam Zimmet", f"{total_zimmet:,}")
        c2.metric("✅ Teslim Edilen", f"{total_teslim:,}")
        c3.metric("🚨 Devir / Teslim Edilemeyen", f"{total_devir:,}")
        c4.metric("🎯 Genel Başarı Oranı", f"%{avg_rate}")

        st.markdown("---")

        # ----------------------------------------------------
        # 1. KART: Kurye Başarı Oranları (Fotoğraf ve Değerler Daha Büyük)
        # ----------------------------------------------------
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown(
            "<h3 style='color: #FFB703 !important; margin-bottom: 20px;'>📊 Kurye Başarı Oranları (%)</h3>",
            unsafe_allow_html=True,
        )

        c_sol, c_sag = st.columns([1, 2])
        with c_sol:
            max_p = (
                perf_df.loc[perf_df["Başarı Oranı"].idxmax()]
                if not perf_df.empty
                else None
            )
            max_name = max_p["Personel"] if max_p is not None else "-"
            max_val = max_p["Başarı Oranı"] if max_p is not None else 0
            
            max_avatar_url = get_courier_photo(max_name) if max_p is not None else ""

            st.markdown(
                f"""
                <div style="padding: 5px 0;" class="notranslate">
                    <div class="stat-label">En Başarılı Kurye</div>
                    <div style="display: flex; align-items: center; gap: 20px; margin-top: 12px; margin-bottom: 18px;">
                        <img src="{max_avatar_url}" style="width: 110px; height: 110px; border-radius: 50%; border: 4px solid #FFB703; object-fit: cover; background-color: #1E3E62;">
                        <div>
                            <div style="font-size: 24px; font-weight: bold; color: #FFFFFF; line-height: 1.3;">{max_name}</div>
                            <div style="font-size: 38px; font-weight: 800; color: #FFB703; margin-top: 6px;">%{max_val}</div>
                        </div>
                    </div>
                    <div class="stat-label" style="margin-top: 15px;">Toplam Aktif Kurye</div>
                    <div style="font-size: 18px; font-weight: 700; color: #00B4D8; margin-top: 2px;">{len(perf_df)} Kişi</div>
                </div>
            """,
                unsafe_allow_html=True,
            )

        with c_sag:
            bars_html = ""
            for _, r in perf_df.iterrows():
                p_adi = r["Personel"]
                p_oran = r["Başarı Oranı"]
                bars_html += f"""
                    <div class="progress-container notranslate">
                        <div style="display: flex; justify-content: space-between; font-size: 13px; font-weight: 600;">
                            <span>{p_adi}</span>
                            <span style="color: #FFB703;">%{p_oran}</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill-orange" style="width: {min(p_oran, 100)}%;"></div>
                        </div>
                    </div>
                    """
            st.markdown(bars_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ----------------------------------------------------
        # 2. KART: Teslimat Kanalları Dağılımı
        # ----------------------------------------------------
        st.markdown('<div class="dashboard-card">', unsafe_allow_html=True)
        st.markdown(
            "<h3 style='color: #FFB703 !important; margin-bottom: 20px;'>📲 Teslimat Kanalları Dağılımı</h3>",
            unsafe_allow_html=True,
        )

        chan_sol, chan_sag = st.columns([1, 2])
        imza_t = perf_df["İMZA"].sum()
        sms_t = perf_df["SMS"].sum()
        ks_t = perf_df["KS"].sum()
        kspe_t = perf_df["KS-PE"].sum()
        toplam_kanal = imza_t + sms_t + ks_t + kspe_t

        imza_oran = (
            round((imza_t / toplam_kanal) * 100, 1) if toplam_kanal > 0 else 0
        )
        sms_oran = (
            round((sms_t / toplam_kanal) * 100, 1) if toplam_kanal > 0 else 0
        )
        ks_oran = round((ks_t / toplam_kanal) * 100, 1) if toplam_kanal > 0 else 0
        kspe_oran = (
            round((kspe_t / toplam_kanal) * 100, 1) if toplam_kanal > 0 else 0
        )

        p1 = imza_oran
        p2 = p1 + sms_oran
        p3 = p2 + ks_oran

        with chan_sol:
            st.markdown(
                '<div class="stat-label">En Çok Tercih Edilen</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="font-size: 18px; font-weight: bold; color: #FF6B6B; margin-bottom: 2px;">İMZA</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div style="font-size: 13px; color: rgba(255,255,255,0.7); margin-bottom: 12px;">Yüzde: %{imza_oran}</div>',
                unsafe_allow_html=True,
            )

            st.metric(label="TOPLAM İŞLEM ADEDİ", value=f"{toplam_kanal:,} Adet")

        with chan_sag:
            donut_html = f"""
            <div style="display: flex; align-items: center; justify-content: center; gap: 30px; flex-wrap: wrap;">
                <div style="position: relative; width: 150px; height: 150px;">
                    <svg width="150" height="150" viewBox="0 0 42 42" style="transform: rotate(-90deg);">
                        <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="rgba(255,255,255,0.1)" stroke-width="5"></circle>
                        <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#FF6B6B" stroke-width="5" 
                                    stroke-dasharray="{p1} {100 - p1}" stroke-dashoffset="0"></circle>
                        <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#4EA8DE" stroke-width="5" 
                                    stroke-dasharray="{sms_oran} {100 - sms_oran}" stroke-dashoffset="-{p1}"></circle>
                        <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#FFB703" stroke-width="5" 
                                    stroke-dasharray="{ks_oran} {100 - ks_oran}" stroke-dashoffset="-{p2}"></circle>
                        <circle cx="21" cy="21" r="15.91549430918954" fill="transparent" stroke="#4CAF50" stroke-width="5" 
                                    stroke-dasharray="{kspe_oran} {100 - kspe_oran}" stroke-dashoffset="-{p3}"></circle>
                    </svg>
                    <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center;">
                        <span style="font-size: 12px; color: rgba(255,255,255,0.5); display: block;">Kanal</span>
                        <strong style="font-size: 14px; color: #FFFFFF;">Dağılımı</strong>
                    </div>
                </div>
                <div style="flex-grow: 1; min-width: 180px;">
                    <div style="margin-bottom: 6px; font-size: 13px;"><span style="display:inline-block; width:10px; height:10px; background:#FF6B6B; border-radius:50%; margin-right:6px;"></span> <b>İMZA:</b> %{imza_oran} ({imza_t})</div>
                    <div style="margin-bottom: 6px; font-size: 13px;"><span style="display:inline-block; width:10px; height:10px; background:#4EA8DE; border-radius:50%; margin-right:6px;"></span> <b>SMS:</b> %{sms_oran} ({sms_t})</div>
                    <div style="margin-bottom: 6px; font-size: 13px;"><span style="display:inline-block; width:10px; height:10px; background:#FFB703; border-radius:50%; margin-right:6px;"></span> <b>KS:</b> %{ks_oran} ({ks_t})</div>
                    <div style="font-size: 13px;"><span style="display:inline-block; width:10px; height:10px; background:#4CAF50; border-radius:50%; margin-right:6px;"></span> <b>KS-PE:</b> %{kspe_oran} ({kspe_t})</div>
                </div>
            </div>
            """
            st.markdown(donut_html, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.subheader("📋 Genel Performans Tablosu")
        st.dataframe(perf_df, use_container_width=True)

    else:
        st.info(
            "💡 Sol menüden **AT ZİMMET İZLEME** dosyanızı yükleyerek ana paneli görüntüleyebilirsiniz."
        )

# ==========================================
# TAB 2: KURYE PERFORMANS PANELİ
# ==========================================
elif st.session_state.active_tab == "Kurye Performans":
    st.title("🏃‍♂️ Kurye Performans Paneli")

    perf_df = st.session_state.perf_df
    if perf_df is not None and not perf_df.empty:
        st.success(
            f"✅ AT ZİMMET İZLEME raporu aktif. Toplam **{len(perf_df)}** kurye bulundu."
        )

        all_personnel = ["Tümü"] + sorted(
            perf_df["Personel"].dropna().unique().tolist()
        )
        selected_personnel = st.selectbox(
            "🔍 Personel Seçerek Süzgeçle:", all_personnel
        )

        if selected_personnel != "Tümü":
            filtered_perf_df = perf_df[perf_df["Personel"] == selected_personnel]
        else:
            filtered_perf_df = perf_df

        for idx, row in filtered_perf_df.iterrows():
            p_name = row["Personel"]
            zimmet = row["Zimmet"]
            teslim = row["Teslim Edilen"]
            devir = row["Teslim Edilemeyen"]
            rate = row["Başarı Oranı"]
            imza = row["İMZA"]
            sms = row["SMS"]
            ks = row["KS"]
            ks_pe = row["KS-PE"]

            avatar_url = get_courier_photo(p_name)

            card_html = f"""
            <div class="person-card notranslate">
                <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 15px;">
                    <div class="profile-section" style="min-width: 220px;">
                        <img src="{avatar_url}" class="avatar-circle">
                        <div>
                            <div class="person-name">{p_name}</div>
                            <small style="color: #FFB703;">Saha Kuryesi</small>
                        </div>
                    </div>
                    <div style="text-align: center;">
                        <div class="metric-title">Zimmet Sayısı</div>
                        <div class="metric-value" style="color: #FFFFFF;">{zimmet}</div>
                    </div>
                    <div style="text-align: center;">
                        <div class="metric-title">Teslim Edilen</div>
                        <div class="metric-value" style="color: #4CAF50;">{teslim}</div>
                    </div>
                    <div style="text-align: center;">
                        <div class="metric-title">Teslim Edilemeyen</div>
                        <div class="metric-value" style="color: #F44336;">{devir}</div>
                    </div>
                    <div style="text-align: center; min-width: 80px;">
                        <div class="metric-title">Başarı Oranı</div>
                        <div class="metric-value" style="color: #FFB703;">%{rate}</div>
                    </div>
                </div>
                <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.06);">
                    <div class="channel-badge">✍️ İMZA: <span class="badge-val">{imza}</span></div>
                    <div class="channel-badge">📲 SMS: <span class="badge-val">{sms}</span></div>
                    <div class="channel-badge">🚪 KS: <span class="badge-val">{ks}</span></div>
                    <div class="channel-badge">💳 KS-PE: <span class="badge-val">{ks_pe}</span></div>
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

    else:
        st.warning(
            "⚠️ Kurye performans kartlarını görmek için sol menüden **AT ZİMMET İZLEME** dosyasını yükleyin."
        )
