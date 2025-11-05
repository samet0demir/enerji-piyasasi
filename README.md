#  EPİAŞ Enerji Fiyat Tahmin & Analiz Platformu

> **TL;DR:** Türkiye elektrik piyasasında saatlik MCP (Piyasa Takas Fiyatı) tahminleri yapan, üretim-tüketim analizleri sunan ve geçmiş performansı izleyen **full-stack web uygulaması**. Prophet ML modeli + React frontend + otomatik veri senkronizasyonu.

[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat&logo=typescript&logoColor=white)]()
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)]()
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)]()
[![Prophet](https://img.shields.io/badge/Prophet-Time%20Series-blue)]()
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white)]()

---

##  Proje Hakkında

EPİAŞ (Enerji Piyasaları İşletme A.Ş.) Şeffaflık Platformu'ndan alınan gerçek piyasa verileriyle:

-  **7 günlük MCP fiyat tahmini** (168 saatlik detay)
-  **Üretim analizi** (kaynak bazlı: doğalgaz, rüzgar, güneş, vs.)
-  **Tüketim analizi** (saatlik, günlük, haftalık)
-  **Model performans takibi** (MAPE, MAE, RMSE metrikleri)
-  **Haftalık karşılaştırma** (tahmin vs gerçekleşen)
-  **Otomatik veri toplama** (günlük EPİAŞ sync + haftalık model eğitimi)

###  Benim Rolüm (Solo Proje)

 **Full-stack geliştirme** - Frontend (React + TypeScript) + Backend (Node.js + Express)
 **ML pipeline** - Prophet model eğitimi, tahmin üretimi, performans ölçümü
 **Database tasarımı** - SQLite schema, veri normalizasyonu
 **CI/CD** - GitHub Actions ile otomatik veri sync ve model retraining
 **UI/UX tasarımı** - Responsive dashboard, dinamik grafikler, renk kodlu performans göstergeleri

---

##  Kullanım Alanları

1. **Enerji Tüccarları** → Alım-satım kararları için fiyat tahminleri
2. **Sanayi Tesisleri** → Üretim planlaması (ucuz saatlerde operasyon)
3. **Enerji Perakende** → Fiyatlandırma stratejileri
4. **Araştırmacılar** → Enerji piyasası analizi

---

##  Teknoloji Yığını ve Seçim Nedenleri

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
-  MVP için 17k+ kayıt SQLite'a fazlasıyla yeter
-  Deployment basitleşti (tek `.db` dosyası)
-  Zero-config (PostgreSQL server'a gerek yok)

---

##  Ekran Görüntüleri

### Dashboard - Genel Bakış & Tahmin Performansı
![Dashboard](screenshots/dashboard-overview.png)

**Özellikler:**
-  Tahmin vs Gerçek karşılaştırma grafiği
-  MAPE kartı (performansa göre renk değişimi: yeşil=iyi, kırmızı=kötü)
-  Ortalama tahmin, Min-Max fiyat aralıkları
-  Hafta seçici (geçmiş performansları görüntüleme)

### Production - Üretim Kaynakları Analizi
![Production](screenshots/production-page.png)

**Özellikler:**
-  Kaynak bazlı breakdown (Doğalgaz, Rüzgar, Güneş, Hidrolik, Kömür, vs.)
-  Saatlik üretim grafikleri
-  Kaynak karşılaştırma tablosu
-  Toplam üretim metrikleri

### Consumption - Tüketim Analizi
![Consumption](screenshots/consumption-page.png)

**Özellikler:**
-  Saatlik tüketim trendi
-  Peak saatler analizi (en yüksek tüketim)
-  Off-peak saatler analizi (en düşük tüketim)
-  Hafta içi vs hafta sonu karşılaştırması

---

## Gereksinimler
- **Node.js** 18+
- **Python** 3.11+
- **Git**

---

##  Metrikler ve Performans

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

 **GitHub Actions** ile tam otomatik:
1. **Günlük veri toplama** - Her gün 02:00 UTC (05:00 TRT)
2. **Haftalık model eğitimi** - Her Pazartesi 04:00 UTC (07:00 TRT)
3. **Otomatik commit/push** - Database ve model versiyonlama

---

##  Testing & CI/CD

### GitHub Actions (Otomatik)

**Workflow Dosyaları:**
- `.github/workflows/daily-sync.yml` - Günlük veri toplama
- `.github/workflows/weekly-training.yml` - Haftalık model eğitimi

**CI Badge'ler:**
-  Daily Sync: Son başarılı çalışma görünür
-  Weekly Training: Model versiyonu track edilir

---

##  Roadmap (Gelecek Geliştirmeler)

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

##  Bilinen Limitasyonlar

### Model (v1.0)
1.  **Univariate yaklaşım** - Sadece geçmiş MCP verisi kullanılıyor
   - Talep, üretim, gaz fiyatı gibi sürücüler yok
   - **Çözüm:** Faz 1'de multivariate model

2.  **Spike yakalamama** - Ani fiyat sıçramalarını tahmin edemez
   - Örn: Santral arızası, gaz kesintisi
   - **Çözüm:** Classification + Regression iki aşamalı model

3.  **7 günden uzun tahmin güvenilmez** - Prophet'in doğası
   - Kabul edilen limitasyon (kısa vadeli tahmin odaklı sistem)

### Infrastructure
1.  **SQLite limitleri** - 100k+ kayıtta yavaşlayabilir
   - **Çözüm:** PostgreSQL migration (Faz 4)

2.  **Single instance** - Horizontal scaling yok
   - **Çözüm:** Docker + Load Balancer (Faz 4)


---

**Son Güncelleme:** 5 Kasım 2025
**Versiyon:** 1.0 (MVP Tamamlandı)
