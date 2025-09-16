from dataclasses import dataclass

@dataclass(frozen=True)
class Theme:
    # core tokens you already use
    BG: str
    BG_QSS: str       # optional gradient (right-hand side of a CSS value)
    TXT: str
    TXT_STRONG: str
    CARD_BG: str
    CARD_BORDER: str
    PLOT_FG: str
    BTN_BG: str
    BTN_BG_DOWN: str
    BTN_BORDER: str
    GOOD: str
    BAD: str
    GRAY: str
    PLOT_BG: str

DARK = Theme(
    BG="#0f1b22", BG_QSS="", TXT="#EAF2FF", TXT_STRONG="#000000",
    CARD_BG="#132530", CARD_BORDER="#1f3642", PLOT_FG="#7fdbff", 
    BTN_BG="#142a36", BTN_BG_DOWN="#0e2029", BTN_BORDER="#224050",
    GOOD="#2ecc71", BAD="#ff4136", GRAY="#7f8c8d", PLOT_BG="#0f1b22",
)

LIGHT = Theme(
    BG="#f6f8fb", BG_QSS="", TXT="#17212b", TXT_STRONG="#0b1117",
    CARD_BG="#ffffff", CARD_BORDER="#d5dde6", PLOT_FG="#8a99a6", 
    BTN_BG="#eef2f7", BTN_BG_DOWN="#e2e8f0", BTN_BORDER="#cbd5e1",
    GOOD="#1f9d55", BAD="#cc2936", GRAY="#8a99a6", PLOT_BG="#f6f8fb", 
)
SUB_DRK = Theme(
    BG="#0b2a38",     
    BG_QSS=("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #0a1a21, stop:0.45 #093340, stop:1 #0a4a5b)"),
    TXT="white", TXT_STRONG="#000000", 
    CARD_BG="#0e3b4e", CARD_BORDER="#2d6f88", PLOT_FG="#7fdbff", 
    BTN_BG="#0e3b4e", BTN_BG_DOWN="#11475e",BTN_BORDER="#2d6f88",
    GOOD="#2ecc40", BAD="#b71c1c", GRAY="#7f8c8d", PLOT_BG="#0b2a38", 
)
# --- Discord-inspired looks ---

NEON_LIGHTS = Theme(
    BG="#0e1822",
    BG_QSS=("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #0E1B24, stop:0.45 #14324A, stop:1 #2B1950)"),
    TXT="#E9F5FF", TXT_STRONG="#FFFFFF",
    CARD_BG="#112836", CARD_BORDER="#1e3e51", PLOT_FG="#7fdbff", 
    BTN_BG="#16364A", BTN_BG_DOWN="#0f2735", BTN_BORDER="#28556e",
    GOOD="#2ee6a6", BAD="#ff5a87", GRAY="#7f8c8d",
    PLOT_BG="#0f1b24",
)

CHROMA_GLOW = Theme(
    BG="#0b1220",
    BG_QSS=("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #0B1220, stop:0.35 #0d2b52, stop:0.7 #3c1f69, stop:1 #6e1448)"),
    TXT="#EAF2FF", TXT_STRONG="#FFFFFF",
    CARD_BG="#0f2134", CARD_BORDER="#244466", PLOT_FG="#7fdbff", 
    BTN_BG="#12385a", BTN_BG_DOWN="#0e2b45", BTN_BORDER="#2a5e8b",
    GOOD="#38e6b5", BAD="#ff4d7a", GRAY="#8aa0b3",
    PLOT_BG="#0b1220",
)

THEMES = {
    "Light": LIGHT,
    "Dark": DARK,
    "Submarine": SUB_DRK,
    "Neon Lights": NEON_LIGHTS,
    "Chroma Glow": CHROMA_GLOW,
}

DEFAULT_THEME = "Dark"