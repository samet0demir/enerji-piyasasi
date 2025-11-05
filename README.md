# ⚡ EPİAŞ Enerji Fiyat Tahmin & Analiz Platformu

> **TL;DR:** Türkiye elektrik piyasasında saatlik MCP (Piyasa Takas Fiyatı) tahminleri yapan, üretim-tüketim analizleri sunan ve geçmiş performansı izleyen **full-stack web uygulaması**. Prophet ML modeli + React frontend + otomatik veri senkronizasyonu.

[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat&logo=typescript&logoColor=white)]()
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)]()
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)]()
[![Prophet](https://img.shields.io/badge/Prophet-Time%20Series-blue)]()
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)]()

---

## 🎯 Proje Hakkında

EPİAŞ (Enerji Piyasaları İşletme A.Ş.) Şeffaflık Platformu'ndan alınan gerçek piyasa verileriyle:

- 📊 **7 günlük MCP fiyat tahmini** (168 saatlik detay)
- 📈 **Üretim analizi** (kaynak bazlı: doğalgaz, rüzgar, güneş, vs.)
- 📉 **Tüketim analizi** (saatlik, günlük, haftalık)
- 🎯 **Model performans takibi** (MAPE, MAE, RMSE metrikleri)
- 🕒 **Haftalık karşılaştırma** (tahmin vs gerçekleşen)
- 🤖 **Otomatik veri toplama** (günlük EPİAŞ sync + haftalık model eğitimi)

### 👨‍💻 Benim Rolüm (Solo Proje)

✅ **Full-stack geliştirme** - Frontend (React + TypeScript) + Backend (Node.js + Express)
✅ **ML pipeline** - Prophet model eğitimi, tahmin üretimi, performans ölçümü
✅ **Database tasarımı** - SQLite schema, veri normalizasyonu
✅ **CI/CD** - GitHub Actions ile otomatik veri sync ve model retraining
✅ **UI/UX tasarımı** - Responsive dashboard, dinamik grafikler, renk kodlu performans göstergeleri

---

## 🚀 Kullanım Alanları

1. **Enerji Tüccarları** → Alım-satım kararları için fiyat tahminleri
2. **Sanayi Tesisleri** → Üretim planlaması (ucuz saatlerde operasyon)
3. **Enerji Perakende** → Fiyatlandırma stratejileri
4. **Araştırmacılar** → Enerji piyasası analizi

---

## 🏗️ Teknoloji Yığını ve Seçim Nedenleri

| Katman | Teknoloji | Neden? |
|--------|-----------|--------|
| **Frontend** | React 18 + TypeScript + Vite | Modern UI, type safety, hızlı dev server |
| **Grafik** | Recharts | Responsive, React-native, kolay customization |
| **Backend** | Node.js + Express + TypeScript | Full-stack TypeScript consistency, REST API |
| **ML** | Python + Prophet | Time series için industry standard, tatil/trend/seasonality otomatik |
| **Database** | SQLite + better-sqlite3 | Dosya tabanlı, kolay deployment, transaction support |
| **CI/CD** | GitHub Actions | Ücretsiz, kolay setup, cron scheduling |
| **Deployment** | Otomatik commit/push | Database ve model dosyaları Git'te versiyon kontrolü |

