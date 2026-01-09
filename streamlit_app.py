import streamlit as st
import sqlite3
import os
import subprocess
import json
import pandas as pd
import time
from pathlib import Path

# Try to import requests for health checks
try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Page configuration
st.set_page_config(page_title="Token Tracking Database Manager", layout="wide")


# Database configuration
def get_database_path():
    """Get the database path from environment or default location"""
    if os.getenv("DATABASE_URL"):
        db_url = os.getenv("DATABASE_URL")
        if db_url.startswith("sqlite:///"):
            path = db_url[10:]  # len("sqlite:///") = 10
            if not path.startswith("/"):
                path = "/" + path
            return path
        elif db_url.startswith("sqlite+sqlcipher:///"):
            path = db_url[20:]  # len("sqlite+sqlcipher:///") = 20
            if not path.startswith("/"):
                path = "/" + path
            return path

    # Try Docker path first
    docker_paths = [
        "/app/backend/data/webui.db",
        "/app/data/webui.db",
    ]
    for path in docker_paths:
        if os.path.exists(path):
            return path

    # Fallback to local path
    backend_dir = Path(__file__).parent / "backend"
    local_path = backend_dir / "data" / "webui.db"
    if local_path.exists():
        return str(local_path)

    # Return default Docker path (will be created if needed)
    return "/app/backend/data/webui.db"


def check_open_webui_health():
    """Check if Open WebUI is running and healthy"""
    if not HAS_REQUESTS:
        # Fallback to checking if port is open using subprocess
        try:
            result = subprocess.run(
                ["curl", "-sf", "http://localhost:8080/health"],
                capture_output=True,
                timeout=2,
            )
            return result.returncode == 0
        except:
            return False
    try:
        response = requests.get("http://localhost:8080/health", timeout=2)
        return response.status_code == 200
    except:
        return False


def get_db_connection():
    """Create a connection to the database"""
    db_path = get_database_path()

    # Debug info
    db_dir = os.path.dirname(db_path)
    db_dir_exists = os.path.exists(db_dir) if db_dir else False

    # Ensure the directory exists
    if db_dir and not db_dir_exists:
        try:
            os.makedirs(db_dir, exist_ok=True)
            db_dir_exists = True
        except Exception as e:
            st.error(f"Could not create database directory {db_dir}: {e}")
            st.info(f"Current working directory: {os.getcwd()}")
            st.info(f"Database path: {db_path}")
            st.info(f"Directory exists: {db_dir_exists}")
            return None

    # Check if Open WebUI is running
    webui_healthy = check_open_webui_health()

    # Initialize session state for retry tracking
    if "db_retry_count" not in st.session_state:
        st.session_state.db_retry_count = 0
    if "db_last_check" not in st.session_state:
        st.session_state.db_last_check = 0

    max_retries = 15  # Increased retries
    retry_delay = 2  # 2 seconds delay

    # Check if database file exists
    db_exists = os.path.exists(db_path)

    if not db_exists:
        current_time = time.time()
        # Only wait if enough time has passed since last check (to avoid blocking)
        if current_time - st.session_state.db_last_check >= retry_delay:
            st.session_state.db_last_check = current_time
            if st.session_state.db_retry_count < max_retries:
                st.session_state.db_retry_count += 1
                with st.spinner(
                    f"Waiting for database... (attempt {st.session_state.db_retry_count}/{max_retries})"
                ):
                    time.sleep(retry_delay)
                st.rerun()
            else:
                st.error(f"Database not found at: {db_path}")
                st.info(f"Directory exists: {db_dir_exists}")
                st.info(f"Directory path: {db_dir}")
                st.info(
                    f"Open WebUI health check: {'✓ Healthy' if webui_healthy else '✗ Not responding'}"
                )
                st.info("Open WebUI may still be starting up. Please wait and refresh.")
                if st.button("Retry Connection", key="retry_db"):
                    st.session_state.db_retry_count = 0
                    st.session_state.db_last_check = 0
                    st.rerun()
                return None

    # Reset retry count on success
    st.session_state.db_retry_count = 0

    # Database file exists, try to connect
    try:
        conn = sqlite3.connect(db_path)

        # Check if database is initialized (has tables)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1")
        tables_exist = cursor.fetchone() is not None

        if not tables_exist:
            # Database file exists but no tables - Open WebUI might still be initializing
            conn.close()
            st.warning(
                f"Database file exists at {db_path} but appears to be empty (no tables found)."
            )
            st.info(
                "Open WebUI is still initializing the database schema. Please wait a few moments."
            )
            st.info(
                f"Open WebUI health check: {'✓ Healthy' if webui_healthy else '✗ Not responding'}"
            )
            if st.button("Check Again", key="check_again"):
                st.rerun()
            return None

        return conn
    except sqlite3.Error as e:
        st.error(f"SQLite error connecting to database: {e}")
        st.info(f"Database path: {db_path}")
        return None
    except Exception as e:
        st.error(f"Unexpected error connecting to database: {e}")
        st.info(f"Database path: {db_path}")
        return None


