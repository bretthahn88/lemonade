#!/bin/bash

# Cleanup old GCP projects

# Check if gcloud is installed and set GCLOUD variable
if command -v gcloud &> /dev/null; then
    GCLOUD="gcloud"
elif [ -f "$HOME/google-cloud-sdk/bin/gcloud" ]; then
    GCLOUD="$HOME/google-cloud-sdk/bin/gcloud"
else
    echo "Error: gcloud CLI is not installed"
    exit 1
fi

echo "=========================================="
echo "GCP Project Cleanup"
echo "=========================================="
echo ""
echo "Your current projects:"
echo ""

$GCLOUD projects list --format="table(projectId,name,createTime)" --sort-by=createTime

echo ""
echo "=========================================="
echo ""
echo "Let's delete the old test projects to free up your billing quota."
echo ""

# List projects with lemonade in the name
LEMONADE_PROJECTS=$($GCLOUD projects list --format="value(projectId)" --filter="projectId:lemonade*" | sort)

if [ -z "$LEMONADE_PROJECTS" ]; then
    echo "No lemonade projects found."
    exit 0
fi

echo "Found these lemonade-related projects:"
echo "$LEMONADE_PROJECTS"
echo ""

# Show which one is currently active
CURRENT_PROJECT=$($GCLOUD config get-value project 2>/dev/null)
echo "Current active project: $CURRENT_PROJECT"
echo ""

echo "Which projects would you like to DELETE?"
echo "(Keep the newest one: $CURRENT_PROJECT)"
echo ""

for project in $LEMONADE_PROJECTS; do
    if [ "$project" != "$CURRENT_PROJECT" ]; then
        read -p "Delete $project? [y/N]: " confirm
        if [[ "$confirm" =~ ^[Yy]$ ]]; then
            echo "Deleting $project..."
            $GCLOUD projects delete $project --quiet
            echo "✓ Deleted $project"
        else
            echo "Skipped $project"
        fi
    else
        echo "Keeping current project: $project ✓"
    fi
    echo ""
done

echo "=========================================="
echo "Cleanup complete!"
echo "=========================================="
echo ""
echo "Wait 30 seconds for quota to refresh, then try:"
echo "  ./setup-gcp-auto.sh"
echo ""
