import streamlit as st
import sqlite3
import os
import subprocess
import json
import pandas as pd
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Token Tracking Database Manager",
    page_icon="🔐",
    layout="wide"
)

# Database configuration
def get_database_path():
    """Get the database path from environment or default location"""
    if os.getenv("DATABASE_URL"):
        db_url = os.getenv("DATABASE_URL")
        if db_url.startswith("sqlite:///"):
            # SQLite URL format: sqlite:///path or sqlite:////absolute/path
            # Remove the protocol prefix (sqlite:///)
            path = db_url[10:]  # len("sqlite:///") = 10
            # If path doesn't start with /, add it for absolute path
            # (SQLite URLs with 3 slashes can have absolute paths that need the / added back)
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

def get_db_connection():
    """Create a connection to the database"""
    db_path = get_database_path()
    
    # Debug info
    st.sidebar.info(f"DB Path: {db_path}")
    st.sidebar.info(f"DB Exists: {os.path.exists(db_path) if db_path else False}")
    if os.getenv("DATABASE_URL"):
        st.sidebar.info(f"DB URL: {os.getenv('DATABASE_URL')}")
    
    if not os.path.exists(db_path):
        st.error(f"Database not found at: {db_path}")
        st.info("Make sure the database file exists and the path is correct.")
        # Show available paths for debugging
        debug_paths = [
            "/app/backend/data/webui.db",
            "/app/data/webui.db",
            str(Path(__file__).parent / "backend" / "data" / "webui.db"),
        ]
        st.info("Checking these paths:")
        for p in debug_paths:
            exists = os.path.exists(p) if p else False
            st.text(f"  {p}: {'✓' if exists else '✗'}")
        return None
    try:
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        st.error(f"Error connecting to database: {e}")
        return None

def get_all_tables(conn):
    """Get list of all tables in the database"""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]

def get_table_data(conn, table_name, limit=100):
    """Get data from a table"""
    try:
        df = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT {limit}", conn)
        return df
    except Exception as e:
        st.error(f"Error reading table {table_name}: {e}")
        return None

def run_token_tracking_command(command):
    """Run a token tracking CLI command"""
    try:
        # Set database URL
        db_path = get_database_path()
        env = os.environ.copy()
        env['DATABASE_URL'] = f"sqlite:///{db_path}"
        
        # Change to backend directory if it exists
        backend_dirs = [
            Path("/app/backend"),
            Path(__file__).parent / "backend",
        ]
        for backend_dir in backend_dirs:
            if backend_dir.exists():
                os.chdir(str(backend_dir))
                break
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 1
    except Exception as e:
        return "", str(e), 1

# Main app
st.title("🔐 Token Tracking Database Manager")

# Sidebar navigation
page = st.sidebar.selectbox(
    "Navigation",
    ["Database Tables", "Token Tracking Operations", "Model Management"]
)

# Initialize database connection
conn = get_db_connection()

if page == "Database Tables":
    st.header("📊 Database Tables Viewer")
    
    if conn:
        tables = get_all_tables(conn)
        
        if tables:
            selected_table = st.selectbox("Select a table to view", tables)
            
            if selected_table:
                st.subheader(f"Table: `{selected_table}`")
                
                # Get table schema
                cursor = conn.cursor()
                cursor.execute(f"PRAGMA table_info({selected_table})")
                columns = cursor.fetchall()
                
                if columns:
                    col_info = pd.DataFrame(columns, columns=['cid', 'name', 'type', 'notnull', 'default_value', 'pk'])
                    st.write("**Schema:**")
                    st.dataframe(col_info[['name', 'type', 'notnull', 'pk']], use_container_width=True)
                
                # Get table data
                limit = st.number_input("Row limit", min_value=1, max_value=10000, value=100, step=100)
                df = get_table_data(conn, selected_table, limit)
                
                if df is not None and not df.empty:
                    st.write(f"**Data ({len(df)} rows):**")
                    st.dataframe(df, use_container_width=True)
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download as CSV",
                        data=csv,
                        file_name=f"{selected_table}.csv",
                        mime="text/csv"
                    )
                elif df is not None:
                    st.info("Table is empty")
        else:
            st.warning("No tables found in the database")
    else:
        st.error("Could not connect to database")

