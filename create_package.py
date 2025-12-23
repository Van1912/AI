import zipfile
import os
from datetime import datetime

def create_project_package():
    """Create a zip file containing all project files"""

    # Create package name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"JobScheduling_Package_{timestamp}.zip"

    # Files and directories to include
    files_to_include = [
        # Main files
        'gui_main.py',
        'main.py',
        'config.py',
        'requirements.txt',
        'README.md',
        'INSTALL_GUIDE.txt',
        'run.bat',
        'run.sh',

        # Algorithms
        'Algorithms/simulated_annealing.py',
        'Algorithms/grey_wolf_optimizer.py',
        'Algorithms/base.py',
        'Algorithms/initial_solution.py',

        # Core
        'Core/objective.py',
        'Core/constraints_hard.py',
        'Core/constraints_soft.py',
        'Core/feasibility.py',
        'Core/neighborhood.py',

        # Model
        'Model/models.py',
        'Model/enums.py',

        # Data
        'Data/data_controller.py',
        'Data/schemas.py',
        'Data/Sample/tasks_small.csv',
        'Data/Sample/resources_small.csv',
        'Data/Sample/tasks_medium.csv',
        'Data/Sample/resources_medium.csv',

        # Output
        'Output/exporter.py',

        # Utils
        'Utils/logger.py',
        'Utils/seed.py',
        'Utils/debug_checker.py',

        # Evaluation
        'Evaluation/metrics.py',
        'Evaluation/plots.py',
        'Evaluation/experiments.py',
    ]

    # Create __init__.py files for packages
    packages = [
        'Algorithms',
        'Core',
        'Model',
        'Data',
        'Output',
        'Utils',
        'Evaluation'
    ]

    print("=" * 60)
    print("Creating Job Scheduling Package")
    print("=" * 60)
    print()

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all files
        for file_path in files_to_include:
            if os.path.exists(file_path):
                zipf.write(file_path)
                print(f"[OK] Added: {file_path}")
            else:
                print(f"[SKIP] Missing: {file_path}")

        # Add __init__.py for each package
        for package in packages:
            init_file = f"{package}/__init__.py"
            if os.path.exists(init_file):
                zipf.write(init_file)
                print(f"[OK] Added: {init_file}")
            else:
                # Create empty __init__.py in zip
                zipf.writestr(init_file, "# Package init file\n")
                print(f"[OK] Created: {init_file}")

        # Create empty directories
        zipf.writestr('Data/Uploads/.gitkeep', '')
        zipf.writestr('Output/results/.gitkeep', '')
        print(f"[OK] Created: Data/Uploads/")
        print(f"[OK] Created: Output/results/")

    print()
    print("=" * 60)
    print(f"SUCCESS! Package created: {zip_filename}")
    print("=" * 60)
    print()
    print("To use the package:")
    print("1. Extract the zip file")
    print("2. Run: pip install -r requirements.txt")
    print("3. Run: python gui_main.py")
    print()

    return zip_filename

if __name__ == '__main__':
    create_project_package()