def get_all_tables(conn):
    """Get list of all tables in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]


def get_table_data(conn, table_name, limit=100, where_clause=""):
    """Get data from a table"""
    try:
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        return df
    except Exception as e:
        st.error(f"Error reading table {table_name}: {e}")
        return None


def execute_query(conn, query, params=None):
    """Execute a query and return results"""
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return cursor.rowcount
    except Exception as e:
        st.error(f"Error executing query: {e}")
        conn.rollback()
        return None


def get_credit_groups(conn):
    """Get all credit groups as a list of tuples (id, display_name)"""
    try:
        df = get_table_data(conn, "token_tracking_credit_group", limit=1000)
        if df is not None and not df.empty:
            result = []
            for _, row in df.iterrows():
                group_id = row["id"]
                group_name = row.get("name", "Unknown")
                max_credit = row.get("max_credit", "")
                display_name = (
                    f"{group_name} (Limit: {max_credit})" if max_credit else group_name
                )
                result.append((group_id, display_name))
            return result
        return []
    except Exception as e:
        st.warning(f"Could not load credit groups: {e}")
        return []


def get_users(conn):
    """Get all users as a list of tuples (id, email/name)"""
    try:
        df = get_table_data(conn, "user", limit=1000)
        if df is not None and not df.empty:
            result = []
            for _, row in df.iterrows():
                user_id = row["id"]
                email = row.get("email", "")
                name = row.get("name", "")
                display_name = (
                    f"{name} ({email})"
                    if name and email
                    else (email if email else name if name else user_id)
                )
                result.append((user_id, display_name))
            return result
        return []
    except Exception as e:
        st.warning(f"Could not load users: {e}")
        return []


def get_user_group_assignments(conn):
    """Get all user-group assignments with user and group names"""
    try:
        # Get assignments
        assignments_df = get_table_data(
            conn, "token_tracking_credit_group_user", limit=1000
        )
        if assignments_df is None or assignments_df.empty:
            return pd.DataFrame()

        # Get users
        users_df = get_table_data(conn, "user", limit=1000)
        # Get groups
        groups_df = get_table_data(conn, "token_tracking_credit_group", limit=1000)

        if users_df is not None and groups_df is not None:
            # Merge with users (user_id in assignments matches id in users)
            result = assignments_df.merge(
                users_df[["id", "email", "name"]].rename(columns={"id": "user_id"}),
                on="user_id",
                how="left",
            )
            # Merge with groups (credit_group_id in assignments matches id in groups)
            result = result.merge(
                groups_df[["id", "name"]].rename(
                    columns={"id": "credit_group_id", "name": "group_name"}
                ),
                on="credit_group_id",
                how="left",
            )
            return result

        return assignments_df
    except Exception as e:
        st.warning(f"Could not load user-group assignments: {e}")
        return pd.DataFrame()


def run_token_tracking_command(command):
    """Run a token tracking CLI command"""
    try:
        db_path = get_database_path()
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path}"

        backend_dirs = [
            Path("/app/backend"),
            Path(__file__).parent / "backend",
        ]
        for backend_dir in backend_dirs:
            if backend_dir.exists():
                os.chdir(str(backend_dir))
                break

        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, env=env, timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1


def check_password():
    """Returns True if the user had the correct password."""

    # Get password from environment variable
    correct_password = os.getenv("STREAMLIT_PASSWORD", "admin123")

    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # If already authenticated, return True
    if st.session_state.authenticated:
        return True

    # Show login form
    st.markdown("## 🔐 Authentication Required")
    st.markdown(
        "Please enter the password to access the Token Tracking Database Manager"
    )

    with st.form("login_form"):
        password = st.text_input(
            "Password", type="password", placeholder="Enter password"
        )
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if password == correct_password:
                st.session_state.authenticated = True
                st.success("Authentication successful!")
                st.rerun()
            else:
                st.error("❌ Incorrect password. Please try again.")
                return False

    return False


# Check authentication before showing main app
if not check_password():
    st.stop()

# Main app
st.title("Token Tracking Database Manager")

# Sidebar navigation
page = st.sidebar.selectbox(
    "Navigation",
    [
        "Database Tables",
        "Credit Groups",
        "User Assignments",
        "Model Management",
        "Base Settings",
        "Migrations",
    ],
)

# Initialize database connection
conn = get_db_connection()

if page == "Database Tables":
    st.header("Database Tables Viewer")

    if conn:
        tables = get_all_tables(conn)

        if tables:
            selected_table = st.selectbox("Select a table to view", tables)

            if selected_table:
                st.subheader(f"Table: {selected_table}")

                # Get table schema
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({selected_table})")
                columns = cursor.fetchall()

                if columns:
                    col_info = pd.DataFrame(
                        columns,
                        columns=[
                            "cid",
                            "name",
                            "type",
                            "notnull",
                            "default_value",
                            "pk",
                        ],
                    )
                    st.write("**Schema:**")
                    st.dataframe(
                        col_info[["name", "type", "notnull", "pk"]],
                        use_container_width=True,
                    )

                # Get table data
                limit = st.number_input(
                    "Row limit", min_value=1, max_value=10000, value=100, step=100
                )
                df = get_table_data(conn, selected_table, limit)

                if df is not None and not df.empty:
                    st.write(f"**Data ({len(df)} rows):**")
                    st.dataframe(df, use_container_width=True)

                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv,
                        file_name=f"{selected_table}.csv",
                        mime="text/csv",
                    )
                elif df is not None:
                    st.info("Table is empty")
        else:
            st.warning("No tables found in the database")
    else:
        st.error("Could not connect to database")

elif page == "Credit Groups":
    st.header("Credit Groups Management")

    if not conn:
        st.error("Could not connect to database")
        st.stop()

    # Get existing groups
    groups_df = get_table_data(conn, "token_tracking_credit_group", limit=1000)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Existing Credit Groups")
        if groups_df is not None and not groups_df.empty:
            # Display groups with edit/delete options
            for idx, row in groups_df.iterrows():
                group_name = row.get("name", "Unknown")
                max_credit = row.get("max_credit", "N/A")
                group_id = row.get("id")

                with st.expander(f"{group_name} - Limit: {max_credit}"):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(
                            f"**Description:** {row.get('description', 'No description')}"
                        )
                        st.write(f"**Max Credit:** {max_credit}")
                        st.write(f"**ID:** {group_id}")

                    with col_b:
                        # Edit form
                        with st.form(f"edit_group_{idx}"):
                            current_limit = (
                                int(row.get("max_credit", 1000))
                                if isinstance(row.get("max_credit"), (int, float))
                                else 1000
                            )
                            new_limit = st.number_input(
                                "Max Credit",
                                value=current_limit,
                                min_value=1,
                                key=f"limit_{idx}",
                            )
                            new_desc = st.text_area(
                                "Description",
                                value=str(row.get("description", "")),
                                key=f"desc_{idx}",
                                height=80,
                            )
                            submitted = st.form_submit_button(
                                "Update", use_container_width=True
                            )
                            if submitted:
                                # Update group using correct column names
                                update_query = "UPDATE token_tracking_credit_group SET max_credit = ?, description = ? WHERE id = ?"
                                result = execute_query(
                                    conn, update_query, (new_limit, new_desc, group_id)
                                )

                                if result is not None and result > 0:
                                    st.success("Group updated successfully")
                                    st.rerun()
                                elif result == 0:
                                    st.warning("No rows updated. Group may not exist.")

                        # Delete button with cascade delete
                        if st.button(
                            "Delete",
                            key=f"delete_{idx}",
                            type="secondary",
                            use_container_width=True,
                        ):
                            # First, delete all user assignments for this group (cascade delete)
                            delete_assignments_query = "DELETE FROM token_tracking_credit_group_user WHERE credit_group_id = ?"
                            assignments_result = execute_query(
                                conn, delete_assignments_query, (group_id,)
                            )

                            # Then delete the group
                            delete_query = (
                                "DELETE FROM token_tracking_credit_group WHERE id = ?"
                            )
                            result = execute_query(conn, delete_query, (group_id,))

                            if result is not None and result > 0:
                                assignments_count = (
                                    assignments_result
                                    if assignments_result is not None
                                    else 0
                                )
                                if assignments_count > 0:
                                    st.success(
                                        f"Group deleted successfully. Removed {assignments_count} user assignment(s)."
                                    )
                                else:
                                    st.success("Group deleted successfully.")
                                st.rerun()
                            elif result == 0:
                                st.warning("No rows deleted. Group may not exist.")

            st.dataframe(groups_df, use_container_width=True, hide_index=True)
        else:
            st.info("No credit groups found")

    with col2:
        st.subheader("Create New Group")
        with st.form("create_credit_group"):
            plan_name = st.text_input("Plan Name", placeholder="e.g., Starter Plan")
            max_credit = st.number_input(
                "Max Credit", min_value=1, value=1000, step=100
            )
            description = st.text_area(
                "Description", placeholder="Plan description", height=100
            )

            submitted = st.form_submit_button("Create Group", use_container_width=True)
            if submitted:
                if plan_name:
                    command = f'owui-token-tracking credit-group create "{plan_name}" {max_credit} "{description}"'
                    stdout, stderr, returncode = run_token_tracking_command(command)

                    if returncode == 0:
                        st.success(f"Successfully created credit group: {plan_name}")
                        st.rerun()
                    else:
                        st.error(f"Error creating credit group: {stderr}")
                        st.code(stdout + stderr)
                else:
                    st.error("Plan name is required")

elif page == "User Assignments":
    st.header("User-Group Assignments")

    if not conn:
        st.error("Could not connect to database")
        st.stop()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Current Assignments")
        assignments_df = get_user_group_assignments(conn)

        if assignments_df is not None and not assignments_df.empty:
            # Display assignments with delete option
            # Note: token_tracking_credit_group_user has no id column, only user_id and credit_group_id
            for idx, row in assignments_df.iterrows():
                user_display = row.get(
                    "email", row.get("name", row.get("user_id", "Unknown"))
                )
                group_display = row.get(
                    "group_name", row.get("credit_group_id", "Unknown")
                )
                user_id = row.get("user_id")
                credit_group_id = row.get("credit_group_id")

                with st.expander(f"User: {user_display} → Group: {group_display}"):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        # Show relevant columns
                        display_data = {}
                        if "email" in row:
                            display_data["User Email"] = row["email"]
                        if "name" in row:
                            display_data["User Name"] = row["name"]
                        if "user_id" in row:
                            display_data["User ID"] = row["user_id"]
                        if "group_name" in row:
                            display_data["Group Name"] = row["group_name"]
                        if "credit_group_id" in row:
                            display_data["Group ID"] = row["credit_group_id"]

                        if display_data:
                            st.json(display_data)
                        else:
                            st.dataframe(
                                pd.DataFrame([row]),
                                use_container_width=True,
                                hide_index=True,
                            )

                    with col_b:
                        # Delete assignment using user_id and credit_group_id (no id column in this table)
                        if user_id and credit_group_id:
                            if st.button(
                                "Remove",
                                key=f"remove_{idx}",
                                type="secondary",
                                use_container_width=True,
                            ):
                                delete_query = "DELETE FROM token_tracking_credit_group_user WHERE user_id = ? AND credit_group_id = ?"
                                result = execute_query(
                                    conn, delete_query, (user_id, credit_group_id)
                                )
                                if result is not None and result > 0:
                                    st.success("Assignment removed successfully")
                                    st.rerun()
                                elif result == 0:
                                    st.warning("No rows deleted.")

            # Show full table
            st.dataframe(assignments_df, use_container_width=True, hide_index=True)
        else:
            st.info("No user-group assignments found")

    with col2:
        st.subheader("Add User to Group")
        with st.form("add_user_to_group"):
            # Get users and groups for dropdowns
            users = get_users(conn)
            groups = get_credit_groups(conn)

            if not users:
                st.warning("No users found in database")
            if not groups:
                st.warning("No credit groups found. Create a group first.")

            if users and groups:
                # Create dropdowns
                user_options = {display: user_id for user_id, display in users}
                group_options = {display: group_id for group_id, display in groups}

                # Get group names for lookup
                group_name_map = {}
                groups_df = get_table_data(
                    conn, "token_tracking_credit_group", limit=1000
                )
                if groups_df is not None and not groups_df.empty:
                    for _, row in groups_df.iterrows():
                        group_id = row.get("id")
                        group_name = row.get("name", "")
                        for display, gid in group_options.items():
                            if gid == group_id:
                                group_name_map[display] = group_name
                                break

                selected_user_display = st.selectbox(
                    "Select User",
                    options=list(user_options.keys()),
                    index=0 if user_options else None,
                )
                selected_group_display = st.selectbox(
                    "Select Credit Group",
                    options=list(group_options.keys()),
                    index=0 if group_options else None,
                )

                submitted = st.form_submit_button(
                    "Assign User to Group", use_container_width=True
                )
                if submitted:
                    selected_user_id = user_options[selected_user_display]
                    selected_group_id = group_options[selected_group_display]

                    # Get group name for command - extract from display or use mapping
                    group_name = group_name_map.get(selected_group_display, "")
                    if not group_name:
                        # Fallback: extract from display name
                        group_name = (
                            selected_group_display.split("(")[0].strip()
                            if "(" in selected_group_display
                            else selected_group_display
                        )

                    if group_name:
                        command = f'owui-token-tracking credit-group add-user {selected_user_id} "{group_name}"'
                        stdout, stderr, returncode = run_token_tracking_command(command)

                        if returncode == 0:
                            st.success("Successfully assigned user to group")
                            st.rerun()
                        else:
                            st.error(f"Error assigning user to group: {stderr}")
                            if stdout:
                                st.code(stdout)
                            if stderr:
                                st.code(stderr)
                    else:
                        st.error("Could not determine group name")
            else:
                st.info(
                    "Please ensure users and groups exist before creating assignments."
                )

elif page == "Model Management":
    st.header("Model Management")

    if not conn:
        st.error("Could not connect to database")
        st.stop()

    # Find token_parity.json file
    backend_dirs = [
        Path("/app/backend"),
        Path(__file__).parent / "backend",
    ]
    token_parity_path = None
    for backend_dir in backend_dirs:
        potential_path = backend_dir / "token-tracking" / "token_parity.json"
        if potential_path.exists():
            token_parity_path = potential_path
            break

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Existing Models")
        models_df = get_table_data(conn, "token_tracking_model_pricing", limit=1000)
        if models_df is not None and not models_df.empty:
            # Display models with delete option
            for idx, row in models_df.iterrows():
                model_id = row.get("id", "Unknown")
                provider = row.get("provider", "Unknown")
                name = row.get("name", "Unknown")

                with st.expander(f"{model_id} ({provider}) - {name}"):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        # Show all model details
                        st.json(row.to_dict())

                    with col_b:
                        if st.button(
                            "Delete from DB",
                            key=f"delete_model_{idx}",
                            type="secondary",
                            use_container_width=True,
                        ):
                            delete_query = (
                                "DELETE FROM token_tracking_model_pricing WHERE id = ?"
                            )
                            result = execute_query(conn, delete_query, (model_id,))

                            if result is not None and result > 0:
                                st.success(f"Model '{model_id}' deleted successfully.")
                                st.rerun()
                            elif result == 0:
                                st.warning("No rows deleted. Model may not exist.")

            st.caption("Full Table View")
            st.dataframe(models_df, use_container_width=True, hide_index=True)
        else:
            st.info("No models found")

        st.divider()

        # JSON Editor Section
        st.subheader("Edit token_parity.json")
        if token_parity_path and token_parity_path.exists():
            st.info(f"Editing: {token_parity_path}")

            # Read current content
            try:
                with open(token_parity_path, "r") as f:
                    current_content = f.read()
                    token_parity_data = json.loads(current_content)
            except Exception as e:
                st.error(f"Error reading file: {e}")
                current_content = "[]"
                token_parity_data = []

            # Editor
            edited_content = st.text_area(
                "JSON Content",
                value=json.dumps(token_parity_data, indent=2),
                height=400,
                key="json_editor",
            )

            col_save, col_validate = st.columns(2)

            with col_validate:
                if st.button("Validate JSON", use_container_width=True):
                    try:
                        json.loads(edited_content)
                        st.success("JSON is valid")
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")

            with col_save:
                if st.button("Save Changes", use_container_width=True, type="primary"):
                    try:
                        # Validate JSON before saving
                        parsed_json = json.loads(edited_content)

                        # Validate structure
                        if not isinstance(parsed_json, list):
                            st.error("JSON must be an array of model objects")
                        else:
                            # Check each model has required fields
                            required_fields = [
                                "provider",
                                "id",
                                "name",
                                "input_cost_credits",
                                "per_input_tokens",
                                "output_cost_credits",
                                "per_output_tokens",
                            ]
                            valid = True
                            for i, model in enumerate(parsed_json):
                                if not isinstance(model, dict):
                                    st.error(f"Model at index {i} must be an object")
                                    valid = False
                                    break
                                for field in required_fields:
                                    if field not in model:
                                        st.error(
                                            f"Model at index {i} missing required field: {field}"
                                        )
                                        valid = False
                                        break
                                if not valid:
                                    break

                            if valid:
                                # Write to file
                                # Check if file is writable (in Docker, it might be read-only)
                                try:
                                    with open(token_parity_path, "w") as f:
                                        f.write(edited_content)
                                    st.success("File saved successfully!")
                                    st.rerun()
                                except PermissionError:
                                    st.error(
                                        "Permission denied. File may be read-only in Docker. Check volume mount permissions."
                                    )
                                except Exception as e:
                                    st.error(f"Error saving file: {e}")
                    except json.JSONDecodeError as e:
                        st.error(f"Invalid JSON: {e}")
        else:
            st.warning("token_parity.json not found")
            st.info("Expected location: backend/token-tracking/token_parity.json")

            # Allow creating new file
            st.subheader("Create New token_parity.json")
            new_json_content = st.text_area(
                "JSON Content",
                value=json.dumps(
                    [
                        {
                            "provider": "openai",
                            "id": "gpt-4.1-mini",
                            "name": "GPT-4.1 Mini",
                            "input_cost_credits": 1,
                            "per_input_tokens": 1,
                            "output_cost_credits": 1,
                            "per_output_tokens": 1,
                        }
                    ],
                    indent=2,
                ),
                height=300,
                key="new_json_editor",
            )

            if st.button("Create File", use_container_width=True):
                try:
                    parsed_json = json.loads(new_json_content)
                    # Try to create the directory if it doesn't exist
                    if token_parity_path:
                        token_parity_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(token_parity_path, "w") as f:
                            f.write(new_json_content)
                        st.success("File created successfully!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error creating file: {e}")

    with col2:
        st.subheader("Update Models")
        st.info(
            "After editing token_parity.json, run migration to update the database."
        )

        if token_parity_path and token_parity_path.exists():
            if st.button("Run Model Migration", use_container_width=True):
                command = f"owui-token-tracking init --model-json token-tracking/token_parity.json"
                stdout, stderr, returncode = run_token_tracking_command(command)

                if returncode == 0:
                    st.success("Model migration completed successfully!")
                    st.rerun()
                else:
                    st.warning(f"Migration output: {stderr}")
                    st.code(stdout + stderr)
        else:
            st.info("token_parity.json must exist to run migration")

elif page == "Base Settings":
    st.header("Base Settings")

    if not conn:
        st.error("Could not connect to database")
        st.stop()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Existing Settings")
        settings_df = get_table_data(conn, "token_tracking_base_settings", limit=1000)

        if settings_df is not None and not settings_df.empty:
            for idx, row in settings_df.iterrows():
                key = row.get("setting_key", "Unknown")
                value = row.get("setting_value", "")
                desc = row.get("description", "")

                with st.expander(f"{key}: {value}"):
                    with st.form(f"edit_setting_{idx}"):
                        new_value = st.text_input(
                            "Value", value=str(value), key=f"val_{idx}"
                        )
                        new_desc = st.text_area(
                            "Description", value=str(desc), key=f"desc_{idx}", height=60
                        )

                        col_update, col_delete = st.columns([3, 1])
                        with col_update:
                            submitted = st.form_submit_button(
                                "Update", use_container_width=True
                            )

                        if submitted:
                            update_query = "UPDATE token_tracking_base_settings SET setting_value = ?, description = ? WHERE setting_key = ?"
                            result = execute_query(
                                conn, update_query, (new_value, new_desc, key)
                            )

                            if result is not None and result > 0:
                                st.success(f"Setting '{key}' updated successfully")
                                st.rerun()
                            elif result == 0:
                                st.warning("No rows updated.")

                        with col_delete:
                            # We use a separate button outside the form for delete usually, but inside works if we handle it right.
                            # Actually, streamlit form submit button is the only way to trigger form actions.
                            # For delete, let's use a button outside the form to avoid confusion, or a second submit button?
                            # Streamlit forms allow multiple submit buttons.
                            delete_submitted = st.form_submit_button(
                                "Delete", type="secondary", use_container_width=True
                            )
                            if delete_submitted:
                                delete_query = "DELETE FROM token_tracking_base_settings WHERE setting_key = ?"
                                result = execute_query(conn, delete_query, (key,))
                                if result is not None and result > 0:
                                    st.success(f"Setting '{key}' deleted successfully")
                                    st.rerun()
                                else:
                                    st.warning("Could not delete setting.")

            st.dataframe(settings_df, use_container_width=True, hide_index=True)
        else:
            st.info("No base settings found")

    with col2:
        st.subheader("Add New Setting")
        with st.form("add_setting"):
            new_key = st.text_input("Setting Key", placeholder="e.g., enable_feature_x")
            new_value = st.text_input("Setting Value", placeholder="true")
            new_desc = st.text_area(
                "Description", placeholder="Description of the setting"
            )

            submitted = st.form_submit_button(
                "Create Setting", use_container_width=True
            )
            if submitted:
                if new_key:
                    # Check if key exists
                    check_df = get_table_data(
                        conn,
                        "token_tracking_base_settings",
                        where_clause=f"setting_key = '{new_key}'",
                    )
                    if check_df is not None and not check_df.empty:
                        st.error(f"Setting '{new_key}' already exists.")
                    else:
                        insert_query = "INSERT INTO token_tracking_base_settings (setting_key, setting_value, description) VALUES (?, ?, ?)"
                        result = execute_query(
                            conn, insert_query, (new_key, new_value, new_desc)
                        )
                        if result is not None:
                            st.success(f"Setting '{new_key}' created successfully")
                            st.rerun()
                else:
                    st.error("Setting Key is required")

elif page == "Migrations":
    st.header("Database Migrations")

    if not conn:
        st.error("Could not connect to database")
        st.stop()

    st.subheader("Initial Migration")
    st.info(
        "This will create the token tracking tables if they don't exist. Safe to run multiple times."
    )

    if st.button("Run Initial Migration", use_container_width=True):
        command = "owui-token-tracking init"
        stdout, stderr, returncode = run_token_tracking_command(command)

        if returncode == 0:
            st.success("Migration completed successfully!")
            st.code(stdout)
        else:
            st.warning(f"Migration output: {stderr}")
            st.code(stdout + stderr)

# Close connection
if conn:
    conn.close()
