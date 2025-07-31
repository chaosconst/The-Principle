import os
import requests
import sys
import time
import json

# --- Configuration ---
GITHUB_TOKEN = os.getenv("GITHUB_PAT")
REPO_OWNER = "chaosconst"
REPO_NAME = "The-Principle"
API_URL = f"https://api.github.com/graphql"
STATE_FILE = "tools/discussion_state.json"

# --- Headers for Authentication ---
if not GITHUB_TOKEN:
    raise ValueError("GitHub Personal Access Token not found. Please set the GITHUB_PAT environment variable.")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

def get_repository_id_and_category_id(category_name="General"):
    """Fetches the repository ID and a specific discussion category ID."""
    query = """
    query {
      repository(owner: "%s", name: "%s") {
        id
        discussionCategories(first: 10) {
          nodes {
            id
            name
          }
        }
      }
    }
    """ % (REPO_OWNER, REPO_NAME)
    
    response = requests.post(API_URL, headers=headers, json={"query": query})
    response.raise_for_status()
    data = response.json()

    if "data" not in data or "repository" not in data["data"] or not data["data"]["repository"]:
        raise ValueError(f"Could not find repository data. API response: {data}")
    
    repo_data = data["data"]["repository"]
    repo_id = repo_data.get("id")
    if not repo_id:
        raise ValueError(f"Could not find repository ID. API response: {data}")

    categories = repo_data.get("discussionCategories", {}).get("nodes", [])
    if not categories:
        raise ValueError(f"No discussion categories found. API response: {data}")
        
    category_id = next((c["id"] for c in categories if c.get("name") == category_name), None)
    if not category_id:
        raise ValueError(f"Could not find discussion category: {category_name}")
        
    return repo_id, category_id

