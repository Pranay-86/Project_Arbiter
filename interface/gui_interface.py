"""
Arbiter GUI — Redesigned from scratch.

A premium dark chat interface inspired by Claude.ai and DeepSeek.
Features:
  - Sidebar with conversation history, new chat, model badge
  - Smooth animated message rendering with full Markdown support
  - Typewriter streaming effect
  - Animated thinking indicator
  - Code block rendering with language label
  - Clean centred content column
  - Polished input bar with focus border glow
  - Welcome screen with capability chips

pip install PyQt6
"""

import sys
import re
import html as html_lib
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextBrowser, QLineEdit, QPushButton, QLabel, QScrollArea,
    QFrame, QSizePolicy, QListWidget, QListWidgetItem, QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette

from config.config_loader import cfg

# ── Design tokens ──────────────────────────────────────────────────────────────
C_BG           = "#0f0f10"
C_BG_SIDEBAR   = "#0a0a0b"
C_BG_SURFACE   = "#161618"
C_BG_INPUT     = "#1c1c1f"
C_BG_USER_MSG  = "#1e1e24"
C_BORDER       = "#242428"
C_BORDER_FOCUS = "#5b5bd6"

C_ACCENT       = "#6366f1"
C_ACCENT_GLOW  = "#818cf8"
C_ACCENT_DIM   = "#3730a3"

C_TEXT_PRI     = "#e8e8ed"
C_TEXT_SEC     = "#8b8b99"
C_TEXT_DIM     = "#4b4b56"

C_CODE_BG      = "#0d0d10"
C_CODE_BORDER  = "#2a2a30"
C_CODE_TEXT    = "#a5b4fc"

C_SUCCESS      = "#34d399"
C_ERROR        = "#f87171"
C_THINKING     = "#818cf8"

SIDEBAR_W      = 260
CONTENT_W      = 740
FONT           = "DM Sans"
FONT_FALLBACK  = "Segoe UI"
MONO           = "JetBrains Mono"

IDENTITY = cfg.get("models.identity_name", "Arbiter")
MODEL_ID = cfg.get("models.default_model", "")


# ── Worker ─────────────────────────────────────────────────────────────────────
class AgentWorker(QThread):
    done  = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, agent, text):
        super().__init__()
        self.agent = agent
        self.text  = text

    def run(self):
        try:
            self.done.emit(str(self.agent.run(self.text)))
        except Exception as e:
            self.error.emit(str(e))


# ── Markdown → HTML ────────────────────────────────────────────────────────────
def _esc(t):
    return html_lib.escape(t)

def _inline(text):
    text = _esc(text)
    text = re.sub(r"\*\*(.+?)\*\*",
        rf'<strong style="color:{C_TEXT_PRI};font-weight:650;">\1</strong>', text)
    text = re.sub(r"\*(.+?)\*",
        rf'<em style="color:{C_TEXT_SEC};">\1</em>', text)
    text = re.sub(r"`(.+?)`",
        rf'<code style="background:{C_CODE_BG};color:{C_CODE_TEXT};'
        rf'font-family:{MONO},Consolas,monospace;font-size:8.5pt;'
        rf'padding:1px 6px;border-radius:4px;'
        rf'border:1px solid {C_CODE_BORDER};">\1</code>', text)
    return text

