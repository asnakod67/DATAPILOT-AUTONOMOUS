from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
import pandas as pd
import numpy as np
import io, os, re, json, math
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
ALLOWED = {'.csv', '.tsv', '.txt', '.xlsx', '.xls'}


def clean_value(v):
    if pd.isna(v): return None
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating, float)):
        return None if not math.isfinite(float(v)) else float(v)
    if isinstance(v, (np.bool_,)): return bool(v)
    if isinstance(v, (pd.Timestamp, datetime)): return v.isoformat()
    return str(v) if not isinstance(v, (str, int, bool)) else v


def load_dataframe(file_storage):
    name = secure_filename(file_storage.filename or 'dataset.csv')
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED:
        raise ValueError('Please upload a CSV, TSV, TXT, XLSX, or XLS file.')
    raw = file_storage.read()
    if not raw: raise ValueError('The selected file is empty.')
    bio = io.BytesIO(raw)
    if ext in {'.xlsx', '.xls'}:
        df = pd.read_excel(bio, sheet_name=0)
    else:
        try:
            df = pd.read_csv(bio, sep='\t' if ext == '.tsv' else None, engine='python')
        except Exception:
            bio.seek(0); df = pd.read_csv(bio, encoding='latin-1')
    if df.empty or len(df.columns) == 0:
        raise ValueError('No usable rows or columns were found in this file.')
    if len(df) > 200000 or len(df.columns) > 150:
        raise ValueError('For this demo, datasets are limited to 200,000 rows and 150 columns.')
    df.columns = [str(c).strip() or f'Column_{i+1}' for i, c in enumerate(df.columns)]
    # Keep original data and infer numeric/date candidates conservatively.
    for c in df.columns:
        if df[c].dtype == object:
            s = df[c].astype(str).str.strip()
            nonempty = s.ne('') & s.ne('nan')
            if nonempty.sum() and s[nonempty].str.replace(r'[,₹$€£% ]', '', regex=True).str.match(r'^-?\d+(\.\d+)?$').mean() >= .85:
                cleaned = s.str.replace(r'[,₹$€£% ]', '', regex=True)
                df[c] = pd.to_numeric(cleaned, errors='coerce')
    return df, name


def describe_df(df):
    numeric = [str(c) for c in df.select_dtypes(include=[np.number]).columns]
    categorical = [str(c) for c in df.columns if c not in numeric]
    missing = int(df.isna().sum().sum())
    dupes = int(df.duplicated().sum())
    total_cells = max(1, int(df.shape[0] * df.shape[1]))
    quality = max(0, round(100 * (1 - (missing + dupes * max(1, df.shape[1])) / total_cells)))
    stats = {}
    for c in numeric:
        s = pd.to_numeric(df[c], errors='coerce').dropna()
        if len(s):
            stats[c] = {'count': int(len(s)), 'sum': clean_value(s.sum()), 'mean': clean_value(s.mean()),
                        'median': clean_value(s.median()), 'min': clean_value(s.min()), 'max': clean_value(s.max()),
                        'std': clean_value(s.std())}
    preview = [{str(k): clean_value(v) for k, v in row.items()} for row in df.head(12).to_dict(orient='records')]
    columns = []
    for c in df.columns:
        nonnull = df[c].dropna()
        columns.append({'name': str(c), 'type': 'numeric' if c in numeric else ('date' if re.search(r'date|time', str(c), re.I) else 'text'),
                        'missing': int(df[c].isna().sum()), 'unique': int(df[c].nunique(dropna=True)),
                        'sample': clean_value(nonnull.iloc[0]) if len(nonnull) else None})
    return {'filename': None, 'rows': int(len(df)), 'column_count': int(len(df.columns)), 'columns': columns,
            'numeric_columns': numeric, 'categorical_columns': categorical, 'missing_cells': missing,
            'duplicate_rows': dupes, 'quality_score': quality, 'stats': stats, 'preview': preview}


def aggregate(df, category, measure, operation='sum', limit=12):
    if category not in df.columns or measure not in df.columns: raise ValueError('Choose a valid category and measure.')
    temp = df[[category, measure]].copy()
    temp[measure] = pd.to_numeric(temp[measure], errors='coerce')
    temp[category] = temp[category].fillna('(Blank)').astype(str).replace('', '(Blank)')
    temp = temp.dropna(subset=[measure])
    if operation == 'mean': result = temp.groupby(category, dropna=False)[measure].mean()
    elif operation == 'count': result = temp.groupby(category, dropna=False)[measure].count()
    else: result = temp.groupby(category, dropna=False)[measure].sum()
    result = result.sort_values(ascending=False).head(limit)
    return [{'label': str(k), 'value': clean_value(v)} for k, v in result.items()]


