type LogLevel = 'info' | 'warn' | 'error' | 'success' | 'debug';

const COLORS = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
};

function getTimestamp(): string {
  return new Date().toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}

function formatMessage(level: LogLevel, message: string, indent = 0): string {
  const timestamp = `[${getTimestamp()}]`;
  const prefix = ' '.repeat(indent * 2);

  const icons: Record<LogLevel, string> = {
    info: '',
    warn: '',
    error: '',
    success: '',
    debug: '',
  };

  const colors: Record<LogLevel, string> = {
    info: COLORS.cyan,
    warn: COLORS.yellow,
    error: COLORS.red,
    success: COLORS.green,
    debug: COLORS.magenta,
  };

  return `${colors[level]}${timestamp}${COLORS.reset} ${prefix}${icons[level]} ${message}`;
}

export const logger = {
  info: (message: string, indent = 0) => {
    console.log(formatMessage('info', message, indent));
  },

  warn: (message: string, indent = 0) => {
    console.warn(formatMessage('warn', message, indent));
  },

  error: (message: string, indent = 0) => {
    console.error(formatMessage('error', message, indent));
  },

  success: (message: string, indent = 0) => {
    console.log(formatMessage('success', message, indent));
  },

  debug: (message: string, indent = 0) => {
    if (process.env.DEBUG) {
      console.log(formatMessage('debug', message, indent));
    }
  },

  divider: (char = '=', length = 80) => {
    console.log(char.repeat(length));
  },

  header: (title: string) => {
    console.log('');
    logger.divider();
    console.log(`${COLORS.bright}${title.toUpperCase().padStart((80 + title.length) / 2)}${COLORS.reset}`);
    logger.divider();
    console.log('');
  },

  subheader: (title: string) => {
    logger.divider('-', 80);
    console.log(`${COLORS.bright}  ${title}${COLORS.reset}`);
    logger.divider('-', 80);
  },

  progress: (current: number, total: number, label: string) => {
    const percent = ((current / total) * 100).toFixed(1);
    const bar = '='.repeat(Math.floor((current / total) * 30));
    const empty = ' '.repeat(30 - bar.length);
    console.log(`\r${COLORS.cyan}[${bar}${empty}] ${percent}% ${label}${COLORS.reset}`);
  },

  stats: (stats: Record<string, string | number>) => {
    Object.entries(stats).forEach(([key, value]) => {
      console.log(`  ${COLORS.dim}${key}:${COLORS.reset} ${value}`);
    });
  },
};
