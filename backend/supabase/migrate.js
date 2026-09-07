#!/usr/bin/env node
/**
 * Supabase Migration Runner (Node.js)
 * Reads and applies SQL migrations from backend/supabase/migrations/
 * Tracks applied migrations in the `_schema_migrations` table.
 */

const fs = require('fs');
const path = require('path');

function loadEnv(envPath) {
  const env = {};
  if (!fs.existsSync(envPath)) return env;
  const content = fs.readFileSync(envPath, 'utf-8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith('#') && trimmed.includes('=')) {
      const idx = trimmed.indexOf('=');
      const key = trimmed.slice(0, idx).trim();
      const val = trimmed.slice(idx + 1).trim();
      env[key] = val;
    }
  }
  return env;
}

async function run() {
  const scriptDir = __dirname;
  const backendDir = path.resolve(scriptDir, '..');
  const envPath = path.join(backendDir, '.env');
  const env = loadEnv(envPath);

  const dbUrl = env.DATABASE_URL || process.env.DATABASE_URL;
  const migrationsDir = path.join(scriptDir, 'migrations');

  console.log('='.repeat(60));
  console.log('Autocert Supabase Migration Runner (Node.js)');
  console.log('='.repeat(60));

  const files = fs.readdirSync(migrationsDir)
    .filter(f => f.endsWith('.sql'))
    .sort();

  if (files.length === 0) {
    console.log(`No SQL migration files found in ${migrationsDir}`);
    return;
  }

  console.log(`Found ${files.length} migration files:`);
  files.forEach(f => console.log(`  - ${f}`));
  console.log();

  if (!dbUrl || dbUrl.includes('your-project-ref')) {
    console.log('[NOTICE] Direct DATABASE_URL is not configured in backend/.env.');
    console.log('To run migrations automatically via Node.js, configure DATABASE_URL:');
    console.log('  DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres');
    console.log();
    console.log('Alternatively, you can copy-paste the SQL files directly into the Supabase SQL Editor:');
    files.forEach(f => console.log(`  -> ${path.join(migrationsDir, f)}`));
    return;
  }

  let Client;
  try {
    Client = require('pg').Client;
  } catch (err) {
    console.log('[ERROR] The "pg" package is not installed.');
    console.log('Install it by running: npm install pg');
    return;
  }

  const client = new Client({ connectionString: dbUrl });
  await client.connect();

  try {
    await client.query(`
      CREATE TABLE IF NOT EXISTS _schema_migrations (
        version VARCHAR(255) PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
      );
    `);

    const { rows } = await client.query('SELECT version FROM _schema_migrations;');
    const applied = new Set(rows.map(r => r.version));

    for (const file of files) {
      if (applied.has(file)) {
        console.log(`  [SKIP] ${file} (already applied)`);
        continue;
      }

      console.log(`  [APPLYING] ${file}...`);
      const sqlContent = fs.readFileSync(path.join(migrationsDir, file), 'utf-8');
      await client.query('BEGIN');
      try {
        await client.query(sqlContent);
        await client.query('INSERT INTO _schema_migrations (version) VALUES ($1);', [file]);
        await client.query('COMMIT');
        console.log(`  [SUCCESS] ${file} applied successfully.`);
      } catch (e) {
        await client.query('ROLLBACK');
        throw e;
      }
    }

    if (process.argv.includes('--seed')) {
      const seedPath = path.join(scriptDir, 'seed.sql');
      if (fs.existsSync(seedPath)) {
        console.log(`\n  [APPLYING SEED] seed.sql...`);
        const seedSql = fs.readFileSync(seedPath, 'utf-8');
        await client.query(seedSql);
        console.log('  [SUCCESS] Seed data applied successfully.');
      }
    }

    console.log('\nAll database migrations are up to date.');
  } catch (err) {
    console.error('\n[FAILED] Error applying migrations:', err.message);
    process.exit(1);
  } finally {
    await client.end();
  }
}

run();
