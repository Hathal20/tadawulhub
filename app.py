# app.py
# This is the main backend file. It uses Flask to define API endpoints.
# The frontend will call these endpoints to get data.
# We also enable CORS so the frontend (running on a different port) can access it.



from flask import Flask, render_template, jsonify, request, redirect, url_for, flash
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import numpy as np
import smtplib
from email.mime.text import MIMEText
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from flask_compress import Compress

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


compress = Compress()
compress.init_app(app)

# Add this:
with app.app_context():
    db.create_all()

class User(db.Model):
    id    = db.Column(db.Integer, primary_key=True)
    name  = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

import logging

# tell Flask’s logger to show DEBUG messages
app.logger.setLevel(logging.DEBUG)

app.secret_key = 'H8563athaL4$H8563athaL4$'  # Needed for flash messages in signup form

# Base symbols
symbols_path = os.path.join(os.path.dirname(__file__), 'symbols.txt')
with open(symbols_path, 'r') as f:
    base_symbols = [line.strip() for line in f if line.strip()]

# S&P 500 symbols
sp500_url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
sp_res = requests.get(sp500_url)
sp_soup = BeautifulSoup(sp_res.text, 'lxml')
sp500_table = sp_soup.find('table', {'id': 'constituents'})
sp500_symbols = []
if sp500_table:
    rows = sp500_table.find_all('tr')[1:]
    for row in rows:
        cols = row.find_all('td')
        if len(cols) > 1:
            symbol = cols[0].text.strip()
            name = cols[1].text.strip()
            sp500_symbols.append((symbol, name))


