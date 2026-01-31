import { validateConfig } from './config.js';
import { runScraper } from './scraper/index.js';
import { logger } from './utils/logger.js';

async function main(): Promise<void> {
  try {
    // Validate configuration
    validateConfig();

    // Parse CLI flags
    const updateMode = process.argv.includes('--update');
    const ignoreQuota = process.argv.includes('--ignore-quota');

    // Run the scraper
    await runScraper({ updateMode, ignoreQuota });
  } catch (error) {
    logger.error(`Fatal error: ${(error as Error).message}`);
    process.exit(1);
  }
}

main();
