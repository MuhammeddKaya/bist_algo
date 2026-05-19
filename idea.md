# 🤖 BIST Algo Trading Botu — Tam Rehber

## 📌 Genel Bakış

Bu rehber, Borsa İstanbul (BIST) üzerinde çalışan bir **agentic AI al-sat botu** kurmanın tüm adımlarını anlatır.

- **Sermaye:** 10.000 TL başlangıç
- **Piyasa:** BIST (Borsa İstanbul)
- **Broker:** Deniz Yatırım + AlgoLab API
- **Dil:** Python
- **AI:** Claude API (Anthropic)

---

## 🏗️ Sistem Mimarisi

```
[Yahoo Finance / AlgoLab]
        ↓
   Fiyat Verisi
        ↓
  [Teknik Analiz]
  RSI + MACD + Hacim
        ↓
  [Claude AI Ajan]
  Karar: AL / SAT / BEKLE
        ↓
  [Risk Yöneticisi]
  Stop-loss kontrolü
        ↓
  [AlgoLab API]
  Gerçek Emir Gönder
        ↓
  [Telegram Bot]
  Seni Bilgilendir
```

---

## 🏦 Broker: Deniz Yatırım + AlgoLab

### Neden AlgoLab?
- Türkiye'de **bireysel yatırımcıya açık** tek tam Python API'si
- SPK lisanslı, yasal ve güvenli
- Online hesap açma (10 dakika)
- Ücretsiz API anahtarı