elif page == "Token Tracking Operations":
    st.header("🎯 Token Tracking Operations")
    
    if not conn:
        st.error("Could not connect to database")
        st.stop()
    
    # Tab for different operations
    tab1, tab2, tab3, tab4 = st.tabs(["Credit Groups (Plans)", "User Management", "Usage & Logs", "Migrations"])
    
    with tab1:
        st.subheader("Credit Groups (Plans) Management")
        
        # View existing credit groups
        st.write("### Existing Credit Groups")
        try:
            credit_groups_df = get_table_data(conn, "token_tracking_credit_group", limit=1000)
            if credit_groups_df is not None and not credit_groups_df.empty:
                st.dataframe(credit_groups_df, use_container_width=True)
            else:
                st.info("No credit groups found")
        except Exception as e:
            st.warning(f"Could not load credit groups: {e}")
        
        st.divider()
        
        # Create new credit group
        st.write("### Create New Credit Group")
        with st.form("create_credit_group"):
            plan_name = st.text_input("Plan Name", placeholder="e.g., Starter Plan")
            token_limit = st.number_input("Token Limit", min_value=1, value=1000, step=100)
            description = st.text_area("Description", placeholder="Plan description")
            
            submitted = st.form_submit_button("Create Credit Group")
            if submitted:
                if plan_name:
                    command = f'owui-token-tracking credit-group create "{plan_name}" {token_limit} "{description}"'
                    stdout, stderr, returncode = run_token_tracking_command(command)
                    
                    if returncode == 0:
                        st.success(f"Successfully created credit group: {plan_name}")
                        st.code(stdout)
                        st.rerun()
                    else:
                        st.error(f"Error creating credit group: {stderr}")
                        st.code(stdout + stderr)
                else:
                    st.error("Plan name is required")
        
        st.divider()
        
        # View credit group user assignments
        st.write("### Credit Group User Assignments")
        try:
            credit_group_users_df = get_table_data(conn, "token_tracking_credit_group_user", limit=1000)
            if credit_group_users_df is not None and not credit_group_users_df.empty:
                st.dataframe(credit_group_users_df, use_container_width=True)
            else:
                st.info("No user assignments found")
        except Exception as e:
            st.warning(f"Could not load credit group user assignments: {e}")
        
        st.divider()
        
        # Add user to credit group
        st.write("### Add User to Credit Group")
        with st.form("add_user_to_group"):
            user_id = st.text_input("User ID", placeholder="e.g., 39eb28ea-73a2-437a-bc7e-4e0a90529105")
            group_name = st.text_input("Credit Group Name", placeholder="e.g., Starter Plan")
            
            submitted = st.form_submit_button("Add User to Group")
            if submitted:
                if user_id and group_name:
                    command = f'owui-token-tracking credit-group add-user {user_id} "{group_name}"'
                    stdout, stderr, returncode = run_token_tracking_command(command)
                    
                    if returncode == 0:
                        st.success(f"Successfully added user {user_id} to {group_name}")
                        st.code(stdout)
                        st.rerun()
                    else:
                        st.error(f"Error adding user to group: {stderr}")
                        st.code(stdout + stderr)
                else:
                    st.error("User ID and Group Name are required")
    
    with tab2:
        st.subheader("User Management")
        
        # Find user by email
        st.write("### Find User by Email")
        with st.form("find_user"):
            email = st.text_input("Email Address", placeholder="user@example.com")
            
            submitted = st.form_submit_button("Find User")
            if submitted:
                if email:
                    command = f'owui-token-tracking user find --email "{email}"'
                    stdout, stderr, returncode = run_token_tracking_command(command)
                    
                    if returncode == 0:
                        st.success("User found!")
                        st.code(stdout)
                    else:
                        st.error(f"Error finding user: {stderr}")
                        st.code(stdout + stderr)
                else:
                    st.error("Email is required")
        
        st.divider()
        
        # View users table
        st.write("### Users Table")
        try:
            users_df = get_table_data(conn, "user", limit=1000)
            if users_df is not None and not users_df.empty:
                st.dataframe(users_df, use_container_width=True)
            else:
                st.info("No users found")
        except Exception as e:
            st.warning(f"Could not load users: {e}")
    
    with tab3:
        st.subheader("Usage Logs & Tracking")
        
        # View usage logs
        st.write("### Token Usage Logs")
        try:
            usage_logs_df = get_table_data(conn, "token_tracking_usage_log", limit=1000)
            if usage_logs_df is not None and not usage_logs_df.empty:
                st.dataframe(usage_logs_df, use_container_width=True)
            else:
                st.info("No usage logs found")
        except Exception as e:
            st.warning(f"Could not load usage logs: {e}")
        
        st.divider()
        
        # View sponsored allowances
        st.write("### Sponsored Allowances")
        try:
            sponsored_df = get_table_data(conn, "token_tracking_sponsored_allowance", limit=1000)
            if sponsored_df is not None and not sponsored_df.empty:
                st.dataframe(sponsored_df, use_container_width=True)
            else:
                st.info("No sponsored allowances found")
        except Exception as e:
            st.warning(f"Could not load sponsored allowances: {e}")
    
    with tab4:
        st.subheader("Database Migrations")
        
        st.write("### Run Initial Migration")
        st.info("This will create the token tracking tables if they don't exist. Safe to run multiple times.")
        if st.button("Run Initial Migration"):
            command = "owui-token-tracking init"
            stdout, stderr, returncode = run_token_tracking_command(command)
            
            if returncode == 0:
                st.success("Migration completed successfully!")
                st.code(stdout)
            else:
                st.warning(f"Migration output: {stderr}")
                st.code(stdout + stderr)

elif page == "Model Management":
    st.header("🤖 Model Management")
    
    if not conn:
        st.error("Could not connect to database")
        st.stop()
    
    # View existing models
    st.write("### Existing Models")
    try:
        models_df = get_table_data(conn, "token_tracking_model_pricing", limit=1000)
        if models_df is not None and not models_df.empty:
            st.dataframe(models_df, use_container_width=True)
        else:
            st.info("No models found")
    except Exception as e:
        st.warning(f"Could not load models: {e}")
    
    st.divider()
    
    # Model migration from token_parity.json
    st.write("### Update Models from token_parity.json")
    st.info("This will update the database with models from token_parity.json. Run this after adding new models to the JSON file.")
    
    # Check if token_parity.json exists
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
    
    if token_parity_path.exists():
        st.success(f"Found token_parity.json at: {token_parity_path}")
        
        # Display current token_parity.json content
        with open(token_parity_path, 'r') as f:
            token_parity = json.load(f)
        
        st.write("**Current token_parity.json content:**")
        st.json(token_parity)
        
        if st.button("Run Model Migration"):
            command = f"owui-token-tracking init --model-json token-tracking/token_parity.json"
            stdout, stderr, returncode = run_token_tracking_command(command)
            
            if returncode == 0:
                st.success("Model migration completed successfully!")
                st.code(stdout)
                st.rerun()
            else:
                st.warning(f"Migration output: {stderr}")
                st.code(stdout + stderr)
    else:
        st.warning(f"token_parity.json not found at: {token_parity_path}")
        st.info("The token_parity.json file should be located at: backend/token-tracking/token_parity.json")

# Close connection
if conn:
    conn.close()