# Tadawul stocks by sector (code and name, no .SR shown here)
# Format: sector: [(name, code), ...]
# ----------------------------------------
# Tadawul stocks by sector (code and name, no .SR shown here)
tadawul_sectors = {
    "مؤشر السوق السعودي - تاسي": [("TASI Tadawul", "^TASI"),],
    "الطاقة": [
        ("المصافي", "2030"),
        ("ارامكو السعودية", "2222"),
        ("بترورابغ", "2380"),
        ("الحفر العربية", "2381"),
        ("أديس", "2382"),
        ("بحري", "4030"),
        ("الدريس", "4200"),
    ],
    "المواد الأساسية": [
        ("تكوين", "1201"), ("مبكو", "1202"), ("بي سي آي", "1210"), ("معادن", "1211"),
        ("أسلاك", "1301"), ("اليمامةللحديد", "1304"), ("أنابيب السعودية", "1320"), ("أنابيب الشرق", "1321"),
        ("أماك", "1322"), ("كيمانول", "2001"), ("سابك", "2010"), ("سابك للمغذيات الزراعية", "2020"),
        ("التصنيع", "2060"), ("جبسكو", "2090"), ("زجاج", "2150"), ("اللجين", "2170"),
        ("فيبكو", "2180"), ("أنابيب", "2200"), ("نماء للكيماويات", "2210"), ("معدنية", "2220"),
        ("لوبريف", "2223"), ("الزامل للصناعة", "2240"), ("المجموعة السعودية", "2250"), ("ينساب", "2290"),
        ("صناعة الورق", "2300"), ("سبكيم", "2310"), ("المتقدمة", "2330"), ("كيان السعودية", "2350"),
        ("لفخارية", "2360"), ("أسمنت نجران", "3002"), ("أسمنت المدينة", "3003"), ("أسمنت الشمالية", "3004"),
        ("أسمنت أم القرى", "3005"), ("الواحة", "3007"), ("الكثيري", "3008"), ("أسمنت العربية", "3010"),
        ("أسمنت اليمامة", "3020"), ("أسمنت السعودية", "3030"), ("أسمنت القصيم", "3040"), ("أسمنت الجنوب", "3050"),
        ("أسمنت ينبع", "3060"), ("أسمنت الشرقية", "3080"), ("أسمنت تبوك", "3090"), ("أسمنت الجوف", "3091"),
        ("أسمنت الرياض", "3092")
    ],
    "السلع الرأسمالية": [
        ("استرا الصناعية", "1212"), ("شاكر", "1214"), ("بوان", "1302"), ("صناعات كهربائية", "1303"),
        ("الخزف السعودي", "2040"), ("لكابلات السعودية", "2110"), ("أميانتيت", "2160"),
        ("البابطين", "2320"), ("مسك", "2370"), ("باتك", "4110"), ("سيكو", "4140"),
        ("العمران", "4141"), ("كابلات الرياض", "4142"), ("تالكو", "4143")
    ],
    "الخدمات التجارية والمهنية": [
        ("شركة مهارة للموارد البشرية", "1831"), ("شركة صدر للخدمات اللوجستية", "1832"),
        ("شركة الموارد للقوى البشرية", "1833"), ("الشركة السعودية لحلول القوى البشرية", "1834"),
        ("شركة تمكين للموارد البشرية", "1835"), ("الشركة السعودية للطباعة والتغليف", "4270"),
        ("شركة كاتريون للتموين القابضة", "6004")
    ],
    "النقل": [
        ("شركة البنى التحتية المستدامة القابضة", "2190"), ("الشركة السعودية للخدمات الأرضية", "4031"),
        ("الشركة السعودية للنقل الجماعي", "4040"), ("الشركة المتحدة الدولية للمواصلات", "4260"),
        ("شركة ذيب لتأجير السيارات", "4261"), ("شركة لومي للتأجير", "4262"),
        ("شركة سال السعودية للخدمات اللوجستية", "4263")
    ],
    "السلع طويلة الاجل": [
        ("شركة نسيج العالمية التجارية", "1213"), ("الشركة السعودية للتنمية الصناعية", "2130"),
        ("شركة ارتيكس للاستثمار الصناعي", "2340"), ("شركة لازوردي للمجوهرات", "4011"),
        ("شركة ثوب الأصيل", "4012"), ("مجموعة فتيحي القابضة", "4180")
    ],
    "الخدمات الإستهلاكية": [
        ("مجموعة سيرا القابضة", "1810"), ("شركة مجموعة بان القابضة", "1820"), ("شركة لجام للرياضة", "1830"),
        ("شركة المشروعات السياحية", "4170"),
        ("شركة الخليج للتدريب والتعليم", "4290"), ("الشركة الوطنية للتربية و التعليم", "4291"),
        ("شركة عطاء التعليمية", "4292"),
        ("شركة هرفي للخدمات الغذائية", "6002"), ("شركة ريدان الغذائية", "6012"),
        ("شركة الأعمال التطويرية الغذائية", "6013"),
        ("شركة الآمار الغذائية", "6014"), ("شركة أمريكانا للمطاعم العالمية بي إل سي - شركة أجنبية", "6015"),
        ("شركة مطاعم بيت الشطيرة للوجبات السريعة", "6016")
    ],
    "الإعلام والترفيه": [
        ("شركة تهامة للإعلان والعلاقات العامة", "4070"), ("الشركة العربية للتعهدات الفنية", "4071"),
        ("شركة مجموعة إم بي سي", "4072"), ("المجموعة السعودية للأبحاث والإعلام", "4210")
    ],
    "تجزئة وتوزيع السلع الكمالية": [
        ("الشركة المتحدة للإلكترونيات", "4003"), ("الشركة السعودية للعدد والأدوات", "4008"),
        ("الشركة السعودية لخدمات السيارات والمعدات", "4050"), ("شركة باعظيم التجارية", "4051"),
        ("شركة جرير للتسويق", "4190"), ("شركة عبد الله سعد محمد أبو معطي للمكتبات", "4191"),
        ("شركة متاجر السيف للتنمية والاستثمار", "4192"), ("شركة فواز عبدالعزيز الحكير وشركاه", "4240")
    ],
    "تجزئة وتوزيع السلع الاستهلاكية": [
        ("شركة أسواق عبدالله العثيم", "4001"), ("الشركة السعودية للتسويق", "4006"),
        ("مجموعة أنعام الدولية القابضة", "4061"),
        ("شركة ثمار التنمية القابضة", "4160"), ("شركة بن داود القابضة", "4161"), ("شركة المنجم للأغذية", "4162"),
        ("شركة الدواء للخدمات الطبية", "4163"), ("شركة النهدي الطبية", "4164")
    ],
    "إنتاج الأغذية": [
        ("مجموعة صافولا", "2050"), ("شركة وفرة للصناعة والتنمية", "2100"),
        ("الشركة السعودية لمنتجات الألبان والأغذية", "2270"), ("شركة المراعي", "2280"),
        ("شركة التنمية الغذائية", "2281"), ("شركة نقي للمياه", "2282"), ("شركة المطاحن الأولى", "2283"),
        ("شركة المطاحن الحديثة للمنتجات الغذائية", "2284"), ("شركة المطاحن العربية للمنتجات الغذائية", "2285"),
        ("شركة المطاحن الرابعة", "2286"),
        ("شركة سناد القابضة", "4080"), ("شركة حلواني إخوان", "6001"), ("الشركة الوطنية للتنمية الزراعية", "6010"),
        ("شركة القصيم القابضة للاستثمار", "6020"),
        ("شركة تبوك للتنمية الزراعية", "6040"), ("الشركة السعودية للأسماك", "6050"), ("شركة الشرقية للتنمية", "6060"),
        ("شركة الجوف الزراعية", "6070"),
        ("شركة جازان للتنمية والاستثمار", "6090")
    ],
    "المنتجات المنزلية و الشخصية": [
        ("شركة الماجد للعود", "4165")
    ],
    "الرعاية الصحية": [
        ("شركة أيان للإستثمار", "2140"), ("الشركة الكيميائية السعودية القابضة", "2230"),
        ("شركة المواساة للخدمات الطبية", "4002"), ("شركة دله للخدمات الصحية", "4004"),
        ("الشركة الوطنية للرعاية الطبية", "4005"), ("شركة الحمادي القابضة", "4007"),
        ("شركة الشرق الأوسط للرعاية الصحية", "4009"),
        ("مجموعة الدكتور سليمان الحبيب للخدمات الطبية", "4013"), ("شركة دار المعدات الطبية والعلمية", "4014"),
        ("شركة مستشفى الدكتور سليمان عبدالقادر فقيه", "4017")
    ],
    "الادوية": [
        ("الشركة السعودية للصناعات الدوائية والمستلزمات الطبية", "2070"), ("شركة مصنع جمجوم للأدوية", "4015"),
        ("شركة الشرق الأوسط للصناعات الدوائية", "4016")
    ],
    "البنوك": [
        ("بنك الرياض", "1010"), ("بنك الجزيرة", "1020"), ("البنك السعودي للإستثمار", "1030"),
        ("البنك السعودي الفرنسي", "1050"),
        ("البنك السعودي الأول", "1060"), ("البنك العربي الوطني", "1080"), ("مصرف الراجحي", "1120"),
        ("بنك البلاد", "1140"),
        ("مصرف الإنماء", "1150"), ("البنك الأهلي السعودي", "1180")
    ],
    "الخدمات الماليه": [
        ("شركة مجموعة تداول السعودية القابضة", "1111"), ("شركة أملاك العالمية للتمويل", "1182"),
        ("شركة سهل للتمويل", "1183"), ("الشركة السعودية للصناعات المتطورة", "2120"),
        ("شركة النايفات للتمويل", "4081"), ("شركة المرابحة المرنة للتمويل", "4082"),
        ("الشركة المتحدة الدولية القابضة", "4083"), ("شركة الباحة للإستثمار والتنمية", "4130"),
        ("شركة المملكة القابضة", "4280")
    ],
    "التأمين": [
        ("الشركة التعاونية للتأمين", "8010"), ("شركة الجزيرة تكافل تعاوني", "8012"),
        ("شركة ملاذ للتأمين التعاوني", "8020"),
        ("شركة المتوسط والخليج للتأمين وإعادة التأمين التعاوني", "8030"), ("شركة متكاملة للتأمين", "8040"),
        ("شركة سلامة للتأمين التعاوني", "8050"), ("شركة ولاء للتأمين التعاوني", "8060"),
        ("شركة الدرع العربي للتأمين التعاوني", "8070"), ("الشركة العربية السعودية للتأمين التعاوني", "8100"),
        ("شركة إتحاد الخليج الأهلية للتأمين التعاوني", "8120"),
        ("المجموعة المتحدة للتأمين التعاوني", "8150"), ("شركة التأمين العربية التعاونية", "8160"),
        ("شركة الاتحاد للتأمين التعاوني", "8170"), ("شركة الصقر للتأمين التعاوني", "8180"),
        ("الشركة المتحدة للتأمين التعاوني", "8190"), ("الشركة السعودية لإعادة التأمين", "8200"),
        ("شركة بوبا العربية للتأمين التعاوني", "8210"), ("شركة الراجحي للتأمين التعاوني", "8230"),
        ("شركة تْشب العربية للتأمين التعاوني", "8240"), ("مجموعة الخليج للتأمين", "8250"),
        ("الشركة الخليجية العامة للتأمين التعاوني", "8260"), ("شركة بروج للتأمين التعاوني", "8270"),
        ("شركة ليفا للتأمين", "8280"), ("الشركة الوطنية للتأمين", "8300"), ("شركة أمانة للتأمين التعاوني", "8310"),
        ("شركة عناية السعودية للتأمين التعاوني", "8311"),
        ("شركة رسن لتقنية المعلومات", "8313")
    ],
    "التطبيقات وخدمات التقنية": [
        ("شركة المعمر لأنظمة المعلومات", "7200"), ("شركة بحر العرب لأنظمة المعلومات", "7201"),
        ("الشركة العربية لخدمات الإنترنت والاتصالات", "7202"), ("شركة علم", "7203"),
        ("شركة العرض المتقن للخدمات التجارية", "7204")
    ],
    "الإتصالات": [
        ("شركة الإتصالات السعودية", "7010"), ("شركة إتحاد إتصالات", "7020"),
        ("شركة الإتصالات المتنقلة السعودية", "7030"), ("شركة إتحاد عذيب للإتصالات", "7040")
    ],
    "المرافق العامة": [
        ("شركة الغاز والتصنيع الأهلية", "2080"), ("شركة الخريف لتقنية المياه والطاقة", "2081"),
        ("شركة أكوا باور", "2082"), ("شركة مرافق الكهرباء والمياه بالجبيل وينبع", "2083"),
        ("شركة مياهنا", "2084"), ("الشركة السعودية للكهرباء", "5110")
    ],
    "الصناديق العقارية المتداولة": [
        ("صندوق الرياض ريت", "4330"), ("صندوق الجزيرة ريت", "4331"), ("صندوق جدوى ريت الحرمين", "4332"),
        ("صندوق تعليم ريت", "4333"), ("صندوق المعذر ريت", "4334"), ("صندوق مشاركة ريت", "4335"),
        ("صندوق ملكية عقارات الخليج ريت", "4336"), ("صندوق سيكو السعودية ريت", "4337"), ("صندوق الأهلي ريت 1", "4338"),
        ("صندوق دراية ريت", "4339"), ("صندوق الراجحي ريت", "4340"), ("صندوق جدوى ريت السعودية", "4342"),
        ("صندوق سدكو كابيتال ريت", "4344"), ("صندوق الإنماء ريت لقطاع التجزئة", "4345"), ("صندوق ميفك ريت", "4346"),
        ("صندوق بنيان ريت", "4347"), ("صندوق الخبير ريت", "4348"), ("صندوق الإنماء ريت الفندقي", "4349"),
        ("صندوق الإستثمار اريك ريت المتنوع", "4350")
    ],
    "إدارة وتطوير العقارات": [
        ("الشركة العقارية السعودية", "4020"), ("شركة طيبة للإستثمار", "4090"), ("شركة مكة للإنشاء والتعمير", "4100"),
        ("شركة الرياض للتعمير", "4150"),
        ("إعمار المدينة الإقتصادية", "4220"), ("شركة البحر الأحمر العالمية", "4230"), ("شركة جبل عمر للتطوير", "4250"),
        ("شركة دار الأركان للتطوير العقاري", "4300"),
        ("مدينة المعرفة الإقتصادية", "4310"), ("شركة الأندلس العقارية", "4320"), ("شركة المراكز العربية", "4321"),
        ("شركة رتال للتطوير العمراني", "4322"),
        ("شركة سمو العقارية", "4323")
    ],
}

