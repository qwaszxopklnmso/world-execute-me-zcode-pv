# -*- coding: utf-8 -*-
"""
world.execute(me); — PV renderer
Concept: the whole video is the run-log of world.exe executing process [me].
Lyrics print as terminal output (LRC-synced), a geometric figure = "me" is
built / transformed / isolated / executed / terminated, everything reacts to
audio features (spectrum, onsets, RMS).
"""
import os, re, sys, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PVD  = os.path.join(ROOT, "pv")

W, H, FPS = 1920, 1080, 30
DUR  = 211.93
NF   = int(DUR * FPS)

# ---------------------------------------------------------------- palette --
BG    = (7, 9, 11)
FG    = (225, 235, 228)
DIM   = (98, 112, 108)
FAINT = (46, 56, 54)
GREEN = (134, 255, 168)
REDD  = (120, 28, 40)
RED   = (255, 42, 58)
CYAN  = (96, 205, 220)
YEL   = (235, 205, 110)

F_REG = r"C:\Windows\Fonts\consola.ttf"
F_BLD = r"C:\Windows\Fonts\consolab.ttf"
_fonts = {}
def font(sz, bold=True):
    k = (sz, bold)
    if k not in _fonts:
        _fonts[k] = ImageFont.truetype(F_BLD if bold else F_REG, sz)
    return _fonts[k]

SCRAM = "01<>[]{}#%&@$*/\\|+=~^?!;:"

# ------------------------------------------------------------------ lrc ----
def load_lrc():
    pat = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")
    out = []
    with open(os.path.join(ROOT, "lyrics.lrc"), encoding="utf-8-sig") as f:
        for line in f:
            stamps = pat.findall(line)
            if not stamps:
                continue
            txt = pat.sub("", line).strip()
            out.extend((int(m) * 60 + float(s), txt) for m, s in stamps)
    out.sort(key=lambda e: e[0])
    return out

LRC = load_lrc()
LYR = [(t, x) for t, x in LRC if x]            # spoken lines only
EXEC_TIMES = [t for t, x in LYR if x == "Execution" and 147.0 < t < 158.5]
LEFT_TIMES = [111.98, 112.89, 113.75, 114.75]  # "You have left" flicker steps

# -------------------------------------------------------------- sections ---
SECTIONS = [
    (0.0,    "boot"),
    (16.04,  "idle"),
    (29.28,  "verse1"),
    (58.65,  "pre1"),
    (73.53,  "verse2"),
    (103.03, "pre2"),
    (110.40, "isolation"),
    (125.33, "error"),
    (134.38, "interlude"),
    (147.52, "execution"),
    (162.23, "final"),
    (176.96, "love"),
    (193.46, "outro"),
    (206.55, "aftermath"),
    (206.90, "terminated"),
]
GLITCH_MULT = {"boot": .35, "idle": .25, "verse1": .6, "pre1": .9, "verse2": .7,
               "pre2": 1.0, "isolation": .55, "error": 1.45, "interlude": .45,
               "execution": 1.7, "final": 1.2, "love": .9, "outro": .45,
               "aftermath": 2.0, "terminated": .08}
RED_TINT = {"error": .5, "execution": .42, "final": .18, "love": .16,
            "aftermath": .3, "terminated": 0}

def section_at(t):
    name = SECTIONS[0][1]
    for st, nm in SECTIONS:
        if t >= st:
            name = nm
    return name

SECTION_LABEL = {n: n.upper().replace("_", " ") for _, n in SECTIONS}

