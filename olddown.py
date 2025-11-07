#!/bin/bash

# --- Configuration ---
DOWNLOADS_DIR="$HOME/Downloads"
AGE_IN_DAYS=30 
DRY_RUN=true    

RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color


echo -e "${BLUE}--- Cleaning up old downloads in '$DOWNLOADS_DIR' ---${NC}"
echo -e "${YELLOW}Files older than $AGE_IN_DAYS days will be processed.${NC}"

if [ ! -d "$DOWNLOADS_DIR" ]; then
    echo -e "${RED}Error: Downloads directory '$DOWNLOADS_DIR' not found.${NC}"
    exit 1
fi

if $DRY_RUN; then
    echo -e "${YELLOW}*** DRY RUN MODE: No files will be deleted. Showing what would be deleted. ***${NC}"
else
    read -p "$(echo -e "${RED}*** WARNING: This will DELETE files! Are you sure? (y/N): ${NC}")" confirm_delete
    if ! [[ "$confirm_delete" =~ ^[yY]$ ]]; then
        echo -e "${YELLOW}Deletion aborted.${NC}"
        exit 0
    fi
    echo -e "${GREEN}DELETION MODE: Files will be permanently removed.${NC}"
fi


if $DRY_RUN; then
    echo -e "${BLUE}Files that WOULD be deleted:${NC}"
    find "$DOWNLOADS_DIR" -maxdepth 1 -type f -mtime +"$AGE_IN_DAYS" -ls
else
    echo -e "${BLUE}Deleting files:${NC}"
    find "$DOWNLOADS_DIR" -maxdepth 1 -type f -mtime +"$AGE_IN_DAYS" -delete -print
    echo -e "${GREEN}Cleanup complete.${NC}"
fi

echo -e "${BLUE}--- End of Cleanup ---${NC}"
