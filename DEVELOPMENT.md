# Development Guide

## 🚀 Quick Start

```bash
python3 run.py
```
- Starts Firebase emulator automatically  
- **Always runs smart sync** - only updates what's different
- Restores deleted data automatically
- Fast because it skips unchanged data

## 🔄 How Smart Sync Works

When you run `python3 run.py`:
1. **Compares** emulator vs production data
2. **Updates only** documents that are different
3. **Adds** new documents (like new cards)
4. **Removes** documents that no longer exist in production
5. **Skips** documents that are identical

### Smart Sync Benefits:
- ✅ **Fast** - Only downloads what changed
- ✅ **Efficient** - Skips identical data
- ✅ **Complete** - Adds new cards, updates profiles
- ✅ **Automatic** - Detects all differences automatically

### What gets synchronized:
- 🔄 **cards/** - New cards added, edited cards updated
- 🔄 **users/** - Your profile changes, friend updates
- 🔄 **decks/** - New decks, modified decks
- 🔄 **internal_config/** - App configuration changes
- 🔄 **Everything else** - Any collection differences

## 🔥 Firebase Emulator

The emulator provides:
- **Complete mirror** - Exact copy of production data
- **FREE** - No Firestore costs
- **Isolated** - Your local changes don't affect production
- **Persistent** - Data saved in `emulator_data/`

### Important Notes:
- **Local changes get overwritten** - Creating a deck locally gets replaced by production version
- **Smart sync** - Only updates what's actually different
- **Manual control** - YOU decide when to sync (not automatic)
- **Production safety** - Local changes never affect production

## 🌐 Environment Strategy

| Environment | Data Source | Data Content | Cost |
|-------------|-------------|--------------|------|
| Local Dev | Firebase Emulator | Full production copy | FREE |
| GitHub Tests | Firebase Emulator | Test data (~10 cards) | FREE |
| Test/Staging | Real Firestore | Production data | CHEAP |
| Production | Real Firestore | Production data | OPTIMIZED |

## 🛠️ Troubleshooting

### Force fresh sync (complete reset)
```bash
rm -rf emulator_data/
python3 run.py
```

### Skip sync (if hanging)
```bash
SKIP_EMULATOR_SYNC=1 python3 run.py
```

### Port already in use
```bash
# Find and kill the process
lsof -i :5001
kill -9 <PID>

# Or use a different port
PORT=5002 python3 run.py
```

### Emulator not starting
Install Firebase CLI:
```bash
npm install -g firebase-tools
```

## 📊 Data Management

### View emulator data size
```bash
du -sh emulator_data/
```

### Backup emulator data
```bash
cp -r emulator_data/ emulator_data_backup/
```

### Restore from backup
```bash
rm -rf emulator_data/
cp -r emulator_data_backup/ emulator_data/
```

## 🧪 Testing Patterns

### Browse without login
- View all cards
- Search and filter
- View public decks

### Test with existing user
- Login with Google
- Your production account works locally
- All your decks and collection available

### Test with new features
- Create test decks locally
- Modify collection locally
- Changes stay in emulator only