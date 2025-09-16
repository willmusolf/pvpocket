#!/bin/bash
echo "Fixing cache headers on ALL images..."

# Fix all image folders
for folder in genetic-apex mythical-island promo-a space-time-smackdown triumphant-light shining-revelry celestial-guardians extradimensional-crisis eevee-grove wisdom-of-sea-and-sky; do
  echo "Processing folder: $folder"
  gsutil -m setmeta -h "Cache-Control:public, max-age=86400" gs://pvpocket-dd286.firebasestorage.app/high_res_cards/$folder/*
done

echo "Done! All images now cacheable for 24 hours."