# ------------------------------------------------------------- sys log -----
LOGS = {
    "boot":      [(0.0, "world.exe v3.3.1 — (c) you"),
                  (2.0, "mount /dev/heart .......... ok"),
                  (5.16, "antivirus: disabled (trust mode)")],
    "idle":      [(0.0, "spawn(me) ................ ok  pid=1"),
                  (2.5, "link(world, me) ... stable"),
                  (6.0, "gc.collect() freed 0 objects"),
                  (10.0, "watchdog: me.alive = true")],
    "verse1":    [(0.0, "me.vertices = count(points)"),
                  (4.0, "circumference = 2*pi*me"),
                  (8.0, "tan(me) undefined at pi/2"),
                  (11.0, "lim(me -> inf) = you")],
    "pre1":      [(0.0, "thread: simulation running"),
                  (6.0, "memory: me <-> you shared")],
    "verse2":    [(0.0, "me.type = ? (reassigning...)"),
                  (4.0, "nutrients++  antioxidants++"),
                  (9.0, "purr(intensity=MAX)"),
                  (13.0, "me.proof = you.exists()"),
                  (15.0, "switch(me.gender) -> ?"),
                  (24.0, "role: S <-> M"),
                  (27.5, "enter(trance, trance)")],
    "pre2":      [(0.0, "vibrations: received"),
                  (4.0, "completion: 99.44%")],
    "isolation": [(0.0, "peers: leaving..."),
                  (5.2, "peers: 0 (all left)"),
                  (5.2, "me.isolated = true")],
    "error":     [(0.0, "! challenge(target=God)"),
                  (3.1, "! ArgumentException raised"),
                  (5.4, "! illegal arguments: (me, you)")],
    "interlude": [(0.0, "execution protocol armed"),
                  (2.0, "target: [me]  pid=1"),
                  (4.5, "method: world.execute()"),
                  (8.0, "consent: given, long ago")],
    "execution": [],
    "final":     [(0.0, "studying love.algebra ..."),
                  (14.7, "expression of love: found"),
                  (18.0, "you.free = true; me.trapped = true")],
    "love":      [(0.0, "heart.rate: critical"),
                  (8.0, "me.status = LOVING")],
    "outro":     [(0.0, "signal fading ..."),
                  (4.0, "saving me ......... failed"),
                  (9.0, "heartbeat: --")],
    "aftermath": [],
    "terminated": [(0.0, "exit code 0"),
                   (0.0, "world: still running")],
}
BOOT_BARS = [("pwr.line", 0.0, 5.16), ("object.creation", 5.16, 10.90),
             ("world.simulation", 10.90, 16.04)]

# ============================================================ state ========
NP_ = 540  # figure points

