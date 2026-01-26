import { validateConfig } from './config.js';
import { runScraper } from './scraper/index.js';
import { logger } from './utils/logger.js';

async function main(): Promise<void> {
  try {
    // Validate configuration
    validateConfig();

    // Run the scraper
    await runScraper();
  } catch (error) {
    logger.error(`Fatal error: ${(error as Error).message}`);
    process.exit(1);
  }
}

main();
