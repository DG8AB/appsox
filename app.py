import os
import subprocess
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory

app = Flask(__name__)
app.secret_key = 'your_strong_random_secret_key_here_seriously_change_this' # !! IMPORTANT: CHANGE THIS TO A REAL, STRONG KEY !!
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['PROJECTS_FOLDER'] = 'projects'
app.config['DATABASE'] = 'database.db'

# Ensure upload and projects folders exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
if not os.path.exists(app.config['PROJECTS_FOLDER']):
    os.makedirs(app.config['PROJECTS_FOLDER'])

### Database Functions ###

def get_db():
    """Connects to the SQLite database."""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row # This allows access to columns by name
    return conn

def init_db():
    """Initializes the database schema."""
    with app.app_context():
        db = get_db()
        # Create a table for projects if it doesn't exist
        db.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                url TEXT NOT NULL,
                pre_build_command TEXT,
                build_command TEXT NOT NULL,
                start_command TEXT, -- Start command is now optional as Flask serves it
                deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        db.commit()

# Call init_db when the application starts
# This ensures the table is created if it doesn't exist
with app.app_context():
    init_db()

### Flask Routes ###

@app.route('/')
def index():
    db = get_db()
    projects_cursor = db.execute('SELECT * FROM projects ORDER BY deployed_at DESC').fetchall()
    projects = [dict(row) for row in projects_cursor]
    db.close()
    return render_template('index.html', projects=projects)

@app.route('/host', methods=['GET', 'POST'])
def host_project():
    if request.method == 'POST':
        project_name = request.form['project_name'].strip()
        pre_build_command = request.form.get('pre_build_command', '').strip()
        build_command = request.form['build_command'].strip()
        start_command = request.form.get('start_command', '').strip() # Make start_command optional

        if not project_name or not build_command:
            flash('Project Name and Build Command are required!', 'error')
            return redirect(request.url)

        db = get_db()
        existing_project = db.execute('SELECT id FROM projects WHERE name = ?', (project_name,)).fetchone()
        if existing_project:
            db.close()
            flash(f'Project with name "{project_name}" already exists! Please choose a different name.', 'error')
            return redirect(request.url)

        if 'project_files' not in request.files:
            db.close()
            flash('No file part', 'error')
            return redirect(request.url)

        files = request.files.getlist('project_files')
        if not files or all(f.filename == '' for f in files):
            db.close()
            flash('No selected files. Please upload your project files.', 'error')
            return redirect(request.url)

        project_path = os.path.join(app.config['PROJECTS_FOLDER'], project_name)
        os.makedirs(project_path, exist_ok=True)

        try:
            # Save uploaded files
            for file in files:
                if file.filename:
                    file_path = os.path.join(project_path, file.filename)
                    file.save(file_path)

            # Execute pre-build command if provided
            if pre_build_command:
                flash(f'Running pre-build command: {pre_build_command}', 'info')
                process = subprocess.run(pre_build_command, shell=True, check=True, cwd=project_path, capture_output=True, text=True)
                flash(f'Pre-build output: {process.stdout}', 'info')
                if process.stderr:
                    flash(f'Pre-build errors: {process.stderr}', 'warning')


            # Execute build command
            flash(f'Running build command: {build_command}', 'info')
            process = subprocess.run(build_command, shell=True, check=True, cwd=project_path, capture_output=True, text=True)
            flash(f'Build output: {process.stdout}', 'info')
            if process.stderr:
                flash(f'Build errors: {process.stderr}', 'warning')


            # If a start command is provided, execute it in the background
            # This is useful for backend services or complex apps that need their own server
            if start_command:
                flash(f'Running start command: {start_command} (in background)', 'info')
                # Use a specific port for the project if it's a separate server
                # Note: This is an unmanaged background process. For real deployment, use systemd/pm2.
                subprocess.Popen(start_command, shell=True, cwd=project_path)


            # The URL for path-based serving
            # This URL will be served by the Flask app itself
            # The 'host' parameter in app.run determines the IP (e.g., 127.0.0.1 or 0.0.0.0)
            project_url = f"http://{request.host}/{project_name}/"


            # Insert project info into the database
            db.execute(
                'INSERT INTO projects (name, path, url, pre_build_command, build_command, start_command) VALUES (?, ?, ?, ?, ?, ?)',
                (project_name, project_path, project_url, pre_build_command, build_command, start_command)
            )
            db.commit()
            db.close()

            flash(f'Project "{project_name}" deployed successfully! Access at: <a href="{project_url}" target="_blank">{project_url}</a>', 'success')
            return redirect(url_for('index'))

        except subprocess.CalledProcessError as e:
            db.close()
            import shutil
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
            flash(f'Command failed for {e.cmd}:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}', 'error')
            return redirect(request.url)
        except Exception as e:
            db.close()
            import shutil
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
            flash(f'An unexpected error occurred during deployment: {e}', 'error')
            return redirect(request.url)
    db.close() # Close DB connection for GET requests too
    return render_template('host.html')

# NEW ROUTE: Serve static files for each project from its unique path
@app.route('/<project_name>/<path:filename>')
def serve_project_files(project_name, filename):
    db = get_db()
    project = db.execute('SELECT path FROM projects WHERE name = ?', (project_name,)).fetchone()
    db.close()

    if project:
        project_root_path = project['path']
        # Ensure the filename is within the project's directory to prevent directory traversal attacks
        # This is a minimal security measure; a full solution would use send_from_directory carefully.
        try:
            return send_from_directory(project_root_path, filename)
        except Exception as e:
            # Handle cases where file is not found or other errors
            app.logger.error(f"Error serving file {filename} from {project_root_path}: {e}")
            return "File not found or access denied.", 404
    else:
        return "Project not found.", 404

# A route for the root of the project path (e.g., /my-project-name/)
@app.route('/<project_name>/')
def serve_project_root(project_name):
    db = get_db()
    project = db.execute('SELECT path FROM projects WHERE name = ?', (project_name,)).fetchone()
    db.close()

    if project:
        project_root_path = project['path']
        # Attempt to serve index.html by default for the root URL
        try:
            return send_from_directory(project_root_path, 'index.html')
        except FileNotFoundError:
            # If index.html doesn't exist, try to serve a directory listing (though send_from_directory typically doesn't do this by default)
            # Or you might want to show a custom error page
            return "Index file not found in project root.", 404
        except Exception as e:
            app.logger.error(f"Error serving project root for {project_name}: {e}")
            return "Error serving project.", 500
    else:
        return "Project not found.", 404


if __name__ == '__main__':
    # Initialize the database when the app starts
    init_db()
    # To make it accessible from other devices on your LAN:
    # app.run(debug=True, host='0.0.0.0', port=5000)
    # The default port is 5000. All projects will be served on this port.
    app.run(debug=True)
