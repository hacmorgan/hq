#!/usr/bin/env bash


# Find large files, write summary files


echo "Finding big files..." >&2
find / -type f -size +100M |
    xargs du |
    tee "big-files.unsorted" | 
    sort --reverse --numeric-sort |
    tee "big-files" 

echo "Finding big folders..." >&2
find / -type d |
    xargs du |
    tee "big-folders.unsorted" | 
    sort --reverse --numeric-sort |
    awk '{if ($1 >= 100000000) print}' |
    tee "big-folders"