# Add missing sectors from previous code snippet (just copy all sectors you had in full):
# Make sure all the sectors with their stocks are included here as before.


# Combine all symbols
all_symbols = {'^TASI.SR': "مؤشر السوق الرئيسي تداول (TASI)"}
for sym in base_symbols:
    all_symbols[sym.upper()] = sym.upper()
for sym, name in sp500_symbols:
    all_symbols[sym.upper()] = name
for sector, stocks in tadawul_sectors.items():
    for (name, code) in stocks:
        all_symbols[code + '.SR'] = name

def fetch_tadawul_data(ticker, interval, n_bars=5000):
    # Placeholder for Tadawul data
    return pd.DataFrame([])


# ── Replace *only* fetch_yahoo_data with this version ─────────
def fetch_yahoo_data(ticker, interval,
                     ema_period=20, rsi_period=14,
                     include_ema=True, include_rsi=True,
                     include_sma50=False, include_sma200=False,
                     include_macd=False, include_stoch=False,
                     include_volume=False, include_bbands=False,
                     include_vwap=False):
    """
    Download OHLCV and calculate requested indicators.
    """
    end_date = datetime.now()
    if interval in ['1m', '5m']:
        start_date = end_date - timedelta(days=7)
    elif interval in ['15m', '60m']:
        start_date = end_date - timedelta(days=60)
    else:
        start_date = end_date - timedelta(days=365 * (10 if ticker.endswith('.SR') else 5))

    data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.droplevel(1)
    if data.empty:
        return {k: [] for k in ('candlestick','ema','sma50','sma200','rsi','macd',
                                'stochrsi','volume','bbands','vwap')}

    # Indicators
    if include_ema:    data['EMA']   = ta.ema(data['Close'], length=ema_period)
    if include_sma50:  data['SMA50'] = ta.sma(data['Close'], length=50)
    if include_sma200: data['SMA200']= ta.sma(data['Close'], length=200)
    if include_rsi:    data['RSI']   = ta.rsi(data['Close'], length=rsi_period)
    if include_macd:
        macd = ta.macd(data['Close'])
        data['MACD'] = macd['MACD_12_26_9']
    if include_stoch:
        stoch = ta.stochrsi(data['Close'])
        data['STOCH'] = stoch['STOCHRSIk_14_14_3_3']
    if include_bbands:
        bb = ta.bbands(data['Close'], length=20, std=2)
        data['BBU'], data['BBL'] = bb['BBU_20_2.0'], bb['BBL_20_2.0']
    if include_vwap:
        data['VWAP'] = ta.vwap(high=data['High'], low=data['Low'],
                               close=data['Close'], volume=data['Volume'])

    # Build payload
    def ts(row): return int(row.Index.timestamp())
    payload = {
        'candlestick':[{'time':ts(r),'open':r.Open,'high':r.High,'low':r.Low,'close':r.Close}
                       for r in data.itertuples()],
        'ema'     :[{'time':ts(r),'value':r.EMA   } for r in data.itertuples() if include_ema   and pd.notna(r.EMA)],
        'sma50'   :[{'time':ts(r),'value':r.SMA50 } for r in data.itertuples() if include_sma50 and pd.notna(r.SMA50)],
        'sma200'  :[{'time':ts(r),'value':r.SMA200} for r in data.itertuples() if include_sma200 and pd.notna(r.SMA200)],
        'rsi'     :[{'time':ts(r),'value':r.RSI   } for r in data.itertuples() if include_rsi   and pd.notna(r.RSI)],
        'macd'    :[{'time':ts(r),'value':r.MACD  } for r in data.itertuples() if include_macd  and pd.notna(r.MACD)],
        'stochrsi':[{'time':ts(r),'value':r.STOCH } for r in data.itertuples() if include_stoch and pd.notna(r.STOCH)],
        'volume'  :[{'time':ts(r),'value':int(r.Volume)} for r in data.itertuples() if include_volume],
        'bbands'  :[{'time':ts(r),'upper':r.BBU,'lower':r.BBL}
                     for r in data.itertuples() if include_bbands and pd.notna(r.BBU) and pd.notna(r.BBL)],
        'vwap'    :[{'time':ts(r),'value':r.VWAP  } for r in data.itertuples() if include_vwap  and pd.notna(r.VWAP)],
    }
    return payload

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/watchlist')
def watchlist_page():
    return render_template('watchlist.html')

