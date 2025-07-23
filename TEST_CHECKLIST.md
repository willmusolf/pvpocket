# 🧪 Complete Test Checklist for PvPocket App

Run through these tests to make sure everything is working properly!

## 1. Basic Health Checks ✅

### Production Site
```bash
# Test if site is up
curl https://pvpocket.xyz/health

# Check performance metrics
curl https://pvpocket.xyz/internal/metrics
```

### Test Environment
```bash
# Test if test site is up
curl https://test-env-dot-pvpocket-dd286.uc.r.appspot.com/health
```

## 2. User Flow Tests 🧑‍💻

### On https://pvpocket.xyz:
1. [ ] Homepage loads
2. [ ] Click "Login with Google" → Should redirect to Google
3. [ ] Complete login → Should return to site
4. [ ] Set username if prompted
5. [ ] Navigate to "My Collection" → Should load card collection
6. [ ] Navigate to "Decks" → Should show deck builder
7. [ ] Try creating a deck
8. [ ] Check "Friends" section
9. [ ] Logout works

## 3. Performance Tests ⚡

### Check these metrics at https://pvpocket.xyz/internal/metrics:
- [ ] Cache hit rate > 80% (good performance)
- [ ] No active alerts
- [ ] Page loads fast (< 2 seconds)

## 4. Security Tests 🔒

### Verify secrets are NOT visible:
```bash
# This should NOT show any passwords/secrets
curl https://pvpocket.xyz/env 2>/dev/null | grep -i secret
# (Should return nothing or error)
```

## 5. Local Development Test 💻

```bash
# In your project directory
python run.py

# Then visit http://localhost:5001
# Should work exactly like production
```

## 6. Deployment Test 🚀

### Test the deployment process:
```bash
# Make a small change (like updating README)
echo "Test deployment $(date)" >> README.md
git add README.md
git commit -m "Test: deployment pipeline"
git push origin main

# Then check GitHub Actions tab - should see workflow running
# After ~5 minutes, change should be live on pvpocket.xyz
```

## 7. Monitoring & Logs 📊

### Check Google Cloud Console:
1. Go to: https://console.cloud.google.com/appengine?project=pvpocket-dd286
2. Check "Versions" - should see recent deployments
3. Check "Logs" - should see request logs

### View live logs:
```bash
gcloud app logs tail -s default
```

## 8. Database & Backup Test 💾

### Check Firestore is working:
1. Login to the app
2. Create/modify a deck
3. Logout and login again
4. Deck should still be there

### Verify backups are configured:
```bash
# List available backups
gsutil ls gs://pvpocket-dd286-backups/
```

## 🎉 If All Tests Pass...

Your app is fully operational with:
- ✅ Secure secret management
- ✅ Automated CI/CD pipeline
- ✅ Performance monitoring
- ✅ Automated backups
- ✅ Multi-environment setup
- ✅ Health monitoring

## 🚨 Troubleshooting

### If OAuth login fails:
- Clear browser cookies
- Check OAuth settings in Google Cloud Console
- Wait 5-10 minutes (OAuth changes take time)

### If deployment fails:
- Check GitHub Actions logs
- Verify secrets in Secret Manager
- Check `gcloud app logs tail`

### If site is slow:
- Check cache hit rate in /internal/metrics
- Look for errors in logs
- Verify database connections are working

## 📞 Getting Help

If something isn't working:
1. Check the logs: `gcloud app logs tail`
2. Check GitHub Actions for deployment errors
3. Review DEPLOYMENT_GUIDE.md for detailed instructions
4. Check Google Cloud Console for service status