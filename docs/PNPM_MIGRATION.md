# Migrating to pnpm for Frontend

## Why pnpm?

`pnpm` is a fast, disk space efficient package manager for Node.js:
- ✅ **3x faster** than npm
- ✅ **Saves disk space** - uses hard links to avoid duplicate packages
- ✅ **Stricter** - prevents phantom dependencies
- ✅ **Better monorepo support**

## Changes Made

### 1. `package.json` - Added packageManager field
```json
{
  "packageManager": "pnpm@9.0.0"
}
```

This ensures the correct package manager is used.

### 2. `deploy.sh` - Updated to use pnpm
- Auto-installs pnpm if not available
- Uses `pnpm install` instead of `npm install`
- Uses `pnpm run build` and `pnpm run start`

### 3. `dev.sh` - Updated to use pnpm
- Auto-installs pnpm if not available
- Uses `pnpm run dev` for development

## Installation

### On Your Mac (Development)
```bash
# Install pnpm globally
npm install -g pnpm

# Or via Homebrew
brew install pnpm
```

### On Server (mac-mini)
The deploy script will automatically install pnpm if it's not available.

## Usage

### Development
```bash
# Install dependencies
cd frontend/nextjs-app
pnpm install

# Run dev server
pnpm run dev

# Build
pnpm run build
```

### Production
The `deploy.sh` script automatically uses pnpm.

## Benefits

1. **Faster installs** - 3x faster than npm
2. **Disk space efficient** - Shares packages across projects
3. **Stricter dependency resolution** - Prevents phantom dependencies
4. **Better for CI/CD** - Faster builds in production

## Migration Notes

- `node_modules` structure is different with pnpm (uses symlinks)
- If you have issues, you can delete `node_modules` and reinstall:
  ```bash
  rm -rf node_modules
  pnpm install
  ```

## Compatibility

- ✅ Works with Next.js 15
- ✅ Works with all existing npm scripts
- ✅ Compatible with npm (can fallback if needed)
