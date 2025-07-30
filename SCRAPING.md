# SCRAPING.md

This file documents the automated data pipeline for Pokemon TCG Pocket card data, including scraping, processing, and automatic set ordering.

## 🎯 Overview

The app automatically keeps card data up-to-date through a fully automated pipeline that:
1. **Monitors** external sources for new cards/sets
2. **Scrapes** card data from Limitless TCG
3. **Downloads** high-resolution images from Google Drive
4. **Processes** data with automatic shiny detection and set ordering
5. **Updates** Firestore with new cards while preserving existing data

## 🏗️ Architecture

### Data Sources
- **Primary Data**: [Limitless TCG Pocket](https://limitlesstcg.com/tools/pocket) - Card stats, rarities, set info
- **High-Res Images**: Google Drive - Official card images with better quality
- **Monitoring**: Cloud Function tracks source changes to trigger updates

### Key Components

```
main.py (Cloud Function)      → Monitors external sources, triggers scraping
scraping/scraper.py          → Web scraping from Limitless TCG  
scraping/download_icons.py   → Downloads images from Google Drive
scraping/post_processor.py   → Data cleaning and shiny detection
scripts/assign_release_order.py → Automatic set ordering system
checker/main.py              → Cloud Run job for change detection
```

## 🔄 Automated Workflow

### 1. Change Detection
- **Checker Job** (`checker/main.py`) runs periodically on Cloud Run
- Monitors Limitless TCG for new cards or set releases
- Triggers main scraping pipeline when changes detected

### 2. Data Scraping (`scraping/scraper.py`)
- Scrapes all card data from Limitless TCG
- Extracts: name, HP, attacks, energy types, rarities, set codes
- Handles pagination and rate limiting
- Saves raw data to staging area

### 3. Image Processing (`scraping/download_icons.py`)
- Downloads high-resolution card images from Google Drive
- Uploads to Firebase Storage with CDN optimization
- Generates optimized URLs for fast loading
- Handles missing images gracefully

### 4. Data Processing (`scraping/post_processor.py`)

#### Automatic Shiny Detection
```python
# Shinies appear between ☆☆☆ and ♛ cards in the data
# Algorithm automatically identifies and converts them:
if is_between_three_star_and_crown(card_position):
    if not card.name.endswith(' ☆'):
        card.name += ' ☆'  # Add shiny indicator
        card.rarity = '☆☆☆☆'  # Upgrade rarity
```

#### Set Normalization
- Cleans set names (removes code suffixes)
- Standardizes rarity symbols
- Validates card numbers and types

### 5. Automatic Set Ordering (`scripts/assign_release_order.py`)

**The Key Innovation**: Sets get automatic priority numbers based on release chronology.

```python
# Automatic release order assignment
SET_RELEASE_ORDER = {
    "Genetic Apex": 1,          # A1 - First set
    "Mythical Island": 2,       # A1a - Mini expansion  
    "Space-Time Smackdown": 3,  # P-A - Promo set
    "Celestial Guardians": 4,   # A2 - Second major set
    # ... continues automatically for new sets
}

# When new set detected:
new_release_order = max(existing_orders) + 1
new_set.release_order = new_release_order
```

**Benefits**:
- ✅ **No Manual Updates**: New sets automatically get next order number
- ✅ **Correct Sorting**: DESC shows newest sets first, ASC shows oldest first  
- ✅ **Future-Proof**: Works for A3, A4, A5... without code changes

### 6. Database Updates
- **Incremental Updates**: Only adds new cards, preserves existing data
- **Conflict Resolution**: Handles duplicate detection intelligently
- **Rollback Safety**: Can revert if issues detected

## 🎮 Set Sorting Logic

### Current Behavior (Fixed)
```
DESC (⬇️ Down Arrow):  Newest sets first → A4, A3, A2, A1
ASC  (⬆️ Up Arrow):    Oldest sets first → A1, A2, A3, A4
```

### Implementation
```python
# In app/routes/decks.py set sorting:
if direction == "desc":
    set_priority = card.set_release_order    # Higher numbers = newer = shows first
else:  
    set_priority = -card.set_release_order   # Lower numbers = older = shows first
```

### Special Cases
- **Promo-A**: Always appears last regardless of sort direction
- **Missing release_order**: Falls back to hardcoded `SET_RELEASE_ORDER` lookup

## 🚀 Deployment & Automation

### Cloud Functions
```yaml
# main.py deployment
runtime: python39
entry_point: main
trigger: HTTP
environment_variables:
  GCP_PROJECT_ID: ${PROJECT_ID}
```

### Cloud Run Jobs  
```yaml
# checker/main.py deployment  
apiVersion: run.googleapis.com/v1
kind: Job
spec:
  template:
    spec:
      containers:
      - image: gcr.io/PROJECT/checker
        env:
        - name: TASK_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              name: task-auth-token
```

### Automated Triggers
- **Cron Schedule**: Checker runs every 6 hours
- **Manual Trigger**: Can force refresh via `/api/refresh-cards` endpoint
- **CI/CD Integration**: Auto-deploys on code changes

## 🔧 Manual Operations

### Force Data Refresh
```bash
# Trigger manual scraping update
curl -X POST "https://your-app.com/api/refresh-cards" \
  -H "X-Refresh-Key: YOUR_SECRET_KEY"
```

### Add New Set Manually
```python
# In scripts/assign_release_order.py
SET_RELEASE_ORDER["New Set Name"] = 11  # Next number in sequence
```

### Debug Scraping Issues
```bash
# Check scraping logs
gcloud functions logs read scraping-function --limit 50

# Test locally
cd scraping/
python scraper.py --test-mode
```

## 📊 Data Flow Diagram

```
External Sources → Change Detection → Scraping → Processing → Database
      ↓                   ↓             ↓           ↓          ↓
Limitless TCG    →    checker/     →  scraper  → processor → Firestore
Google Drive     →    main.py      →  *.py     → *.py      → + Storage
                                     ↓
                              Image Download
                                     ↓  
                              Firebase Storage
```

## 🛡️ Error Handling & Monitoring

### Automatic Recovery
- **Retry Logic**: Failed operations retry with exponential backoff
- **Partial Updates**: Can complete even if some cards fail to process
- **Data Validation**: Rejects malformed data to prevent corruption

### Monitoring & Alerts
- **Performance Tracking**: Scraping duration and success rates
- **Error Notifications**: Alerts sent to monitoring channels on failures
- **Cost Monitoring**: Firebase usage tracking with budget alerts

### Troubleshooting Common Issues

#### No New Cards Appearing
1. Check checker logs: `gcloud run jobs executions logs EXECUTION_ID`
2. Verify triggers: Look for recent scraping function invocations
3. Test manually: Hit `/api/refresh-cards` endpoint

#### Wrong Set Order
1. Verify `release_order` field: Check Firestore documents
2. Check assignment script: Review `assign_release_order.py` 
3. Test sorting logic: Use `/api/cards?sort=set&direction=desc`

#### Missing Images
1. Check Firebase Storage: Verify uploads completed
2. Review download logs: Look for Google Drive API errors
3. Check CDN: Ensure image URLs are accessible

## 🔮 Future Enhancements

### Planned Improvements
- **Real-time Updates**: WebSocket notifications for instant card additions
- **Advanced Filtering**: ML-powered card categorization  
- **Multi-source Scraping**: Additional data sources for redundancy
- **Performance Optimization**: Incremental updates and smart caching

### Maintenance Notes
- **Release Order**: Add new sets to `SET_RELEASE_ORDER` as they're announced
- **Shiny Detection**: May need updates if Limitless changes their format
- **Rate Limiting**: Monitor and adjust scraping frequency as needed

---

## 📝 Developer Notes

### Key Files to Understand
1. **`scraping/scraper.py`** - Core scraping logic
2. **`scripts/assign_release_order.py`** - Set ordering system  
3. **`scraping/post_processor.py`** - Data cleaning and shiny detection
4. **`app/routes/decks.py`** - Set sorting implementation (lines 757-798)

### Testing the Pipeline
```bash
# Test full pipeline locally
python scripts/test_scraping_pipeline.py

# Test just set ordering  
python scripts/assign_release_order.py --dry-run

# Test sorting logic
curl "localhost:5001/api/cards?sort=set&direction=desc&limit=5"
```

This automated system ensures the app stays current with new Pokemon TCG Pocket releases without manual intervention.