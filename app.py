from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import pandas as pd
import pdfplumber

app = Flask(__name__,
    template_folder=None  # templates klasörü kullanılmayacak
)
app.secret_key = "secret-key"
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_merged_table(altmenu):
    altmenu_columns = {
        "1donem_dersici1": [0, 1, 2, 9],
        "1donem_dersici2": [0, 1, 2, 10],
        "1donem_dersici3": [0, 1, 2, 11],
        "2donem_dersici1": [0, 1, 2, 21],
        "2donem_dersici2": [0, 1, 2, 22],
        "2donem_dersici3": [0, 1, 2, 23],
        "2donem_proje":    [0, 1, 2, 19],
    }
    altmenu_names = {
        "1donem_dersici1": "1. Dönem Dersiçi 1",
        "1donem_dersici2": "1. Dönem Dersiçi 2",
        "1donem_dersici3": "1. Dönem Dersiçi 3",
        "2donem_dersici1": "2. Dönem Dersiçi 1",
        "2donem_dersici2": "2. Dönem Dersiçi 2",
        "2donem_dersici3": "2. Dönem Dersiçi 3",
        "2donem_proje":    "2. Dönem Proje",
    }
    columns = altmenu_columns.get(altmenu)
    menu_name = altmenu_names.get(altmenu, "Not")
    if columns is None:
        return None, None, None

    # Ana PDF dosyasını bul
    files = sorted(
        [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().endswith(".pdf") and not f.lower().startswith("scale_")],
        key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)),
        reverse=True
    )
    if not files:
        return None, None, None
    pdf_path = os.path.join(UPLOAD_FOLDER, files[0])

    # Ölçek PDF dosyasını bul
    scale_files = sorted(
        [f for f in os.listdir(UPLOAD_FOLDER) if f.lower().startswith("scale_") and f.lower().endswith(".pdf")],
        key=lambda x: os.path.getmtime(os.path.join(UPLOAD_FOLDER, x)),
        reverse=True
    )
    scale_headers = []
    if scale_files:
        scale_pdf_path = os.path.join(UPLOAD_FOLDER, scale_files[0])
        with pdfplumber.open(scale_pdf_path) as scale_pdf:
            for page in scale_pdf.pages:
                table = page.extract_table()
                if table and len(table) > 0:
                    # 4. sütundaki başlık gibi: harfler arası boşluklı ve reverse (örn: "ABC" -> "C B A")
                    def vertical_like_col4_reverse(text):
                        if not text:
                            return ""
                        return "".join(list(str(text))[::-1])
                    scale_headers = [vertical_like_col4_reverse(h) if h else "" for h in table[0]]
                    break

    data = []
    headers = []
    kriterler = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table and len(table) > 2:
                merged_headers = []
                for idx, col in enumerate(columns):
                    if idx == 0:
                        merged_headers.append("SIRA NO")
                    elif idx == 1:
                        merged_headers.append("NO")
                    elif idx == 2:
                        merged_headers.append("ADI SOYADI")
                    elif idx == 3:
                        merged_headers.append(menu_name)
                if scale_headers:
                    merged_headers.extend(scale_headers)
                    kriterler = scale_headers
                while len(merged_headers) < 24:
                    merged_headers.append("")
                headers = merged_headers
                ana_data = []
                for row in table[2:]:
                    if len(row) > max(columns):
                        ana_data.append([row[i] for i in columns])
                data.clear()
                for row in ana_data:
                    while len(row) < 4:
                        row.append("")
                    value = row[3]
                    n = 20  # 5-24 arası 20 sütun
                    dagilim = []
                    # 1 ile 5 arası sayı kullanarak dağıtım
                    if value and str(value).isdigit():
                        toplam = int(value)
                        dagilim = [1] * n  # Her sütuna önce 1 ver
                        kalan = toplam - n
                        idx = 0
                        # Sırayla 1 artırarak 5'i geçmeden dağıt
                        while kalan > 0:
                            if dagilim[idx] < 5:
                                dagilim[idx] += 1
                                kalan -= 1
                            idx = (idx + 1) % n
                        dagilim = [str(x) for x in dagilim]
                    else:
                        dagilim = ["0"] * n
                    new_row = row[:4] + dagilim
                    while len(new_row) < 24:
                        new_row.append("")
                    data.append(new_row)
                break
    return headers, data, f"{len(data)} satır veri bulundu." if data else None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Ana PDF yükleme alanı
        if "file" in request.files and request.files["file"].filename != "":
            file = request.files["file"]
            if allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                flash("Dosya başarıyla yüklendi.")
                return redirect(url_for("index"))
            else:
                flash("Sadece PDF dosyası yükleyebilirsiniz.")
                return redirect(request.url)
        # Ölçek ekle dosya yükleme kontrolü
        if request.method == "POST":
            if "file" in request.files and request.files["file"].filename != "":
                file = request.files["file"]
                if allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                    flash("Dosya başarıyla yüklendi.")
                    return redirect(url_for("index"))
                else:
                    flash("Sadece PDF dosyası yükleyebilirsiniz.")
                    return redirect(request.url)
            if "scale_file" in request.files and request.files["scale_file"].filename != "":
                scale_file = request.files["scale_file"]
                if allowed_file(scale_file.filename):
                    scale_filename = secure_filename("scale_" + scale_file.filename)
                    scale_file.save(os.path.join(app.config["UPLOAD_FOLDER"], scale_filename))
                    flash("Ölçek dosyası başarıyla yüklendi.")
                else:
                    flash("Sadece PDF dosyası yükleyebilirsiniz. (Ölçek)")
    headers, data, info = get_merged_table("1donem_dersici1")
    # index.html artık ana klasörde, send_from_directory ile gönder
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), "index.html")

