# EPİAŞ Enerji Fiyat Tahmini

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat&logo=python&logoColor=white)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat&logo=typescript&logoColor=white)]()

Türkiye elektrik piyasası (EPİAŞ) için 7 günlük MCP fiyat tahmini yapan full-stack web uygulaması.

Prophet time-series modeliyle saatlik tahminler üretiyor, React dashboard'da gösteriyor. Günlük otomatik veri senkronizasyonu ve haftalık model eğitimi için GitHub Actions kullanıyor.

**Veri:** EPİAŞ Şeffaflık Platformu API (17k+ saatlik kayıt)

---

## Özellikler

- 7 günlük MCP fiyat tahmini (Prophet time-series)
- Üretim/tüketim analizi (kaynak bazlı breakdown)
- Model performans takibi (MAPE, MAE, RMSE)
- Günlük veri senkronizasyonu (GitHub Actions)
- Haftalık otomatik model re-training

---

## Stack

**Frontend:** React + TypeScript + Vite + Recharts  
**Backend:** Node.js + Express + TypeScript  
**ML:** Python + Prophet  
**Database:** SQLite  
**CI/CD:** GitHub Actions

### Neden SQLite?

İlk başta PostgreSQL düşündüm ama MVP için SQLite yeterli geldi:
- 17k kayıt için performans sorunu yok
- Tek `.db` dosyası, deployment kolay
- PostgreSQL server kurmaya gerek kalmadı

Ama 100k+ kayıt geçerse PostgreSQL'e migrate etmek gerekecek.

---

## Ekran Görüntüleri

![Dashboard](screenshots/dashboard-overview.png)

![Production](screenshots/production-page.png)

![Consumption](screenshots/consumption-page.png)

---

## Model Performansı

17k+ saatlik EPİAŞ verisiyle eğitilmiş univariate Prophet modeli. 

**Tipik performans:**
- MAPE: %40-50 arası (fiyat volatilitesine göre değişiyor)
- Univariate model limiti (sadece geçmiş fiyat kullanıyor)

**Hedef:** Talep, üretim, gaz fiyatı eklenerek %15-20 MAPE'ye düşürülecek.

**Bilinen limit:** Ani spike'ları yakalamıyor (santral arızası vs.).

---

## Bilinen Limitler

**Univariate model:** Sadece geçmiş fiyat kullanıyor. Talep, üretim, doğalgaz fiyatı eklenince performans artacak.

**Spike yakalayamıyor:** Santral arızası, gaz kesintisi gibi ani sıçramalarda tahmin yanılıyor. Bunun için anomaly detection veya hybrid model gerekir.

**7+ gün güvenilmez:** Prophet'in yapısı gereği uzun vadeli tahmin zayıf. Kısa vadeli tahmin için tasarlandı.

**SQLite limiti:** 100k+ kayıtta yavaşlayabilir. O noktada PostgreSQL'e geçilmeli.

## Geçmiş tahminler ve yerel veri güncelleme

Git pull sonrasında yerel geliştirme veritabanını güncellemek için backend klasöründe `npm run db:sync` çalıştırın (backend sunucusu kapalı olmalıdır). `.env` dosyasındaki `DB_PATH=data/energy-dev.db` ayrı bir kopyayı kullanır; Git pull bu kopyayı güncellemez.

Eksik veya tarihleri hatalı haftaları kontrol etmek için backend klasöründe `python src/ml/catchup_weekly_forecasts.py --dry-run` kullanın. `--dry-run` olmadan her hafta kendi Pazartesi başlangıcından önceki fiyatlarla ayrı ayrı eğitilir. Gerçekleşen fiyatlar yalnızca tahminler kaydedildikten sonra karşılaştırma için okunur. Geriye dönük tahminlerin üretim zamanı, eğitim sınırı, son eğitim tarihi, satır sayısı ve veri özeti `forecast_provenance` tablosunda kaydedilir.

`forecast-history.json` tüm haftaları yayımlar; arayüz backend erişilemediğinde bu arşivi kullanır. Yeniden oluşturulan geçmiş haftalar **Geriye dönük tahmin** etiketi taşır. Haftalık otomasyon da geçmiş boşlukları kontrol eder.
