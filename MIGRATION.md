Migration: Move C:\Code\wine-analysis into this repository under jetbrains-junie

Overview
- This repository includes a helper PowerShell script to copy your existing code from C:\Code\wine-analysis into a new top-level folder named jetbrains-junie.
- The script excludes typical non-source items such as .git, .venv, node_modules, dist/build artifacts, and common IDE folders.

Steps
1) Close any editors or processes locking files under C:\Code\wine-analysis.
2) Open PowerShell and run (as needed with appropriate permissions):

   powershell -ExecutionPolicy Bypass -File .\scripts\migrate_wine_analysis.ps1

   By default, it will:
   - Source: C:\Code\wine-analysis
   - Destination: <repo-root>\jetbrains-junie

3) If you need to override paths:

   powershell -ExecutionPolicy Bypass -File .\scripts\migrate_wine_analysis.ps1 -SourcePath "C:\\Code\\wine-analysis" -DestinationPath "C:\\Code\\ai-wine-analysis\\jetbrains-junie"

What gets excluded
- .git, .hg, .svn
- .venv, venv, env
- node_modules
- dist, build, out, target
- .idea, .vscode
- __pycache__, *.pyc, .mypy_cache, .pytest_cache
- .DS_Store, Thumbs.db

After migration
- Review the newly copied files under jetbrains-junie.
- If Python packages need to be importable, consider renaming package directories from hyphenated names to underscores (e.g., jetbrains_junie) and adjusting imports. For now, this migration only copies files; it does not rewrite imports.
- Run tests/linters as applicable.