**Key Decision:** SQLite yerine PostgreSQL düşündüm ama:
- ✅ MVP için 17k+ kayıt SQLite'a fazlasıyla yeter
- ✅ Deployment basitleşti (tek `.db` dosyası)
- ✅ Zero-config (PostgreSQL server'a gerek yok)

---

## 📸 Ekran Görüntüleri

### Dashboard - Genel Bakış & Tahmin Performansı
![Dashboard](screenshots/dashboard-overview.png)

**Özellikler:**
- 📊 Tahmin vs Gerçek karşılaştırma grafiği
- 🎯 MAPE kartı (performansa göre renk değişimi: yeşil=iyi, kırmızı=kötü)
- 📈 Ortalama tahmin, Min-Max fiyat aralıkları
- 🕒 Hafta seçici (geçmiş performansları görüntüleme)

### Production - Üretim Kaynakları Analizi
![Production](screenshots/production-page.png)

**Özellikler:**
- ⚡ Kaynak bazlı breakdown (Doğalgaz, Rüzgar, Güneş, Hidrolik, Kömür, vs.)
- 📊 Saatlik üretim grafikleri
- 📋 Kaynak karşılaştırma tablosu
- 🔋 Toplam üretim metrikleri

### Consumption - Tüketim Analizi
![Consumption](screenshots/consumption-page.png)

**Özellikler:**
- 📉 Saatlik tüketim trendi
- ⬆️ Peak saatler analizi (en yüksek tüketim)
- ⬇️ Off-peak saatler analizi (en düşük tüketim)
- 📊 Hafta içi vs hafta sonu karşılaştırması

---

## ⚙️ Kurulum ve Çalıştırma

### Gereksinimler
- **Node.js** 18+
- **Python** 3.11+
- **Git**

### 1. Projeyi Klonla

```bash
git clone https://github.com/yourusername/epias-energy-forecast.git
cd epias-energy-forecast
```

### 2. Backend Kurulumu

```bash
cd backend

# Node.js bağımlılıkları
npm install

# Python virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Python bağımlılıkları
pip install -r requirements.txt
```

### 3. Environment Variables

`.env` dosyası oluştur (backend klasöründe):

```env
# EPİAŞ Transparency Platform Credentials
EPIAS_USERNAME=your_email@example.com
EPIAS_PASSWORD=your_password

# API Port
PORT=5001
```

**EPİAŞ hesabı yoksa:** [https://giris.epias.com.tr](https://giris.epias.com.tr) - ücretsiz kayıt

### 4. Backend'i Başlat

```bash
npm run dev
```

✅ API: `http://localhost:5001`

### 5. Frontend Kurulumu (Yeni Terminal)

```bash
cd frontend
npm install
npm run dev
```

✅ UI: `http://localhost:5173`

---

## 📊 Kullanım Örnekleri

### API Endpoint'leri

#### 1. Haftalık Veri Çekme
```bash
curl http://localhost:5001/api/weeks/available
```

**Response:**
```json
{
  "success": true,
  "weeks": [
    {
      "week_start": "2025-10-27",
      "week_end": "2025-11-02",
      "is_complete": true,
      "completion_percentage": 100,
      "performance": {
        "mape": 44.59,
        "mae": 525.11,
        "rmse": 682.09
      }
    }
  ]
}
```

#### 2. Belirli Bir Hafta Detayları
```bash
curl http://localhost:5001/api/weeks/2025-10-27/data
```

#### 3. Sunucu Durumu
```bash
curl http://localhost:5001/api/health
```

---

## 📈 Metrikler ve Performans

### Veri Seti
- **17,712+ saatlik kayıt** (2+ yıllık veri)
- **168 saatlik tahmin** (7 gün)
- **Günlük otomatik sync** (saat 05:00 TRT)
- **Haftalık model eğitimi** (her Pazartesi 07:00 TRT)

### Model Performansı

| Metrik | Açıklama | Değer |
|--------|----------|-------|
| **MAPE** | Mean Absolute Percentage Error | %44.6 (geçen hafta) |
| **MAE** | Ortalama mutlak hata | 525 TRY |
| **RMSE** | Kök ortalama kare hata | 682 TRY |

**Performans Değerlendirmesi (MAPE):**
- 🟢 < 10%: Mükemmel
- 🟢 10-20%: İyi
- 🟡 20-30%: Orta
- 🟠 30-40%: Zayıf
- 🔴 ≥ 40%: Kötü

**Not:** Şu anki %44 MAPE, univariate (tek değişkenli) modelin beklenen sınırı. Multivariate model (talep, üretim, gaz fiyatı) ile %15-20 hedefleniyor.

### Otomatik İş Akışları

✅ **GitHub Actions** ile tam otomatik:
1. **Günlük veri toplama** - Her gün 02:00 UTC (05:00 TRT)
2. **Haftalık model eğitimi** - Her Pazartesi 04:00 UTC (07:00 TRT)
3. **Otomatik commit/push** - Database ve model versiyonlama

---

## 🧠 Teknik Zorluklar ve Çözümler

### 1. **Cumartesi Verisi Kaybı Bug** 🐛

**Problem:**
- Haftalık performans hesaplamasında her hafta 24 saat eksik (%86 tamamlanma)
- Sadece Cumartesi günleri kayboluyor

**Root Cause:**
```python
# YANLIŞ: String comparison
WHERE date <= '2025-10-26 23:59:59'

# mcp_data'daki format: '2025-10-26T00:00:00+03:00'
# 'T' > ' ' (ASCII), bu yüzden Cumartesi filtreleniyor ❌
```

**Çözüm:**
```python
# DOĞRU: Date boundary kullan
next_day = week_end + 1 day
WHERE date >= week_start AND date < next_day
```

**Etki:** %86 → %100 tamamlanma, doğru MAPE hesaplaması

---

### 2. **MAPE Değerlendirme Yanılgısı** 🎨

**Problem:**
- MAPE %46 (kötü performans) ama UI'da **yeşil kart** + "Düşük" yazıyordu
- Kullanıcı kafa karışıklığı (yeşil = iyi zannetme)

**Çözüm:**
```typescript
// Dinamik renk sistemi
const getMapeColorClass = (mape: number) => {
  if (mape < 10) return 'mape-excellent';  // Koyu yeşil
  if (mape < 20) return 'mape-good';       // Yeşil
  if (mape < 30) return 'mape-average';    // Sarı
  if (mape < 40) return 'mape-poor';       // Turuncu
  return 'mape-bad';                       // Kırmızı
};
```

**Etki:** MAPE %46 → **kırmızı kart** + "Kötü" yazısı (doğru görsel feedback)

---

### 3. **Haftalık Performans Tracking** 📊

**Challenge:** Geçmiş haftalara göz atma + karşılaştırma

**Çözüm:**
- `forecast_history` tablosuna `week_start`/`week_end` kolonları eklendi
- `weekly_performance` tablosu (MAPE, MAE, RMSE)
- Backend API: `/api/weeks/available`, `/api/weeks/:week_start/data`
- Frontend: `WeekSelector` component (dropdown ile geçmiş haftalar)

**Sonuç:** Kullanıcı herhangi bir geçmiş haftayı seçip o haftanın tahmin vs gerçek performansını görebiliyor

---

## 🧪 Testing & CI/CD

### Manuel Test (Lokal)

```bash
# Backend API test
curl http://localhost:5001/api/health

# Model eğitimi test (Python venv aktif)
cd backend
python src/ml/train_prophet.py

# Haftalık workflow test
python src/ml/weekly_workflow.py
```

### GitHub Actions (Otomatik)

**Workflow Dosyaları:**
- `.github/workflows/daily-sync.yml` - Günlük veri toplama
- `.github/workflows/weekly-training.yml` - Haftalık model eğitimi

**CI Badge'ler:**
- ✅ Daily Sync: Son başarılı çalışma görünür
- ✅ Weekly Training: Model versiyonu track edilir

---

## 🗺️ Roadmap (Gelecek Geliştirmeler)

### **Faz 1: Model İyileştirme** (Öncelikli)
- [ ] **Multivariate model** - Talep, üretim, gaz fiyatı, hava durumu ekle
- [ ] **XGBoost ensemble** - Prophet + XGBoost kombinasyonu
- [ ] **Hyperparameter tuning** - Optuna ile otomatik optimizasyon
- [ ] **Hedef:** MAPE %44 → %15-20

### **Faz 2: UI/UX İyileştirmeleri**
- [ ] **Alert sistemi** - Fiyat eşik uyarıları (email/SMS)
- [ ] **Karşılaştırma modu** - İki haftayı yan yana karşılaştır
- [ ] **Export fonksiyonu** - CSV/PDF rapor indirme
- [ ] **Dark/Light mode** - Kullanıcı tercihi

### **Faz 3: Advanced Analytics**
- [ ] **Senaryo analizi** - "Eğer gaz fiyatı %20 artarsa?" simülasyonu
- [ ] **P&L hesaplayıcı** - Alım-satım stratejisi kar/zarar
- [ ] **Anomaly detection** - Spike tespiti ve uyarı

### **Faz 4: Production Hardening**
- [ ] **PostgreSQL migration** - Scalability için
- [ ] **Redis caching** - API response caching
- [ ] **Docker containerization** - Kolay deployment
- [ ] **Monitoring** - Prometheus + Grafana
- [ ] **Unit tests** - Backend + Frontend coverage

---

## 🐛 Bilinen Limitasyonlar

### Model (v1.0)
1. ✗ **Univariate yaklaşım** - Sadece geçmiş MCP verisi kullanılıyor
   - Talep, üretim, gaz fiyatı gibi sürücüler yok
   - **Çözüm:** Faz 1'de multivariate model

2. ✗ **Spike yakalamama** - Ani fiyat sıçramalarını tahmin edemez
   - Örn: Santral arızası, gaz kesintisi
   - **Çözüm:** Classification + Regression iki aşamalı model

3. ✗ **7 günden uzun tahmin güvenilmez** - Prophet'in doğası
   - Kabul edilen limitasyon (kısa vadeli tahmin odaklı sistem)

### Infrastructure
1. ✗ **SQLite limitleri** - 100k+ kayıtta yavaşlayabilir
   - **Çözüm:** PostgreSQL migration (Faz 4)

2. ✗ **Single instance** - Horizontal scaling yok
   - **Çözüm:** Docker + Load Balancer (Faz 4)

---

## 📁 Proje Yapısı

```
enerji/
├── frontend/                    # React + TypeScript UI
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx    # Ana sayfa (tahmin grafikleri)
│   │   │   ├── Production.tsx   # Üretim analizi
│   │   │   └── Consumption.tsx  # Tüketim analizi
│   │   ├── components/
│   │   │   └── WeekSelector.tsx # Hafta seçici dropdown
│   │   ├── services/
│   │   │   └── api.ts           # Backend API client
│   │   └── App.css              # Global styles (MAPE renkleri)
│   └── package.json
│
├── backend/                     # Node.js + Express API
│   ├── src/
│   │   ├── index.ts             # Express server
│   │   ├── ml/
│   │   │   ├── train_prophet.py         # Model eğitimi
│   │   │   ├── predict.py               # Tahmin üretimi
│   │   │   ├── compare_forecasts.py     # Performans hesaplama
│   │   │   ├── export_json.py           # Frontend JSON export
│   │   │   └── weekly_workflow.py       # Otomatik iş akışı
│   │   ├── scripts/
│   │   │   └── dailyDataSync.ts         # Günlük EPİAŞ sync
│   │   └── services/
│   │       └── epiasClient.ts           # EPİAŞ API wrapper
│   ├── data/
│   │   └── energy.db            # SQLite (17,712+ kayıt)
│   ├── models/
│   │   └── prophet_model.json   # Eğitilmiş model
│   ├── public/
│   │   └── forecasts.json       # Frontend için export
│   └── requirements.txt         # Python dependencies
│
├── .github/workflows/           # CI/CD
│   ├── daily-sync.yml          # Günlük veri toplama
│   └── weekly-training.yml     # Haftalık model eğitimi
│
└── README.md                    # Bu dosya
```

---

## 📝 Lisans

MIT License - Açık kaynak

---

## 👤 Geliştirici

**Samet Demir**
- 📧 Email: demirsamett11@gmail.com
- 💼 LinkedIn: [linkedin.com/in/samet-demir](https://linkedin.com/in/samet-demir)
- 🐙 GitHub: [github.com/yourusername](https://github.com/yourusername)

---

## 🙏 Acknowledgments

- **EPİAŞ Transparency Platform** - Veri kaynağı
- **Facebook Prophet** - Time series forecasting library
- **Recharts** - React charting library

---

**Son Güncelleme:** 5 Kasım 2025
**Versiyon:** 1.0 (MVP Tamamlandı)
**Durum:** ✅ Production Ready (deployment bekleniyor)

---

### 🚀 Hızlı Başlangıç (TL;DR)

```bash
# 1. Clone + Backend setup
git clone <repo> && cd enerji/backend
npm install && python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt

# 2. .env dosyası oluştur (EPİAŞ credentials)
echo "EPIAS_USERNAME=your@email.com" > .env
echo "EPIAS_PASSWORD=yourpass" >> .env

# 3. Backend başlat
npm run dev  # http://localhost:5001

# 4. Frontend başlat (yeni terminal)
cd ../frontend && npm install && npm run dev  # http://localhost:5173
```

✅ Tarayıcıda `http://localhost:5173` → Dashboard'u görmelisin!
