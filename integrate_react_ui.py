#!/usr/bin/env python3
"""
Script to integrate React UI into Flask app
"""

import os
import shutil
import subprocess
import sys

def integrate_react_ui():
    """Integrate the React UI into the Flask application"""
    
    print("🚀 Integrating React Battle Simulator into Flask App")
    print("=" * 60)
    
    # Paths
    frontend_dir = "frontend"
    static_dir = "static"
    templates_dir = "templates"
    
    # Step 1: Build React app
    print("📦 Building React application...")
    try:
        os.chdir(frontend_dir)
        result = subprocess.run(["npm", "run", "build"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Build failed: {result.stderr}")
            return False
        print("✅ React build completed successfully")
        os.chdir("..")
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False
    
    # Step 2: Create directories
    os.makedirs(f"{static_dir}/battle-simulator", exist_ok=True)
    
    # Step 3: Copy built files
    print("📁 Copying built files to Flask static directory...")
    
    # Copy CSS and JS files
    build_assets = f"{frontend_dir}/dist/assets"
    if os.path.exists(build_assets):
        for file in os.listdir(build_assets):
            src = os.path.join(build_assets, file)
            dst = os.path.join(f"{static_dir}/battle-simulator", file)
            shutil.copy2(src, dst)
            print(f"  Copied: {file}")
    
    # Step 4: Create template
    print("📄 Creating Flask template...")
    
    # Read the built index.html
    with open(f"{frontend_dir}/dist/index.html", "r") as f:
        html_content = f.read()
    
    # Modify paths for Flask static serving
    html_content = html_content.replace('/assets/', '/static/battle-simulator/')
    
    # Wrap in Flask template
    flask_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pokemon TCG Pocket - Battle Simulator</title>
    {html_content.split('<head>')[1].split('</head>')[0]}
</head>
<body>
    <div id="root"></div>
    <script>
        // Set up environment for React app
        window.FLASK_BASE_URL = "{{{{ url_for('static', filename='') }}}}";
        window.API_BASE_URL = "";  // Same domain as Flask
    </script>
    {html_content.split('<body>')[1]}
</body>
</html>"""
    
    # Write Flask template
    with open(f"{templates_dir}/battle_simulator.html", "w") as f:
        f.write(flask_template)
    
    print("✅ Template created: templates/battle_simulator.html")
    
    print("\n🎯 Integration Complete!")
    print("=" * 60)
    print("Next steps:")
    print("1. Update your battle.py route to serve the new template")
    print("2. Start your Flask server: python run.py")
    print("3. Visit: http://localhost:5002/battle-simulator")
    print("\n💡 The React UI will now be served directly from Flask!")
    
    return True

if __name__ == "__main__":
    if integrate_react_ui():
        sys.exit(0)
    else:
        sys.exit(1)