@app.route("/get_data", methods=["POST"])
def get_data():
    altmenu = None
    teacher_name = ""
    if request.is_json:
        altmenu = request.json.get("altmenu")
        teacher_name = request.json.get("teacherName", "")
    if not altmenu:
        altmenu = request.form.get("altmenu")
    if not teacher_name:
        teacher_name = request.form.get("teacherName", "")
    if not altmenu:
        altmenu = request.args.get("altmenu")
    if not teacher_name:
        teacher_name = request.args.get("teacherName", "")
    if not altmenu:
        return jsonify({"error": "Alt menü bilgisi alınamadı."}), 400

    altmenu_columns = {
        "1donem_dersici1": [0, 1, 2, 9],
        "1donem_dersici2": [0, 1, 2, 10],
        "1donem_dersici3": [0, 1, 2, 11],
        "2donem_dersici1": [0, 1, 2, 21],
        "2donem_dersici2": [0, 1, 2, 22],
        "2donem_dersici3": [0, 1, 2, 23],
        "2donem_proje":    [0, 1, 2, 19],
    }
    altmenu_names = {
        "1donem_dersici1": "1. Dönem Dersiçi 1",
        "1donem_dersici2": "1. Dönem Dersiçi 2",
        "1donem_dersici3": "1. Dönem Dersiçi 3",
        "2donem_dersici1": "2. Dönem Dersiçi 1",
        "2donem_dersici2": "2. Dönem Dersiçi 2",
        "2donem_dersici3": "2. Dönem Dersiçi 3",
        "2donem_proje":    "2. Dönem Proje",
    }
    columns = altmenu_columns.get(str(altmenu).strip())
    menu_name = altmenu_names.get(str(altmenu).strip(), "Not")
    if columns is None:
        return jsonify({"error": "Geçersiz alt menü seçimi."}), 400

    # Ana PDF dosyasını bul
    files = sorted(
        [f for f in os.listdir(app.config["UPLOAD_FOLDER"]) if f.lower().endswith(".pdf") and not f.lower().startswith("scale_")],
        key=lambda x: os.path.getmtime(os.path.join(app.config["UPLOAD_FOLDER"], x)),
        reverse=True
    )
    if not files:
        return jsonify({"error": "Yüklü PDF dosyası bulunamadı."}), 400
    pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], files[0])

    # Ölçek PDF dosyasını bul
    scale_files = sorted(
        [f for f in os.listdir(app.config["UPLOAD_FOLDER"]) if f.lower().startswith("scale_") and f.lower().endswith(".pdf")],
        key=lambda x: os.path.getmtime(os.path.join(app.config["UPLOAD_FOLDER"], x)),
        reverse=True
    )
    scale_headers = []
    if scale_files:
        scale_pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], scale_files[0])
        with pdfplumber.open(scale_pdf_path) as scale_pdf:
            for page in scale_pdf.pages:
                table = page.extract_table()
                if table and len(table) > 0:
                    def vertical_like_col4_reverse(text):
                        if not text:
                            return ""
                        return " ".join(list(str(text))[::-1])
                    scale_headers = [vertical_like_col4_reverse(h) if h else "" for h in table[0]]
                    break
    try:
        all_pages = []
        with pdfplumber.open(pdf_path) as pdf:
            # Her sayfa için ayrı bir tablo oluştur
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                table = page.extract_table()
                page_obj = {
                    "headers": [],
                    "data": [],
                    "info": "",
                    "pdf_title_lines": [],
                    "pdf_footer_line": "",
                    "teacher_name": teacher_name
                }
                if table and len(table) > 2:
                    merged_headers = []
                    for idx, col in enumerate(columns):
                        if idx == 0:
                            merged_headers.append("SIRA NO")
                        elif idx == 1:
                            merged_headers.append("NO")
                        elif idx == 2:
                            merged_headers.append("ADI SOYADI")
                        elif idx == 3:
                            merged_headers.append(menu_name)
                    if scale_headers:
                        merged_headers.extend(scale_headers)
                    while len(merged_headers) < 24:
                        merged_headers.append("")
                    page_obj["headers"] = merged_headers
                    ana_data = []
                    for row in table[2:]:
                        if len(row) > max(columns):
                            # 2. dönem proje için 4. sütun boşsa satırı gösterme
                            if str(altmenu).strip() == "2donem_proje" and (not row[columns[3]] or str(row[columns[3]]).strip() == ""):
                                continue
                            ana_data.append([row[i] for i in columns])
                    page_obj["data"] = []
                    for row in ana_data:
                        while len(row) < 4:
                            row.append("")
                        value = row[3]
                        n = 20  # 5-24 arası 20 sütun
                        # 4. sütun boşsa sadece ilk 4 sütunu ekle, 5-24'e 0 ekleme
                        if not value or not str(value).isdigit():
                            new_row = row[:4]
                        else:
                            toplam = int(value)
                            dagilim = [1] * n
                            kalan = toplam - n
                            idx = 0
                            while kalan > 0:
                                if dagilim[idx] < 5:
                                    dagilim[idx] += 1
                                    kalan -= 1
                                idx = (idx + 1) % n
                            dagilim = [str(x) for x in dagilim]
                            new_row = row[:4] + dagilim
                        while len(new_row) < 24:
                            new_row.append("")
                        page_obj["data"].append(new_row)
                    # En alttaki tamamen boş (tüm hücreleri boş veya "") satırı kaldır
                    while page_obj["data"]:
                        last_row = page_obj["data"][-1]
                        if all((str(x).strip() == "") for x in last_row):
                            page_obj["data"].pop()
                        else:
                            break
                    # Tablo altına hiçbir ek veri ekleme (footer veya öğretmen adı dahil değil)
                    page_obj["pdf_footer_line"] = ""
                    page_obj["info"] = f"{len(page_obj['data'])} satır veri bulundu." if page_obj["data"] else ""
                    # Başlık
                    tablo_baslik = table[0][0] if table[0][0] else ""
                    if tablo_baslik and tablo_baslik in page_text:
                        idx = page_text.find(tablo_baslik)
                        title_text = page_text[:idx].strip()
                        title_lines = [line.strip() for line in title_text.splitlines() if line.strip()]
                        page_obj["pdf_title_lines"] = title_lines[:4]
                    else:
                        title_lines = [line.strip() for line in page_text.splitlines() if line.strip()]
                        page_obj["pdf_title_lines"] = title_lines[:4]
                all_pages.append(page_obj)
        # En az bir sayfada veri yoksa hata döndür
        if not any(p["data"] for p in all_pages):
            return jsonify({"error": "PDF'den tablo veya veri bulunamadı. PDF dosyanızda tablo olduğundan ve ilgili sütunların olduğundan emin olun."}), 400
        return jsonify({"pages": all_pages, "teacher_name": teacher_name})
    except Exception as e:
        return jsonify({"error": f"PDF okunurken hata: {str(e)}"}), 500

