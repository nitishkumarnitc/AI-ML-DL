#!/bin/bash

# =============================================================================
# PUSH ENHANCED NOTEBOOKS TO GITHUB
# =============================================================================

echo "================================================================================"
echo "🚀 PUSHING ENHANCED DL NOTEBOOKS TO GITHUB"
echo "================================================================================"
echo ""

# Navigate to repository
cd "/Users/nitishkumar/Documents/IITK AI-ML"

echo "📍 Current directory: $(pwd)"
echo ""

# Check Git status
echo "📊 Checking Git status..."
git status
echo ""

# Stage all changes
echo "📦 Staging all changes..."
git add .
echo "✅ Changes staged"
echo ""

# Commit with detailed message
echo "💾 Creating commit..."
git commit -m "🧠 Enhanced 4 DL notebooks with comprehensive educational content

Enhanced Notebooks:
- 3.04: Perceptron-Based Classification (912→1,274 lines, +40%)
- 3.06: Neural Networks & Activation Functions (323→1,207 lines, +273%)  
- 4.04: Forward Propagation (320→1,214 lines, +279%)
- 5.02: TensorFlow Tensors (958→1,295 lines, +35%)

Added Content:
✅ Learning objectives and prerequisites for each notebook
✅ Detailed line-by-line code comments
✅ Mathematical foundations with intuitive explanations
✅ Real-world application examples
✅ Debugging tips and best practices
✅ Challenge exercises for practice
✅ Comprehensive summaries with key takeaways

Quality Improvements:
✅ Visual organization with emojis
✅ Theory + Math + Code integration
✅ Progressive complexity (beginner-friendly)
✅ Industry-standard practices
✅ Total ~1,905 lines of educational content added

Progress: 4/31 notebooks complete (12.9%)"

echo "✅ Commit created"
echo ""

echo "================================================================================"
echo "⚠️  IMPORTANT: AUTHENTICATION REQUIRED"
echo "================================================================================"
echo ""
echo "GitHub no longer accepts passwords. You need a Personal Access Token (PAT)."
echo ""
echo "📋 Follow these steps:"
echo ""
echo "1. Create Personal Access Token:"
echo "   👉 Go to: https://github.com/settings/tokens"
echo "   👉 Click: 'Generate new token' → 'Generate new token (classic)'"
echo "   👉 Name: 'AI-ML-DL Repository Access'"
echo "   👉 Expiration: 90 days (or your preference)"
echo "   👉 Scopes: Check ✅ 'repo' (full control)"
echo "   👉 Click: 'Generate token'"
echo "   👉 COPY THE TOKEN (you won't see it again!)"
echo ""
echo "2. The token looks like: ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
echo ""
echo "3. When prompted for credentials:"
echo "   Username: nitishkumarnitc@gmail.com"
echo "   Password: <PASTE YOUR TOKEN HERE>"
echo ""
echo "================================================================================"
echo ""

# Prompt user to continue
read -p "Press ENTER when you have your token ready, or Ctrl+C to cancel..."

echo ""
echo "🚀 Pushing to GitHub..."
echo ""

# Push to GitHub
git push -u origin main

# Check if push was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "================================================================================"
    echo "✅ SUCCESS! Your enhanced notebooks are now on GitHub!"
    echo "================================================================================"
    echo ""
    echo "🎉 Your hard work is safely backed up and versioned!"
    echo ""
    echo "📊 View your repository at:"
    echo "   https://github.com/nitishkumarnitc/AI-ML-DL"
    echo ""
    echo "📈 Next steps:"
    echo "   - Continue enhancing more notebooks"
    echo "   - Commit and push regularly"
    echo "   - Your token is now saved in macOS Keychain"
    echo ""
else
    echo ""
    echo "================================================================================"
    echo "❌ PUSH FAILED"
    echo "================================================================================"
    echo ""
    echo "Common issues:"
    echo "  1. Branch might be 'master' instead of 'main'"
    echo "     Try: git push -u origin master"
    echo ""
    echo "  2. Token might be incorrect"
    echo "     - Make sure you copied the entire token"
    echo "     - Check that 'repo' scope is enabled"
    echo ""
    echo "  3. Token might be expired"
    echo "     - Generate a new token"
    echo ""
    echo "📖 See GITHUB_SETUP_GUIDE.md for detailed troubleshooting"
    echo ""
fi