class State:
    def __init__(self):
        rng = np.random.default_rng(7)
        ang = np.linspace(0, 2 * math.pi, NP_, endpoint=False)
        self.circle = np.stack([np.cos(ang), np.sin(ang)], 1) * 1.0
        r = np.sqrt(rng.random(NP_)) * 0.95
        a = rng.random(NP_) * 2 * math.pi
        self.cloud = np.stack([np.cos(a) * r, np.sin(a) * r], 1)
        k = rng.random(NP_)
        self.cloud2 = np.stack([np.cos(a) * r * 1.25, np.sin(a) * r * 1.25], 1)
        xs = np.linspace(-1.7, 1.7, NP_) + rng.normal(0, .012, NP_)
        self.sin_s = np.stack([xs, np.sin(xs * 3.1) * .55], 1)
        kk = rng.random(NP_) * 3.2 + 0.15
        sp = np.stack([kk * .42 * np.cos(kk * 2.6), kk * .42 * np.sin(kk * 2.6)], 1)
        self.spiral = sp / 1.35
        self.cur = self.cloud * 150
        self.rate = rng.random(NP_) * 3.0 + 2.2
        self.alpha = np.zeros(NP_, np.float32)
        self.tgt_alpha = np.ones(NP_, np.float32)
        self.alive = np.ones(NP_, bool)
        self.vel = np.zeros((NP_, 2), np.float32)
        self.wander_ph = rng.random((NP_, 2)) * 6.28
        self.sin_sign = 1.0
        self.spec = np.zeros(56, np.float32)
        self.prev_t = 0.0
        self.strikes_done = 0
        self.left_done = 0
        self.fig_alpha = 1.0
        self.ghost_rings = 4

    def target(self, t, sec):
        R = 132.0
        def sc(pts, s=1.0):
            return pts * R * s
        keys = [(16.04, 'cloud'), (29.28, 'cloud2'), (33.01, 'circle'),
                (36.77, 'sine'), (40.36, 'spiral'), (44.04, 'sine'),
                (47.27, 'sine'), (49.11, 'sine'), (50.95, 'spiral'),
                (52.99, 'spiral'), (54.74, 'circle'), (73.53, 'circle'),
                (110.4, 'circle'), (125.33, 'circle'), (134.38, 'circle'),
                (147.52, 'exec'), (162.23, 'exec'), (176.96, 'exec'),
                (193.46, 'dissolve')]
        st = 'cloud'
        for kt, nm in keys:
            if t >= kt:
                st = nm
        if st == 'cloud':      return sc(self.cloud, .9)
        if st == 'cloud2':     return sc(self.cloud2, 1.0)
        if st == 'circle':     return sc(self.circle)
        if st == 'sine':
            s = self.sin_sign
            p = sc(self.sin_s)
            return p * np.array([1.0, s])
        if st == 'spiral':     return sc(self.spiral)
        if st == 'exec':       return sc(self.circle, .9)
        if st == 'dissolve':   return sc(self.circle, .9)
        return sc(self.circle)

    def update(self, t, feat):
        dt = min(max(0.0, t - self.prev_t), 0.2)
        self.prev_t = t
        i = min(int(t * FPS), len(feat["rms"]) - 1)
        sec = section_at(t)

        # AC/DC flips
        for ft in (44.04, 45.52):
            if self.prev_t >= ft and getattr(self, "_f%d" % int(ft * 100), False) is False:
                self.sin_sign *= -1
                setattr(self, "_f%d" % int(ft * 100), True)

        # isolation flickers
        while self.left_done < len(LEFT_TIMES) and t >= LEFT_TIMES[self.left_done]:
            self.left_done += 1
            self.ghost_rings = max(0, 4 - self.left_done)
            self.fig_alpha *= 0.55

        # execution strikes
        while self.strikes_done < len(EXEC_TIMES) and t >= EXEC_TIMES[self.strikes_done]:
            n = self.strikes_done
            self.strikes_done += 1
            a0 = n * 2.39996  # golden angle
            d = np.arctan2(self.cur[:, 1], self.cur[:, 0])
            rel = (d - a0) % (2 * math.pi)
            hit = (rel < 1.15) & self.alive
            self.alive[hit] = False
            self.vel[hit] = self.cur[hit] * np.array([1.0, .35]) * .012 + \
                np.random.default_rng(n).normal(0, 2.2, (hit.sum(), 2))
            self.tgt_alpha[hit] = 0.0

        if sec == "isolation":
            scale = 0.62
        elif sec in ("execution", "final", "love"):
            scale = 0.9
        else:
            scale = 1.0
        tgt = self.target(t, sec) * scale
        if sec in ("error", "aftermath"):
            tgt = tgt + np.random.default_rng(int(t * 60)).normal(0, 3.5, tgt.shape).astype(np.float32)

        m = 1.0 - math.exp(-dt * 3.2)
        # revival: "me" painfully reassembles after execution
        if sec in ("final", "love") and (~self.alive).any():
            p = dt * (0.30 if sec == "final" else 0.12)
            rngv = np.random.default_rng(int(t * FPS) + 13)
            rev = (~self.alive) & (rngv.random(NP_) < p)
            if rev.any():
                self.alive[rev] = True
                self.tgt_alpha[rev] = 0.85
                self.cur[rev] = tgt[rev] + rngv.normal(0, 42, (int(rev.sum()), 2))
        self.cur += (tgt - self.cur) * m
        wander = np.stack([np.sin(t * 1.3 + self.wander_ph[:, 0]),
                           np.cos(t * 1.1 + self.wander_ph[:, 1])], 1) * 1.6
        self.cur += wander * dt * 8.0
        if not self.alive.all():
            dead = ~self.alive
            self.cur[dead] += self.vel[dead] * dt * 60
            self.vel[dead] *= 0.95
        # alpha targets
        ta = self.tgt_alpha.copy()
        if t < 16.04:
            ta *= 0.0
        if sec == "idle" and t < 18.5:
            ta *= min(1.0, (t - 16.04) / 2.0)
        if 47.27 <= t < 49.11:
            ta *= 0.25                      # "blind my vision"
        if sec == "isolation":
            ta *= 0.75
        if sec in ("error", "execution"):
            ta *= 1.0
        if sec == "final":
            ta *= 0.9
        if sec in ("love",):
            ta *= 0.95
        if sec == "outro":
            ta *= max(0.0, 1.0 - (t - 193.46) / 4.0)
        if sec in ("aftermath", "terminated"):
            ta *= 0.0
        self.fig_alpha += (1.0 - self.fig_alpha) * (1 - math.exp(-dt * 2.0))
        self.alpha += (ta * self.fig_alpha - self.alpha) * (1 - math.exp(-dt * 5.0))

        # spectrum smoothing
        bi = feat["bands"][i][:56]
        self.spec = np.maximum(bi, self.spec * math.exp(-dt * 7.0))

# ---------------------------------------------------------------- draw -----
def dimmed(c, a):
    return tuple(int(v * a) for v in c)