@app.route("/get_scale", methods=["POST"])
def get_scale():
    # Son yüklenen ölçek dosyasını bul
    files = sorted(
        [f for f in os.listdir(app.config["UPLOAD_FOLDER"]) if f.lower().startswith("scale_") and f.lower().endswith(".pdf")],
        key=lambda x: os.path.getmtime(os.path.join(app.config["UPLOAD_FOLDER"], x)),
        reverse=True
    )
    if not files:
        return jsonify({"error": "Yüklü ölçek PDF dosyası bulunamadı."}), 400
    pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], files[0])
    try:
        data = []
        headers = []
        table_found = False
        first_row = []
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                table = page.extract_table()
                if table and len(table) > 0:
                    table_found = True
                    first_row = table[0]
                    # Tüm başlıkları ve verileri eksiksiz al, hücrelerdeki satır sonlarını <br> ile değiştir
                    headers = [str(h).replace('\n', '<br>').replace('\r', '<br>').strip() if h else "" for h in table[0]]
                    for row in table[1:]:
                        data.append([str(cell).replace('\n', '<br>').replace('\r', '<br>').strip() if cell else "" for cell in row])
                    break
        if not table_found:
            return jsonify({"error": "Ölçek PDF'de hiç tablo bulunamadı. Lütfen PDF'inizde tablo olduğundan emin olun."}), 400
        if not data:
            msg = (
                f"Ölçek PDF'de tablo bulundu ancak veri yok. "
                f"Bulunan tablo sütun sayısı: {len(first_row) if first_row else 0}.<br>"
                f"Tablo başlıkları: {first_row if first_row else 'Yok'}"
            )
            return jsonify({"error": msg}), 400
        return jsonify({"headers": headers, "data": data})
    except Exception as e:
        return jsonify({"error": f"Ölçek PDF okunurken hata: {str(e)}"}), 500

