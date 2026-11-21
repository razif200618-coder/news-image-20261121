#!/usr/bin/env python3
"""The Saturday Globe -- one-page newspaper summing up the world news of
Saturday 21 November 2026. Pure standard library: draws the whole page
with a built-in 5x7 bitmap font and writes a deterministic PNG.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py
Writes entry.png (1024x1024, under 1 MiB) to the output directory.
"""

import hashlib
import os
import struct
import zlib

W, H = 1024, 1024

PAPER = (247, 243, 232)
INK = (17, 17, 17)
NAVY = (22, 35, 63)
RED = (176, 46, 46)
GREY = (110, 108, 100)
FAINT = (214, 210, 198)
WHITE = (255, 255, 255)

# 5x7 bitmap font. Each glyph is 7 rows; each row is a 5-bit value,
# bit 4 is the leftmost pixel. Only the characters the page uses.
FONT = {
    " ": (0, 0, 0, 0, 0, 0, 0),
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x1B, 0x11),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    ".": (0, 0, 0, 0, 0, 0x0C, 0x0C),
    ",": (0, 0, 0, 0, 0x0C, 0x04, 0x08),
    "'": (0x04, 0x04, 0x08, 0, 0, 0, 0),
    "!": (0x04, 0x04, 0x04, 0x04, 0x04, 0x00, 0x04),
    "?": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x00, 0x04),
    "-": (0, 0, 0, 0x0E, 0, 0, 0),
    ":": (0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0),
    ";": (0, 0x0C, 0x0C, 0, 0x0C, 0x04, 0x08),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    "%": (0x19, 0x19, 0x02, 0x04, 0x08, 0x13, 0x13),
    "&": (0x0C, 0x12, 0x14, 0x08, 0x15, 0x12, 0x0D),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "+": (0, 0x04, 0x04, 0x0E, 0x04, 0x04, 0),
    "=": (0, 0, 0x1F, 0, 0x1F, 0, 0),
    '"': (0x0A, 0x0A, 0x0A, 0, 0, 0, 0),
    "|": (0x04, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
}

# The lead story, then the 39 column stories.
# Each entry: (section, headline, one-line deck of at most 52 chars).
LEAD = (
    "TOP STORY",
    "KYIV UNDER FIRE; MISSILES LAND IN POLAND",
    "More than 400 drones and 110 missiles hit Ukraine overnight, killing "
    "at least eight in Kyiv. NATO calls the Polish landings a grave violation.",
)

