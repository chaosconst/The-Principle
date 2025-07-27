import json
import argparse
from datetime import datetime

def is_sortable_message(obj):
    """Checks if an object is a dictionary and has a timestamp."""
    return isinstance(obj, dict) and 'updatedAt' in obj

def convert_json_to_md(input_file, output_file):
    """
    Converts a JSON file from OpenRouter into a formatted Markdown file.
    This version finds ALL message blocks by inspecting content structure,
    merges them, and then sorts the combined list.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found at '{input_file}'")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from '{input_file}'. Please check the file format.")
        return

    if not isinstance(data, dict):
        print("Error: JSON data must be a dictionary.")
        return

    # --- v1.6: Find and merge ALL message blocks ---
    all_messages = []
    other_metadata = []

    for key, value in data.items():
        # Check if the value is a dictionary containing message-like objects
        if isinstance(value, dict) and value:
            first_item = next(iter(value.values()), None)
            if is_sortable_message(first_item):
                print(f"Found message block in '{key}'. Adding {len(value)} messages to the pool.")
                all_messages.extend(value.values())
                continue # Go to the next top-level item

        # If it's not a message block, it's metadata
        other_metadata.append({'id': key, 'data': value})
    
    if not all_messages:
        print("\nError: Could not find any blocks containing valid messages.")
    # ---------------------------------------------------

    # Filter the combined list one last time for safety
    valid_messages = [msg for msg in all_messages if is_sortable_message(msg)]
    
    if len(all_messages) > 0 and not valid_messages:
        print("\nWarning: Message blocks were found, but none of the entries had a valid timestamp.")

    # --- v1.8: Reverse the list to get chronological order ---
    # The source file seems to be in reverse chronological order.
    valid_messages.reverse()
    # ---------------------------------------------------------

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Conversation Log\n\n")
        f.write(f"Converted from: `{input_file}` on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        for msg in valid_messages:
            content = msg.get('content', '*No content*')
            timestamp = msg.get('updatedAt', 'No timestamp')
            
            # Forgiving speaker detection
            character_id = msg.get('characterId')
            if character_id and character_id != 'USER':
                speaker = "🤖 **ASSISTANT**"
            else:
                speaker = "👤 **USER**"

            f.write(f"**{speaker}**\n")
            f.write(f"*Timestamp: {timestamp}*\n\n")
            f.write("```text\n")
            f.write(content.strip() if content else "")
            f.write("\n```\n\n")
            f.write("---\n\n")

        if other_metadata:
            f.write("## Metadata & Skipped Entries\n\n")
            f.write("The following top-level entries were treated as metadata:\n\n")
            f.write("```json\n")
            f.write(json.dumps(other_metadata, indent=2, default=str))
            f.write("\n```\n")
            print(f"\nInfo: {len(other_metadata)} metadata entries were logged. See details at the end of '{output_file}'.")

    print(f"Successfully processed {len(valid_messages)} messages and created '{output_file}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert a conversation log from JSON format to Markdown.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("input_file", help="Path to the input JSON file.")
    parser.add_argument("output_file", help="Path for the output Markdown file.")
    parser.add_argument("-v", "--version", action="version", version="%(prog)s 1.8 (Reverse Order)")

    args = parser.parse_args()
    convert_json_to_md(args.input_file, args.output_file) 