"""
config/stocks.py — NSE stock universe (~420 liquid names).

Coverage  (approximate Nifty 500 composition):
  • Nifty 50             ~50  large-caps / index heavyweights
  • Nifty Next 50        ~50  large / upper-mid caps
  • Nifty Midcap 150     ~150 liquid midcaps
  • Additional           ~170 sector leaders, liquid small-caps

Tickers use Yahoo Finance NSE format  (suffix ".NS").
Stocks with very low volume or questionable data quality are excluded.
The liquidity filter in strategies/long_breakout.py provides a further
run-time check (₹5 Cr minimum daily turnover) on top of this list.
"""

STOCKS: dict[str, str] = {

    # ── BANKING ────────────────────────────────────────────────────────────────
    "HDFCBANK.NS":    "HDFC Bank",
    "ICICIBANK.NS":   "ICICI Bank",
    "KOTAKBANK.NS":   "Kotak Bank",
    "SBIN.NS":        "SBI",
    "AXISBANK.NS":    "Axis Bank",
    "INDUSINDBK.NS":  "IndusInd Bank",
    "BANDHANBNK.NS":  "Bandhan Bank",
    "FEDERALBNK.NS":  "Federal Bank",
    "IDFCFIRSTB.NS":  "IDFC First Bank",
    "RBLBANK.NS":     "RBL Bank",
    "BANKBARODA.NS":  "Bank of Baroda",
    "PNB.NS":         "Punjab Natl Bank",
    "CANBK.NS":  "Canara Bank",
    "UNIONBANK.NS":   "Union Bank",
    "INDIANB.NS":     "Indian Bank",
    "AUBANK.NS":      "AU Small Fin. Bank",
    "EQUITASBNK.NS":  "Equitas Small Fin.",
    "UJJIVANSFB.NS":  "Ujjivan Small Fin.",
    "IDBI.NS":        "IDBI Bank",
    "KTKBANK.NS":     "Karnataka Bank",
    "DCBBANK.NS":     "DCB Bank",
    "CSBBANK.NS":     "CSB Bank",

    # ── NBFC & FINANCIAL SERVICES ──────────────────────────────────────────────
    "BAJFINANCE.NS":  "Bajaj Finance",
    "BAJAJFINSV.NS":  "Bajaj Finserv",
    "CHOLAFIN.NS":    "Cholamandalam Fin.",
    "MUTHOOTFIN.NS":  "Muthoot Finance",
    "MANAPPURAM.NS":  "Manappuram Fin.",
    "ABCAPITAL.NS":   "Aditya Birla Cap.",
    "SBICARD.NS":     "SBI Cards",
    "SHRIRAMFIN.NS":  "Shriram Finance",
    "M&MFIN.NS":      "M&M Finance",
    "IIFL.NS": "IIFL Finance",
    "POONAWALLA.NS":  "Poonawalla Fin.",
    "MASFIN.NS":      "MAS Financial",
    "CREDITACC.NS":   "Credit Access Grameen",
    "5PAISA.NS":      "5paisa Capital",

    # ── INSURANCE ─────────────────────────────────────────────────────────────
    "LICI.NS":        "LIC India",
    "SBILIFE.NS":     "SBI Life",
    "HDFCLIFE.NS":    "HDFC Life",
    "ICICIGI.NS":     "ICICI Lombard",
    "ICICIPRULI.NS":  "ICICI Pru Life",
    "STARHEALTH.NS":  "Star Health",
    "JIOFIN.NS":      "Jio Financial",

    # ── ASSET MANAGEMENT ──────────────────────────────────────────────────────
    "HDFCAMC.NS":     "HDFC AMC",
    "UTIAMC.NS":      "UTI AMC",
    "NAM-INDIA.NS":  "Nippon Life AMC",
    "CAMS.NS":        "CAMS",
    "KFINTECH.NS":    "KFin Technologies",

    # ── CAPITAL MARKETS ────────────────────────────────────────────────────────
    "BSE.NS":         "BSE",
    "MCX.NS":         "MCX",
    "CDSL.NS":        "CDSL",
    "CRISIL.NS":      "CRISIL",
    "ANGELONE.NS":    "Angel One",
    "MOTILALOFS.NS":       "Motilal Oswal FS",
    "ICRA.NS":        "ICRA",
    "NUVAMA.NS":      "Nuvama Wealth",

    # ── INFORMATION TECHNOLOGY ─────────────────────────────────────────────────
    "TCS.NS":         "TCS",
    "INFY.NS":        "Infosys",
    "WIPRO.NS":       "Wipro",
    "HCLTECH.NS":     "HCL Tech",
    "TECHM.NS":       "Tech Mahindra",
    "LTIM.NS":        "LTIMindtree",
    "LTTS.NS":        "L&T Tech Svcs",
    "PERSISTENT.NS":  "Persistent Sys.",
    "COFORGE.NS":     "Coforge",
    "MPHASIS.NS":     "Mphasis",
    "KPITTECH.NS":    "KPIT Tech",
    "TATAELXSI.NS":   "Tata Elxsi",
    "OFSS.NS":        "Oracle Fin. Svcs",
    "CYIENT.NS":      "Cyient",
    "NAUKRI.NS":      "Info Edge",
    "MASTEK.NS":      "Mastek",
    "HAPPSTMNDS.NS":  "Happiest Minds",
    "TANLA.NS":       "Tanla Platforms",
    "NEWGEN.NS":      "Newgen Software",
    "LATENTVIEW.NS":  "LatentView Analytics",
    "BSOFT.NS":       "Birlasoft",
    "SONATSOFTW.NS":  "Sonata Software",
    "INTELLECT.NS":   "Intellect Design",
    "TATATECH.NS":    "Tata Technologies",
    "ZENSAR.NS":      "Zensar Tech",
    "RATEGAIN.NS":    "RateGain Travel",
    "HEXAWARE.NS":    "Hexaware Tech",
    "ECLERX.NS":      "eClerx Services",
    "DATAMATICS.NS":  "Datamatics Global",
    "ROUTE.NS":       "Route Mobile",

    # ── PHARMA & HEALTHCARE ────────────────────────────────────────────────────
    "SUNPHARMA.NS":   "Sun Pharma",
    "DRREDDY.NS":     "Dr. Reddy's",
    "CIPLA.NS":       "Cipla",
    "DIVISLAB.NS":    "Divi's Labs",
    "LUPIN.NS":       "Lupin",
    "TORNTPHARM.NS":  "Torrent Pharma",
    "BIOCON.NS":      "Biocon",
    "AUROPHARMA.NS":  "Aurobindo Pharma",
    "GLAND.NS":       "Gland Pharma",
    "SYNGENE.NS":     "Syngene Int.",
    "ZYDUSLIFE.NS":   "Zydus Lifesciences",
    "ALKEM.NS":       "Alkem Labs",
    "IPCALAB.NS":     "IPCA Labs",
    "LAURUSLABS.NS":  "Laurus Labs",
    "GRANULES.NS":    "Granules India",
    "NATCOPHARM.NS":  "Natco Pharma",
    "MANKIND.NS":     "Mankind Pharma",
    "AJANTPHARM.NS":  "Ajanta Pharma",
    "GLENMARK.NS":    "Glenmark Pharma",
    "SANOFI.NS":      "Sanofi India",
    "JBCHEPHARM.NS":  "JB Chemicals",
    "ERISLIFE.NS":    "Eris Lifesciences",
    "CAPLIPOINT.NS":  "Caplin Point Lab",
    "SEQUENT.NS":     "Sequent Scientific",

    # ── HOSPITALS & DIAGNOSTICS ────────────────────────────────────────────────
    "APOLLOHOSP.NS":  "Apollo Hospitals",
    "MAXHEALTH.NS":   "Max Healthcare",
    "FORTIS.NS":      "Fortis Healthcare",
    "ABBOTINDIA.NS":  "Abbott India",
    "LALPATHLAB.NS":  "Dr Lal PathLabs",
    "METROPOLIS.NS":  "Metropolis Healthcare",
    "CONCORD.NS":     "Concord Biotech",
    "THYROCARE.NS":   "Thyrocare Tech",
    "KIMS.NS":        "KIMS Hospitals",
    "RAINBOW.NS":     "Rainbow Children's",
    "NH.NS":          "Narayana Hrudayalaya",

    # ── AUTOMOBILE ─────────────────────────────────────────────────────────────
    "MARUTI.NS":      "Maruti Suzuki",
    "TATAMOTORS.NS":  "Tata Motors",
    "M&M.NS":         "Mahindra & Mah.",
    "BAJAJ-AUTO.NS":  "Bajaj Auto",
    "HEROMOTOCO.NS":  "Hero MotoCorp",
    "EICHERMOT.NS":   "Eicher Motors",
    "TVSMOTOR.NS":    "TVS Motor",
    "ASHOKLEY.NS":    "Ashok Leyland",

    # ── AUTO ANCILLARIES ───────────────────────────────────────────────────────
    "MOTHERSON.NS":   "Samvardhana Mother.",
    "BOSCHLTD.NS":    "Bosch",
    "EXIDEIND.NS":    "Exide Industries",
    "ARE&M.NS":   "Amara Raja Energy",
    "BALKRISIND.NS":  "Balkrishna Ind.",
    "APOLLOTYRE.NS":  "Apollo Tyres",
    "MRF.NS":         "MRF",
    "TIINDIA.NS":     "Tube Investments",
    "ENDURANCE.NS":   "Endurance Tech",
    "CRAFTSMAN.NS":   "Craftsman Auto",
    "SUPRAJIT.NS":    "Suprajit Engg.",
    "SONACOMS.NS":    "Sona BLW Precision",
    "UNOMINDA.NS":    "Uno Minda",
    "MAHINDCIE.NS":   "Mahindra CIE",
    "GABRIEL.NS":     "Gabriel India",
    "SUNDRMFAST.NS":  "Sundram Fasteners",
    "BEML.NS":        "BEML",
    "JKTYRE.NS":      "JK Tyre",
    "CEATLTD.NS":     "CEAT",

    # ── CONSUMER GOODS & FMCG ──────────────────────────────────────────────────
    "HINDUNILVR.NS":  "Hindustan Unilever",
    "ITC.NS":         "ITC",
    "NESTLEIND.NS":   "Nestle India",
    "BRITANNIA.NS":   "Britannia",
    "MARICO.NS":      "Marico",
    "GODREJCP.NS":    "Godrej Consumer",
    "COLPAL.NS":      "Colgate-Palmolive",
    "DABUR.NS":       "Dabur India",
    "EMAMILTD.NS":    "Emami",
    "TATACONSUM.NS":  "Tata Consumer",
    "MCDOWELL-N.NS":  "United Spirits",
    "VBL.NS":         "Varun Beverages",
    "RADICO.NS":      "Radico Khaitan",
    "JUBLFOOD.NS":    "Jubilant Foodworks",
    "DEVYANI.NS":     "Devyani Intl.",
    "PATANJALI.NS":   "Patanjali Foods",
    "BIKAJI.NS":      "Bikaji Foods",
    "BATAINDIA.NS":   "Bata India",
    "VSTIND.NS":      "VST Industries",
    "JYOTHYLAB.NS":   "Jyothy Labs",
    "HATSUN.NS":      "Hatsun Agro",
    "HERITAGE.NS":    "Heritage Foods",
    "BAJAJCON.NS":    "Bajaj Consumer Care",
    "METRO.NS":       "Metro Brands",
    "SAPPHIRE.NS":    "Sapphire Foods",

    # ── METALS & MINING ────────────────────────────────────────────────────────
    "JSWSTEEL.NS":    "JSW Steel",
    "TATASTEEL.NS":   "Tata Steel",
    "HINDALCO.NS":    "Hindalco",
    "VEDL.NS":        "Vedanta",
    "SAIL.NS":        "SAIL",
    "NMDC.NS":        "NMDC",
    "COALINDIA.NS":   "Coal India",
    "NATIONALUM.NS":  "National Aluminium",
    "HINDCOPPER.NS":  "Hindustan Copper",
    "APLAPOLLO.NS":   "APL Apollo Tubes",
    "WELCORP.NS":     "Welspun Corp",
    "JSL.NS":         "Jindal Stainless",
    "JINDALSTEL.NS":  "Jindal Steel & Pwr",
    "RATNAMANI.NS":   "Ratnamani Metals",
    "SHYAMMETL.NS":   "Shyam Metalics",
    "MOIL.NS":        "MOIL",
    "MIDHANI.NS":     "Mishra Dhatu Nigam",

    # ── ENERGY & OIL-GAS ───────────────────────────────────────────────────────
    "RELIANCE.NS":    "Reliance Ind.",
    "ONGC.NS":        "ONGC",
    "BPCL.NS":        "BPCL",
    "IOC.NS":         "Indian Oil",
    "GAIL.NS":        "GAIL",
    "PETRONET.NS":    "Petronet LNG",
    "IGL.NS":         "Indraprastha Gas",
    "MGL.NS":         "Mahanagar Gas",

    # ── POWER & UTILITIES ──────────────────────────────────────────────────────
    "NTPC.NS":        "NTPC",
    "POWERGRID.NS":   "Power Grid",
    "TATAPOWER.NS":   "Tata Power",
    "ADANIGREEN.NS":  "Adani Green",
    "ADANIPOWER.NS":  "Adani Power",
    "CESC.NS":        "CESC",
    "TORNTPOWER.NS":  "Torrent Power",
    "ATGL.NS":        "Adani Total Gas",
    "NHPC.NS":        "NHPC",
    "SJVN.NS":        "SJVN",
    "INOXWIND.NS":    "Inox Wind",
    "SUZLON.NS":      "Suzlon Energy",
    "JSWENERGY.NS":   "JSW Energy",
    "GIPCL.NS":       "GIPCL",

    # ── CEMENT ────────────────────────────────────────────────────────────────
    "ULTRACEMCO.NS":  "UltraTech Cement",
    "SHREECEM.NS":    "Shree Cement",
    "AMBUJACEM.NS":   "Ambuja Cement",
    "GRASIM.NS":      "Grasim Ind.",
    "DALBHARAT.NS":   "Dalmia Bharat",
    "JKCEMENT.NS":    "JK Cement",
    "RAMCOCEM.NS":    "Ramco Cements",
    "HEIDELBERG.NS":  "Heidelberg Cement",
    "NUVOCO.NS":      "Nuvoco Vistas",
    "JKPAPER.NS":     "JK Paper",

    # ── CAPITAL GOODS & ENGINEERING ────────────────────────────────────────────
    "LT.NS":          "L&T",
    "SIEMENS.NS":     "Siemens",
    "ABB.NS":         "ABB India",
    "BHEL.NS":        "BHEL",
    "CGPOWER.NS":     "CG Power",
    "THERMAX.NS":     "Thermax",
    "BHARATFORG.NS":  "Bharat Forge",
    "GRINDWELL.NS":   "Grindwell Norton",
    "HAVELLS.NS":     "Havells India",
    "POLYCAB.NS":     "Polycab India",
    "VOLTAS.NS":      "Voltas",
    "CROMPTON.NS":    "Crompton Greaves",
    "AMBER.NS":       "Amber Enterprises",
    "CUMMINSIND.NS":  "Cummins India",
    "SCHAEFFLER.NS":  "Schaeffler India",
    "TIMKEN.NS":      "Timken India",
    "SKFINDIA.NS":    "SKF India",
    "ELGIEQUIP.NS":   "Elgi Equipments",
    "PRAJ.NS":        "Praj Industries",
    "AIAENG.NS":      "AIA Engineering",
    "APARINDS.NS":    "Apar Industries",
    "CARBORUNIV.NS":  "Carborundum Universal",
    "VGUARD.NS":      "V-Guard Industries",
    "WHIRLPOOL.NS":   "Whirlpool India",
    "BLUESTARCO.NS":  "Blue Star",
    "KEC.NS":         "KEC International",
    "KALPATPOWR.NS":  "Kalpataru Power",
    "TITAGARH.NS":    "Titagarh Rail",

    # ── DEFENCE & PSU MANUFACTURING ────────────────────────────────────────────
    "BEL.NS":         "Bharat Electronics",
    "HAL.NS":         "Hindustan Aeronautics",
    "MAZDOCK.NS":     "Mazagon Dock",
    "COCHINSHIP.NS":  "Cochin Shipyard",
    "GRSE.NS":        "Garden Reach Ship.",
    "DATAPATTNS.NS":  "Data Patterns",

    # ── INFRASTRUCTURE & CONSTRUCTION ──────────────────────────────────────────
    "CONCOR.NS":      "Container Corp.",
    "IRFC.NS":        "IRFC",
    "RVNL.NS":        "Rail Vikas Nigam",
    "IRCON.NS":       "IRCON Intl.",
    "NBCC.NS":        "NBCC India",
    "RAILTEL.NS":     "RailTel Corp.",
    "HUDCO.NS":       "HUDCO",
    "PNCINFRA.NS":    "PNC Infratech",
    "GMRINFRA.NS":    "GMR Airports Infra",
    "IRB.NS":         "IRB Infrastructure",
    "ASHOKA.NS":      "Ashoka Buildcon",
    "JKIL.NS":        "J. Kumar Infraprojects",

    # ── CHEMICALS & SPECIALTY ──────────────────────────────────────────────────
    "PIDILITIND.NS":  "Pidilite Ind.",
    "ASTRAL.NS":      "Astral",
    "PIIND.NS":       "PI Industries",
    "SRF.NS":         "SRF",
    "DEEPAKNI.NS":    "Deepak Nitrite",
    "GNFC.NS":        "GNFC",
    "TATACHEM.NS":    "Tata Chemicals",
    "AARTIIND.NS":    "Aarti Industries",
    "NAVINFLUOR.NS":  "Navin Fluorine",
    "ATUL.NS":        "Atul",
    "FINEORG.NS":     "Fine Organics",
    "ALKYLAMINE.NS":  "Alkyl Amines",
    "PCBL.NS":        "PCBL",
    "GALAXYSURF.NS":  "Galaxy Surfactants",
    "LXCHEM.NS":   "Laxmi Organic",
    "CLEAN.NS":       "Clean Science",
    "LINDEINDIA.NS":  "Linde India",
    "VINATIORGA.NS":      "Vinati Organics",
    "NOCIL.NS":       "NOCIL",
    "ROSSARI.NS":     "Rossari Biotech",
    "SUDARSCHEM.NS":  "Sudarshan Chemical",
    "DCMSHRIRAM.NS":  "DCM Shriram",

    # ── AGRI, FERTILISERS & CROP SCIENCE ──────────────────────────────────────
    "COROMANDEL.NS":  "Coromandel Intl.",
    "RALLIS.NS":      "Rallis India",
    "SUMICHEM.NS":    "Sumitomo Chemical",
    "GHCL.NS":        "GHCL",
    "DEEPAKFERT.NS":  "Deepak Fertilizers",
    "EIDPARRY.NS":    "EID Parry",
    "BAYERCROP.NS":       "Bayer CropScience",
    "GODREJAGRO.NS":  "Godrej Agrovet",
    "UPL.NS":         "UPL",

    # ── PAINTS ────────────────────────────────────────────────────────────────
    "ASIANPAINT.NS":  "Asian Paints",
    "BERGEPAINT.NS":  "Berger Paints",
    "KANSAINER.NS":   "Kansai Nerolac",
    "AKZOINDIA.NS":   "Akzo Nobel",

    # ── REAL ESTATE & CONSTRUCTION ─────────────────────────────────────────────
    "DLF.NS":         "DLF",
    "GODREJPROP.NS":  "Godrej Properties",
    "OBEROIRLTY.NS":  "Oberoi Realty",
    "PRESTIGE.NS":    "Prestige Estates",
    "BRIGADE.NS":     "Brigade Enterprises",
    "PHOENIXLTD.NS":  "Phoenix Mills",
    "SOBHA.NS":       "Sobha",
    "MAHLIFE.NS":     "Mahindra Lifespace",
    "ANANTRAJ.NS":    "Anant Raj",
    "KOLTEPATIL.NS":  "Kolte-Patil Dev.",
    "SIGNATURE.NS":   "Signatureglobal",
    "JSWINFRA.NS":    "JSW Infrastructure",

    # ── TELECOM ────────────────────────────────────────────────────────────────
    "BHARTIARTL.NS":  "Bharti Airtel",
    "INDUSTOWER.NS":  "Indus Towers",
    "TATACOMM.NS":    "Tata Communications",

    # ── LOGISTICS & TRANSPORT ──────────────────────────────────────────────────
    "IRCTC.NS":       "IRCTC",
    "DELHIVERY.NS":   "Delhivery",
    "ALLCARGO.NS":    "Allcargo Logistics",
    "BLUEDART.NS":    "Blue Dart",
    "VRLLOG.NS":         "VRL Logistics",
    "TCI.NS":         "Transport Corp.",
    "MAHLOG.NS":      "Mahindra Logistics",
    "TCIEXPRES.NS":   "TCI Express",

    # ── RETAIL & CONSUMER DISCRETIONARY ───────────────────────────────────────
    "TITAN.NS":       "Titan",
    "TRENT.NS":       "Trent",
    "DMART.NS":       "Avenue Supermarts",
    "NYKAA.NS":       "Nykaa",
    "ETERNAL.NS":      "Eternal Limited",
    "PAYTM.NS":       "Paytm",
    "POLICYBZR.NS":   "PB Fintech",
    "KALYANKJIL.NS":  "Kalyan Jewellers",
    "SENCO.NS":       "Senco Gold",
    "DOMS.NS":        "DOMS Industries",
    "EASEMYTRIP.NS":  "EaseMyTrip",
    "WONDERLA.NS":    "Wonderla Holidays",
    "BARBEQUE.NS":    "Barbeque-Nation",
    "VEDANT.NS":      "Vedant Fashions",
    "OLECTRA.NS":     "Olectra Greentech",

    # ── TEXTILES & APPAREL ────────────────────────────────────────────────────
    "PAGEIND.NS":     "Page Industries",
    "RAYMOND.NS":     "Raymond",
    "ARVIND.NS":      "Arvind",
    "VARDHMAN.NS":    "Vardhman Textiles",
    "WELSPUNIND.NS":  "Welspun India",
    "TRIDENT.NS":     "Trident",
    "KPRMILL.NS":     "KPR Mill",

    # ── MEDIA & ENTERTAINMENT ──────────────────────────────────────────────────
    "PVRINOX.NS":     "PVR Inox",
    "ZEEL.NS":        "Zee Entertainment",
    "SUNTV.NS":       "Sun TV Network",
    "NAZARA.NS":      "Nazara Technologies",
    "SAREGAMA.NS":    "Saregama India",
    "NETWORK18.NS":   "Network18 Media",

    # ── HOSPITALITY & TRAVEL ──────────────────────────────────────────────────
    "INDHOTEL.NS":    "Indian Hotels",
    "LEMONTREE.NS":   "Lemon Tree Hotels",
    "CHALET.NS":      "Chalet Hotels",
    "JUNIPER.NS":     "Juniper Hotels",

    # ── CONGLOMERATES ─────────────────────────────────────────────────────────
    "ADANIENT.NS":    "Adani Enterprises",
    "ADANIPORTS.NS":  "Adani Ports",
    "GODREJIND.NS":   "Godrej Industries",
    "BAJAJHLDNG.NS":  "Bajaj Holdings",

    # ── EDUCATION & MISC ──────────────────────────────────────────────────────
    "JUSTDIAL.NS":    "Just Dial",
    "INDIAMART.NS":   "IndiaMART",
    "DIXONTECH.NS":   "Dixon Technologies",
    "KAYNES.NS":      "Kaynes Technology",
    "RAJESHEXPO.NS":  "Rajesh Exports",
    "POLYPLEX.NS":    "Polyplex Corp.",
    "MTARTECH.NS":    "MTAR Technologies",

    # ── ADDITIONAL PHARMA ─────────────────────────────────────────────────────
    "PFIZER.NS":      "Pfizer India",
    "GLAXO.NS":       "GSK Pharma India",
    "WOCKHARDT.NS":   "Wockhardt",
    "SOLARA.NS":      "Solara Active Pharma",

    # ── ADDITIONAL FINANCIAL SERVICES ─────────────────────────────────────────
    "SUNDARMFIN.NS":  "Sundaram Finance",
    "JMFINANCIL.NS":  "JM Financial",
    "MFSL.NS":        "Max Financial Svcs",
    "CHOLAHLDNG.NS":  "Cholamandalam Inv.",
    "IIFLSEC.NS":     "IIFL Securities",
    "RECLTD.NS":      "REC Ltd",
    "IREDA.NS":       "IREDA",

    # ── ADDITIONAL CAPITAL GOODS ──────────────────────────────────────────────
    "INOXINDIA.NS":   "INOX India",
    "KENNAMET.NS":    "Kennametal India",
    "POWERMECH.NS":   "Power Mech Projects",
    "ISGEC.NS":       "ISGEC Heavy Engg.",
    "HFCL.NS":        "HFCL",

    # ── ADDITIONAL REAL ESTATE ────────────────────────────────────────────────
    "MACROTECH.NS":   "Macrotech (Lodha)",

    # ── ADDITIONAL AUTO ───────────────────────────────────────────────────────
    "JTEKTINDIA.NS":  "JTEKT India",

    # ── ADDITIONAL IT ─────────────────────────────────────────────────────────
    "SYRMA.NS":       "Syrma SGS Tech",
    "RAMCOSYS.NS":    "Ramco Systems",

    # ── ADDITIONAL CONSUMER ───────────────────────────────────────────────────
    "GILLETTE.NS":    "Gillette India",
    "HONAUT.NS":      "Honeywell Automation",
    "3MINDIA.NS":     "3M India",

    # ── ADDITIONAL LOGISTICS ──────────────────────────────────────────────────
    "GDL.NS":         "Gateway Distriparks",
    "SNOWMAN.NS":     "Snowman Logistics",

    # ── ADDITIONAL CHEMICALS ──────────────────────────────────────────────────
    "BALAMINES.NS":   "Balaji Amines",
    "BASF.NS":        "BASF India",

    # ── ADDITIONAL METALS ─────────────────────────────────────────────────────
    "GPPL.NS":        "Gujarat Pipavav Port",

    # ── ADDITIONAL ENERGY / PSU ───────────────────────────────────────────────
    "ADANITRANS.NS":  "Adani Transmission",
    "MMTC.NS":        "MMTC",

    # ── ADDITIONAL DIVERSIFIED ────────────────────────────────────────────────
    "NAVINFLUOR.NS":  "Navin Fluorine",     # guard  (already above)
    "JSWHL.NS":       "JSW Holdings",
    "TATAINVEST.NS":  "Tata Investment Corp",
    "MCDOWELL-N.NS":  "United Spirits",     # guard  (already above)
    "AVANTIFEED.NS":  "Avanti Feeds",
    "VENKEYS.NS":     "Venky's India",
    "HATSUN.NS":      "Hatsun Agro",        # guard  (already above)
    "KRSNAA.NS":      "Krsnaa Diagnostics",
    "VIJAYAETL.NS":   "Vijaya Diagnostic",
    "MEDANTA.NS":     "Global Health (Medanta)",
    "SAREGAMA.NS":    "Saregama India",     # guard  (already above)
    "NETWORK18.NS":   "Network18 Media",    # guard  (already above)
    "KPRMILL.NS":     "KPR Mill",           # guard  (already above)

    # ── EXTENDED UNIVERSE — BANKING & HOUSING FINANCE ─────────────────────────
    "CITYUNIONBK.NS": "City Union Bank",
    "JKBANK.NS":      "J&K Bank",
    "KARURVYSYA.NS":  "Karur Vysya Bank",
    "SOUTHBANK.NS":   "South Indian Bank",
    "AAVAS.NS":       "Aavas Financiers",
    "HOMEFIRST.NS":   "Home First Finance",
    "APTUS.NS":       "Aptus Value Housing",
    "PNBHOUSING.NS":  "PNB Housing Finance",
    "CANFIN.NS":      "Can Fin Homes",
    "REPCO.NS":       "Repco Home Finance",
    "SPANDANA.NS":    "Spandana Sphoorty",
    "FUSION.NS":      "Fusion Micro Finance",

    # ── EXTENDED UNIVERSE — IT & TECH ─────────────────────────────────────────
    "AFFLE.NS":       "Affle India",
    "STLTECH.NS":     "Sterlite Technologies",
    "TEJAS.NS":       "Tejas Networks",
    "QUICKHEAL.NS":   "Quick Heal Tech",
    "NUCLEUS.NS":     "Nucleus Software",

    # ── EXTENDED UNIVERSE — PHARMA & HEALTHCARE ───────────────────────────────
    "ASTRAZEN.NS":    "AstraZeneca India",
    "SUVEN.NS":       "Suven Pharma",
    "UNICHEM.NS":     "Unichem Labs",
    "HESTER.NS":      "Hester Biosciences",
    "IOLCP.NS":       "IOL Chemicals",
    "STRIDES.NS":     "Strides Pharma",
    "JUBILANT.NS":    "Jubilant Pharmova",
    "YATHARTH.NS":    "Yatharth Hospital",
    "ASTERDM.NS":     "Aster DM Healthcare",

    # ── EXTENDED UNIVERSE — AUTO & ANCILLARIES ────────────────────────────────
    "ESCORTS.NS":     "Escorts Kubota",
    "VARROC.NS":      "Varroc Engineering",
    "MINDACORP.NS":   "Minda Corp",

    # ── EXTENDED UNIVERSE — CHEMICALS & SPECIALTY ─────────────────────────────
    "ANUPAM.NS":      "Anupam Rasayan",
    "TATVA.NS":     "Tatva Chintan Pharma",
    "TARSONS.NS":     "Tarsons Products",
    "GFL.NS":         "Gujarat Fluorochemicals",

    # ── EXTENDED UNIVERSE — AGRI, FOOD & BEVERAGES ────────────────────────────
    "KRBL.NS":        "KRBL",
    "LTFOODS.NS":     "LT Foods",
    "BALRAMCHIN.NS":  "Balrampur Chini",
    "TRIVENI.NS":     "Triveni Engineering",
    "KAVERI.NS":      "Kaveri Seed",
    "DHANUKA.NS":     "Dhanuka Agritech",

    # ── EXTENDED UNIVERSE — ENERGY & PSU ──────────────────────────────────────
    "HINDPETRO.NS":   "HPCL",
    "MRPL.NS":        "MRPL",
    "CPCL.NS":        "CPCL",
    "OIL.NS":         "Oil India",
    "RITES.NS":       "RITES",
    "BDL.NS":         "Bharat Dynamics",

    # ── EXTENDED UNIVERSE — METALS & MINING ───────────────────────────────────
    "HINDZINC.NS":    "Hindustan Zinc",
    "GPIL.NS":        "Godawari Power",
    "SUNFLAG.NS":     "Sunflag Iron",

    # ── EXTENDED UNIVERSE — CAPITAL GOODS & INFRA ────────────────────────────
    "TRIVENITRB.NS":  "Triveni Turbine",
    "TDPOWERSYS.NS":  "TD Power Systems",
    "ELECON.NS":      "Elecon Engineering",
    "PSPPROJECT.NS":  "PSP Projects",
    "HGINFRA.NS":     "HG Infra Engineering",
    "SOLARINDS.NS":   "Solar Industries India",
    "BAJAJELEC.NS":   "Bajaj Electricals",
    "HAPPYFORG.NS":   "Happy Forgings",

    # ── EXTENDED UNIVERSE — BUILDING MATERIALS ────────────────────────────────
    "CENTURYPLY.NS":  "Century Plyboards",
    "GREENPLY.NS":    "Greenply Industries",
    "GREENLAM.NS":    "Greenlam Industries",
    "KAJARIA.NS":     "Kajaria Ceramics",
    "CERA.NS":        "Cera Sanitaryware",
    "SOMANYCER.NS":   "Somany Ceramics",
    "ORIENTBELL.NS":  "Orient Bell",

    # ── EXTENDED UNIVERSE — PIPES, CABLES & PACKAGING ────────────────────────
    "SUPREMEIND.NS":  "Supreme Industries",
    "FINCABLES.NS":   "Finolex Cables",
    "FINOLEXPIPE.NS": "Finolex Industries",
    "APOLLOPIPE.NS":  "Apollo Pipes",
    "PRINCEPIPE.NS":  "Prince Pipes",

    # ── EXTENDED UNIVERSE — REAL ESTATE ───────────────────────────────────────
    "SUNTECK.NS":     "Sunteck Realty",
    "PURVA.NS":       "Puravankara",

    # ── EXTENDED UNIVERSE — LOGISTICS ─────────────────────────────────────────
    "AEGIS.NS":       "Aegis Logistics",
    "GATI.NS":        "GATI",

    # ── EXTENDED UNIVERSE — TEXTILES & APPAREL ────────────────────────────────
    "GOKALDAS.NS":    "Gokaldas Exports",
    "RUPA.NS":        "Rupa & Company",
    "DOLLAR.NS":      "Dollar Industries",

    # ── EXTENDED UNIVERSE — CONSUMER GOODS ───────────────────────────────────
    "VAIBHAVGBL.NS":  "Vaibhav Global",
}