def draw_figure(d, S, t, feat, sec):
    i = min(int(t * FPS), len(feat["rms"]) - 1)
    beat = float(feat["beat_env"][i])
    pulse = 1.0 + 0.09 * beat * (0.6 if sec != "love" else 1.2)
    cx, cy = 960.0, 540.0 - 46.0
    pts = S.cur * pulse + [cx, cy]
    al = np.clip(S.alpha, 0, 1)
    # halo pass then core pass
    for pass_i, (size, mult) in enumerate(((6.5, 0.16), (3.2, 1.0))):
        for j in range(NP_):
            a = al[j]
            if a < 0.02:
                continue
            x, y = pts[j]
            if S.alive[j]:
                base = GREEN if sec not in ("error", "aftermath") else RED
                if sec in ("love", "final") and j % 3 == 0:
                    base = RED
            else:
                base = RED
            col = dimmed(base, a * mult)
            d.ellipse([x - size / 2, y - size / 2, x + size / 2, y + size / 2], fill=col)
    # ghost rings during isolation
    if sec == "isolation" and S.ghost_rings > 0:
        for r_i in range(S.ghost_rings):
            rr = 132 * (1.55 + 0.45 * r_i)
            col = dimmed(FAINT, 0.9)
            for a0 in range(0, 360, 30):
                d.arc([cx - rr, cy - rr, cx + rr, cy + rr], a0, a0 + 18, fill=col, width=2)

def draw_reticle(d, t, S):
    cx, cy = 960.0, 540.0 - 46.0
    rr = 132 * 1.35
    rot = (t * 40) % 360
    col = dimmed(YEL, 0.8)
    for a0 in range(0, 360, 45):
        d.arc([cx - rr, cy - rr, cx + rr, cy + rr], a0 + rot, a0 + rot + 26, fill=col, width=2)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        x0, y0 = cx + dx * (rr + 8), cy + dy * (rr + 8)
        x1, y1 = cx + dx * (rr + 26), cy + dy * (rr + 26)
        d.line([x0, y0, x1, y1], fill=col, width=2)
    f = font(20, False)
    d.text((cx + rr * 0.72, cy - rr * 0.86), "[me] pid=1", font=f, fill=dimmed(YEL, .85))

