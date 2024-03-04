#!/bin/bash

# Remove `.git/` from `admin` to prevent conflict
rm -rf admin/.git

# Iterate over each subfolder in the tmp directory
for folder in admin/src/*; do
  if [ -d "$folder" ]; then
    # Extract the application version name (e.g., 'appli17') from the folder path
    version=${folder##*/}

    echo "Updating $version..."

    # Checkout to a temporary branch for the update
    git checkout -b temp-update-branch

    # Clean branch
    find . -mindepth 1 -maxdepth 1 ! -name "admin" ! -name ".git" ! -name ".github" -exec rm -rf {} \;

    # Copy new files from the corresponding tmp/version subfolder
    cp -r $folder/* .

    # Add, commit, tag
    git add -- . ':!admin'
    git commit -m "Update $version"
    git tag -f $version  

    # Delete the temporary branch
    git checkout main
    git branch -D temp-update-branch

    git push origin $version -f
  fi
done