def md_to_html(text):
    lines, out = text.split("\n"), []
    in_code = in_list = in_ol = False

    for raw in lines:
        m_fence = re.match(r"^```(\w*)", raw.strip())
        if m_fence or raw.strip() == "```":
            if in_list:  out.append("</ul>"); in_list = False
            if in_ol:    out.append("</ol>"); in_ol = False
            if in_code:
                out.append("</code></pre></div>"); in_code = False
            else:
                lang = m_fence.group(1) if m_fence else ""
                lang_badge = (f'<span style="color:{C_TEXT_DIM};font-size:7.5pt;'
                              f'font-family:{MONO},monospace;float:right;">'
                              f'{lang.upper()}</span>') if lang else ""
                out.append(
                    f'<div style="position:relative;">'
                    f'<pre style="background:{C_CODE_BG};border:1px solid {C_CODE_BORDER};'
                    f'border-radius:10px;padding:14px 16px;margin:12px 0;overflow-x:auto;'
                    f'line-height:1.6;">{lang_badge}'
                    f'<code style="color:{C_CODE_TEXT};font-family:{MONO},Consolas,monospace;'
                    f'font-size:8.5pt;">')
                in_code = True
            continue

        if in_code:
            out.append(_esc(raw) + "\n"); continue

        line = raw
        m_ol = re.match(r"^(\d+)\.\s+(.+)", line.strip())
        if m_ol:
            if in_list: out.append("</ul>"); in_list = False
            if not in_ol:
                out.append(f'<ol style="margin:6px 0;padding-left:24px;color:{C_TEXT_PRI};">')
                in_ol = True
            out.append(f'<li style="margin:4px 0;line-height:1.7;">{_inline(m_ol.group(2))}</li>')
            continue
        else:
            if in_ol: out.append("</ol>"); in_ol = False

        if re.match(r"^[-•*]\s+", line.strip()):
            if not in_list:
                out.append(f'<ul style="margin:6px 0;padding-left:22px;">')
                in_list = True
            content = re.sub(r"^[-•*]\s+", "", line.strip())
            out.append(f'<li style="margin:4px 0;color:{C_TEXT_PRI};line-height:1.7;">{_inline(content)}</li>')
            continue
        else:
            if in_list: out.append("</ul>"); in_list = False

        if line.startswith("### "):
            out.append(f'<h3 style="color:{C_TEXT_PRI};font-size:12pt;font-weight:650;margin:16px 0 5px;">{_inline(line[4:])}</h3>'); continue
        if line.startswith("## "):
            out.append(f'<h2 style="color:{C_TEXT_PRI};font-size:14pt;font-weight:700;margin:18px 0 6px;">{_inline(line[3:])}</h2>'); continue
        if line.startswith("# "):
            out.append(f'<h1 style="color:{C_TEXT_PRI};font-size:16pt;font-weight:750;margin:20px 0 8px;">{_inline(line[2:])}</h1>'); continue

        if re.match(r"^[-_*]{3,}$", line.strip()):
            out.append(f'<hr style="border:none;border-top:1px solid {C_BORDER};margin:16px 0;">'); continue

        if line.strip().startswith("✓"):
            out.append(f'<p style="color:{C_SUCCESS};margin:3px 0;line-height:1.7;">{_inline(line)}</p>'); continue
        if line.strip().startswith(("✗", "⚠")):
            out.append(f'<p style="color:{C_ERROR};margin:3px 0;line-height:1.7;">{_inline(line)}</p>'); continue

        if not line.strip():
            out.append("<br>"); continue

        out.append(f'<p style="color:{C_TEXT_PRI};margin:2px 0;line-height:1.8;letter-spacing:0.1px;">{_inline(line)}</p>')

    if in_list: out.append("</ul>")
    if in_ol:   out.append("</ol>")
    if in_code: out.append("</code></pre></div>")
    return "\n".join(out)


# ── Streaming text ─────────────────────────────────────────────────────────────
class StreamText(QTextBrowser):
    tick = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full = ""
        self._idx  = 0
        self._tmr  = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self.setReadOnly(True)
        self.setOpenExternalLinks(False)
        self.setFont(QFont(FONT, 10))
        self.setStyleSheet(f"""
            QTextBrowser {{ background:transparent; color:{C_TEXT_PRI};
                border:none; padding:0; }}
            QScrollBar {{ width:0; height:0; }}
        """)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.document().setDocumentMargin(0)
        self.document().contentsChanged.connect(self._relayout)

    def stream(self, text, instant=False):
        self._full = text; self._idx = 0; self.clear()
        if instant or len(text) < 60: self._finish()
        else: self._tmr.start(8)

    def _step(self):
        step = min(6, len(self._full) - self._idx)
        if step <= 0: self._tmr.stop(); self._finish(); return
        self._idx += step
        self.setPlainText(self._full[:self._idx])
        self._relayout(); self.tick.emit()

    def _finish(self):
        self._tmr.stop()
        self.setHtml(md_to_html(self._full))
        self._relayout(); self.tick.emit()

    def _relayout(self):
        self.document().adjustSize()
        h = int(self.document().size().height()) + 4
        self.setFixedHeight(max(h, 20))