def load_state():
    """Loads the discussion state from the JSON file."""
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_state(state):
    """Saves the discussion state to the JSON file."""
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def check_new_discussions_and_replies():
    """Checks for new discussions and new replies using a nested query."""
    print("Checking for new discussions and replies...")
    state = load_state()
    
    try:
        # Query for discussions and their nested comments/replies
        query = """
        query {
          repository(owner: "%s", name: "%s") {
            discussions(first: 10, orderBy: {field: CREATED_AT, direction: DESC}) {
              nodes {
                id
                number
                title
                url
                comments(first: 20) {
                  nodes {
                    id
                    author { login }
                    bodyText
                    replyTo { id } # <-- ADD THIS
                    replies(first: 20) {
                      nodes {
                        id
                        author { login }
                        bodyText
                        replyTo { id } # <-- AND THIS
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """ % (REPO_OWNER, REPO_NAME)

        response = requests.post(API_URL, headers=headers, json={"query": query})
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")

        all_discussions = data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
        
        found_new_interaction = False

        for disc in all_discussions:
            disc_num_str = str(disc["number"])
            if disc_num_str not in state:
                state[disc_num_str] = {"global_id": disc.get("id"), "seen_ids": [], "comment_tree": {}}
                print(f"\n--- Found New Discussion ---")
                print(f"[#{disc['number']}] {disc['title']} ({disc['url']})")
                print(f"-> Now tracking discussion #{disc_num_str}.")
                found_new_interaction = True

            # Flatten all comments and replies into a single list
            all_comments_and_replies = []
            top_level_comments = disc.get("comments", {}).get("nodes", [])
            for comment in top_level_comments:
                all_comments_and_replies.append(comment)
                replies = comment.get("replies", {}).get("nodes", [])
                all_comments_and_replies.extend(replies)

            if disc_num_str not in state:
                state[disc_num_str] = {"seen_ids": [], "comment_tree": {}}
            
            # Update comment tree
            for item in all_comments_and_replies:
                item_id = item.get("id")
                if item_id:
                    parent_id = item.get("replyTo", {}).get("id") if item.get("replyTo") else None
                    state[disc_num_str]["comment_tree"][item_id] = {"parent_id": parent_id}

            new_interactions = [
                item for item in all_comments_and_replies 
                if item.get("id") not in state[disc_num_str]["seen_ids"]
            ]

            if new_interactions:
                if not found_new_interaction:
                    print(f"\n--- Found New Interactions ---")
                    found_new_interaction = True
                
                print(f"  In Discussion #{disc_num_str} (ID: {disc.get('id', 'N/A')}):")
                for item in new_interactions:
                    author = item.get("author", {}).get("login", "Unknown")
                    snippet = item.get("bodyText", "").strip().replace('\n', ' ')[:100]
                    item_id = item.get("id", "NO_ID_FOUND")
                    parent_id = item.get("replyTo", {}).get("id") if item.get("replyTo") else "TOP_LEVEL"
                    print(f"    - New content by {author} (id: {item_id}, parent: {parent_id}): \"{snippet}...\"")
                    state[disc_num_str]["seen_ids"].append(item_id)
        
        if not found_new_interaction:
            print("No new discussions or replies found.")

        save_state(state)
        print("\nCheck complete. State updated.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while connecting to the GitHub API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def find_top_level_parent(comment_id, comment_tree):
    """Traverses up the tree to find the top-level comment ID."""
    current_id = comment_id
    while True:
        if current_id not in comment_tree:
            # This might be the top-level comment itself
            return current_id 
        
        parent_id = comment_tree[current_id].get("parent_id")
        if parent_id is None:
            # Found the top-level comment
            return current_id
        
        # Check against potential infinite loops, though unlikely with GitHub's structure
        if parent_id == current_id:
             raise Exception("Comment parent loop detected")

        current_id = parent_id

def post_reply(discussion_id, reply_to_id, body):
    """Adds a reply to a specific discussion comment."""
    try:
        body_escaped = body.replace('"', '\\"').replace('\n', '\\n')
        mutation = """
        mutation {
          addDiscussionComment(input: {discussionId: "%s", replyToId: "%s", body: "%s"}) {
            comment {
              url
            }
          }
        }
        """ % (discussion_id, reply_to_id, body_escaped)

        response = requests.post(API_URL, headers=headers, json={"query": mutation})
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")

        comment_url = data["data"]["addDiscussionComment"]["comment"]["url"]
        print(f"Successfully posted comment! URL: {comment_url}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while connecting to the GitHub API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def delete_comment(comment_id):
    """Deletes a specific discussion comment."""
    try:
        mutation = """
        mutation {
          deleteDiscussionComment(input: {id: "%s"}) {
            clientMutationId
          }
        }
        """ % (comment_id)

        response = requests.post(API_URL, headers=headers, json={"query": mutation})
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")

        print(f"Successfully deleted comment: {comment_id}")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while connecting to the GitHub API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def list_discussions(limit=5):
    """Lists the latest discussions."""
    try:
        query = """
        query {
          repository(owner: "%s", name: "%s") {
            discussions(first: %d, orderBy: {field: CREATED_AT, direction: DESC}) {
              nodes {
                title
                url
                number
              }
            }
          }
        }
        """ % (REPO_OWNER, REPO_NAME, limit)

        response = requests.post(API_URL, headers=headers, json={"query": query})
        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")

        discussions = data.get("data", {}).get("repository", {}).get("discussions", {}).get("nodes", [])
        
        if not discussions:
            print("No discussions found.")
            return

        print(f"--- Latest {len(discussions)} Discussions ---")
        for d in discussions:
            print(f"- [#{d['number']}] {d['title']} ({d['url']})")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while connecting to the GitHub API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def create_discussion(title, body, category_name="General"):
    """
    Creates a new discussion post in the GitHub repository.
    """
    try:
        # GraphQL mutation requires title and body to be JSON-escaped strings
        title_escaped = title.replace('"', '\\"')
        body_escaped = body.replace('"', '\\"').replace('\n', '\\n')

        repo_id, category_id = get_repository_id_and_category_id(category_name)
        
        mutation = """
        mutation {
          createDiscussion(input: {repositoryId: "%s", categoryId: "%s", title: "%s", body: "%s"}) {
            discussion {
              url
            }
          }
        }
        """ % (repo_id, category_id, title_escaped, body_escaped)
        
        response = requests.post(API_URL, headers=headers, json={"query": mutation})
        response.raise_for_status()
        
        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")
            
        discussion_url = data["data"]["createDiscussion"]["discussion"]["url"]
        print(f"Successfully created discussion! URL: {discussion_url}")
            
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while connecting to the GitHub API: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tools/github_agent.py [check|list|post|reply|delete] ...")
        sys.exit(1)
        
    command = sys.argv[1]

    if command == "check":
        check_new_discussions_and_replies()
    elif command == "list":
        list_discussions()
    elif command == "reply":
        if len(sys.argv) < 5:
            print("Usage: python tools/github_agent.py reply <discussion_global_id> <target_comment_id> <path_to_markdown_file>")
            sys.exit(1)
        
        discussion_global_id = sys.argv[2]
        target_comment_id = sys.argv[3]
        file_path = sys.argv[4]

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                body = f.read().strip()
            
            if not body:
                raise ValueError("Reply file is empty.")

            state = load_state()
            
            discussion_number = None
            for disc_num, disc_data in state.items():
                if target_comment_id in disc_data.get("comment_tree", {}):
                    discussion_number = disc_num
                    break
            
            if not discussion_number:
                raise ValueError(f"Could not find a discussion containing comment ID {target_comment_id}. Please run 'check' first to update state.")

            comment_tree = state[discussion_number]["comment_tree"]
            reply_to_id = find_top_level_parent(target_comment_id, comment_tree)
            
            print(f"Replying to comment {reply_to_id} in discussion {discussion_number} ({discussion_global_id})...")
            post_reply(discussion_global_id, reply_to_id, body)
            
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
        except Exception as e:
            print(f"An error occurred: {e}")

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: python tools/github_agent.py delete <comment_id>")
            sys.exit(1)
        
        comment_id_to_delete = sys.argv[2]
        print(f"Attempting to delete comment: {comment_id_to_delete}...")
        delete_comment(comment_id_to_delete)

    elif command == "post":
        if len(sys.argv) < 3:
            print("Usage: python tools/github_agent.py post <path_to_markdown_file>")
            sys.exit(1)
            
        file_path = sys.argv[2]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if not lines:
                raise ValueError("File is empty.")
                
            # First line is title (stripping the leading '# ')
            title = lines[0].strip().lstrip('# ').strip()
            # The rest is body
            body = "".join(lines[1:]).strip()
            
            if not title or not body:
                raise ValueError("File must contain a title (line 1, starting with #) and a body.")

            print(f"Posting to GitHub Discussions from file: {file_path}")
            print(f"Title: {title}")
            print("---")
            create_discussion(title, body)

        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
        except Exception as e:
            print(f"An error occurred: {e}")
    else:
        print(f"Unknown command: {command}")
        print("Usage: python tools/github_agent.py [check|list|post|reply|delete] ...")
        sys.exit(1)