def analyze_question(df, question, numeric, categorical):
    q = (question or '').lower()
    findings = []
    if not question.strip():
        return [{'title':'Start with a business question','detail':'Try asking which category leads, how a metric changes over time, or where data quality needs attention.','kind':'tip'}]
    metric = next((c for c in numeric if any(w in q for w in c.lower().replace('_',' ').split()) or c.lower() in q), None)
    if not metric:
        metric = next((c for c in numeric if re.search(r'revenue|sales|profit|amount|cost|price|spend|total', c, re.I)), numeric[0] if numeric else None)
    cat = next((c for c in categorical if c.lower() in q), None)
    if not cat:
        cat = next((c for c in categorical if re.search(r'region|category|product|channel|segment|department|country|city', c, re.I)), categorical[0] if categorical else None)
    if re.search(r'missing|null|blank|quality|duplicate|clean', q):
        findings.append({'title':'Data quality check','detail':f"There are {int(df.isna().sum().sum()):,} missing cells and {int(df.duplicated().sum()):,} exact duplicate rows. Review blanks before drawing conclusions.",'kind':'quality'})
    if metric:
        s = pd.to_numeric(df[metric], errors='coerce').dropna()
        if len(s):
            if re.search(r'average|mean', q): label, val = 'Average', s.mean()
            elif re.search(r'minimum|lowest|smallest', q): label, val = 'Lowest value', s.min()
            elif re.search(r'maximum|highest|largest|top|best|lead', q): label, val = 'Highest value', s.max()
            else: label, val = 'Total', s.sum()
            findings.append({'title':f'{label}: {metric}','detail':f'{label} is {val:,.2f}, calculated from {len(s):,} valid numeric values.','kind':'metric'})
            if cat:
                try:
                    grouped = aggregate(df, cat, metric, 'mean' if re.search(r'average|mean', q) else 'sum', 1)
                    if grouped:
                        findings.append({'title':f"Leading {cat}: {grouped[0]['label']}",'detail':f"This group has the highest {'average' if re.search(r'average|mean', q) else 'total'} {metric} ({grouped[0]['value']:,.2f}). This is an association in the uploaded data, not proof of cause.",'kind':'insight'})
                except Exception: pass
    if not findings:
        findings.append({'title':'Question captured','detail':'The current built-in analyst supports descriptive summaries and common comparisons. Try asking “Which region has the highest revenue?”, “What is the average profit?”, or “Are there missing values?”','kind':'tip'})
    return findings

@app.route('/')
def home(): return render_template('index.html')

@app.route('/api/health')
def health(): return jsonify({'ok': True, 'service':'DATAPILOT analysis API', 'version':'1.0'})

@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    try:
        if 'file' not in request.files: return jsonify({'error':'Choose a dataset file first.'}), 400
        df, filename = load_dataframe(request.files['file'])
        profile = describe_df(df); profile['filename'] = filename
        question = request.form.get('question', '')
        profile['findings'] = analyze_question(df, question, profile['numeric_columns'], profile['categorical_columns'])
        # Include date-like fields only when parseable enough to be useful.
        profile['date_columns'] = []
        for c in df.columns:
            if re.search(r'date|time', str(c), re.I):
                parsed = pd.to_datetime(df[c], errors='coerce')
                if parsed.notna().sum() >= max(2, int(len(df)*.25)): profile['date_columns'].append(str(c))
        return jsonify(profile)
    except Exception as e:
        return jsonify({'error': str(e) if isinstance(e, ValueError) else 'Unable to analyze this file. Check that it is a valid spreadsheet or delimited text file.'}), 400

@app.route('/api/chart', methods=['POST'])
def api_chart():
    try:
        if 'file' not in request.files: return jsonify({'error':'Upload a file first.'}), 400
        df, _ = load_dataframe(request.files['file'])
        category = request.form.get('category', '')
        measure = request.form.get('measure', '')
        operation = request.form.get('operation', 'sum')
        grouped = aggregate(df, category, measure, operation, 12)
        return jsonify({'category':category, 'measure':measure, 'operation':operation, 'data':grouped})
    except Exception as e:
        return jsonify({'error': str(e) if isinstance(e, ValueError) else 'Unable to build this chart.'}), 400

@app.route('/api/export', methods=['POST'])
def api_export():
    try:
        if 'file' not in request.files: return jsonify({'error':'Upload a file first.'}), 400
        df, filename = load_dataframe(request.files['file'])
        profile = describe_df(df)
        summary = pd.DataFrame([{'Column':c, **s} for c,s in profile['stats'].items()])
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as writer:
            summary.to_excel(writer, index=False, sheet_name='Numeric Summary')
            pd.DataFrame(profile['columns']).to_excel(writer, index=False, sheet_name='Data Quality')
            df.head(5000).to_excel(writer, index=False, sheet_name='Data Preview')
            notes = pd.DataFrame([['Source file', filename], ['Rows', profile['rows']], ['Columns', profile['column_count']], ['Missing cells', profile['missing_cells']], ['Exact duplicate rows', profile['duplicate_rows']], ['Heuristic quality score', f"{profile['quality_score']}%"], ['Generated at', datetime.now().isoformat(timespec='seconds')], ['Note', 'Descriptive analysis only. Review data definitions before business decisions.']], columns=['Item','Value'])
            notes.to_excel(writer, index=False, sheet_name='Report Notes')
            for ws in writer.book.worksheets:
                ws.freeze_panes = 'A2'; ws.auto_filter.ref = ws.dimensions
                for cell in ws[1]:
                    cell.font = cell.font.copy(bold=True, color='FFFFFF')
                    from openpyxl.styles import PatternFill
                    cell.fill = PatternFill('solid', fgColor='27364B')
                for col in ws.columns:
                    letter = col[0].column_letter
                    ws.column_dimensions[letter].width = min(max(max(len(str(c.value or '')) for c in col)+2, 12), 36)
        out.seek(0)
        return send_file(out, as_attachment=True, download_name='DATAPILOT_Analysis_Report.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        return jsonify({'error': str(e) if isinstance(e, ValueError) else 'Unable to export this report.'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
