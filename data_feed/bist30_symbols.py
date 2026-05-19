BIST30_SYMBOLS = [
    "THYAO.IS",
    "GARAN.IS",
    "AKBNK.IS",
    "EREGL.IS",
    "SISE.IS",
    "KCHOL.IS",
    "TUPRS.IS",
    "BIMAS.IS",
    "FROTO.IS",
    "ASELS.IS",
    "YKBNK.IS",
    "SAHOL.IS",
    "PGSUS.IS",
    "TCELL.IS",
    "ENKAI.IS",
    "KOZAL.IS",
    "VESTL.IS",
    "EKGYO.IS",
    "TOASO.IS",
    "SOKM.IS",
]

SYMBOL_NAMES = {
    "THYAO.IS": "Türk Hava Yolları",
    "GARAN.IS": "Garanti Bankası",
    "AKBNK.IS": "Akbank",
    "EREGL.IS": "Ereğli Demir Çelik",
    "SISE.IS": "Şişecam",
    "KCHOL.IS": "Koç Holding",
    "TUPRS.IS": "Tüpraş",
    "BIMAS.IS": "BİM Mağazalar",
    "FROTO.IS": "Ford Otosan",
    "ASELS.IS": "Aselsan",
    "YKBNK.IS": "Yapı Kredi Bankası",
    "SAHOL.IS": "Sabancı Holding",
    "PGSUS.IS": "Pegasus",
    "TCELL.IS": "Turkcell",
    "ENKAI.IS": "Enka İnşaat",
    "KOZAL.IS": "Koza Altın",
    "VESTL.IS": "Vestel",
    "EKGYO.IS": "Emlak Konut GYO",
    "TOASO.IS": "Tofaş",
    "SOKM.IS": "Şok Marketler",
}


def display_name(symbol: str) -> str:
    return SYMBOL_NAMES.get(symbol, symbol.replace(".IS", ""))