STORIES = [
    ("WORLD", "COURT: MYANMAR GUILTY OF ROHINGYA GENOCIDE",
     "First state ever convicted of genocide."),
    ("WORLD", "TANKERS HIT NEAR HORMUZ AS IRAN TALKS STALL",
     "Projectiles strike ships by the strait."),
    ("WORLD", "HOUTHIS FIRE ON RIYADH; COALITION HITS BACK",
     "Three missiles intercepted over Riyadh."),
    ("WORLD", "ISRAELI FIRE KILLS PALESTINIANS IN GAZA",
     "Strikes go on; West Bank tensions rise."),
    ("WORLD", "BRITAIN AND EU SIGN THREE POST-BREXIT DEALS",
     "Food, carbon and youth mobility pacts."),
    ("WORLD", "DENMARK EXPELS RUSSIAN DIPLOMAT OVER PLOT",
     "Two held over a plot to kill a rapper."),
    ("WORLD", "PROTESTS SWEEP 25 EUROPEAN COUNTRIES",
     "Students walk out over costs and fees."),
    ("WORLD", "ZELENSKY CALLS PUTIN A KILLER",
     "Kyiv hits back as Trump praises Putin."),
    ("WORLD", "JAPAN SIDELINED AS CHINA TIES HIT LOW",
     "Tokyo frozen out as ties hit rock bottom."),
    ("WORLD", "SPAIN HEADS FOR NOVEMBER 29 ELECTION",
     "Conservatives gain; bank tax extended."),
    ("WORLD", "BOLSONARO HOSPITALISED IN BRAZIL",
     "Ex-president treated for bowel blockage."),
    ("WORLD", "QUAKE OF 6.7 SHAKES CENTRAL PERU",
     "Magnitude 6.7 tremor strikes Junin."),
    ("WORLD", "FUNERAL BOAT CAPSIZES IN NIGERIA",
     "Mourners drown as boat overturns."),
    ("WORLD", "BASRA POWER PLANT FIRE KILLS FOUR",
     "Blaze at Al-Haritha station probed."),
    ("WORLD", "19 YEARS FOR PLOT TO KILL SIKH LEADER",
     "Indian man jailed in New York plot."),
    ("WORLD", "PALISADES FIRE ARSONIST CONVICTED",
     "Los Angeles arsonist faces 40 years."),
    ("WORLD", "SALVADORAN TROOPS LOSE MEN IN HAITI",
     "Soldiers killed by explosives in Haiti."),
    ("WORLD", "TRUMP: EUROPE SHOULD DEFUND UKRAINE",
     "President's call follows Putin summit."),
    ("WORLD", "TRUMP WEIGHS NEW STRIKES ON IRAN",
     "Israel presses for swift US action."),
    ("ECONOMY", "AI SELL-OFF DRAGS MARKETS DOWN",
     "S&P 500 falls 3.7%; Nikkei down 5.1%."),
    ("ECONOMY", "ANTHROPIC DEBUTS AS $2 TRILLION FIRM",
     "Biggest IPO ever raises $81.3 billion."),
    ("ECONOMY", "ARGENTINA RISK TOPS 1,000 POINTS",
     "Investors grow nervous over economy."),
    ("ECONOMY", "KENYA STARTS ONSHORE OIL DRILLING",
     "First crude wells drilled in Turkana."),
    ("ECONOMY", "TRUMP THREATENS TAX ON AI CENTRES",
     "US firms building abroad face levy."),
    ("ECONOMY", "LUFTHANSA TO CUT 1,000 JOBS",
     "Cuts planned at Frankfurt and Munich."),
    ("CLIMATE", "CLIMATE TALKS RUN PAST DEADLINE",
     "COP31 deadlocked over fossil fuels."),
    ("SCIENCE", "PILL MAKES PANCREATIC TUMOURS VANISH",
     "Daraxonrasib works in 1 in 12 patients."),
    ("TECH", "FBI CRIME DATABASE REPORTEDLY HACKED",
     "Hackers said to enter FBI and USDA."),
    ("SPACE", "BEPICOLOMBO REACHES MERCURY ORBIT",
     "Probe arrives after eight-year trip."),
    ("HEALTH", "US LOSES MEASLES-FREE STATUS",
     "Elimination status lost as cases grow."),
    ("HEALTH", "UGANDA CURBS TRAVEL OVER EBOLA",
     "Gatherings limited as outbreak spreads."),
    ("SCIENCE", "CERN FINDS FIRST ULTRA-RARE DECAY",
     "Physicists see a rare particle decay."),
    ("SPACE", "VOYAGER 1 NOW 24 LIGHT-HOURS AWAY",
     "Farthest probe sails on through space."),
    ("SCIENCE", "AI MATHEMATICIAN CLAIMS RIEMANN PROOF",
     "Anthropic researcher cites AI help."),
    ("CULTURE", "BTS WIN FIVE MAMA AWARDS",
     "K-pop giants triumph in Osaka."),
    ("CULTURE", "RAMAYANA PASSES 1,574 CRORE WORLDWIDE",
     "Epic holds strong after 16 days."),
    ("SPORT", "VERSTAPPEN TAKES LAS VEGAS POLE",
     "Champion leads after Antonelli penalty."),
    ("SPORT", "ALCARAZ WINS AT ATP FINALS",
     "Spaniard beats Cobolli in Turin."),
    ("SPORT", "HARDEN PASSES KOBE ON 50-POINT LIST",
     "Most 50-point games in NBA history."),
]

# Columns: (x, width, [(header, [story indexes])]).
COLUMNS = [
    (24, 313, [("WORLD", list(range(0, 13)))]),
    (355, 313, [("WORLD", list(range(13, 19))),
                ("ECONOMY", list(range(19, 25))),
                ("CLIMATE", [25])]),
    (686, 314, [("SCIENCE & HEALTH", list(range(26, 34))),
                ("CULTURE", [34, 35]),
                ("SPORT", [36, 37, 38])]),
]

TICKER = ("MARKETS: S&P 500 6,910 -3.7% | NIKKEI -5.1% | FTSE 100 -1.0% "
          "| GOLD -4.6% | BITCOIN $57,850 | BRENT $89.95 +0.6%")
