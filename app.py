import os
import subprocess
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'your_strong_random_secret_key_here' # !! IMPORTANT: CHANGE THIS TO A REAL, STRONG KEY !!
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
                start_command TEXT NOT NULL,
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
    # Fetch all projects from the database
    projects_cursor = db.execute('SELECT * FROM projects ORDER BY deployed_at DESC').fetchall()
    projects = [dict(row) for row in projects_cursor] # Convert Row objects to dictionaries
    db.close()
    return render_template('index.html', projects=projects)

@app.route('/host', methods=['GET', 'POST'])
def host_project():
    if request.method == 'POST':
        project_name = request.form['project_name'].strip()
        pre_build_command = request.form.get('pre_build_command', '').strip()
        build_command = request.form['build_command'].strip()
        start_command = request.form['start_command'].strip()

        if not project_name or not build_command or not start_command:
            flash('Project Name, Build Command, and Start Command are required!', 'error')
            return redirect(request.url)

        db = get_db()
        # Check if project name already exists in DB
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
                subprocess.run(pre_build_command, shell=True, check=True, cwd=project_path, capture_output=True, text=True) # Added capture_output
                # You might want to log or display output/errors from subprocess runs

            # Execute build command
            flash(f'Running build command: {build_command}', 'info')
            subprocess.run(build_command, shell=True, check=True, cwd=project_path, capture_output=True, text=True)

            # Execute start command (this will run in the background)
            flash(f'Running start command: {start_command}', 'info')
            # Using subprocess.Popen allows the command to run in the background.
            # In a production setup, you'd use a robust process manager like systemd, pm2, or gunicorn.
            subprocess.Popen(start_command, shell=True, cwd=project_path)

            # Construct a hypothetical URL for the project
            # This URL assumes your project is accessible on a specific port from your Chromebook's IP
            # YOU WILL NEED TO REPLACE 'YOUR_CHROMBOOK_IP_OR_DOMAIN' and 'YOUR_PROJECT_PORT'
            # The 'start_command' should ensure your project starts a server on 'YOUR_PROJECT_PORT'
            project_url = f"http://YOUR_CHROMBOOK_IP_OR_DOMAIN:YOUR_PROJECT_PORT/{project_name}/" # Example

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
            db.close() # Close DB connection before potential rmtree
            # Clean up partially deployed project if commands fail
            import shutil
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
            flash(f'Command failed for {e.cmd}: {e.stderr}', 'error') # Display stderr for more info
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

if __name__ == '__main__':
    # Initialize the database when the app starts
    init_db()
    # To make it accessible from other devices on your LAN:
    # app.run(debug=True, host='0.0.0.0', port=5000)
    # Make sure to adjust 'YOUR_CHROMBOOK_IP_OR_DOMAIN' and 'YOUR_PROJECT_PORT' above in project_url
    app.run(debug=True) # Runs on http://127.0.0.1:5000 by default