# Python dicts reject duplicate keys at parse time; this line is a safety net.
STOCKS = {k: v for k, v in STOCKS.items()}


# ── Sector mapping ─────────────────────────────────────────────────────────────
# Keys are base tickers WITHOUT the .NS suffix.
# Used by the backtest sector-concentration cap (MAX_TRADES_PER_SECTOR).
# Unmapped tickers fall back to "OTHER".

SECTORS: dict[str, str] = {
    # BANKING
    "HDFCBANK": "BANKING",   "ICICIBANK": "BANKING",  "KOTAKBANK": "BANKING",
    "SBIN": "BANKING",       "AXISBANK": "BANKING",   "INDUSINDBK": "BANKING",
    "BANDHANBNK": "BANKING", "FEDERALBNK": "BANKING", "IDFCFIRSTB": "BANKING",
    "RBLBANK": "BANKING",    "BANKBARODA": "BANKING", "PNB": "BANKING",
    "CANARABANK": "BANKING", "UNIONBANK": "BANKING",  "INDIANB": "BANKING",
    "AUBANK": "BANKING",     "EQUITASBNK": "BANKING", "UJJIVANSFB": "BANKING",
    "IDBI": "BANKING",       "KTKBANK": "BANKING",    "DCBBANK": "BANKING",
    "CSBBANK": "BANKING",

    # NBFC & FINANCIAL SERVICES
    "BAJFINANCE": "NBFC",   "BAJAJFINSV": "NBFC",  "CHOLAFIN": "NBFC",
    "MUTHOOTFIN": "NBFC",   "MANAPPURAM": "NBFC",  "ABCAPITAL": "NBFC",
    "SBICARD": "NBFC",      "SHRIRAMFIN": "NBFC",  "M&MFIN": "NBFC",
    "IIFLFINANCE": "NBFC",  "POONAWALLA": "NBFC",  "MASFIN": "NBFC",
    "CREDITACC": "NBFC",    "5PAISA": "NBFC",      "SUNDARMFIN": "NBFC",
    "JMFINANCIL": "NBFC",   "MFSL": "NBFC",        "CHOLAHLDNG": "NBFC",
    "IIFLSEC": "NBFC",      "RECLTD": "NBFC",      "IREDA": "NBFC",

    # INSURANCE
    "LICI": "INSURANCE",    "SBILIFE": "INSURANCE",  "HDFCLIFE": "INSURANCE",
    "ICICIGI": "INSURANCE",  "ICICIPRULI": "INSURANCE", "STARHEALTH": "INSURANCE",
    "JIOFIN": "INSURANCE",

    # AMC & CAPITAL MARKETS
    "HDFCAMC": "AMC",    "UTIAMC": "AMC",    "NIPPONLIFE": "AMC",
    "CAMS": "AMC",       "KFINTECH": "AMC",
    "BSE": "CAP_MARKETS",    "MCX": "CAP_MARKETS",  "CDSL": "CAP_MARKETS",
    "CRISIL": "CAP_MARKETS", "ANGELONE": "CAP_MARKETS", "MOFSL": "CAP_MARKETS",
    "ICRA": "CAP_MARKETS",   "NUVAMA": "CAP_MARKETS",

    # INFORMATION TECHNOLOGY
    "TCS": "IT",         "INFY": "IT",       "WIPRO": "IT",
    "HCLTECH": "IT",     "TECHM": "IT",      "LTIM": "IT",
    "LTTS": "IT",        "PERSISTENT": "IT", "COFORGE": "IT",
    "MPHASIS": "IT",     "KPITTECH": "IT",   "TATAELXSI": "IT",
    "OFSS": "IT",        "CYIENT": "IT",     "NAUKRI": "IT",
    "MASTEK": "IT",      "HAPPSTMNDS": "IT", "TANLA": "IT",
    "NEWGEN": "IT",      "LATENTVIEW": "IT", "BSOFT": "IT",
    "SONATSOFTW": "IT",  "INTELLECT": "IT",  "TATATECH": "IT",
    "ZENSAR": "IT",      "RATEGAIN": "IT",   "HEXAWARE": "IT",
    "ECLERX": "IT",      "DATAMATICS": "IT", "ROUTE": "IT",
    "RAMCOSYS": "IT",    "SYRMA": "IT",

    # PHARMA
    "SUNPHARMA": "PHARMA",  "DRREDDY": "PHARMA",   "CIPLA": "PHARMA",
    "DIVISLAB": "PHARMA",   "LUPIN": "PHARMA",     "TORNTPHARM": "PHARMA",
    "BIOCON": "PHARMA",     "AUROPHARMA": "PHARMA","GLAND": "PHARMA",
    "SYNGENE": "PHARMA",    "ZYDUSLIFE": "PHARMA", "ALKEM": "PHARMA",
    "IPCALAB": "PHARMA",    "LAURUSLABS": "PHARMA","GRANULES": "PHARMA",
    "NATCOPHARM": "PHARMA", "MANKIND": "PHARMA",   "AJANTPHARM": "PHARMA",
    "GLENMARK": "PHARMA",   "SANOFI": "PHARMA",    "JBCHEPHARM": "PHARMA",
    "ERISLIFE": "PHARMA",   "CAPLIPOINT": "PHARMA","SEQUENT": "PHARMA",
    "PFIZER": "PHARMA",     "GLAXO": "PHARMA",     "WOCKHARDT": "PHARMA",
    "SOLARA": "PHARMA",     "ABBOTINDIA": "PHARMA",

    # HOSPITALS & DIAGNOSTICS
    "APOLLOHOSP": "HOSPITALS", "MAXHEALTH": "HOSPITALS", "FORTIS": "HOSPITALS",
    "LALPATHLAB": "HOSPITALS", "METROPOLIS": "HOSPITALS","CONCORD": "HOSPITALS",
    "THYROCARE": "HOSPITALS",  "KIMS": "HOSPITALS",     "RAINBOW": "HOSPITALS",
    "NH": "HOSPITALS",         "KRSNAA": "HOSPITALS",   "VIJAYAETL": "HOSPITALS",
    "MEDANTA": "HOSPITALS",

    # AUTOMOBILE (OEM)
    "MARUTI": "AUTO",    "TATAMOTORS": "AUTO", "M&M": "AUTO",
    "BAJAJ-AUTO": "AUTO","HEROMOTOCO": "AUTO", "EICHERMOT": "AUTO",
    "TVSMOTOR": "AUTO",  "ASHOKLEY": "AUTO",

    # AUTO ANCILLARIES
    "MOTHERSON": "AUTO_ANC",  "BOSCHLTD": "AUTO_ANC",  "EXIDEIND": "AUTO_ANC",
    "AMARARAJA": "AUTO_ANC",  "BALKRISIND": "AUTO_ANC","APOLLOTYRE": "AUTO_ANC",
    "MRF": "AUTO_ANC",        "TIINDIA": "AUTO_ANC",   "ENDURANCE": "AUTO_ANC",
    "CRAFTSMAN": "AUTO_ANC",  "SUPRAJIT": "AUTO_ANC",  "SONACOMS": "AUTO_ANC",
    "UNOMINDA": "AUTO_ANC",   "MAHINDCIE": "AUTO_ANC", "GABRIEL": "AUTO_ANC",
    "SUNDRMFAST": "AUTO_ANC", "BEML": "AUTO_ANC",      "JKTYRE": "AUTO_ANC",
    "CEATLTD": "AUTO_ANC",    "JTEKTINDIA": "AUTO_ANC",

    # FMCG & CONSUMER STAPLES
    "HINDUNILVR": "FMCG", "ITC": "FMCG",      "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG",  "MARICO": "FMCG",   "GODREJCP": "FMCG",
    "COLPAL": "FMCG",     "DABUR": "FMCG",    "EMAMILTD": "FMCG",
    "TATACONSUM": "FMCG", "MCDOWELL-N": "FMCG","VBL": "FMCG",
    "RADICO": "FMCG",     "PATANJALI": "FMCG", "BIKAJI": "FMCG",
    "BATAINDIA": "FMCG",  "VSTIND": "FMCG",   "JYOTHYLAB": "FMCG",
    "HATSUN": "FMCG",     "HERITAGE": "FMCG", "BAJAJCON": "FMCG",
    "GILLETTE": "FMCG",   "AVANTIFEED": "FMCG","VENKEYS": "FMCG",

    # METALS & MINING
    "JSWSTEEL": "METALS",  "TATASTEEL": "METALS", "HINDALCO": "METALS",
    "VEDL": "METALS",      "SAIL": "METALS",      "NMDC": "METALS",
    "COALINDIA": "METALS", "NATIONALUM": "METALS","HINDCOPPER": "METALS",
    "APLAPOLLO": "METALS", "WELCORP": "METALS",   "JSL": "METALS",
    "JINDALSTEL": "METALS","RATNAMANI": "METALS", "SHYAMMETL": "METALS",
    "MOIL": "METALS",      "MIDHANI": "METALS",   "MMTC": "METALS",
    "GPPL": "METALS",

    # OIL & GAS
    "RELIANCE": "OIL_GAS", "ONGC": "OIL_GAS", "BPCL": "OIL_GAS",
    "IOC": "OIL_GAS",      "GAIL": "OIL_GAS", "PETRONET": "OIL_GAS",
    "IGL": "OIL_GAS",      "MGL": "OIL_GAS",

    # POWER & UTILITIES
    "NTPC": "POWER",      "POWERGRID": "POWER",  "TATAPOWER": "POWER",
    "ADANIGREEN": "POWER","ADANIPOWER": "POWER", "CESC": "POWER",
    "TORNTPOWER": "POWER","ATGL": "POWER",       "NHPC": "POWER",
    "SJVN": "POWER",      "INOXWIND": "POWER",   "SUZLON": "POWER",
    "JSWENERGY": "POWER", "GIPCL": "POWER",      "ADANITRANS": "POWER",

    # CEMENT & BUILDING MATERIALS
    "ULTRACEMCO": "CEMENT","SHREECEM": "CEMENT", "AMBUJACEM": "CEMENT",
    "GRASIM": "CEMENT",    "DALBHARAT": "CEMENT","JKCEMENT": "CEMENT",
    "RAMCOCEM": "CEMENT",  "HEIDELBERG": "CEMENT","NUVOCO": "CEMENT",
    "JKPAPER": "CEMENT",

    # CAPITAL GOODS & ENGINEERING
    "LT": "CAP_GOODS",       "SIEMENS": "CAP_GOODS",  "ABB": "CAP_GOODS",
    "BHEL": "CAP_GOODS",     "CGPOWER": "CAP_GOODS",  "THERMAX": "CAP_GOODS",
    "BHARATFORG": "CAP_GOODS","GRINDWELL": "CAP_GOODS","HAVELLS": "CAP_GOODS",
    "POLYCAB": "CAP_GOODS",  "VOLTAS": "CAP_GOODS",   "CROMPTON": "CAP_GOODS",
    "AMBER": "CAP_GOODS",    "CUMMINS": "CAP_GOODS",  "SCHAEFFLER": "CAP_GOODS",
    "TIMKEN": "CAP_GOODS",   "SKFINDIA": "CAP_GOODS", "ELGIEQUIP": "CAP_GOODS",
    "PRAJ": "CAP_GOODS",     "AIAENG": "CAP_GOODS",   "APARINDS": "CAP_GOODS",
    "CARBORUNIV": "CAP_GOODS","VGUARD": "CAP_GOODS",  "WHIRLPOOL": "CAP_GOODS",
    "BLUESTARCO": "CAP_GOODS","KEC": "CAP_GOODS",     "KALPATPOWR": "CAP_GOODS",
    "TITAGARH": "CAP_GOODS", "ISGEC": "CAP_GOODS",   "KENNAMET": "CAP_GOODS",
    "POWERMECH": "CAP_GOODS","INOXINDIA": "CAP_GOODS","HFCL": "CAP_GOODS",
    "HONAUT": "CAP_GOODS",   "3MINDIA": "CAP_GOODS",

    # DEFENCE & SHIPBUILDING
    "BEL": "DEFENCE",       "HAL": "DEFENCE",      "MAZDOCK": "DEFENCE",
    "COCHINSHIP": "DEFENCE","GRSE": "DEFENCE",     "DATAPATTNS": "DEFENCE",

    # INFRASTRUCTURE & PSU CONSTRUCTION
    "CONCOR": "INFRA",  "IRFC": "INFRA",   "RVNL": "INFRA",
    "IRCON": "INFRA",   "NBCC": "INFRA",   "RAILTEL": "INFRA",
    "HUDCO": "INFRA",   "PNCINFRA": "INFRA","GMRINFRA": "INFRA",
    "IRB": "INFRA",     "ASHOKA": "INFRA", "JKIL": "INFRA",

    # CHEMICALS & SPECIALTY
    "PIDILITIND": "CHEMICALS","ASTRAL": "CHEMICALS", "PIIND": "CHEMICALS",
    "SRF": "CHEMICALS",       "DEEPAKNI": "CHEMICALS","GNFC": "CHEMICALS",
    "TATACHEM": "CHEMICALS",  "AARTIIND": "CHEMICALS","NAVINFLUOR": "CHEMICALS",
    "ATUL": "CHEMICALS",      "FINEORG": "CHEMICALS", "ALKYLAMINE": "CHEMICALS",
    "PCBL": "CHEMICALS",      "GALAXYSURF": "CHEMICALS","LAXMICHEM": "CHEMICALS",
    "CLEAN": "CHEMICALS",     "LINDEINDIA": "CHEMICALS","VINATI": "CHEMICALS",
    "NOCIL": "CHEMICALS",     "ROSSARI": "CHEMICALS",  "SUDARSCHEM": "CHEMICALS",
    "DCMSHRIRAM": "CHEMICALS","BALAMINES": "CHEMICALS","BASF": "CHEMICALS",
    "POLYPLEX": "CHEMICALS",

    # AGRI & FERTILISERS
    "COROMANDEL": "AGRI","RALLIS": "AGRI","SUMICHEM": "AGRI",
    "GHCL": "AGRI",     "DEEPAKFERT": "AGRI","EIDPARRY": "AGRI",
    "BAYER": "AGRI",    "GODREJAGRO": "AGRI","UPL": "AGRI",

    # PAINTS
    "ASIANPAINT": "PAINTS","BERGEPAINT": "PAINTS",
    "KANSAINER": "PAINTS", "AKZOINDIA": "PAINTS",

    # REAL ESTATE
    "DLF": "REAL_ESTATE",       "GODREJPROP": "REAL_ESTATE","OBEROIRLTY": "REAL_ESTATE",
    "PRESTIGE": "REAL_ESTATE",  "BRIGADE": "REAL_ESTATE",  "PHOENIXLTD": "REAL_ESTATE",
    "SOBHA": "REAL_ESTATE",     "MAHLIFE": "REAL_ESTATE",  "ANANTRAJ": "REAL_ESTATE",
    "KOLTEPATIL": "REAL_ESTATE","SIGNATURE": "REAL_ESTATE","JSWINFRA": "REAL_ESTATE",
    "MACROTECH": "REAL_ESTATE",

    # TELECOM
    "BHARTIARTL": "TELECOM","INDUSTOWER": "TELECOM","TATACOMM": "TELECOM",

    # LOGISTICS & TRANSPORT
    "IRCTC": "LOGISTICS",  "DELHIVERY": "LOGISTICS","ALLCARGO": "LOGISTICS",
    "BLUEDART": "LOGISTICS","VRL": "LOGISTICS",     "TCI": "LOGISTICS",
    "MAHLOG": "LOGISTICS", "TCIEXPRES": "LOGISTICS","GDL": "LOGISTICS",
    "SNOWMAN": "LOGISTICS",

    # RETAIL & CONSUMER DISCRETIONARY
    "TITAN": "RETAIL",    "TRENT": "RETAIL",    "DMART": "RETAIL",
    "NYKAA": "RETAIL",    "ZOMATO": "RETAIL",   "PAYTM": "RETAIL",
    "POLICYBZR": "RETAIL","KALYANKJIL": "RETAIL","SENCO": "RETAIL",
    "DOMS": "RETAIL",     "EASEMYTRIP": "RETAIL","WONDERLA": "RETAIL",
    "BARBEQUE": "RETAIL", "VEDANT": "RETAIL",   "OLECTRA": "RETAIL",
    "METRO": "RETAIL",    "SAPPHIRE": "RETAIL", "JUBLFOOD": "RETAIL",
    "DEVYANI": "RETAIL",

    # TEXTILES
    "PAGEIND": "TEXTILES","RAYMOND": "TEXTILES","ARVIND": "TEXTILES",
    "VARDHMAN": "TEXTILES","WELSPUNIND": "TEXTILES","TRIDENT": "TEXTILES",
    "KPRMILL": "TEXTILES","CANTABIL": "TEXTILES",

    # MEDIA & ENTERTAINMENT
    "PVRINOX": "MEDIA","ZEEL": "MEDIA","SUNTV": "MEDIA",
    "NAZARA": "MEDIA", "SAREGAMA": "MEDIA","NETWORK18": "MEDIA",

    # HOSPITALITY
    "INDHOTEL": "HOSPITALITY","LEMONTREE": "HOSPITALITY",
    "CHALET": "HOSPITALITY",  "JUNIPER": "HOSPITALITY",

    # CONGLOMERATES
    "ADANIENT": "CONGLOMERATES","ADANIPORTS": "CONGLOMERATES",
    "GODREJIND": "CONGLOMERATES","BAJAJHLDNG": "CONGLOMERATES",
    "JSWHL": "CONGLOMERATES",   "TATAINVEST": "CONGLOMERATES",

    # EXTENDED — BANKING / HOUSING FINANCE
    "CITYUNIONBK":"BANKING",    "JKBANK": "BANKING",
    "KARURVYSYA": "BANKING",    "SOUTHBANK": "BANKING",
    "AAVAS": "HOUSING_FINANCE", "HOMEFIRST": "HOUSING_FINANCE",
    "APTUS": "HOUSING_FINANCE", "PNBHOUSING": "HOUSING_FINANCE",
    "CANFIN": "HOUSING_FINANCE","REPCO": "HOUSING_FINANCE",
    "SPANDANA": "NBFC",         "FUSION": "NBFC",

    # EXTENDED — IT & TECH
    "AFFLE": "IT",      "STLTECH": "IT",    "TEJAS": "IT",
    "QUICKHEAL": "IT",  "NUCLEUS": "IT",

    # EXTENDED — PHARMA & HEALTHCARE
    "ASTRAZEN": "PHARMA",   "SUVEN": "PHARMA",
    "UNICHEM":  "PHARMA",   "HESTER": "PHARMA",
    "IOLCP":    "PHARMA",   "STRIDES": "PHARMA",
    "JUBILANT": "PHARMA",   "YATHARTH": "HEALTHCARE",
    "ASTERDM":  "HEALTHCARE",

    # EXTENDED — AUTO
    "ESCORTS": "AUTO",      "VARROC": "AUTO",
    "MINDACORP": "AUTO",

    # EXTENDED — CHEMICALS
    "ANUPAM": "CHEMICALS",  "TATVACC": "CHEMICALS",
    "TARSONS": "CHEMICALS", "GFL": "CHEMICALS",

    # EXTENDED — AGRI / FOOD
    "KRBL": "AGRI",         "LTFOODS": "AGRI",
    "BALRAMCHIN": "AGRI",   "TRIVENI": "AGRI",
    "KAVERI": "AGRI",       "DHANUKA": "AGRI",

    # EXTENDED — ENERGY / PSU
    "HINDPETRO": "OIL_GAS", "MRPL": "OIL_GAS",
    "CPCL": "OIL_GAS",      "OIL": "OIL_GAS",
    "RITES": "INFRA",       "BDL": "DEFENCE",

    # EXTENDED — METALS
    "HINDZINC": "METALS",   "GPIL": "METALS",
    "SUNFLAG": "METALS",

    # EXTENDED — CAPITAL GOODS / INFRA
    "TRIVENITRB": "CAPITAL_GOODS", "TDPOWERSYS": "CAPITAL_GOODS",
    "ELECON": "CAPITAL_GOODS",     "PSPPROJECT": "INFRA",
    "HGINFRA": "INFRA",            "SOLARINDS": "DEFENCE",
    "BAJAJELEC": "CAPITAL_GOODS",  "HAPPYFORG": "CAPITAL_GOODS",

    # EXTENDED — BUILDING MATERIALS
    "CENTURYPLY": "BUILDING_MATERIALS", "GREENPLY": "BUILDING_MATERIALS",
    "GREENLAM": "BUILDING_MATERIALS",   "KAJARIA": "BUILDING_MATERIALS",
    "CERA": "BUILDING_MATERIALS",       "SOMANYCER": "BUILDING_MATERIALS",
    "ORIENTBELL": "BUILDING_MATERIALS",

    # EXTENDED — PIPES / CABLES
    "SUPREMEIND": "PIPES_CABLES",   "FINCABLES": "PIPES_CABLES",
    "FINOLEXPIPE": "PIPES_CABLES",  "APOLLOPIPE": "PIPES_CABLES",
    "PRINCEPIPE": "PIPES_CABLES",

    # EXTENDED — REAL ESTATE
    "SUNTECK": "REAL_ESTATE",  "PURVA": "REAL_ESTATE",

    # EXTENDED — LOGISTICS
    "AEGIS": "LOGISTICS",  "GATI": "LOGISTICS",

    # EXTENDED — TEXTILES
    "GOKALDAS": "TEXTILES", "RUPA": "TEXTILES", "DOLLAR": "TEXTILES",

    # EXTENDED — CONSUMER
    "VAIBHAVGBL": "CONSUMER",
}