# ── Thinking indicator ─────────────────────────────────────────────────────────
class ThinkingRow(QWidget):
    def __init__(self):
        super().__init__()
        self._phase = 0
        self._tmr = QTimer(self); self._tmr.timeout.connect(self._tick)
        self._build()

    def _build(self):
        lay = QHBoxLayout(self); lay.setContentsMargins(0, 8, 0, 8)
        col = QWidget(); col.setMaximumWidth(CONTENT_W + 72)
        col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        inn = QHBoxLayout(col); inn.setContentsMargins(0, 0, 0, 0); inn.setSpacing(12)

        av = QLabel(IDENTITY[0].upper()); av.setFixedSize(34, 34)
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av.setFont(QFont(FONT, 11, QFont.Weight.Bold))
        av.setStyleSheet(f"background:{C_ACCENT_DIM};color:{C_ACCENT_GLOW};border-radius:17px;")
        inn.addWidget(av, alignment=Qt.AlignmentFlag.AlignTop)

        vcol = QVBoxLayout(); vcol.setSpacing(2)
        nm = QLabel(IDENTITY); nm.setFont(QFont(FONT, 9, QFont.Weight.Bold))
        nm.setStyleSheet(f"color:{C_TEXT_PRI};"); vcol.addWidget(nm)
        self._lbl = QLabel(); self._lbl.setFont(QFont(FONT, 9))
        self._lbl.setStyleSheet(f"color:{C_THINKING};"); vcol.addWidget(self._lbl)
        inn.addLayout(vcol); inn.addStretch()

        lay.addStretch(); lay.addWidget(col); lay.addStretch()
        self._tick()

    def _tick(self):
        f = ["Thinking ·", "Thinking · ·", "Thinking · · ·", "Thinking · ·"]
        self._lbl.setText(f[self._phase % len(f)]); self._phase += 1

    def start(self): self._phase = 0; self._tmr.start(450); self.show()
    def stop(self):  self._tmr.stop(); self.hide()


# ── Message row ────────────────────────────────────────────────────────────────
class MsgRow(QWidget):
    _tick = pyqtSignal()

    def __init__(self, text, role, ts, animate=False):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        outer = QHBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0); outer.setSpacing(0)
        col = QWidget(); col.setMaximumWidth(CONTENT_W + 72)
        col.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        vbox = QVBoxLayout(col); vbox.setContentsMargins(0, 20, 0, 8); vbox.setSpacing(0)
        self.setStyleSheet(f"background:{C_BG};")

        if role == "bot": self._bot(vbox, text, ts, animate)
        else: self._user(vbox, text, ts)

        outer.addStretch(); outer.addWidget(col); outer.addStretch()

    def _av(self, letter, bg, fg, size=34):
        av = QLabel(letter); av.setFixedSize(size, size)
        av.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av.setFont(QFont(FONT, 11, QFont.Weight.Bold))
        av.setStyleSheet(f"background:{bg};color:{fg};border-radius:{size//2}px;")
        return av

    def _bot(self, vbox, text, ts, animate):
        hdr = QHBoxLayout(); hdr.setSpacing(10); hdr.setContentsMargins(0, 0, 0, 8)
        hdr.addWidget(self._av(IDENTITY[0].upper(), C_ACCENT_DIM, C_ACCENT_GLOW),
                      alignment=Qt.AlignmentFlag.AlignVCenter)
        nm = QLabel(IDENTITY); nm.setFont(QFont(FONT, 9, QFont.Weight.Bold))
        nm.setStyleSheet(f"color:{C_TEXT_PRI};letter-spacing:0.3px;")
        hdr.addWidget(nm, alignment=Qt.AlignmentFlag.AlignVCenter)
        hdr.addStretch()
        tsl = QLabel(ts); tsl.setFont(QFont(FONT, 8))
        tsl.setStyleSheet(f"color:{C_TEXT_DIM};")
        hdr.addWidget(tsl, alignment=Qt.AlignmentFlag.AlignVCenter)
        vbox.addLayout(hdr)

        wrap = QHBoxLayout(); wrap.setContentsMargins(46, 0, 0, 16)
        body = StreamText(); body.tick.connect(self._tick); wrap.addWidget(body)
        vbox.addLayout(wrap); body.stream(text, instant=not animate)

    def _user(self, vbox, text, ts):
        hdr = QHBoxLayout(); hdr.setSpacing(10); hdr.setContentsMargins(0, 0, 0, 8)
        tsl = QLabel(ts); tsl.setFont(QFont(FONT, 8))
        tsl.setStyleSheet(f"color:{C_TEXT_DIM};")
        hdr.addWidget(tsl, alignment=Qt.AlignmentFlag.AlignVCenter)
        hdr.addStretch()
        nm = QLabel("You"); nm.setFont(QFont(FONT, 9, QFont.Weight.Bold))
        nm.setStyleSheet(f"color:{C_TEXT_PRI};letter-spacing:0.3px;")
        hdr.addWidget(nm, alignment=Qt.AlignmentFlag.AlignVCenter)
        hdr.addWidget(self._av("Y", "#2a2a35", C_TEXT_SEC),
                      alignment=Qt.AlignmentFlag.AlignVCenter)
        vbox.addLayout(hdr)

        row = QHBoxLayout(); row.setContentsMargins(80, 0, 46, 16); row.addStretch()
        bubble = QLabel(text); bubble.setWordWrap(True); bubble.setFont(QFont(FONT, 10))
        bubble.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        bubble.setStyleSheet(f"""
            background:{C_BG_USER_MSG}; color:{C_TEXT_PRI};
            border:1px solid {C_BORDER}; border-radius:16px;
            border-bottom-right-radius:4px; padding:12px 18px; line-height:1.7;
        """)
        row.addWidget(bubble); vbox.addLayout(row)