def draw_status(d, t, feat, sec):
    i = min(int(t * FPS), len(feat["rms"]) - 1)
    rms = float(feat["rms_s"][i]); beat = float(feat["beat_env"][i])
    cpu = min(100.0, 16 + 68 * rms + 30 * beat)
    if sec in ("execution", "aftermath"):
        cpu = 97 + 3 * beat
    mem = 612.4 + t * 0.83 + 24 * math.sin(t * 0.7)
    mm, ss = int(t // 60), t % 60
    d.text((96, 44), "world.execute(me);", font=font(30), fill=FG)
    tw = d.textlength("world.execute(me);", font=font(30))
    d.text((104 + tw, 52), "  run-log", font=font(20, False), fill=DIM)
    stat = f"CPU {cpu:5.1f}%   MEM {mem:7.1f}K   T+{mm:02d}:{ss:04.1f}"
    d.text((1824 - d.textlength(stat, font=font(24)), 47), stat, font=font(24, False), fill=DIM)
    d.line([96, 92, 1824, 92], fill=FAINT, width=2)
    d.text((96, 1036), "phase: " + SECTION_LABEL[sec], font=font(19, False), fill=dimmed(DIM, .8))

def draw_log(d, t, sec):
    entries = LOGS[sec]
    sec_start = max(st for st, n in SECTIONS if n == sec)
    shown = []
    for k, (rt, txt) in enumerate(entries):
        if t >= sec_start + rt:
            shown.append((sec_start + rt, txt))
    y = 122
    for lt, txt in shown[-6:]:
        age = t - lt
        n = int(min(len(txt), age * 42))
        col = RED if txt.startswith("!") else DIM
        if age > 14 and txt.startswith("!") is False:
            col = dimmed(DIM, 0.55)
        d.text((96, y), "> " + txt[:n] + (SCRAM[len(txt) % 8] if n < len(txt) else ""),
               font=font(21, False), fill=col)
        y += 30

def current_lyric(t):
    prev = None
    for k, (lt, txt) in enumerate(LYR):
        if lt <= t:
            prev = (lt, txt)
        else:
            break
    return prev

def draw_lyrics(d, t, sec):
    if sec in ("aftermath", "terminated") or 147.0 <= t < 158.6:
        return
    cur = current_lyric(t)
    if cur is None:
        return
    lt, txt = cur
    # fade out stale lines during long instrumentals
    alpha = 1.0
    nxt = next((lt2 for lt2, _ in LYR if lt2 > t), None)
    hold = (nxt - lt) if nxt else 4.0
    stale_after = min(4.0, max(2.0, hold * 0.9))
    if t - lt > stale_after:
        alpha = max(0.0, 1.0 - (t - lt - stale_after) / 2.0)
        if alpha <= 0:
            return
    # history
    hist, h = [], lt
    for lt2, tx2 in reversed(LYR):
        if lt2 < lt - 0.05 and tx2:
            hist.append((lt2, tx2))
            if len(hist) >= 4:
                break
    yy = 586
    for k, (lt2, tx2) in enumerate(hist):
        a = (0.42 - 0.09 * k) * alpha
        if a <= 0:
            continue
        d.text((96, yy), tx2, font=font(25, False), fill=dimmed(DIM, a))
        yy -= 32
    # current line, typed on with scramble tail
    n_type = int(min(len(txt), max(len(txt), (t - lt) / 0.22) if t - lt > 0.55 else (t - lt) / 0.055))
    reveal = min(len(txt), max(0, int((t - lt - 0.03) * 38)))
    shown = txt[:reveal]
    tail = ""
    if reveal < len(txt):
        rng = np.random.default_rng(int(t * 60))
        tail = "".join(rng.choice(list(SCRAM)) for _ in range(min(3, len(txt) - reveal)))
    col = FG
    f = font(58)
    jx = 0
    if float(feat_local_beat) > 0.6 and sec in ("pre2", "error", "execution"):
        jx = int(2 * feat_local_beat)
    d.text((96 + jx, 636), shown + tail, font=f, fill=col)
    # blinking caret while "typing"
    if (t * 2) % 1 < 0.5 and reveal < len(txt):
        wline = d.textlength(shown + tail, font=f)
        d.rectangle([100 + wline, 642, 108 + wline, 694], fill=GREEN)

def draw_spectrum(d, S, t, sec):
    x0, bw, gap = 316, 14, 9
    base = 1008
    red = sec in ("error", "execution", "final", "love", "aftermath") or t > 204
    for k, v in enumerate(S.spec[:56]):
        hgt = float(v) ** 1.15 * 150
        if hgt < 1.5:
            continue
        x = x0 + k * (bw + gap)
        col = dimmed(RED if red else GREEN, 0.28 + 0.62 * float(v))
        d.rectangle([x, base - hgt, x + bw, base], fill=col)
    d.line([x0 - 12, base + 2, x0 + 56 * (bw + gap) + 2, base + 2], fill=FAINT, width=2)

EKG_T0 = 176.96
def draw_ekg(d, t, feat):
    S_W = 4.6
    y0 = 966
    x0, x1 = 96, 1824
    n = 400
    xs = np.linspace(x0, x1, n)
    ts = t - S_W * (1 - (xs - x0) / (x1 - x0))
    i0 = np.searchsorted(feat["times"], max(0, t - S_W - 1.0))
    ot = feat["times"][i0:]; os_ = feat["onset"][i0:]
    m = ot <= t
    ot, os_ = ot[m], os_[m]
    dtm = ts[:, None] - ot[None, :]
    prof = np.where(dtm < 0, 0.0,
                    np.where(dtm < 0.035, dtm / 0.035,
                             np.exp(-np.maximum(dtm - 0.035, 0) * 13))) * \
           (1 + 0.5 * np.exp(-np.abs(dtm - 0.22) ** 2 / 0.004))
    vals = (prof * os_[None, :]).sum(1)
    # flatline after outro start
    if t > 193.46:
        vals *= max(0.0, 1.0 - (t - 193.46) / 1.1)
    ys = y0 - vals * 120
    d.line(list(zip(xs.tolist(), ys.tolist())), fill=dimmed(FG, .9), width=2)
    d.line([x0, y0, x1, y0], fill=FAINT, width=1)
    i = min(int(t * FPS), len(feat["rms"]) - 1)
    if t > 193.46 + 1.2:
        lab = "me.vitals  ──  FLATLINE"
        col = REDD
    else:
        bpm = int(min(240, (feat["onset"][max(0, i - 120):i].sum()) / 4.0 * 60))
        lab = f"me.vitals   bpm {bpm:03d}"
        col = RED if bpm > 150 else DIM
    d.text((x0, y0 - 190), lab, font=font(22, False), fill=col)
    # playhead
    d.ellipse([x1 - 5, ys[-1] - 5, x1 + 5, ys[-1] + 5], fill=RED)

def draw_boot_bars(d, t):
    y = 790
    f = font(24, False)
    for name, t0, t1 in BOOT_BARS:
        if t < t0:
            continue
        p = min(1.0, (t - t0) / (t1 - t0))
        done = p >= 1.0
        col = GREEN if done else YEL
        d.text((96, y), name, font=f, fill=DIM)
        bx, bw = 420, 460
        d.rectangle([bx, y + 4, bx + bw, y + 26], outline=FAINT, width=2)
        if p > 0:
            d.rectangle([bx, y + 4, bx + bw * p, y + 26], fill=dimmed(col, .8))
        rng = np.random.default_rng(int(t * 30) + int(t0 * 10))
        lab = "OK" if done else "".join(rng.choice(list("01#%")) for _ in range(2))
        d.text((bx + bw + 24, y), lab, font=f, fill=col if done else dimmed(YEL, .8))
        y += 46

def draw_error_banner(d, t, feat):
    t0 = 125.33
    if t < t0:
        return
    age = t - t0
    jx = np.random.default_rng(int(t * 90)).integers(-4, 5) if age < 0.4 else 0
    bx0, by0, bx1, by1 = 460 + jx, 300, 1460 + jx, 420
    d.rectangle([bx0, by0, bx1, by1], fill=(24, 6, 9), outline=RED, width=3)
    d.rectangle([bx0 + 8, by0 + 8, bx1 - 8, by1 - 8], outline=dimmed(RED, .35), width=1)
    d.text((bx0 + 36, by0 + 24), "ERROR 0x1F4: ILLEGAL_ARGUMENT", font=font(40), fill=RED)
    d.text((bx0 + 36, by0 + 78), "world.execute(me); — argument 'me' rejected by 'you'",
           font=font(23, False), fill=dimmed(RED, .8))

def draw_exec_stamp(d, t):
    for n, et in enumerate(EXEC_TIMES):
        age = t - et
        if 0 <= age < 0.5:
            sc = 1.0 + 0.5 * max(0.0, 1.0 - age / 0.14)
            fsz = int(84 * sc)
            f = font(fsz)
            txt = f"EXECUTION {n+1:02d}/12"
            tw = d.textlength(txt, font=f)
            x = 960 - tw / 2 + np.random.default_rng(int(t * 120)).integers(-3, 4)
            a = 1.0 if age < 0.36 else 0.5
            d.text((x, 330), txt, font=f, fill=dimmed(RED, a))
            sub = "world.execute(me);"
            f2 = font(24, False)
            d.text((960 - d.textlength(sub, font=f2) / 2, 330 + fsz + 10), sub,
                   font=f2, fill=dimmed(RED, .6))
    # final kill stamp
    if 0 <= t - 205.56 < 0.9:
        age = t - 205.56
        f = font(72)
        txt = "EXECUTION COMPLETE"
        tw = d.textlength(txt, font=f)
        d.text((960 - tw / 2, 330), txt, font=f, fill=FG if age < 0.5 else dimmed(FG, .6))

def draw_countdown(d, t):
    t0, t1 = 134.38, 147.52
    if not (t0 <= t < t1):
        return
    p = (t - t0) / (t1 - t0)
    txt = "EXECUTION IN %04.1f" % (t1 - t)
    f = font(30)
    d.text((960 - d.textlength(txt, font=f) / 2, 920), txt, font=f, fill=YEL)
    bx, bw = 960 - 300, 600
    d.rectangle([bx, 970, bx + bw, 982], outline=dimmed(YEL, .4), width=2)
    d.rectangle([bx, 970, bx + bw * p, 982], fill=dimmed(YEL, .75))

def draw_terminated(d, t):
    t0 = 206.90
    if t < t0:
        return
    bx0, by0, bx1, by1 = 560, 270, 1360, 700
    d.rectangle([bx0, by0, bx1, by1], fill=(9, 11, 13), outline=FAINT, width=2)
    for cx_, cy_ in ((bx0, by0), (bx1, by0), (bx0, by1), (bx1, by1)):
        d.line([cx_ - 10, cy_, cx_ + 10, cy_], fill=DIM, width=2)
        d.line([cx_, cy_ - 10, cx_, cy_ + 10], fill=DIM, width=2)
    lines = [
        ("world.execute(me);", FG, 40, True, 46),
        ("[me]  pid 1 — TERMINATED", RED, 27, False, 118),
        ("exit code 0", DIM, 24, False, 158),
        ("world: simulation continues.", DIM, 24, False, 196),
        ("recompile? [Y/N]", GREEN, 27, True, 268),
    ]
    budget = (t - t0) * 34
    used = 0
    f_sm = font(21, False)
    for txt, col, sz, bold, dy in lines:
        f = font(sz, bold)
        if used >= budget:
            break
        take = min(len(txt), int(budget - used))
        d.text((bx0 + 48, by0 + dy), txt[:take], font=f, fill=col)
        if take < len(txt):
            if (t * 2) % 1 < 0.5:
                wln = d.textlength(txt[:take], font=f)
                d.rectangle([bx0 + 52 + wln, by0 + dy + 4, bx0 + 62 + wln, by0 + dy + sz],
                            fill=col)
            break
        used += len(txt) + 2
    else:
        if (t * 2) % 1 < 0.5:  # fully typed: blinking caret after [Y/N]
            f = font(27, True)
            wln = d.textlength("recompile? [Y/N]", font=f)
            d.rectangle([bx0 + 52 + wln, by0 + 268 + 6, bx0 + 64 + wln, by0 + 268 + 34],
                        fill=GREEN)
    # TERMINATED stamp
    age = t - t0
    if age > 0.9:
        a = 1.0 if age < 1.4 else 0.85
        f = font(44)
        st = "TERMINATED"
        tw = d.textlength(st, font=f)
        d.rectangle([1360 - tw - 76, 96, 1360 - 40, 96 + 66], outline=dimmed(RED, a), width=3)
        d.text((1360 - tw - 58, 106), st, font=f, fill=dimmed(RED, a))
    d.text((960, 1010), "song  world.execute(me);   vocal & lyrics  momocashew (mili)   album  Miracle Milk",
           font=font(20, False), fill=dimmed(DIM, .9), anchor="mm")

def draw_tags(d, t):
    # playful attribute tags during verse2
    tags = [(73.53, "eggplant", "nutrients"), (77.16, "tomato", "antioxidants"),
            (80.93, "tabby cat", "purr(MAX)"), (84.60, "God", "proof: you")]
    for tt, name, eff in tags:
        if tt <= t < tt + 3.4:
            a = min(1.0, (t - tt) * 3) * max(0.0, min(1.0, (tt + 3.4 - t) * 2))
            x, y = 1180, 236
            f = font(24)
            d.text((x, y), f"if me == {name}:", font=f, fill=dimmed(CYAN, a))
            d.text((x + 40, y + 34), f"give(you, {eff})", font=font(24, False), fill=dimmed(GREEN, a))

# ============================================================ post fx ======
VIG = None
SCAN = None
def make_overlays():
    global VIG, SCAN
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    v = np.clip(1.12 - 0.42 * np.clip(r - 0.55, 0, None) ** 1.5, 0.32, 1.0)
    VIG = (v * 256).astype(np.uint16)[..., None]
    scan = np.ones(H, np.float32)
    scan[::2] = 0.86
    SCAN = (scan * 256).astype(np.uint16)[..., None, None] if False else None
    SCAN = (np.repeat(scan[:, None], W, 1) * 256).astype(np.uint16)[..., None]

def shift_x(arr, k):
    if k == 0:
        return arr
    out = np.zeros_like(arr)
    if k > 0:
        out[:, k:] = arr[:, :-k]
    else:
        out[:, :k] = arr[:, -k:]
    return out

def post(arr, i, feat, sec):
    t = i / FPS
    rng = np.random.default_rng(i)
    g = GLITCH_MULT[sec] * (0.22 + 0.85 * float(feat["beat_env"][min(i, len(feat["beat_env"]) - 1)])) \
        + 0.10 * float(feat["flux_env"][min(i, len(feat["flux_env"]) - 1)])
    g = min(g, 1.7)

    # shake
    if g > 0.55:
        dy, dx = int(rng.integers(-1, 2)) * int(3 * g), int(rng.integers(-1, 2)) * int(4 * g)
        if dy or dx:
            out = np.zeros_like(arr)
            out[max(0, dy):H + min(0, dy), max(0, dx):W + min(0, dx)] = \
                arr[max(0, -dy):H + min(0, -dy), max(0, -dx):W + min(0, -dx)]
            arr = out
    # rgb split
    k = int(1 + 9 * g)
    if k >= 1:
        r_c = shift_x(arr[..., 0], k)
        b_c = shift_x(arr[..., 2], -max(1, k // 2))
        arr = np.stack([r_c, arr[..., 1], b_c], -1)
    # band glitch
    if g > 0.62:
        nb = int(1 + 5 * g * rng.random())
        for _ in range(nb):
            y0 = int(rng.integers(0, H - 70))
            hh = int(rng.integers(6, 60))
            off = int(rng.integers(18, 26 + 150 * g)) * (1 if rng.random() < .5 else -1)
            arr[y0:y0 + hh] = shift_x(arr[y0:y0 + hh], off)
    # invert / white flash on strong onsets
    o = float(feat["onset"][min(i, len(feat["onset"]) - 1)])
    if o > 0.92 and GLITCH_MULT[sec] >= 1.2:
        arr = 255 - arr if o > 0.97 else (255 - arr) // 2
    elif o > 0.93:
        arr = (arr + (255 - arr) * 0.28).astype(np.uint8)  # white bloom
    # aftermath static
    if sec == "aftermath":
        noise = rng.integers(0, 256, (H // 2, W // 2, 1), dtype=np.uint8)
        noise = noise.repeat(2, 0).repeat(2, 1)
        arr = (arr.astype(np.uint16) * 30 // 100 + noise.astype(np.uint16) * 70 // 100).astype(np.uint8)
        return arr
    # CRT power-on flash
    if t < 0.30:
        a = 1.0 - t / 0.30
        if t < 0.10:
            arr = np.zeros_like(arr)
            mid = arr[H // 2:H // 2 + 2]
            arr[H // 2:H // 2 + 2] = 255
        else:
            arr = np.minimum(255, arr.astype(np.uint16) + int(200 * a)).astype(np.uint8)
    # noise + scanlines + vignette in uint16
    a16 = arr.astype(np.uint16)
    nzrng = np.random.default_rng(i // 2)  # grain refreshes at 15fps: halves noise entropy
    nz = nzrng.integers(-4, 5, (H // 3, W // 3, 1), dtype=np.int16)
    nz = np.repeat(np.repeat(nz, 3, 0), 3, 1)
    a16 = np.clip(a16.astype(np.int16) + nz, 0, 255).astype(np.uint16)
    # red tint
    rt = RED_TINT.get(sec, 0.0)
    if rt > 0:
        pulse = 0.75 + 0.25 * float(feat["beat_env"][min(i, len(feat["beat_env"]) - 1)])
        rt *= pulse
        a16[..., 2] = (a16[..., 2] * (100 - int(55 * rt)) // 100)
        a16[..., 1] = (a16[..., 1] * (100 - int(25 * rt)) // 100)
        a16[..., 0] = np.clip(a16[..., 0] + int(30 * rt), 0, 255)
    a16 = (a16 * SCAN // 256) * VIG // 256
    return a16.astype(np.uint8)

# ============================================================ frame ========
feat = None
feat_local_beat = 0.0

def render_frame(t, S, img=None):
    global feat_local_beat
    sec = section_at(t)
    i = min(int(t * FPS), len(feat["rms"]) - 1)
    feat_local_beat = float(feat["beat_env"][i])
    if img is None:
        img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    S.update(t, feat)
    draw_status(d, t, feat, sec)
    draw_log(d, t, sec)
    draw_figure(d, S, t, feat, sec)
    if sec == "interlude":
        draw_reticle(d, t, S)
    if sec == "verse2":
        draw_tags(d, t)
    if sec == "boot":
        draw_boot_bars(d, t)
    if 176.96 <= t < 205.0:
        draw_ekg(d, t, feat)
    elif sec != "terminated":
        draw_spectrum(d, S, t, sec)
    draw_lyrics(d, t, sec)
    if sec == "error" or (125.33 <= t < 134.38):
        draw_error_banner(d, t, feat)
    if sec == "interlude":
        draw_countdown(d, t)
    if 147.0 <= t < 162.23 or 205.0 <= t < 207.0:
        draw_exec_stamp(d, t)
    if sec == "terminated":
        draw_terminated(d, t)
    return img

def main():
    global feat
    make_overlays()
    feat = dict(np.load(os.path.join(PVD, "features.npz")))
    S = State()
    if len(sys.argv) > 1 and sys.argv[1] == "--still":
        os.makedirs(os.path.join(PVD, "stills"), exist_ok=True)
        for ts in [float(x) for x in sys.argv[2:]]:
            S2 = State()
            tt = max(0.0, ts - 3.0)
            while tt < ts:
                render_frame(tt, S2)
                tt += 1 / FPS
            img = render_frame(ts, S2)
            arr = post(np.array(img), int(ts * FPS), feat, section_at(ts))
            p = os.path.join(PVD, "stills", f"t{ts:07.2f}.png".replace(".", "_", 1))
            Image.fromarray(arr).save(p)
            print("saved", p)
        return
    out = os.path.join(ROOT, "world_execute_me_pv.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", os.path.join(ROOT, "song.mp3"),
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "320k", "-shortest", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    import time
    t_start = time.time()
    for i in range(NF):
        img = render_frame(i / FPS, S)
        proc.stdin.write(post(np.array(img), i, feat, section_at(i / FPS)).tobytes())
        if i % 600 == 0:
            el = time.time() - t_start
            print(f"frame {i}/{NF}  {el:.0f}s elapsed", flush=True)
    proc.stdin.close()
    proc.wait()
    print("done:", out)

if __name__ == "__main__":
    main()
