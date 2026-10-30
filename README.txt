DATAPILOT AUTONOMOUS — FULL-STACK STARTER
========================================

WHAT'S INCLUDED
- Professional responsive frontend inspired by modern BI tools.
- Light/dark theme toggle in the top bar; the choice is remembered in this browser.
- Flask backend for file parsing, numeric summaries, missing-value/duplicate checks, category aggregation and Excel report export.
- Interactive bar and doughnut charts, KPI cards, plain-language findings, data preview and ranked summary.
- Sample Excel workbook in static/sample.xlsx.
- Upload processing is request-based; files are not stored in a database or written to disk by the app.

REQUIREMENTS
- Python 3.10 or newer
- Internet connection for the Google Fonts and Chart.js CDN used by the frontend

RUN ON WINDOWS
1. Extract the ZIP to a folder.
2. Open Command Prompt or PowerShell in that folder.
3. Create a virtual environment (recommended):
   py -m venv .venv
   .venv\Scripts\activate
4. Install dependencies:
   pip install -r requirements.txt
5. Start the app:
   python app.py
6. Open this address in your browser:
   http://127.0.0.1:5000
7. Click “Try sample data” or upload your own CSV/XLSX file.

RUN ON MAC / LINUX
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
Then open http://127.0.0.1:5000

API ROUTES
GET  /api/health  — backend health check
POST /api/analyze — multipart form: file, question
POST /api/chart   — multipart form: file, category, measure, operation (sum/mean/count)
POST /api/export  — multipart form: file; returns an Excel report

LIMITATIONS / HONEST SCOPE
- This is a working full-stack descriptive analytics starter, not a complete replacement for Power BI/Tableau or a human analyst.
- Natural-language question support is rule-based and handles common descriptive questions; it is not an LLM and will not reliably interpret arbitrary business questions.
- Excel analysis currently reads the first worksheet only. Multiple-file joins, database connectors, advanced statistics, causal analysis, forecasting, authentication, saved projects and cloud deployment are not included.
- The data-quality score is a simple heuristic, not a formal certification.
- Use localhost for personal testing. Before public deployment, add authentication, HTTPS, rate limits, logging, stricter privacy controls and deployment configuration.


PUBLISH ONLINE FOR FREE (RENDER)
1. Create a GitHub account if you do not already have one.
2. Create a NEW public repository named datapilot-autonomous.
3. Extract this ZIP. Upload the CONTENTS of the datapilot_autonomous folder to the repository root (app.py, requirements.txt, Procfile, render.yaml, templates/, static/, etc.).
4. Open https://dashboard.render.com/ and sign in using GitHub.
5. Choose New + > Web Service, connect the repository, and choose the Free plan.
6. Use build command: pip install -r requirements.txt
7. Use start command: gunicorn app:app --bind 0.0.0.0:$PORT
8. Click Create Web Service and wait for the build to finish. Render will provide a public https://...onrender.com address.

FREE HOSTING NOTES
- Render free web services can sleep after 15 minutes without traffic; the next visit may take around a minute to wake up.
- The free service has an ephemeral filesystem. This app does not persist uploaded files, which is appropriate for this prototype.
- This project has no login system. Do not upload confidential, regulated, or personal datasets to a public demo. Add authentication, rate limits, privacy controls and security review before inviting general users.
- The dashboard uses Chart.js and Google Fonts from CDNs, so those visual assets need internet access.
