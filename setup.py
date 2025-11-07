#!/bin/bash


DEFAULT_TEMPLATES_DIR="$HOME/ProjectTemplates"


create_project() {
    if [ -z "$1" ]; then
        echo "Usage: create_project <project_name>"
        echo "Optional: create_project <project_name> <template_name>"
        echo "Available templates (from $DEFAULT_TEMPLATES_DIR):"
        find "$DEFAULT_TEMPLATES_DIR" -maxdepth 1 -mindepth 1 -type d -printf "  %f\n" 2>/dev/null || echo "  No templates found."
        return 1
    fi

    local project_name="$1"
    local template_name="$2"
    local project_dir="./$project_name"

    if [ -d "$project_dir" ]; then
        echo "Error: Directory '$project_dir' already exists. Aborting."
        return 1
    fi

    echo "Creating project directory: $project_dir"
    mkdir "$project_dir" || { echo "Failed to create directory."; return 1; }
    cd "$project_dir" || { echo "Failed to enter directory."; return 1; }

    echo "Initializing Git repository..."
    git init -b main > /dev/null 2>&1

    echo "Creating initial README.md..."
    echo "# $project_name" > README.md
    echo "" >> README.md
    echo "This is a new project called **$project_name**." >> README.md

    # If a template is specified, copy its contents
    if [ -n "$template_name" ]; then
        local template_path="$DEFAULT_TEMPLATES_DIR/$template_name"
        if [ -d "$template_path" ]; then
            echo "Copying contents from template '$template_name'..."
            cp -r "$template_path"/. . || { echo "Failed to copy template contents."; return 1; }
        else
            echo "Warning: Template '$template_name' not found at '$template_path'. Skipping template copy."
        fi
    fi

    echo "Project '$project_name' created successfully!"
    echo "You are now in the project directory."
    ls -a
}


mkdir -p "$DEFAULT_TEMPLATES_DIR"


