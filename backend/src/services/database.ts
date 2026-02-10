import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import type { MCPItem, GenerationItem, ConsumptionItem } from '../types/epias.js';

// ES module için __dirname alternatifi
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Yolu .env'den al, yoksa varsayılanı kullan (prod için)
// Local development'ta DB_PATH=data/energy-dev.db olmalı
import dotenv from 'dotenv';
dotenv.config({ path: path.join(__dirname, '../../.env') });

const dbPathRel = process.env.DB_PATH || '../../data/energy.db';
const dbPath = path.isAbsolute(dbPathRel)
  ? dbPathRel
  : path.join(__dirname, dbPathRel.startsWith('data/') ? '../../' + dbPathRel : dbPathRel);

console.log(`🔌 Connecting to database at: ${dbPath}`);

// Database bağlantısı oluştur
export const db = new Database(dbPath);

// WAL mode etkinleştir (daha iyi performans)
db.pragma('journal_mode = WAL');

/**
 * Database tablolarını oluşturur
 */
export function initDatabase() {
  console.log('📦 Initializing database...');

  // MCP (Market Clearing Price) tablosu
  db.exec(`
    CREATE TABLE IF NOT EXISTS mcp_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      date TEXT NOT NULL,
      hour TEXT NOT NULL,
      price REAL NOT NULL,
      price_usd REAL,
      price_eur REAL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(date, hour)
    )
  `);

  // İndeks ekle (hızlı sorgular için)
  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_mcp_date ON mcp_data(date);
    CREATE INDEX IF NOT EXISTS idx_mcp_date_hour ON mcp_data(date, hour);
  `);

  // Üretim (Generation) tablosu
  db.exec(`
    CREATE TABLE IF NOT EXISTS generation_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      date TEXT NOT NULL,
      hour TEXT NOT NULL,
      total REAL NOT NULL,
      biomass REAL,
      fueloil REAL,
      geothermal REAL,
      hydro REAL,
      import_export REAL,
      lignite REAL,
      lng REAL,
      natural_gas REAL,
      naphtha REAL,
      river REAL,
      solar REAL,
      wind REAL,
      wasteheat REAL,
      asphaltite_coal REAL,
      black_coal REAL,
      import_coal REAL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(date, hour)
    )
  `);

  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_generation_date ON generation_data(date);
    CREATE INDEX IF NOT EXISTS idx_generation_date_hour ON generation_data(date, hour);
  `);

  // Tüketim (Consumption) tablosu
  db.exec(`
    CREATE TABLE IF NOT EXISTS consumption_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      date TEXT NOT NULL,
      hour TEXT NOT NULL,
      consumption REAL NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(date, hour)
    )
  `);

  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_consumption_date ON consumption_data(date);
    CREATE INDEX IF NOT EXISTS idx_consumption_date_hour ON consumption_data(date, hour);
  `);

  // Tahmin Geçmişi (Forecast History) tablosu
  db.exec(`
    CREATE TABLE IF NOT EXISTS forecast_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      week_start DATE NOT NULL,
      week_end DATE NOT NULL,
      forecast_datetime TEXT NOT NULL,

      predicted_price REAL NOT NULL,
      actual_price REAL,
      absolute_error REAL,
      percentage_error REAL,
      prophet_component REAL,
      xgboost_component REAL,
      lstm_component REAL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(week_start, forecast_datetime)
    )
  `);

  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_forecast_week ON forecast_history(week_start, week_end);
    CREATE INDEX IF NOT EXISTS idx_forecast_datetime ON forecast_history(forecast_datetime);
  `);

  // Haftalık Performans (Weekly Performance) tablosu
  db.exec(`
    CREATE TABLE IF NOT EXISTS weekly_performance (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      week_start DATE NOT NULL,
      week_end DATE NOT NULL,
      mape REAL NOT NULL,
      mae REAL NOT NULL,
      rmse REAL NOT NULL,
      total_predictions INTEGER NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(week_start)
    )
  `);

  db.exec(`
    CREATE INDEX IF NOT EXISTS idx_weekly_perf_week ON weekly_performance(week_start);
  `);

  console.log('✅ Database initialized successfully');
}

