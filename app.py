import os
import subprocess
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, g, jsonify

app = Flask(__name__)
app.secret_key = 'SUPER_STRONG_NEON_SECRET_KEY_12345' # ✨ Change this to a truly random, complex key! ✨
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
    """Connects to the SQLite database and stores it in g."""
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database schema."""
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                path TEXT NOT NULL,
                url TEXT NOT NULL,
                pre_build_command TEXT,
                build_command TEXT NOT NULL,
                start_command TEXT,
                deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        db.commit()

with app.app_context():
    init_db()

### Flask Routes ###

@app.route('/')
def index():
    db = get_db()
    projects_cursor = db.execute('SELECT * FROM projects ORDER BY deployed_at DESC').fetchall()
    projects = [dict(row) for row in projects_cursor]
    return render_template('index.html', projects=projects)

@app.route('/host', methods=['GET', 'POST'])
def host_project():
    db = get_db()

    if request.method == 'POST':
        project_name = request.form['project_name'].strip()
        pre_build_command = request.form.get('pre_build_command', '').strip()
        build_command = request.form['build_command'].strip()
        start_command = request.form.get('start_command', '').strip()

        if not project_name or not build_command:
            flash('Project Name and Build Command are required!', 'error')
            return redirect(request.url)

        existing_project = db.execute('SELECT id FROM projects WHERE name = ?', (project_name,)).fetchone()
        if existing_project:
            flash(f'Project with name "{project_name}" already exists! Please choose a different name.', 'error')
            return redirect(request.url)

        if 'project_files' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        files = request.files.getlist('project_files')
        if not files or all(f.filename == '' for f in files):
            flash('No selected files. Please upload your project files.', 'error')
            return redirect(request.url)

        project_path = os.path.join(app.config['PROJECTS_FOLDER'], project_name)
        os.makedirs(project_path, exist_ok=True)

        try:
            for file in files:
                if file.filename:
                    file_path = os.path.join(project_path, file.filename)
                    file.save(file_path)

            if pre_build_command:
                flash(f'Running pre-build command: {pre_build_command}', 'info')
                process = subprocess.run(pre_build_command, shell=True, check=True, cwd=project_path, capture_output=True, text=True)
                flash(f'Pre-build output: {process.stdout}', 'info')
                if process.stderr:
                    flash(f'Pre-build errors: {process.stderr}', 'warning')

            flash(f'Running build command: {build_command}', 'info')
            process = subprocess.run(build_command, shell=True, check=True, cwd=project_path, capture_output=True, text=True)
            flash(f'Build output: {process.stdout}', 'info')
            if process.stderr:
                flash(f'Build errors: {process.stderr}', 'warning')

            if start_command:
                flash(f'Running start command: {start_command} (in background)', 'info')
                subprocess.Popen(start_command, shell=True, cwd=project_path)

            project_url = f"http://{request.host}/{project_name}/"

            db.execute(
                'INSERT INTO projects (name, path, url, pre_build_command, build_command, start_command) VALUES (?, ?, ?, ?, ?, ?)',
                (project_name, project_path, project_url, pre_build_command, build_command, start_command)
            )
            db.commit()

            flash(f'Project "{project_name}" deployed successfully! Access at: <a href="{project_url}" target="_blank">{project_url}</a>', 'success')
            return redirect(url_for('index'))

        except subprocess.CalledProcessError as e:
            import shutil
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
            flash(f'Command failed for {e.cmd}:\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}', 'error')
            return redirect(request.url)
        except Exception as e:
            import shutil
            if os.path.exists(project_path):
                shutil.rmtree(project_path)
            flash(f'An unexpected error occurred during deployment: {e}', 'error')
            return redirect(request.url)
    return render_template('host.html')

# Serve static files for each project from its unique path
@app.route('/<project_name>/<path:filename>')
def serve_project_files(project_name, filename):
    db = get_db()
    project = db.execute('SELECT path FROM projects WHERE name = ?', (project_name,)).fetchone()

    if project:
        project_root_path = project['path']
        try:
            return send_from_directory(project_root_path, filename)
        except Exception as e:
            app.logger.error(f"Error serving file {filename} from {project_root_path}: {e}")
            return "File not found or access denied.", 404
    else:
        return "Project not found.", 404

# A route for the root of the project path (e.g., /my-project-name/)
@app.route('/<project_name>/')
def serve_project_root(project_name):
    db = get_db()
    project = db.execute('SELECT path FROM projects WHERE name = ?', (project_name,)).fetchone()

    if project:
        project_root_path = project['path']
        try:
            return send_from_directory(project_root_path, 'index.html')
        except FileNotFoundError:
            return "Index file not found in project root.", 404
        except Exception as e:
            app.logger.error(f"Error serving project root for {project_name}: {e}")
            return "Error serving project.", 500
    else:
        return "Project not found.", 404

# NEW ROUTE: Console for each hosted site
@app.route('/<project_name>/console', methods=['GET', 'POST'])
def project_console(project_name):
    db = get_db()
    project = db.execute('SELECT name, path FROM projects WHERE name = ?', (project_name,)).fetchone()

    if not project:
        return "Project not found.", 404

    output = ""
    error = ""
    if request.method == 'POST':
        command = request.form.get('command')
        if command:
            try:
                # !! DANGER: Running arbitrary commands with shell=True is highly insecure !!
                # !! This is for demonstration based on user request ("no security"). !!
                # !! DO NOT USE IN PRODUCTION ENVIRONMENTS. !!
                process = subprocess.run(
                    command,
                    shell=True,
                    check=True,
                    cwd=project['path'], # Execute command in the project's directory
                    capture_output=True,
                    text=True,
                    timeout=60 # Add a timeout to prevent commands from hanging indefinitely
                )
                output = process.stdout
                error = process.stderr
            except subprocess.CalledProcessError as e:
                output = e.stdout
                error = f"Command failed with exit code {e.returncode}:\n{e.stderr}"
            except subprocess.TimeoutExpired:
                error = "Command timed out after 60 seconds."
            except Exception as e:
                error = f"An unexpected error occurred: {e}"
        else:
            error = "No command provided."

    return render_template('console.html', project_name=project['name'], output=output, error=error)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000) # Listen on all interfaces