@app.route('/about')
def about_page():
    return render_template('about.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('الأسم')
        email = request.form.get('الايميل')
        if not name or not email:
            flash("الرجاء إضافة الاسم والبريد الإلكتروني.")
            return redirect(url_for('signup'))

        # Save to database
        new_user = User(name=name, email=email)
        db.session.add(new_user)
        db.session.commit()

        flash("تم التسجيل بنجاح! سيتم تحويلك إلى الصفحة الرئيسية...")
        return redirect(url_for('signup'))

    return render_template('signup.html')


# @app.route('/users')
# def users():
#    all_users = User.query.all()  # Fetch all users from the database
#    return render_template('users.html', users=all_users)


def send_welcome_email(email, name):
    # NOTE: This is a demo function. Replace with real SMTP credentials.
    # For demonstration, we will just print the email to console.
    # If you want to test actual sending, configure SMTP server.
    subject = "Welcome to TadawulHub"
    body = f"Hello {name},\n\nWelcome to TadawulHub!\nEnjoy exploring the platform.\n\nRegards,\nTadawulHub Team"
    print(f"Sending email to {email} with subject '{subject}' and body:\n{body}")
    # In production, you'd use smtplib or a mail service. Example:
    # msg = MIMEText(body)
    # msg['Subject'] = subject
    # msg['From'] = 'your_email@example.com'
    # msg['To'] = email
    # with smtplib.SMTP('localhost') as server:
    #     server.send_message(msg)

# ── And change the /api/data route so it passes **all** toggles through ──
@app.route('/api/data/<ticker>/<interval>/<int:ema_period>/<int:rsi_period>')
def get_data(ticker, interval, ema_period, rsi_period):
    params = dict(request.args)


    # 🛠 FIX ticker formatting
    ticker = ticker.upper()
    if ticker == 'TASI':
        ticker = '^TASI.SR'
    elif not ticker.startswith('^') and not ticker.endswith('.SR'):
        ticker = ticker + '.SR'



    # tiny helper
    data = fetch_yahoo_data(
        ticker, interval,
        ema_period, rsi_period,
        include_ema      = params.get('ema')      == 'true',
        include_rsi      = params.get('rsi')      == 'true',
        include_sma50    = params.get('sma50')    == 'true',
        include_sma200   = params.get('sma200')   == 'true',
        include_macd     = params.get('macd')     == 'true',
        include_stoch    = params.get('stochrsi') == 'true',
        include_volume   = params.get('volume')   == 'true',
        include_bbands   = params.get('bbands')   == 'true',
        include_vwap     = params.get('vwap')     == 'true',
    )
    return jsonify(data)

@app.route('/api/symbols')
def get_symbols():
    symbols_list = []
    for s in all_symbols:
        display_symbol = s
        if display_symbol.endswith('.SR'):
            display_symbol = display_symbol[:-3]
        if display_symbol == '^TASI':
            display_symbol = '^TASI'
        symbols_list.append({'symbol': display_symbol, 'name': all_symbols[s]})
    return jsonify(symbols_list)

@app.route('/api/search_symbols/<query>')
def search_symbols(query):
    query = query.upper()
    results = []
    for sym, name in all_symbols.items():
        display_sym = sym
        if display_sym.endswith('.SR'):
            display_sym = display_sym[:-3]
        if display_sym == '^TASI':
            display_sym = '^TASI'
        if display_sym.startswith(query):
            results.append({'symbol': display_sym, 'name': name})
    results = results[:20]
    return jsonify(results)

@app.route('/api/tadawul_watchlist')
def tadawul_watchlist():
    output = {}
    # Include ^TASI under "Index" or a special sector
    output["Index"] = [{'code': 'TASI', 'name': "مؤشر تداول للسوق الرئيسي (TASI)"}]
    for sector, stocks in tadawul_sectors.items():
        output[sector] = []
        for (name, code) in stocks:
            output[sector].append({'code': code, 'name': name})
    return jsonify(output)

if __name__ == '__main__':
    app.run(debug=False)

