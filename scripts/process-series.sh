#!/usr/bin/env bash
#
# This script hardlinks Series Name Season 02 and Season 03
# from the source directory to the destination directory
# and renames them in the style of:
#   Series Name - SxxEyy - <Episode Title> WEBRip-1080p.mp4
# Also processes subtitles for all seasons.
#
# Usage: ./process-series.sh [--check]

# ----------------------
# 1) Adjust paths below
# ----------------------
SRC_BASE="/media/Downloads/sonarr/Series Name.S01.1080p.WEBRip.x265"
DEST_BASE="/media/TV/Series Name"

# Check if we're in check mode
CHECK_MODE=false
if [[ "$1" == "--check" ]]; then
    CHECK_MODE=true
    echo "Running in check mode - no changes will be made"
    echo "-----------------------------------------"
fi

# -------------------------------------
# 2) Define episode titles for each season
# -------------------------------------

# Season 01 (10 episodes)
season1_titles=(
"Episode Names"
"Fire"
"The Old Lie"
)

# Season 02 (9 episodes)
season2_titles=(
"Episode Names"
)

# Season 03 (10 episodes)
season3_titles=(
"Episode Names"
)

# -------------------------------------
# 3) Functions to handle linking
# -------------------------------------

# Function to link subtitles only
link_subtitles() {
    local season="$1"
    local -n titles="$2"
    local src_dir="${SRC_BASE}/.S${season}.1080p.WEBRip.x265-RARBG"
    local dest_dir="${DEST_BASE}/Season ${season}"

    if [[ ! -d "${src_dir}/Subs" ]]; then
        echo "Warning: No Subs directory found for Season ${season}"
        return
    fi

    for ep_dir in "${src_dir}/Subs/"*; do
        [[ -d "$ep_dir" ]] || continue

        ep_num=$(echo "$ep_dir" | sed -E "s/.*S${season}E0*([0-9]+).*/\1/")
        idx=$((ep_num - 1))

        if [[ $idx -ge ${#titles[@]} ]]; then
            echo "Error: No title found for subtitle S${season}E${ep_num}"
            continue
        fi

        ep_title="${titles[$idx]}"
        
        if [[ -f "${ep_dir}/2_English.srt" ]]; then
            dest_srt="Series Name - S${season}E$(printf "%02d" ${ep_num}) - ${ep_title} WEBRip-1080p.srt"
            
            if [[ -e "${dest_dir}/${dest_srt}" ]]; then
                echo "Warning: Destination subtitle already exists, skipping: ${dest_srt}"
                continue
            fi

            if [[ "$CHECK_MODE" == true ]]; then
                echo "[CHECK] Would create hardlink: ${ep_dir}/2_English.srt -> ${dest_dir}/${dest_srt}"
            else
                echo "Linking subtitle for S${season}E$(printf "%02d" ${ep_num})"
                ln "${ep_dir}/2_English.srt" "${dest_dir}/${dest_srt}" || \
                    echo "Error: Failed to create hardlink for ${dest_srt}"
            fi
        else
            echo "Warning: No English subtitle found for S${season}E$(printf "%02d" ${ep_num})"
        fi
    done
}

# Function to link video files and subtitles
link_and_rename_season() {
    local season="$1"
    local -n titles="$2"
    local src_dir="${SRC_BASE}/Series.Name.S${season}.1080p.WEBRip.x265-RARBG"
    local dest_dir="${DEST_BASE}/Season ${season}"

    if [[ ! -d "${src_dir}" ]]; then
        echo "Error: Source directory not found: ${src_dir}"
        return 1
    fi

    if [[ "$CHECK_MODE" == false ]]; then
        mkdir -p "${dest_dir}"
    fi

    echo "Processing Season ${season} from: ${src_dir}"
    echo "Linking to: ${dest_dir}"
    echo

    # Process video files
    local mp4_count=$(ls "${src_dir}"/*.mp4 2>/dev/null | wc -l)
    if [[ ${#titles[@]} -ne $mp4_count ]]; then
        echo "Warning: Number of episode titles (${#titles[@]}) doesn't match number of MP4 files ($mp4_count)"
    fi

    for file in "${src_dir}"/*.mp4; do
        [[ -e "$file" ]] || continue

        ep_num=$(echo "$file" | sed -E "s/.*S${season}E0*([0-9]+).*/\1/")
        idx=$((ep_num - 1))

        if [[ $idx -ge ${#titles[@]} ]]; then
            echo "Error: No title found for S${season}E${ep_num}"
            continue
        fi

        ep_title="${titles[$idx]}"
        dest_file="Series Name - S${season}E$(printf "%02d" ${ep_num}) - ${ep_title} WEBRip-1080p.mp4"

        if [[ -e "${dest_dir}/${dest_file}" ]]; then
            echo "Warning: Destination file already exists, skipping: ${dest_file}"
            continue
        fi

        if [[ "$CHECK_MODE" == true ]]; then
            echo "[CHECK] Would create hardlink: $file -> ${dest_dir}/${dest_file}"
        else
            echo "Hardlinking episode S${season}E$(printf "%02d" ${ep_num}) -> ${dest_file}"
            ln "$file" "${dest_dir}/${dest_file}" || echo "Error: Failed to create hardlink for ${dest_file}"
        fi
    done

    # Process subtitles
    link_subtitles "$season" "$2"

    echo
    echo "Season ${season} complete."
    echo "-----------------------------------------"
    echo
}

# ------------------------------
# 4) Process all seasons
# ------------------------------
# Only process subtitles for Season 1
echo "Processing subtitles for Season 01..."
link_subtitles "01" season1_titles

# Process both videos and subtitles for Seasons 2 and 3
link_and_rename_season "02" season2_titles
link_and_rename_season "03" season3_titles

if [[ "$CHECK_MODE" == true ]]; then
    echo "Check mode complete - no changes were made"
else
    echo "All done!"
fi