# ── Sidebar ────────────────────────────────────────────────────────────────────
class Sidebar(QFrame):
    sig_new = pyqtSignal()
    sig_dbg = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(SIDEBAR_W)
        self.setStyleSheet(f"QFrame{{background:{C_BG_SIDEBAR};border-right:1px solid {C_BORDER};}}")
        self._build()

    def _build(self):
        lay = QVBoxLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(0)

        # Logo
        logo = QWidget(); logo.setFixedHeight(56)
        logo.setStyleSheet(f"background:{C_BG_SIDEBAR};")
        lr = QHBoxLayout(logo); lr.setContentsMargins(16, 0, 16, 0); lr.setSpacing(10)
        mark = QLabel("◈"); mark.setFont(QFont(FONT, 18))
        mark.setStyleSheet(f"color:{C_ACCENT};"); lr.addWidget(mark)
        name = QLabel(IDENTITY); name.setFont(QFont(FONT, 13, QFont.Weight.Bold))
        name.setStyleSheet(f"color:{C_TEXT_PRI};letter-spacing:-0.3px;"); lr.addWidget(name)
        lr.addStretch()
        badge = QLabel("AI"); badge.setFont(QFont(FONT, 7, QFont.Weight.Bold))
        badge.setStyleSheet(f"background:{C_ACCENT_DIM};color:{C_ACCENT_GLOW};"
                           f"border-radius:4px;padding:2px 5px;letter-spacing:0.5px;")
        lr.addWidget(badge); lay.addWidget(logo)
        lay.addWidget(self._div())

        # New chat
        nb = QPushButton("＋  New conversation"); nb.setFixedHeight(38)
        nb.setFont(QFont(FONT, 9)); nb.setCursor(Qt.CursorShape.PointingHandCursor)
        nb.setStyleSheet(f"""
            QPushButton{{background:transparent;color:{C_TEXT_SEC};border:1px solid {C_BORDER};
            border-radius:9px;margin:10px 12px 6px 12px;text-align:left;padding:0 12px;}}
            QPushButton:hover{{background:{C_BG_SURFACE};color:{C_TEXT_PRI};border-color:{C_BORDER_FOCUS};}}
        """)
        nb.clicked.connect(self.sig_new); lay.addWidget(nb)

        # Section
        lbl = QLabel("CONVERSATIONS"); lbl.setFont(QFont(FONT, 7, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color:{C_TEXT_DIM};padding:10px 14px 4px;letter-spacing:1.5px;")
        lay.addWidget(lbl)

        # History
        self._hist = QListWidget()
        self._hist.setStyleSheet(f"""
            QListWidget{{background:transparent;border:none;color:{C_TEXT_SEC};
                font-family:{FONT},{FONT_FALLBACK};font-size:9pt;outline:none;padding:0;}}
            QListWidget::item{{padding:9px 12px;border-radius:8px;margin:1px 8px;}}
            QListWidget::item:hover{{background:{C_BG_SURFACE};color:{C_TEXT_PRI};}}
            QListWidget::item:selected{{background:{C_BG_SURFACE};color:{C_TEXT_PRI};border:1px solid {C_BORDER};}}
            QScrollBar:vertical{{background:transparent;width:3px;}}
            QScrollBar::handle:vertical{{background:{C_BORDER};border-radius:1px;min-height:20px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
        """)
        lay.addWidget(self._hist, stretch=1)
        lay.addWidget(self._div())

        # Bottom
        bot = QWidget(); bot.setStyleSheet(f"background:{C_BG_SIDEBAR};")
        bl = QVBoxLayout(bot); bl.setContentsMargins(12, 8, 12, 12); bl.setSpacing(6)
        dr = QHBoxLayout()
        dl = QLabel("Debug mode"); dl.setFont(QFont(FONT, 8))
        dl.setStyleSheet(f"color:{C_TEXT_SEC};"); dr.addWidget(dl); dr.addStretch()
        self._dbg = QCheckBox()
        self._dbg.setStyleSheet(f"""
            QCheckBox::indicator{{width:15px;height:15px;border-radius:4px;
                border:1px solid {C_BORDER};background:transparent;}}
            QCheckBox::indicator:checked{{background:{C_ACCENT};border-color:{C_ACCENT};}}
            QCheckBox::indicator:hover{{border-color:{C_ACCENT_GLOW};}}
        """)
        self._dbg.toggled.connect(self.sig_dbg); dr.addWidget(self._dbg)
        bl.addLayout(dr)
        if MODEL_ID:
            ml = QLabel(f"⬡  {MODEL_ID}"); ml.setFont(QFont(FONT, 7))
            ml.setStyleSheet(f"color:{C_TEXT_DIM};letter-spacing:0.3px;")
            ml.setWordWrap(True); bl.addWidget(ml)
        lay.addWidget(bot)

    def _div(self):
        d = QFrame(); d.setFrameShape(QFrame.Shape.HLine)
        d.setFixedHeight(1); d.setStyleSheet(f"background:{C_BORDER};border:none;")
        return d

    def add_history(self, text):
        short = text[:36] + ("…" if len(text) > 36 else "")
        item = QListWidgetItem("  " + short)
        self._hist.insertItem(0, item); self._hist.setCurrentItem(item)


# ── Welcome widget ─────────────────────────────────────────────────────────────
class Welcome(QWidget):
    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self); lay.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.setSpacing(12)
        mark = QLabel("◈"); mark.setFont(QFont(FONT, 52))
        mark.setStyleSheet(f"color:{C_ACCENT};"); mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(mark)
        title = QLabel(IDENTITY); title.setFont(QFont(FONT, 24, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{C_TEXT_PRI};letter-spacing:-0.8px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(title)
        sub = QLabel("Your autonomous AI agent — ready to act.")
        sub.setFont(QFont(FONT, 11)); sub.setStyleSheet(f"color:{C_TEXT_SEC};")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(sub)
        lay.addSpacing(28)
        caps = [("⟡", "Research"), ("⟐", "Run Code"), ("⊙", "Files"), ("⬡", "Browse"), ("◎", "Control")]
        row = QHBoxLayout(); row.setAlignment(Qt.AlignmentFlag.AlignCenter); row.setSpacing(8)
        for icon, lbl in caps:
            chip = QLabel(f"{icon}  {lbl}"); chip.setFont(QFont(FONT, 8))
            chip.setStyleSheet(f"background:{C_BG_SURFACE};color:{C_TEXT_SEC};"
                             f"border:1px solid {C_BORDER};border-radius:20px;padding:6px 14px;")
            row.addWidget(chip)
        lay.addLayout(row)


# ── Main window ────────────────────────────────────────────────────────────────
class ArbiterWindow(QMainWindow):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent; self.worker = None
        self.setWindowTitle(IDENTITY); self.setMinimumSize(860, 580); self.resize(1160, 820)
        self._palette(); self._build()

    def _palette(self):
        p = QPalette()
        for role, hex_ in [
            (QPalette.ColorRole.Window, C_BG), (QPalette.ColorRole.WindowText, C_TEXT_PRI),
            (QPalette.ColorRole.Base, C_BG_INPUT), (QPalette.ColorRole.Text, C_TEXT_PRI),
            (QPalette.ColorRole.Button, C_BG_SURFACE), (QPalette.ColorRole.ButtonText, C_TEXT_PRI),
            (QPalette.ColorRole.Highlight, C_ACCENT), (QPalette.ColorRole.HighlightedText, "#ffffff"),
        ]:
            p.setColor(role, QColor(hex_))
        QApplication.instance().setPalette(p); self.setStyleSheet(f"background:{C_BG};")

    def _build(self):
        root = QWidget(); self.setCentralWidget(root)
        h = QHBoxLayout(root); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        self._sidebar = Sidebar(); self._sidebar.sig_new.connect(self._new_chat)
        h.addWidget(self._sidebar); h.addWidget(self._chat_panel(), stretch=1)

    def _chat_panel(self):
        panel = QWidget(); panel.setStyleSheet(f"background:{C_BG};")
        col = QVBoxLayout(panel); col.setContentsMargins(0, 0, 0, 0); col.setSpacing(0)

        self._scroll = QScrollArea(); self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"""
            QScrollArea{{background:{C_BG};border:none;}}
            QScrollBar:vertical{{background:transparent;width:5px;border-radius:2px;}}
            QScrollBar::handle:vertical{{background:{C_BORDER};border-radius:2px;min-height:24px;}}
            QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{{height:0;}}
        """)
        self._chat_w = QWidget(); self._chat_w.setStyleSheet(f"background:{C_BG};")
        self._chat_lay = QVBoxLayout(self._chat_w)
        self._chat_lay.setContentsMargins(0, 0, 0, 60); self._chat_lay.setSpacing(0)
        self._welcome = Welcome(); self._chat_lay.addWidget(self._welcome)
        self._chat_lay.addStretch()
        self._thinking = ThinkingRow(); self._thinking.hide()
        self._chat_lay.addWidget(self._thinking)
        self._scroll.setWidget(self._chat_w); col.addWidget(self._scroll, stretch=1)
        col.addWidget(self._input_bar()); return panel

    def _input_bar(self):
        wrap = QWidget(); wrap.setStyleSheet(f"background:{C_BG};")
        outer = QVBoxLayout(wrap); outer.setContentsMargins(0, 12, 0, 20); outer.setSpacing(8)
        centre = QWidget(); centre.setMaximumWidth(CONTENT_W + 72)
        centre.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        inn = QVBoxLayout(centre); inn.setContentsMargins(0, 0, 0, 0); inn.setSpacing(8)

        box = QFrame(); box.setObjectName("ib")
        box.setStyleSheet(f"""
            QFrame#ib{{background:{C_BG_INPUT};border:1px solid {C_BORDER};border-radius:14px;}}
            QFrame#ib:focus-within{{border-color:{C_BORDER_FOCUS};}}
        """)
        br = QHBoxLayout(box); br.setContentsMargins(16, 8, 8, 8); br.setSpacing(8)
        self._inp = QLineEdit(); self._inp.setPlaceholderText(f"Message {IDENTITY}…")
        self._inp.setFont(QFont(FONT, 10)); self._inp.setFixedHeight(40)
        self._inp.setStyleSheet(f"""
            QLineEdit{{background:transparent;color:{C_TEXT_PRI};border:none;}}
        """)
        self._inp.returnPressed.connect(self._send); br.addWidget(self._inp)
        self._sbtn = QPushButton("↑"); self._sbtn.setFixedSize(36, 36)
        self._sbtn.setFont(QFont(FONT, 14, QFont.Weight.Bold))
        self._sbtn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sbtn.setStyleSheet(f"""
            QPushButton{{background:{C_ACCENT};color:white;border:none;border-radius:10px;}}
            QPushButton:hover{{background:{C_ACCENT_GLOW};}}
            QPushButton:pressed{{background:{C_ACCENT_DIM};}}
            QPushButton:disabled{{background:{C_BG_SURFACE};color:{C_TEXT_DIM};border:1px solid {C_BORDER};}}
        """)
        self._sbtn.clicked.connect(self._send); br.addWidget(self._sbtn)
        inn.addWidget(box)

        sr = QHBoxLayout(); sr.setSpacing(6)
        self._dot = QLabel("●"); self._dot.setFont(QFont(FONT, 7))
        self._dot.setStyleSheet(f"color:{C_SUCCESS};"); sr.addWidget(self._dot)
        self._stxt = QLabel("Ready"); self._stxt.setFont(QFont(FONT, 8))
        self._stxt.setStyleSheet(f"color:{C_TEXT_DIM};"); sr.addWidget(self._stxt)
        sr.addStretch()
        hint = QLabel("Enter to send  ·  Esc to cancel"); hint.setFont(QFont(FONT, 8))
        hint.setStyleSheet(f"color:{C_TEXT_DIM};letter-spacing:0.2px;"); sr.addWidget(hint)
        inn.addLayout(sr)

        row = QHBoxLayout(); row.addStretch(); row.addWidget(centre); row.addStretch()
        outer.addLayout(row); return wrap

    def _ts(self): return datetime.now().strftime("%H:%M")

    def _insert(self, row):
        n = self._chat_lay.count()
        self._chat_lay.insertWidget(n - 1, row)
        row._tick.connect(self._bottom); self._bottom()

    def _bot(self, t, animate=True):
        if self._welcome.isVisible(): self._welcome.hide()
        self._insert(MsgRow(t, "bot", self._ts(), animate=animate))

    def _user(self, t):
        if self._welcome.isVisible(): self._welcome.hide()
        self._insert(MsgRow(t, "user", self._ts()))

    def _bottom(self):
        QTimer.singleShot(50, lambda:
            self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()))

    def _status(self, txt, col):
        self._dot.setStyleSheet(f"color:{col};")
        self._stxt.setText(txt)

    def _send(self):
        t = self._inp.text().strip()
        if not t or self.worker: return
        self._inp.clear(); self._user(t); self._sidebar.add_history(t)
        self._inp.setEnabled(False); self._sbtn.setEnabled(False)
        self._status("Thinking…", C_THINKING); self._thinking.start(); self._bottom()
        self.worker = AgentWorker(self.agent, t)
        self.worker.done.connect(self._got); self.worker.error.connect(self._err)
        self.worker.finished.connect(self._done); self.worker.start()

    def _got(self, t):
        self._thinking.stop(); self._bot(t, animate=True); self._status("Ready", C_SUCCESS)

    def _err(self, e):
        self._thinking.stop(); self._bot(f"⚠ Error: {e}", animate=False)
        self._status("Error", C_ERROR)

    def _done(self):
        self.worker = None; self._inp.setEnabled(True)
        self._sbtn.setEnabled(True); self._inp.setFocus()

    def _new_chat(self):
        while self._chat_lay.count() > 3:
            item = self._chat_lay.takeAt(0)
            w = item.widget()
            if w and w not in (self._welcome, self._thinking): w.deleteLater()
        self._welcome.show()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape and self.worker:
            self.worker.terminate(); self.worker = None
            self._thinking.stop(); self._bot("Cancelled.", animate=False)
            self._status("Ready", C_SUCCESS)
            self._inp.setEnabled(True); self._sbtn.setEnabled(True)
        super().keyPressEvent(e)


# ── Entry point ────────────────────────────────────────────────────────────────
def launch_gui(agent):
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(IDENTITY); app.setStyle("Fusion")
    p = QPalette()
    for role, hex_ in [
        (QPalette.ColorRole.Window, C_BG), (QPalette.ColorRole.WindowText, C_TEXT_PRI),
        (QPalette.ColorRole.Base, C_BG_INPUT), (QPalette.ColorRole.AlternateBase, C_BG_SURFACE),
        (QPalette.ColorRole.Text, C_TEXT_PRI), (QPalette.ColorRole.Button, C_BG_SURFACE),
        (QPalette.ColorRole.ButtonText, C_TEXT_PRI), (QPalette.ColorRole.BrightText, "#ffffff"),
        (QPalette.ColorRole.Highlight, C_ACCENT), (QPalette.ColorRole.HighlightedText, "#ffffff"),
        (QPalette.ColorRole.PlaceholderText, C_TEXT_DIM),
    ]:
        p.setColor(role, QColor(hex_))
    app.setPalette(p)
    win = ArbiterWindow(agent); win.show(); sys.exit(app.exec())