/**
 * MCP verilerini database'e toplu olarak ekler
 *
 * @param items - Eklenecek MCP verileri
 * @returns Eklenen kayıt sayısı
 */
export function insertMCPData(items: MCPItem[]): number {
  const insert = db.prepare(`
    INSERT OR REPLACE INTO mcp_data (date, hour, price, price_usd, price_eur)
    VALUES (?, ?, ?, ?, ?)
  `);

  // Transaction içinde toplu insert (çok daha hızlı)
  const insertMany = db.transaction((data: MCPItem[]) => {
    for (const item of data) {
      insert.run(item.date, item.hour, item.price, item.priceUsd, item.priceEur);
    }
  });

  insertMany(items);

  console.log(`✅ Inserted ${items.length} MCP records into database`);
  return items.length;
}

/**
 * Belirli bir tarih aralığındaki MCP verilerini getirir
 *
 * @param startDate - Başlangıç tarihi (YYYY-MM-DD)
 * @param endDate - Bitiş tarihi (YYYY-MM-DD)
 * @returns MCP verileri array'i
 */
export function getMCPData(startDate: string, endDate: string): MCPItem[] {
  const query = db.prepare(`
    SELECT date, hour, price, price_usd as priceUsd, price_eur as priceEur
    FROM mcp_data
    WHERE date >= ? AND date <= ?
    ORDER BY date, hour
  `);

  return query.all(startDate, endDate) as MCPItem[];
}

/**
 * Database'deki toplam kayıt sayısını getirir
 *
 * @returns Toplam MCP kayıt sayısı
 */
export function getMCPCount(): number {
  const query = db.prepare('SELECT COUNT(*) as count FROM mcp_data');
  const result = query.get() as { count: number };
  return result.count;
}

/**
 * Üretim verilerini database'e toplu olarak ekler
 *
 * @param items - Eklenecek üretim verileri
 * @returns Eklenen kayıt sayısı
 */
export function insertGenerationData(items: GenerationItem[]): number {
  const insert = db.prepare(`
    INSERT OR REPLACE INTO generation_data (
      date, hour, total, biomass, fueloil, geothermal, hydro,
      import_export, lignite, lng, natural_gas, naphtha, river, solar, wind,
      wasteheat, asphaltite_coal, black_coal, import_coal
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const insertMany = db.transaction((data: GenerationItem[]) => {
    for (const item of data) {
      insert.run(
        item.date, item.hour, item.total, item.biomass, item.fueloil,
        item.geothermal, item.dammedHydro, item.importExport, item.lignite,
        item.lng, item.naturalGas, item.naphta, item.river, item.sun, item.wind,
        item.wasteheat, item.asphaltiteCoal, item.blackCoal, item.importCoal
      );
    }
  });

  insertMany(items);

  console.log(`✅ Inserted ${items.length} Generation records into database`);
  return items.length;
}

/**
 * Tüketim verilerini database'e toplu olarak ekler
 *
 * @param items - Eklenecek tüketim verileri
 * @returns Eklenen kayıt sayısı
 */
export function insertConsumptionData(items: ConsumptionItem[]): number {
  const insert = db.prepare(`
    INSERT OR REPLACE INTO consumption_data (date, hour, consumption)
    VALUES (?, ?, ?)
  `);

  const insertMany = db.transaction((data: ConsumptionItem[]) => {
    for (const item of data) {
      // API'den "time" olarak geliyor, database'de "hour" olarak saklıyoruz
      insert.run(item.date, item.time, item.consumption);
    }
  });

  insertMany(items);

  console.log(`✅ Inserted ${items.length} Consumption records into database`);
  return items.length;
}

/**
 * Tüm tabloların kayıt sayısını döndürür
 */
export function getAllCounts() {
  const mcpCount = db.prepare('SELECT COUNT(*) as count FROM mcp_data').get() as { count: number };
  const genCount = db.prepare('SELECT COUNT(*) as count FROM generation_data').get() as { count: number };
  const consCount = db.prepare('SELECT COUNT(*) as count FROM consumption_data').get() as { count: number };

  return {
    mcp: mcpCount.count,
    generation: genCount.count,
    consumption: consCount.count
  };
}

/**
 * Database'i kapat
 */
export function closeDatabase() {
  db.close();
  console.log('🔒 Database connection closed');
}