FOOTER = ("THE SATURDAY GLOBE - COMPILED FROM REPORTING PUBLISHED ON "
          "SATURDAY 21 NOVEMBER 2026 - PAGE 1")


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.buf), 3):
            self.buf[i] = r
            self.buf[i + 1] = g
            self.buf[i + 2] = b

    def px(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i], self.buf[i + 1], self.buf[i + 2] = color

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.px(xx, yy, color)

    def hline(self, x, y, w, color):
        for xx in range(x, x + w):
            self.px(xx, y, color)

    def vline(self, x, y, h, color):
        for yy in range(y, y + h):
            self.px(x, yy, color)

    def circle(self, cx, cy, r, color):
        x, y, d = 0, r, 3 - 2 * r
        while x <= y:
            for sx, sy in ((x, y), (y, x), (-x, y), (-y, x),
                           (x, -y), (y, -x), (-x, -y), (-y, -x)):
                self.px(cx + sx, cy + sy, color)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def text_w(self, text, scale):
        text = text.upper()
        n = len(text)
        if n == 0:
            return 0
        return n * 6 * scale - scale

    def draw_text(self, x, y, text, scale, color):
        text = text.upper()
        cx = x
        for ch in text:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits >> (4 - col) & 1:
                        self.rect(cx + col * scale, y + row * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx - x

    def wrap(self, text, max_w, scale):
        """Word-wrap upper-cased text to lines fitting max_w pixels."""
        words = text.upper().split(" ")
        lines = []
        cur = ""
        for word in words:
            trial = word if not cur else cur + " " + word
            if self.text_w(trial, scale) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines


def draw_section_header(cv, x, y, w, label):
    cv.rect(x, y, w, 20, NAVY)
    cv.draw_text(x + 8, y + 6, label, 1, WHITE)
    return 26  # header height + gap


def story_height(cv, col_w, headline, deck_lines, top_pad, bot_pad):
    lines = cv.wrap(headline, col_w, 2)
    h = top_pad + len(lines) * 16 + bot_pad
    if deck_lines:
        h += 3 + deck_lines * 9
    return h


def draw_story(cv, x, y, col_w, headline, deck, show_deck, top_pad, bot_pad):
    lines = cv.wrap(headline, col_w, 2)
    yy = y + top_pad
    for line in lines:
        cv.draw_text(x, yy, line, 2, INK)
        yy += 16
    if show_deck:
        yy += 3
        cv.draw_text(x, yy, deck, 1, GREY)
        yy += 9
    return yy + bot_pad


def render():
    cv = Canvas(W, H, PAPER)
    mx = 24
    cw = 976

    # Masthead band.
    cv.rect(mx, 16, cw, 76, NAVY)
    name = "THE SATURDAY GLOBE"
    tw = cv.text_w(name, 6)
    cv.draw_text((W - tw) // 2, 37, name, 6, WHITE)
    cv.circle(930, 54, 26, WHITE)
    cv.circle(930, 54, 18, WHITE)
    cv.vline(930, 28, 52, WHITE)
    cv.hline(904, 54, 52, WHITE)

    # Dateline strip.
    cv.hline(mx, 98, cw, INK)
    cv.draw_text(mx, 106, "SATURDAY, 21 NOVEMBER 2026", 1, INK)
    right = "40 STORIES FROM ONE DAY"
    cv.draw_text(W - mx - cv.text_w(right, 1), 106, right, 1, INK)
    cv.hline(mx, 120, cw, INK)

    # Lead story.
    _, headline, deck = LEAD
    cv.draw_text(mx, 130, "TOP STORY", 1, RED)
    cv.draw_text(mx, 144, headline, 4, INK)
    lead_lines = cv.wrap(deck, cw, 2)
    yy = 180
    for line in lead_lines:
        cv.draw_text(mx, yy, line, 2, INK)
        yy += 17
    cv.hline(mx, 222, cw, INK)

    # Columns.
    col_top = 232
    col_bottom = 956
    avail = col_bottom - col_top
    for x, col_w, blocks in COLUMNS:
        # Fit: start with every deck shown; drop decks from the bottom
        # stories and shrink gaps until the column fits.
        top_pad, bot_pad = 4, 5
        show = {}
        for _, idxs in blocks:
            for i in idxs:
                show[i] = True
        while True:
            total = 0
            for header, idxs in blocks:
                total += 26
                for i in idxs:
                    _, h, d = STORIES[i]
                    total += story_height(cv, col_w, h, 1 if show[i] else 0,
                                          top_pad, bot_pad)
            if total <= avail:
                break
            if bot_pad > 3:
                bot_pad -= 1
                continue
            if top_pad > 2:
                top_pad -= 1
                continue
            dropped = False
            for _, idxs in blocks:
                for i in reversed(idxs):
                    if show[i]:
                        show[i] = False
                        dropped = True
                        break
                if dropped:
                    break
            if not dropped:
                break
        y = col_top
        for header, idxs in blocks:
            y += draw_section_header(cv, x, y, col_w, header)
            for i in idxs:
                _, h, d = STORIES[i]
                y = draw_story(cv, x, y, col_w, h, d, show[i],
                               top_pad, bot_pad)
                cv.hline(x, y - 2, col_w, FAINT)

    # Markets ticker.
    cv.hline(mx, 962, cw, INK)
    tw = cv.text_w(TICKER, 1)
    cv.draw_text((W - tw) // 2, 970, TICKER, 1, INK)

    # Footer.
    cv.hline(mx, 986, cw, INK)
    cv.draw_text(mx, 994, FOOTER, 1, GREY)
    return cv


def png_bytes(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)
        start = y * cv.w * 3
        raw += cv.buf[start:start + cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(kind, data):
        out = struct.pack(">I", len(data)) + kind + data
        out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", comp) + chunk(b"IEND", b""))


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    data = png_bytes(render())
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s %d bytes sha256=%s"
          % (path, len(data), hashlib.sha256(data).hexdigest()))


if __name__ == "__main__":
    main()
