#!/bin/bash

# Iterate over each subfolder in the tmp directory
for folder in .gen/*; do
  if [ -d "$folder" ]; then
    # Extract the application version name (e.g., 'appli17') from the folder path
    version=${folder##*/}

    echo "Updating $version..."

    # Checkout to a temporary branch for the update
    git checkout -b temp-update-branch

    find . -mindepth 1 -maxdepth 1 ! -name ".gen" ! -name ".git" -exec rm -rf {} \;

    # Copy new files from the corresponding tmp/version subfolder
    cp -r $folder/* .
    rm -rf .gen/

    # Add changes to git
    git add .

    # Commit the changes
    git commit -m "Update $version"

    # Move the tag to the new commit
    git tag -f $version

    # Delete the temporary branch
    git checkout main
    git branch -D temp-update-branch
  fi
done

# Push new tags
git push --tags -f
