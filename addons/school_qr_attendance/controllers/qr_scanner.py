# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, date

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

KIOSK_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>كشك الحضور - {title}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #1a1a2e;
    color: #eee;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100vh;
  }}
  .header {{
    width: 100%;
    background: #16213e;
    padding: 14px 20px;
    text-align: center;
    border-bottom: 3px solid #0f3460;
  }}
  .header h1 {{ font-size: 1.4rem; color: #e94560; }}
  .header p {{ font-size: 0.9rem; color: #aaa; margin-top: 4px; }}
  .camera-wrap {{
    position: relative;
    margin: 20px auto;
    width: min(90vw, 420px);
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 0 30px rgba(233,69,96,0.4);
  }}
  #video {{
    width: 100%;
    display: block;
    transform: scaleX(-1);
  }}
  .scan-line {{
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: #e94560;
    animation: scan 2s linear infinite;
    box-shadow: 0 0 10px #e94560;
  }}
  @keyframes scan {{
    0%   {{ top: 0; }}
    50%  {{ top: calc(100% - 3px); }}
    100% {{ top: 0; }}
  }}
  .corners::before, .corners::after {{
    content: '';
    position: absolute;
    width: 30px; height: 30px;
    border-color: #e94560;
    border-style: solid;
  }}
  .corners::before {{ top: 10px; right: 10px; border-width: 3px 3px 0 0; }}
  .corners::after  {{ top: 10px; left: 10px;  border-width: 3px 0 0 3px; }}
  .result-box {{
    width: min(90vw, 420px);
    margin: 0 auto 20px;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    font-size: 1.1rem;
    font-weight: bold;
    min-height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
  }}
  .result-waiting {{ background: #16213e; color: #aaa; border: 2px dashed #444; }}
  .result-success {{ background: #0f3d2e; color: #4caf50; border: 2px solid #4caf50; }}
  .result-warning {{ background: #3d2b0f; color: #ff9800; border: 2px solid #ff9800; }}
  .result-error   {{ background: #3d0f0f; color: #f44336; border: 2px solid #f44336; }}
  .stats {{
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
  }}
  .stat-card {{
    background: #16213e;
    border-radius: 8px;
    padding: 12px 20px;
    text-align: center;
    flex: 1;
  }}
  .stat-card .num {{ font-size: 2rem; font-weight: bold; color: #e94560; }}
  .stat-card .lbl {{ font-size: 0.8rem; color: #aaa; }}
  canvas {{ display: none; }}
  .mode-badge {{
    display: inline-block;
    background: #0f3460;
    color: #e94560;
    border-radius: 20px;
    padding: 3px 12px;
    font-size: 0.8rem;
    margin-top: 4px;
  }}
</style>
</head>
<body>
<div class="header">
  <h1>📡 كشك الحضور والانصراف</h1>
  <p>{title}</p>
  <span class="mode-badge">{mode_label}</span>
</div>

<div class="camera-wrap">
  <video id="video" autoplay playsinline muted></video>
  <div class="scan-line"></div>
  <div class="corners"></div>
</div>

<div class="stats" style="width:min(90vw,420px);margin:0 auto 16px;">
  <div class="stat-card">
    <div class="num" id="scan-count">0</div>
    <div class="lbl">عمليات مسح ناجحة</div>
  </div>
  <div class="stat-card">
    <div class="num" id="current-time">--:--</div>
    <div class="lbl">الوقت الحالي</div>
  </div>
</div>

<div class="result-box result-waiting" id="result">
  📷 وجّه الكاميرا نحو رمز QR
</div>

<canvas id="canvas"></canvas>

<script src="/school_qr_attendance/static/src/js/jsQR.min.js"></script>
<script>
const SESSION_ID = {session_id_js};
const MODE = "{mode_js}";
const SCAN_URL = "/school/qr/scan";

let scanCount = 0;
let scanning = true;
let lastCode = null;
let lastCodeTime = 0;

const video = document.getElementById('video');
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const resultBox = document.getElementById('result');
const scanCountEl = document.getElementById('scan-count');

// Clock
function updateClock() {{
  const now = new Date();
  const h = String(now.getHours()).padStart(2,'0');
  const m = String(now.getMinutes()).padStart(2,'0');
  document.getElementById('current-time').textContent = h + ':' + m;
}}
setInterval(updateClock, 1000);
updateClock();

// Start camera
navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'environment' }} }})
  .then(stream => {{ video.srcObject = stream; }})
  .catch(() => {{
    navigator.mediaDevices.getUserMedia({{ video: true }})
      .then(stream => {{ video.srcObject = stream; }})
      .catch(e => showResult('❌ لا يمكن الوصول للكاميرا: ' + e.message, 'error'));
  }});

function showResult(msg, type) {{
  resultBox.className = 'result-box result-' + type;
  resultBox.textContent = msg;
}}

function scanFrame() {{
  if (video.readyState === video.HAVE_ENOUGH_DATA) {{
    canvas.height = video.videoHeight;
    canvas.width  = video.videoWidth;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const code = jsQR(imageData.data, imageData.width, imageData.height, {{
      inversionAttempts: 'dontInvert',
    }});
    if (code) {{
      const now = Date.now();
      // debounce: same code within 4 seconds ignored
      if (code.data !== lastCode || (now - lastCodeTime) > 4000) {{
        lastCode = code.data;
        lastCodeTime = now;
        if (scanning) {{
          scanning = false;
          processScan(code.data);
        }}
      }}
    }}
  }}
  requestAnimationFrame(scanFrame);
}}
requestAnimationFrame(scanFrame);

function processScan(qrData) {{
  showResult('⏳ جاري التحقق...', 'waiting');
  const payload = {{ qr_data: qrData, session_id: SESSION_ID, mode: MODE }};

  fetch(SCAN_URL, {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify(payload),
  }})
  .then(r => r.json())
  .then(data => {{
    if (data.success) {{
      scanCount++;
      scanCountEl.textContent = scanCount;
      showResult(data.message, 'success');
    }} else {{
      showResult(data.message, data.warning ? 'warning' : 'error');
    }}
  }})
  .catch(() => {{
    showResult('❌ خطأ في الاتصال بالخادم', 'error');
  }})
  .finally(() => {{
    setTimeout(() => {{
      scanning = true;
      showResult('📷 وجّه الكاميرا نحو رمز QR', 'waiting');
    }}, 3000);
  }});
}}
</script>
</body>
</html>"""


class QrScannerController(http.Controller):

    @http.route('/school/qr/scanner', type='http', auth='public', website=False)
    def kiosk_page(self, session_id=None, mode=None, **kw):
        if mode == 'teacher':
            title = f"كشك حضور المعلمين — {date.today().strftime('%Y/%m/%d')}"
            mode_label = "وضع المعلمين — دخول / خروج"
            session_id_js = 'null'
            mode_js = 'teacher'
        elif session_id:
            try:
                session = request.env['school.qr.session'].sudo().browse(int(session_id))
                if not session.exists():
                    return request.make_response("جلسة غير موجودة", status=404)
                class_name = session.class_id.name or ''
                teacher_name = session.teacher_id.name or ''
                title = f"{session.name} — {teacher_name}"
                if session.state == 'closed':
                    title += " [مغلقة]"
                mode_label = f"وضع الطلاب — {class_name}"
                session_id_js = str(int(session_id))
                mode_js = 'student'
            except Exception:
                return request.make_response("معرّف الجلسة غير صالح", status=400)
        else:
            return request.make_response(
                "يرجى تحديد session_id أو mode=teacher", status=400
            )

        html = KIOSK_HTML.format(
            title=title,
            mode_label=mode_label,
            session_id_js=session_id_js,
            mode_js=mode_js,
        )
        return request.make_response(html, headers=[('Content-Type', 'text/html; charset=utf-8')])

    @http.route('/school/qr/scan', type='http', auth='public', methods=['POST'], csrf=False)
    def process_scan(self, **kw):
        try:
            body = json.loads(request.httprequest.data)
        except Exception:
            return self._json_response({'success': False, 'message': '❌ بيانات غير صالحة'})

        qr_data = body.get('qr_data', '').strip()
        session_id = body.get('session_id')
        mode = body.get('mode', 'student')

        if not qr_data:
            return self._json_response({'success': False, 'message': '❌ رمز QR فارغ'})

        if qr_data.startswith('STUDENT:'):
            return self._handle_student_scan(qr_data, session_id)
        elif qr_data.startswith('TEACHER:'):
            return self._handle_teacher_scan(qr_data)
        else:
            return self._json_response({
                'success': False,
                'message': '❌ رمز QR غير معروف'
            })

    def _handle_student_scan(self, qr_data, session_id):
        env = request.env
        qr_code = qr_data[len('STUDENT:'):]

        student = env['school.student'].sudo().search([('qr_code', '=', qr_code)], limit=1)
        if not student:
            return self._json_response({
                'success': False,
                'message': f'❌ لم يُعثر على طالب بهذا الرمز: {qr_code}'
            })

        if not session_id:
            return self._json_response({
                'success': False,
                'message': '❌ لا توجد جلسة محددة لتسجيل الحضور'
            })

        session = env['school.qr.session'].sudo().browse(int(session_id))
        if not session.exists():
            return self._json_response({'success': False, 'message': '❌ الجلسة غير موجودة'})
        if session.state == 'closed':
            return self._json_response({'success': False, 'message': '❌ الجلسة مغلقة'})

        today = fields.Date.today()
        existing = env['school.attendance'].sudo().search([
            ('student_id', '=', student.id),
            ('date', '=', today),
        ], limit=1)

        if existing:
            return self._json_response({
                'success': False,
                'warning': True,
                'message': f'⚠️ تم تسجيل حضور {student.name} مسبقاً اليوم',
                'name': student.name,
            })

        env['school.attendance'].sudo().create({
            'student_id': student.id,
            'class_id': session.class_id.id,
            'date': today,
            'status': 'present',
            'teacher_id': session.teacher_id.id if session.teacher_id else False,
            'qr_session_id': session.id,
            'source': 'qr',
        })

        return self._json_response({
            'success': True,
            'action': 'attendance',
            'name': student.name,
            'message': f'✅ تم تسجيل حضور: {student.name}',
        })

    def _handle_teacher_scan(self, qr_data):
        env = request.env
        qr_code = qr_data[len('TEACHER:'):]

        teacher = env['school.teacher'].sudo().search([('qr_code', '=', qr_code)], limit=1)
        if not teacher:
            return self._json_response({
                'success': False,
                'message': f'❌ لم يُعثر على معلم بهذا الرمز: {qr_code}'
            })

        today = fields.Date.today()
        existing = env['school.teacher.attendance'].sudo().search([
            ('teacher_id', '=', teacher.id),
            ('date', '=', today),
        ], limit=1)

        now = datetime.utcnow()

        if not existing:
            env['school.teacher.attendance'].sudo().create({
                'teacher_id': teacher.id,
                'date': today,
                'check_in': now,
                'source': 'qr',
            })
            local_hour = now.hour + 3  # AST = UTC+3
            time_str = f"{local_hour % 24:02d}:{now.minute:02d}"
            return self._json_response({
                'success': True,
                'action': 'check_in',
                'name': teacher.name,
                'message': f'✅ تم تسجيل دخول: {teacher.name}\n🕐 {time_str}',
            })

        if existing.check_in and not existing.check_out:
            existing.sudo().write({'check_out': now})
            local_hour = now.hour + 3
            time_str = f"{local_hour % 24:02d}:{now.minute:02d}"
            return self._json_response({
                'success': True,
                'action': 'check_out',
                'name': teacher.name,
                'message': f'✅ تم تسجيل خروج: {teacher.name}\n🕓 {time_str}',
            })

        return self._json_response({
            'success': False,
            'warning': True,
            'name': teacher.name,
            'message': f'⚠️ انتهى دوام {teacher.name} اليوم بالفعل',
        })

    def _json_response(self, data):
        return request.make_response(
            json.dumps(data, ensure_ascii=False),
            headers=[('Content-Type', 'application/json; charset=utf-8')]
        )
