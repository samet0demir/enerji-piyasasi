
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const prodDbPath = path.join(__dirname, '../data/energy.db');
const devDbPath = path.join(__dirname, '../data/energy-dev.db');

console.log('🔄 Syncing production data to local development database...');

if (!fs.existsSync(prodDbPath)) {
    console.error('❌ Error: Production database (energy.db) not found!');
    console.log('   Run "git pull" to fetch the latest data from GitHub.');
    process.exit(1);
}

try {
    // Backup current dev db just in case
    if (fs.existsSync(devDbPath)) {
        const backupPath = `${devDbPath}.backup-${Date.now()}`;
        fs.copyFileSync(devDbPath, backupPath);
        console.log(`📦 Created backup of current local db: ${path.basename(backupPath)}`);
    }

    // Copy prod to dev
    fs.copyFileSync(prodDbPath, devDbPath);
    console.log('✅ Success! Local database updated with latest production data.');
    console.log('   You can now start the app with "npm run dev".');
} catch (error) {
    console.error('❌ Sync failed:', error);
    process.exit(1);
}