### Hesap Açma Adımları
1. [denizyatirim.com](https://www.denizyatirim.com) adresine git
2. Online hesap aç (TC kimlik gerekli)
3. Kimlik doğrulama yap (1-2 gün)
4. AlgoLab sayfasından API anahtarı talep et
5. 10.000 TL yatır

---

## 💰 Sermaye Yönetimi (10K TL)

```
10.000 TL
├── 7.000 TL → Aktif işlem sermayesi
├── 2.000 TL → Yedek / marjin
└── 1.000 TL → Teknik masraflar (API, sunucu)
```

### Pozisyon Başına Kural
| Kural | Değer |
|-------|-------|
| Max pozisyon | 1.400 TL (%20) |
| Stop-loss | %5 (70 TL max kayıp) |
| Günlük max kayıp | %3 (210 TL) |
| Hedef kâr/işlem | %2-3 |

---

## 📈 Hisse Seçimi

### BIST-30 Hedef Listesi (Yüksek Hacimli)
```
THYAO  - Türk Hava Yolları
GARAN  - Garanti Bankası
AKBNK  - Akbank
EREGL  - Ereğli Demir Çelik
SISE   - Şişecam
KCHOL  - Koç Holding
TUPRS  - Tüpraş
BIMAS  - BİM Mağazalar
FROTO  - Ford Otosan
ASELS  - Aselsan
```

### Neden Bu Hisseler?
- Günlük yüksek işlem hacmi → bot kolayca işlem yapabilir
- Likidite yüksek → alış/satış fiyat farkı (spread) düşük
- BIST-30 endeksinde → güvenilir, manipüle edilmesi zor

### Sabah Tarama (Otomatik)
Bot her sabah 09:45'te şunlara bakar:
- Önceki gün hacmine göre sıralama
- Gün içi volatilite potansiyeli
- RSI aşırı alım/satım bölgesi

---

## 📊 Trading Stratejisi

### Teknik Göstergeler
| Gösterge | Parametre | Sinyal |
|----------|-----------|--------|
| RSI | 14 periyot | <30 AL, >70 SAT |
| MACD | 12/26/9 | Kesişim yönü |
| Hacim | 20 günlük ort. | 1.5x üzeri onay |
| EMA | 9 / 21 | Trend yönü |

### Al Sinyali (3/4 şart sağlanmalı)
- [ ] RSI < 35
- [ ] MACD yukarı kesişim
- [ ] Hacim ortalamanın 1.5x üzerinde
- [ ] Fiyat EMA-9 üzerinde

### Sat Sinyali
- [ ] RSI > 65
- [ ] MACD aşağı kesişim
- [ ] VEYA stop-loss tetiklendi (%5 düşüş)
- [ ] VEYA hedef kâra ulaşıldı (%3)

---

## ⏰ Günlük İşlem Takvimi

```
09:30 - 10:00  → Piyasa açılışı (BOT BEKLER)
                  Açılış dalgalanması tehlikeli

10:00 - 10:15  → Sabah taraması
                  Hacim + sinyal analizi

10:15 - 12:30  → Aktif işlem dönemi
                  Al sinyalleri takip edilir

12:30 - 13:30  → Öğle sakinliği (dikkatli ol)
                  İşlem hacmi düşer

13:30 - 17:00  → Aktif işlem dönemi
                  Çıkış sinyalleri takip edilir

17:00 - 17:30  → Zorunlu çıkış
                  Tüm pozisyonlar kapatılır!

17:30          → Piyasa kapanışı
```

> ⚠️ **Önemli:** Bot gün sonunda tüm pozisyonları kapatır. Geceye pozisyon taşımaz.

---

## ⚖️ BIST Al-Sat Kuralları

### Limit Var mı?
**HAYIR.** Borsa İstanbul'da günlük al-sat işlem sayısı sınırlaması yoktur.

> Not: ABD borsalarındaki "PDT kuralı" (5 günde 3 işlem limiti) BIST'te **geçerli değildir**.

### Takas Süresi (T+2)
- Hisse satışından gelen para **2 iş günü** sonra kullanılabilir
- Bot bunu otomatik takip eder, nakit yönetimini buna göre yapar

### Komisyon
- Her alış + her satış için komisyon kesilir
- Ortalama: işlem tutarının %0.1 - %0.2'si
- Bot, komisyonu kâr hesaplamasına dahil eder

---

## 🛡️ Risk Yönetimi

### Günlük Korumalar
```python
MAX_GUNLUK_KAYIP = 210  # TL (sermayenin %3'ü)
MAX_POZISYON     = 1400  # TL (sermayenin %20'si)
STOP_LOSS        = 0.05  # %5
HEDEF_KAR        = 0.03  # %3
```

### Bot Otomatik Durdurma
Şu durumlarda bot kendini durdurur:
- Günlük kayıp limitine ulaşıldıysa
- İnternet/API bağlantısı koptuysa
- Piyasa devre kesici (circuit breaker) devreye girdiyse

---

## 🔧 Teknik Kurulum

### Gereksinimler
```bash
Python 3.10+
pip install algolab
pip install pandas
pip install ta          # Teknik analiz
pip install anthropic   # Claude API
pip install python-telegram-bot
```

### Temel Kod Yapısı
```python
from algolab import AlgoLab
import anthropic
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD

# Bağlantılar
algolab = AlgoLab(api_key="...", username="TC_NO", password="...")
claude  = anthropic.Anthropic(api_key="...")

# Ana döngü
while piyasa_acik():
    for hisse in HEDEF_LISTE:
        veri    = veri_cek(hisse)          # Fiyat verisi
        sinyal  = analiz_et(veri)          # RSI + MACD
        karar   = claude_karar_ver(sinyal) # AI kararı
        
        if karar == "AL" and nakit_var():
            algolab.buy(hisse, miktar)
        elif karar == "SAT" and pozisyon_var(hisse):
            algolab.sell(hisse, miktar)
    
    time.sleep(60)  # 1 dakikada bir kontrol
```

### Telegram Bildirimleri
Bot her işlemde sana şunu gönderir:
```
🟢 ALIM: THYAO
Fiyat: 285.40 TL
Miktar: 4 lot
RSI: 28 | MACD: ↑
Toplam: 1.141 TL
```

---

## 📅 Tavsiye Edilen Yol Haritası

```
Hafta 1-2:  Deniz Yatırım hesabı aç, API kur
Hafta 3-4:  Paper trading (simülasyon) - gerçek para YOK
Ay 2:       Sonuçları analiz et, stratejiyi ayarla
Ay 3:       500 TL ile gerçek işleme başla
Ay 4+:      Sonuçlara göre sermayeyi artır
```

---

## ⚠️ Önemli Uyarılar

1. **Kayıp riski gerçektir** — hiçbir bot %100 kazanamaz
2. **Paper trading atlanmamalı** — en az 2-4 hafta simülasyon yap
3. **Bot gözetimsiz bırakılmamalı** — günde en az 1 kontrol et
4. **Vergi yükümlülüğü var** — BIST hisse kazançları stopaja tabidir
5. **Bu bir yatırım tavsiyesi değildir** — kendi kararını kendin ver

---

## 📞 Faydalı Kaynaklar

| Kaynak | URL | Ne için? |
|--------|-----|---------|
| AlgoLab | algolab.com.tr | API dokümantasyonu |
| Deniz Yatırım | denizyatirim.com | Hesap açma |
| Fintables | fintables.com | BIST hisse analizi |
| Investing.com/tr | tr.investing.com | Piyasa tarama |
| TradingView | tradingview.com | Grafik analizi |
| BIST Resmi | borsaistanbul.com | Resmi veriler |

---

*Bu rehber Claude (Anthropic) tarafından oluşturulmuştur. Yatırım tavsiyesi niteliği taşımaz.*