@app.route("/get_main_pdf", methods=["POST"])
def get_main_pdf():
    # Son yüklenen ana PDF dosyasını bul
    files = sorted(
        [f for f in os.listdir(app.config["UPLOAD_FOLDER"]) if f.lower().endswith(".pdf") and not f.lower().startswith("scale_")],
        key=lambda x: os.path.getmtime(os.path.join(app.config["UPLOAD_FOLDER"], x)),
        reverse=True
    )
    if not files:
        return jsonify({"error": "Yüklü ana PDF dosyası bulunamadı."}), 400
    pdf_path = os.path.join(app.config["UPLOAD_FOLDER"], files[0])
    try:
        all_pages = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                table = page.extract_table()
                page_obj = {
                    "headers": [],
                    "data": [],
                    "title": "",
                    "footer_left": "",
                    "footer_right": "",
                    "footer_left2": "",
                    "footer_right2": ""
                }
                if table and len(table) > 0:
                    page_obj["headers"] = table[0]
                    # Başlık
                    tablo_baslik = table[0][0] if table[0][0] else ""
                    if tablo_baslik and tablo_baslik in page_text:
                        idx = page_text.find(tablo_baslik)
                        page_obj["title"] = page_text[:idx].strip()
                        tablo_end_idx = idx + len(tablo_baslik)
                        footer_text = page_text[tablo_end_idx:].strip()
                        footer_lines = [line.strip() for line in footer_text.splitlines() if line.strip()]
                        # Sola ve sağa ait verileri ayır
                        for i, line in enumerate(footer_lines):
                            upper_line = line.upper()
                            if "NİMET KAPLAN" in upper_line:
                                page_obj["footer_left"] = line
                                if i+1 < len(footer_lines):
                                    next_line = footer_lines[i+1].upper()
                                    if "DERS ÖĞRETMENİ" in next_line:
                                        page_obj["footer_left2"] = footer_lines[i+1]
                            if "SÜLEYMAN YOLCU" in upper_line:
                                page_obj["footer_right"] = line
                                if i+1 < len(footer_lines):
                                    next_line = footer_lines[i+1].upper()
                                    if "OKUL MÜDÜRÜ" in next_line:
                                        page_obj["footer_right2"] = footer_lines[i+1]
                    else:
                        page_obj["title"] = page_text.strip()
                    # Tablo verileri
                    for row in table[1:]:
                        page_obj["data"].append(row)
                all_pages.append(page_obj)
        return jsonify({"pages": all_pages})
    except Exception as e:
        return jsonify({"error": f"Ana PDF okunurken hata: {str(e)}"}), 500

if __name__ == "__main__":
    # Flask uygulamasını production için çalıştırmak yerine, paketleme için aşağıdaki gibi bırakabilirsiniz.
    # Uygulamanızı paketlemek için aşağıdaki adımları izleyin:
    #
    # 1. GEREKLİ DOSYALAR:
    #    - app.py (bu dosya)
    #    - index.html (artık ana klasörde)
    #    - uploads/ (PDF dosyalarının yükleneceği klasör, boş bırakılabilir)
    #    - requirements.txt (aşağıda örneği var)
    #
    # 2. requirements.txt OLUŞTURUN:
    #    Flask
    #    pdfplumber
    #    pandas
    #    Werkzeug
    #
    # 3. PAKETLEME:
    #    - Tüm dosyaları bir klasöre koyun (ör: not_uygulamasi/)
    #    - requirements.txt dosyasını da ekleyin.
    #    - uploads/ klasörü boş da olsa ekli olmalı.
    #
    # 4. ÇALIŞTIRMA:
    #    - Sanal ortam oluşturun (opsiyonel ama önerilir):
    #        python -m venv venv
    #        venv\Scripts\activate  (Windows)
    #    - Gereksinimleri yükleyin:
    #        pip install -r requirements.txt
    #    - Uygulamayı başlatın:
    #        python app.py
    #
    # 5. TAR/GZ/ZIP ile arşivleyip paylaşabilirsiniz.
    #
    # 6. NOT: index.html dosyası artık ana klasörde olmalı, templates/ klasörü kullanılmıyor.
    #
    app.run(debug=True)
