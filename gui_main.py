import sys
import os
import copy
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QGroupBox, QSpinBox, QDoubleSpinBox, QFileDialog, QMessageBox,
    QDialog, QLineEdit, QDateTimeEdit, QComboBox, QTextEdit,
    QSplitter, QProgressBar, QScrollArea
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QDateTime
from PyQt5.QtGui import QFont, QPalette, QColor

from config import AppConfig
from Core.objective import ObjectiveWeights
from Algorithms.simulated_annealing import SimulatedAnnealingScheduler, SAConfig
from Algorithms.grey_wolf_optimizer import GreyWolfOptimizerScheduler, GWOConfig
from Model.models import Task, Resource
from Data.data_controller import load_tasks_csv, load_resources_csv
from Utils.seed import set_seed

# Import for plotting
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter, HourLocator
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

# Global storage
current_tasks = []
current_resources = []
last_result_sa = None
last_result_gwo = None


class AlgorithmWorker(QThread):
    """Worker thread for running algorithms"""
    finished = pyqtSignal(object, str)  # result, algorithm_name
    error = pyqtSignal(str)

    def __init__(self, algorithm, tasks, resources, params, weights):
        super().__init__()
        self.algorithm = algorithm
        # Use deepcopy to ensure thread safety and prevent UI modification during run
        self.tasks = copy.deepcopy(tasks)
        self.resources = copy.deepcopy(resources)
        self.params = params
        self.weights = weights

    def run(self):
        try:
            set_seed(self.params['random_seed'])

            if self.algorithm == 'sa':
                config = SAConfig(
                    t0=self.params['t0'],
                    t_min=self.params['t_min'],
                    alpha=self.params['alpha'],
                    iters_per_temp=self.params['iters_per_temp']
                )
                scheduler = SimulatedAnnealingScheduler(config, self.weights)
                result = scheduler.solve(self.tasks, self.resources)
                self.finished.emit(result, 'SA')

            elif self.algorithm == 'gwo':
                config = GWOConfig(
                    wolves=self.params['wolves'],
                    iters=self.params['iters']
                )
                scheduler = GreyWolfOptimizerScheduler(config, self.weights)
                result = scheduler.solve(self.tasks, self.resources)
                self.finished.emit(result, 'GWO')

        except Exception as e:
            self.error.emit(str(e))


class GanttCanvas(FigureCanvas):
    """Matplotlib canvas for Gantt chart"""
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(12, 6), facecolor='#FFF9F5')
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)
        self.task_bars = []  # Store bar positions for click detection
        self.click_callback = None

        # Connect click event
        self.mpl_connect('button_press_event', self.on_click)
        self.mpl_connect('scroll_event', self.on_scroll)

    def on_click(self, event):
        """Handle click on Gantt chart"""
        if event.inaxes != self.ax or not self.click_callback:
            return

        for task_id, (y_pos, left, width) in self.task_bars:
            if abs(event.ydata - y_pos) < 0.2 and left <= event.xdata <= left + width:
                self.click_callback(task_id)
                break

    def on_scroll(self, event):
        """Handle scroll event for zooming"""
        if event.inaxes != self.ax:
            return

        if event.button == 'up':
            self.zoom(1)
        elif event.button == 'down':
            self.zoom(-1)

    def zoom(self, direction):
        """Zoom x-axis"""
        xlim = self.ax.get_xlim()
        x_range = xlim[1] - xlim[0]
        center = (xlim[0] + xlim[1]) / 2

        factor = 0.8 if direction > 0 else 1.25
        new_range = x_range * factor

        self.ax.set_xlim(center - new_range / 2, center + new_range / 2)
        self.draw()

    def plot_gantt(self, result, tasks_dict, title="Gantt Chart"):
        """Plot Gantt chart from result"""
        self.ax.clear()
        self.task_bars = []

        if not result or not result.schedule:
            self.ax.text(0.5, 0.5, 'No data to display',
                        ha='center', va='center', transform=self.ax.transAxes)
            self.draw()
            return

        # Pastel colors
        colors = ['#FFD1DC', '#AEC6CF', '#B4E7CE', '#FDFD96', '#E0BBE4',
                 '#FFDAB9', '#C7EFCF', '#E6E6FA', '#FFE5D9', '#C1F0F6']

        # Group by resource
        resource_groups = {}
        for assignment in result.schedule.all_assignments():
            if assignment.resource_id not in resource_groups:
                resource_groups[assignment.resource_id] = []
            resource_groups[assignment.resource_id].append(assignment)

        resources = sorted(resource_groups.keys())
        y_pos = {r: i for i, r in enumerate(resources)}

        # Store coordinates for dependencies
        task_coords = {}

        # Plot bars
        color_idx = 0
        for resource_id, assignments in resource_groups.items():
            y = y_pos[resource_id]

            for assignment in assignments:
                task = tasks_dict.get(assignment.task_id)
                start = assignment.start
                end = assignment.end
                duration_hours = (end - start).total_seconds() / 3600

                # Convert datetime to matplotlib format
                start_num = matplotlib.dates.date2num(start)
                end_num = matplotlib.dates.date2num(end)

                bar = self.ax.barh(y, duration_hours/24, left=start_num,
                                  height=0.4, align='center',
                                  color=colors[color_idx % len(colors)],
                                  edgecolor='white', linewidth=2)

                # Store bar position for click detection
                self.task_bars.append((assignment.task_id, (y, start_num, duration_hours/24)))
                
                # Store coordinates for dependencies
                task_coords[assignment.task_id] = (start_num, end_num, y)

                # Add task label
                self.ax.text(start_num + duration_hours/48, y,
                           f"{assignment.task_id}\n{task.name if task else ''}",
                           ha='center', va='center', fontsize=8, weight='bold')

                # Add due date marker
                if task:
                    due_num = matplotlib.dates.date2num(task.due_date)
                    is_overdue = end > task.due_date
                    l_color = 'r' if is_overdue else '#555555'
                    l_alpha = 0.8 if is_overdue else 0.4
                    l_width = 2 if is_overdue else 1.5
                    self.ax.plot([due_num, due_num], [y-0.3, y+0.3],
                               color=l_color, linestyle='--', linewidth=l_width, alpha=l_alpha)

                color_idx += 1

        # Draw dependency arrows
        for task_id, (start, end, y) in task_coords.items():
            task = tasks_dict.get(task_id)
            if task and task.predecessors:
                for pred_id in task.predecessors:
                    if pred_id in task_coords:
                        p_start, p_end, p_y = task_coords[pred_id]
                        
                        # Draw arrow from predecessor end to current start
                        self.ax.annotate("",
                            xy=(start, y), 
                            xytext=(p_end, p_y),
                            arrowprops=dict(arrowstyle="->", 
                                          connectionstyle="arc3,rad=0.2",
                                          color="#555555", alpha=0.5, linewidth=1,
                                          linestyle='--')
                        )

        # Format x-axis
        self.ax.xaxis.set_major_formatter(DateFormatter('%m/%d %H:%M'))
        self.ax.xaxis.set_major_locator(HourLocator(interval=2))
        self.fig.autofmt_xdate()

        # Labels and title
        self.ax.set_yticks(list(y_pos.values()))
        self.ax.set_yticklabels(resources)
        self.ax.set_xlabel('Timeline', fontsize=12, weight='bold')
        self.ax.set_ylabel('Resources', fontsize=12, weight='bold')
        self.ax.set_title(title, fontsize=14, weight='bold', pad=20)
        self.ax.grid(True, alpha=0.3, axis='x')

        # Add legend
        legend_elements = [
            Line2D([0], [0], color='r', lw=2, linestyle='--', label='Overdue'),
            Line2D([0], [0], color='#555555', lw=1.5, linestyle='--', label='Due Date')
        ]
        self.ax.legend(handles=legend_elements, loc='upper right')

        self.fig.tight_layout()
        self.draw()


class ConvergenceCanvas(FigureCanvas):
    """Matplotlib canvas for convergence plot"""
    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 4), facecolor='#FFF9F5')
        super().__init__(self.fig)
        self.setParent(parent)
        self.ax = self.fig.add_subplot(111)

    def plot_convergence(self, sa_history, gwo_history):
        """Plot convergence comparison"""
        self.ax.clear()

        if sa_history:
            self.ax.plot(sa_history, label='SA', color='#AEC6CF', linewidth=2)
            # Annotate best cost
            min_val = min(sa_history)
            min_idx = sa_history.index(min_val)
            self.ax.annotate(f'{min_val:.1f}', xy=(min_idx, min_val),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, color='#4A4A4A', weight='bold')

        if gwo_history:
            self.ax.plot(gwo_history, label='GWO', color='#E0BBE4', linewidth=2)
            # Annotate best cost
            min_val = min(gwo_history)
            min_idx = gwo_history.index(min_val)
            self.ax.annotate(f'{min_val:.1f}', xy=(min_idx, min_val),
                           xytext=(5, 5), textcoords='offset points',
                           fontsize=8, color='#4A4A4A', weight='bold')

        self.ax.set_xlabel('Iteration', fontsize=12, weight='bold')
        self.ax.set_ylabel('Cost', fontsize=12, weight='bold')
        self.ax.set_title('Convergence Comparison', fontsize=14, weight='bold')
        if sa_history or gwo_history:
            self.ax.legend(loc='best')
        self.ax.grid(True, alpha=0.3)

        self.fig.tight_layout()
        self.draw()


class TaskEditDialog(QDialog):
    """Dialog for editing task"""
    def __init__(self, parent=None, task=None):
        super().__init__(parent)
        self.task = task
        self.is_new = task is None
        self.init_ui()

        if task:
            self.load_task_data()

    def init_ui(self):
        self.setWindowTitle("Add Task" if self.is_new else "Edit Task")
        self.setModal(True)
        self.resize(500, 600)

        layout = QVBoxLayout()

        # Task ID
        layout.addWidget(QLabel("Task ID:"))
        self.id_edit = QLineEdit()
        layout.addWidget(self.id_edit)

        # Task Name
        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # Duration
        layout.addWidget(QLabel("Duration (minutes):"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 10000)
        self.duration_spin.setValue(60)
        layout.addWidget(self.duration_spin)

        # Release Time
        layout.addWidget(QLabel("Release Time:"))
        self.release_edit = QDateTimeEdit()
        self.release_edit.setCalendarPopup(True)
        self.release_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.release_edit.setDateTime(QDateTime.currentDateTime())
        layout.addWidget(self.release_edit)

        # Due Date
        layout.addWidget(QLabel("Due Date:"))
        self.due_edit = QDateTimeEdit()
        self.due_edit.setCalendarPopup(True)
        self.due_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.due_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        layout.addWidget(self.due_edit)

        # Priority
        layout.addWidget(QLabel("Priority:"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 100)
        self.priority_spin.setValue(1)
        layout.addWidget(self.priority_spin)

        # Required Type
        layout.addWidget(QLabel("Required Type:"))
        self.type_edit = QLineEdit()
        self.type_edit.setText("ANY")
        layout.addWidget(self.type_edit)

        # Predecessors
        layout.addWidget(QLabel("Predecessors (T1|T2):"))
        layout.addWidget(QLabel("Predecessors (IDs separated by ',' or '|'):"))
        # Example: T1, T2 (Task must wait for T1 and T2 to finish)
        self.pred_edit = QLineEdit()
        layout.addWidget(self.pred_edit)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.cancel_btn = QPushButton("Cancel")

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_task_data(self):
        """Load task data into form"""
        self.id_edit.setText(self.task.id)
        self.name_edit.setText(self.task.name)
        self.duration_spin.setValue(self.task.duration_min)

        release_qdt = QDateTime()
        release_qdt.setDate(self.task.release_time.date())
        release_qdt.setTime(self.task.release_time.time())
        self.release_edit.setDateTime(release_qdt)

        due_qdt = QDateTime()
        due_qdt.setDate(self.task.due_date.date())
        due_qdt.setTime(self.task.due_date.time())
        self.due_edit.setDateTime(due_qdt)

        self.priority_spin.setValue(self.task.priority)
        self.type_edit.setText(self.task.required_type)
        self.pred_edit.setText('|'.join(self.task.predecessors))

    def get_task_data(self):
        """Get task data from form"""
        release_dt = self.release_edit.dateTime().toPyDateTime()
        due_dt = self.due_edit.dateTime().toPyDateTime()

        predecessors = []
        if self.pred_edit.text().strip():
            predecessors = [p.strip() for p in self.pred_edit.text().split('|')]
        text = self.pred_edit.text().strip()
        if text:
            # Allow both comma and pipe as separators for better UX
            text = text.replace(',', '|')
            predecessors = [p.strip() for p in text.split('|') if p.strip()]

        return Task(
            task_id=self.id_edit.text(),
            name=self.name_edit.text(),
            duration_min=self.duration_spin.value(),
            release_time=release_dt,
            due_date=due_dt,
            priority=self.priority_spin.value(),
            required_type=self.type_edit.text(),
            predecessors=predecessors
        )


class ResourceEditDialog(QDialog):
    """Dialog for editing resource"""
    def __init__(self, parent=None, resource=None):
        super().__init__(parent)
        self.resource = resource
        self.is_new = resource is None
        self.init_ui()

        if resource:
            self.load_resource_data()

    def init_ui(self):
        self.setWindowTitle("Add Resource" if self.is_new else "Edit Resource")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout()

        # Resource ID
        layout.addWidget(QLabel("Resource ID:"))
        self.id_edit = QLineEdit()
        layout.addWidget(self.id_edit)

        # Resource Name
        layout.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # Type
        layout.addWidget(QLabel("Type:"))
        self.type_edit = QLineEdit()
        layout.addWidget(self.type_edit)

        # Capacity
        layout.addWidget(QLabel("Capacity:"))
        self.capacity_spin = QSpinBox()
        self.capacity_spin.setRange(1, 1000)
        self.capacity_spin.setValue(1)
        layout.addWidget(self.capacity_spin)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("💾 Save")
        self.cancel_btn = QPushButton("Cancel")

        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_resource_data(self):
        self.id_edit.setText(self.resource.id)
        self.name_edit.setText(self.resource.name)
        self.type_edit.setText(self.resource.rtype)
        self.capacity_spin.setValue(self.resource.capacity)

    def get_resource_data(self):
        return Resource(
            resource_id=self.id_edit.text(),
            name=self.name_edit.text(),
            rtype=self.type_edit.text(),
            capacity=self.capacity_spin.value()
        )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.apply_pastel_theme()
        self.load_sample_data()

    def init_ui(self):
        self.setWindowTitle("🗓️ Job Scheduling System - SA & GWO")
        self.setGeometry(100, 100, 1600, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout()

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)

        # Left panel
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes
        splitter.setSizes([400, 1200])

        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)

    def create_left_panel(self):
        """Create left panel with data management and parameters"""
        panel = QWidget()
        layout = QVBoxLayout()

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout()

        # Data Management Section
        data_group = self.create_data_management_group()
        scroll_layout.addWidget(data_group)

        # Common Parameters Section
        common_group = self.create_common_params_group()
        scroll_layout.addWidget(common_group)

        # SA Parameters Section
        sa_group = self.create_sa_params_group()
        scroll_layout.addWidget(sa_group)

        # GWO Parameters Section
        gwo_group = self.create_gwo_params_group()
        scroll_layout.addWidget(gwo_group)

        scroll_layout.addStretch()
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)

        layout.addWidget(scroll)
        panel.setLayout(layout)

        return panel

    def create_data_management_group(self):
        """Create data management group"""
        group = QGroupBox("📊 Data Management")
        layout = QVBoxLayout()

        # Load Sample buttons
        layout.addWidget(QLabel("Load Sample Data:"))
        btn_layout = QHBoxLayout()

        self.load_small_btn = QPushButton("Small Dataset")
        self.load_medium_btn = QPushButton("Medium Dataset")
        self.load_large_btn = QPushButton("Large Dataset")

        self.load_small_btn.clicked.connect(lambda: self.load_sample('small'))
        self.load_medium_btn.clicked.connect(lambda: self.load_sample('medium'))
        self.load_large_btn.clicked.connect(lambda: self.load_sample('large'))

        btn_layout.addWidget(self.load_small_btn)
        btn_layout.addWidget(self.load_medium_btn)
        btn_layout.addWidget(self.load_large_btn)
        layout.addLayout(btn_layout)

        # Upload files
        layout.addWidget(QLabel("\nUpload Your Data:"))

        self.upload_tasks_btn = QPushButton("📤 Upload Tasks CSV")
        self.upload_resources_btn = QPushButton("📤 Upload Resources CSV")

        self.upload_tasks_btn.clicked.connect(lambda: self.upload_file('tasks'))
        self.upload_resources_btn.clicked.connect(lambda: self.upload_file('resources'))

        layout.addWidget(self.upload_tasks_btn)
        layout.addWidget(self.upload_resources_btn)

        # Data summary
        layout.addWidget(QLabel("\nData Summary:"))
        self.tasks_count_label = QLabel("Tasks: 0")
        self.resources_count_label = QLabel("Resources: 0")
        layout.addWidget(self.tasks_count_label)
        layout.addWidget(self.resources_count_label)

        # View/Edit data button
        self.view_data_btn = QPushButton("👁️ View/Edit Data")
        self.view_data_btn.clicked.connect(self.show_data_dialog)
        layout.addWidget(self.view_data_btn)

        group.setLayout(layout)
        return group

    def create_common_params_group(self):
        """Create common parameters group"""
        group = QGroupBox("⚙️ Common Settings")
        layout = QVBoxLayout()

        # Random Seed
        layout.addWidget(QLabel("Random Seed:"))
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 99999)
        self.seed_spin.setValue(42)
        layout.addWidget(self.seed_spin)

        # Weights
        layout.addWidget(QLabel("Weight Tardiness:"))
        self.w_tardiness_spin = QDoubleSpinBox()
        self.w_tardiness_spin.setRange(0, 100)
        self.w_tardiness_spin.setValue(5.0)
        self.w_tardiness_spin.setSingleStep(0.1)
        layout.addWidget(self.w_tardiness_spin)

        layout.addWidget(QLabel("Weight Makespan:"))
        self.w_makespan_spin = QDoubleSpinBox()
        self.w_makespan_spin.setRange(0, 100)
        self.w_makespan_spin.setValue(1.0)
        self.w_makespan_spin.setSingleStep(0.1)
        layout.addWidget(self.w_makespan_spin)

        layout.addWidget(QLabel("Weight Earliness:"))
        self.w_earliness_spin = QDoubleSpinBox()
        self.w_earliness_spin.setRange(0, 100)
        self.w_earliness_spin.setValue(0.0)
        self.w_earliness_spin.setSingleStep(0.1)
        layout.addWidget(self.w_earliness_spin)

        group.setLayout(layout)
        return group

    def create_sa_params_group(self):
        """Create SA parameters group"""
        group = QGroupBox("🔥 Simulated Annealing")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Initial Temperature (T₀):"))
        self.sa_t0_spin = QDoubleSpinBox()
        self.sa_t0_spin.setRange(1, 1000000000)
        self.sa_t0_spin.setValue(200.0)
        layout.addWidget(self.sa_t0_spin)

        layout.addWidget(QLabel("Min Temperature (T_min):"))
        self.sa_tmin_spin = QDoubleSpinBox()
        self.sa_tmin_spin.setRange(0.01, 100)
        self.sa_tmin_spin.setValue(0.5)
        self.sa_tmin_spin.setSingleStep(0.1)
        layout.addWidget(self.sa_tmin_spin)

        layout.addWidget(QLabel("Cooling Rate (α):"))
        self.sa_alpha_spin = QDoubleSpinBox()
        self.sa_alpha_spin.setRange(0.01, 0.99)
        self.sa_alpha_spin.setValue(0.95)
        self.sa_alpha_spin.setSingleStep(0.01)
        layout.addWidget(self.sa_alpha_spin)

        layout.addWidget(QLabel("Iterations per Temp:"))
        self.sa_iters_spin = QSpinBox()
        self.sa_iters_spin.setRange(1, 1000000)
        self.sa_iters_spin.setValue(200)
        layout.addWidget(self.sa_iters_spin)

        group.setLayout(layout)
        return group

    def create_gwo_params_group(self):
        """Create GWO parameters group"""
        group = QGroupBox("🐺 Grey Wolf Optimizer")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Number of Wolves:"))
        self.gwo_wolves_spin = QSpinBox()
        self.gwo_wolves_spin.setRange(5, 500)
        self.gwo_wolves_spin.setRange(5, 2000)
        self.gwo_wolves_spin.setValue(25)
        layout.addWidget(self.gwo_wolves_spin)

        layout.addWidget(QLabel("Max Iterations:"))
        self.gwo_iters_spin = QSpinBox()
        self.gwo_iters_spin.setRange(10, 100000)
        self.gwo_iters_spin.setValue(150)
        layout.addWidget(self.gwo_iters_spin)

        group.setLayout(layout)
        return group

    def create_right_panel(self):
        """Create right panel with results and charts"""
        panel = QWidget()
        main_layout = QVBoxLayout(panel)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area to prevent content clipping
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        # Run buttons
        btn_group = QGroupBox("🚀 Run Algorithms")
        btn_layout = QHBoxLayout()

        self.run_sa_btn = QPushButton("▶️ Run SA")
        self.run_gwo_btn = QPushButton("▶️ Run GWO")
        self.compare_btn = QPushButton("🔄 Compare Both")

        self.run_sa_btn.clicked.connect(lambda: self.run_algorithm('sa'))
        self.run_gwo_btn.clicked.connect(lambda: self.run_algorithm('gwo'))
        self.compare_btn.clicked.connect(self.compare_algorithms)

        btn_layout.addWidget(self.run_sa_btn)
        btn_layout.addWidget(self.run_gwo_btn)
        btn_layout.addWidget(self.compare_btn)

        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Results display
        results_group = QGroupBox("📈 Results")
        results_layout = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(250)
        self.results_text.setMinimumHeight(180)
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Create Tab widget for charts
        self.results_tabs = QTabWidget()
        layout.addWidget(self.results_tabs)
        
        # Gantt chart tab
        gantt_tab = QWidget()
        gantt_layout = QVBoxLayout(gantt_tab)

        # Gantt controls
        gantt_ctrl_layout = QHBoxLayout()
        self.gantt_algo_combo = QComboBox()
        self.gantt_algo_combo.addItems(["Select Algorithm", "SA", "GWO"])
        self.gantt_algo_combo.currentTextChanged.connect(self.update_gantt_chart)

        self.export_btn = QPushButton("💾 Export CSV")
        self.export_btn.clicked.connect(self.export_results)

        self.save_img_btn = QPushButton("📷 Save Image")
        self.save_img_btn.clicked.connect(self.save_gantt_image)

        self.zoom_in_btn = QPushButton("➕ Zoom In")
        self.zoom_in_btn.clicked.connect(lambda: self.gantt_canvas.zoom(1))

        self.zoom_out_btn = QPushButton("➖ Zoom Out")
        self.zoom_out_btn.clicked.connect(lambda: self.gantt_canvas.zoom(-1))

        gantt_ctrl_layout.addWidget(self.gantt_algo_combo)
        gantt_ctrl_layout.addWidget(self.export_btn)
        gantt_ctrl_layout.addWidget(self.save_img_btn)
        gantt_ctrl_layout.addWidget(self.zoom_in_btn)
        gantt_ctrl_layout.addWidget(self.zoom_out_btn)
        gantt_ctrl_layout.addStretch()

        gantt_layout.addLayout(gantt_ctrl_layout)

        # Gantt canvas
        self.gantt_canvas = GanttCanvas()
        self.gantt_canvas.click_callback = self.on_gantt_task_clicked
        self.gantt_canvas.setMinimumHeight(450)
        gantt_layout.addWidget(self.gantt_canvas)
        
        self.results_tabs.addTab(gantt_tab, "📊 Gantt Chart")

        # Schedule Table Tab
        schedule_tab = QWidget()
        schedule_layout = QVBoxLayout(schedule_tab)
        
        self.schedule_table = QTableWidget()
        schedule_layout.addWidget(self.schedule_table)
        
        self.results_tabs.addTab(schedule_tab, "📅 THỜI KHÓA BIỂU")


        # Convergence chart
        self.convergence_group = QGroupBox("📉 Convergence Comparison")
        convergence_layout = QVBoxLayout()

        self.convergence_canvas = ConvergenceCanvas()
        self.convergence_canvas.setMinimumHeight(350)
        convergence_layout.addWidget(self.convergence_canvas)

        self.convergence_group.setLayout(convergence_layout)
        self.convergence_group.setVisible(False)
        layout.addWidget(self.convergence_group)

        layout.addStretch()
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        return panel

    def apply_pastel_theme(self):
        """Apply pastel color theme"""
        palette = QPalette()

        # Main colors
        palette.setColor(QPalette.Window, QColor(255, 249, 245))  # FFF9F5
        palette.setColor(QPalette.WindowText, QColor(74, 74, 74))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(230, 230, 250))
        palette.setColor(QPalette.Button, QColor(174, 198, 207))  # Pastel blue
        palette.setColor(QPalette.ButtonText, QColor(74, 74, 74))

        self.setPalette(palette)

        # Stylesheet for specific widgets
        style = """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #E8E8E8;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #AEC6CF;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
                color: #4A4A4A;
            }
            QPushButton:hover {
                background-color: #E0BBE4;
            }
            QPushButton:pressed {
                background-color: #B4E7CE;
            }
            QSpinBox, QDoubleSpinBox, QLineEdit, QComboBox, QDateTimeEdit {
                border: 2px solid #E8E8E8;
                border-radius: 5px;
                padding: 5px;
                background-color: #FFF9F5;
            }
            QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus, QComboBox:focus {
                border: 2px solid #AEC6CF;
            }
            QTextEdit {
                border: 2px solid #E8E8E8;
                border-radius: 5px;
                background-color: white;
            }
            QTableWidget {
                border: 2px solid #E8E8E8;
                border-radius: 5px;
                background-color: white;
                alternate-background-color: #E6E6FA;
            }
            QHeaderView::section {
                background-color: #E0BBE4;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
            QProgressBar {
                border: 2px solid #E8E8E8;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #B4E7CE;
            }
        """
        self.setStyleSheet(style)

    def load_sample_data(self):
        """Load sample data on startup"""
        pass

    def load_sample(self, sample_type):
        """Load sample data"""
        global current_tasks, current_resources, last_result_sa, last_result_gwo

        try:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
            # Handle the specific filename for the large task set
            if sample_type == 'large':
                tasks_filename = 'task_large.csv'
            else:
                tasks_filename = f'tasks_{sample_type}.csv'

            tasks_file = os.path.join(base_path, 'Data', 'Sample', tasks_filename)
            resources_file = os.path.join(base_path, 'Data', 'Sample', f'resources_{sample_type}.csv')

            current_tasks = load_tasks_csv(tasks_file)
            current_resources = load_resources_csv(resources_file)

            # Reset results when loading new data to avoid comparing wrong datasets
            last_result_sa = None
            last_result_gwo = None

            self.update_data_summary()
            self.auto_tune_params()
            QMessageBox.information(self, "Success",
                                   f"Loaded {sample_type} dataset successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load sample data: {str(e)}")

    def upload_file(self, file_type):
        """Upload CSV file"""
        global current_tasks, current_resources, last_result_sa, last_result_gwo

        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {file_type.capitalize()} File", "",
            "CSV Files (*.csv);;Excel Files (*.xlsx *.xls)"
        )

        if not file_path:
            return

        try:
            if file_type == 'tasks':
                if file_path.endswith('.csv'):
                    current_tasks = load_tasks_csv(file_path)
                else:
                    # Convert Excel to CSV
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    temp_csv = 'Data/Uploads/temp_tasks.csv'
                    os.makedirs('Data/Uploads', exist_ok=True)
                    df.to_csv(temp_csv, index=False)
                    current_tasks = load_tasks_csv(temp_csv)

            else:  # resources
                if file_path.endswith('.csv'):
                    current_resources = load_resources_csv(file_path)
                else:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    temp_csv = 'Data/Uploads/temp_resources.csv'
                    os.makedirs('Data/Uploads', exist_ok=True)
                    df.to_csv(temp_csv, index=False)
                    current_resources = load_resources_csv(temp_csv)

            # Reset results when loading new data
            last_result_sa = None
            last_result_gwo = None

            self.update_data_summary()
            self.auto_tune_params()
            QMessageBox.information(self, "Success",
                                   f"{file_type.capitalize()} file loaded successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

    def update_data_summary(self):
        """Update data summary labels"""
        self.tasks_count_label.setText(f"Tasks: {len(current_tasks)}")
        self.resources_count_label.setText(f"Resources: {len(current_resources)}")

    def auto_tune_params(self):
        """Automatically adjust parameters based on data size"""
        n_tasks = len(current_tasks)
        if n_tasks == 0:
            return

        # Heuristic tuning based on dataset size
        if n_tasks > 200:  # Large dataset
            self.sa_t0_spin.setValue(100000.0)
            self.sa_iters_spin.setValue(2000)
            self.gwo_wolves_spin.setValue(100)
            self.gwo_iters_spin.setValue(500)
        elif n_tasks > 50:  # Medium dataset
            self.sa_t0_spin.setValue(5000.0)
            self.sa_iters_spin.setValue(500)
            self.gwo_wolves_spin.setValue(50)
            self.gwo_iters_spin.setValue(300)
        else:  # Small dataset (Default)
            self.sa_t0_spin.setValue(200.0)
            self.sa_iters_spin.setValue(200)
            self.gwo_wolves_spin.setValue(25)
            self.gwo_iters_spin.setValue(150)

    def show_data_dialog(self):
        """Show data management dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Data Management")
        dialog.resize(1000, 600)

        layout = QVBoxLayout()

        # Tab widget
        tabs = QTabWidget()

        # Tasks tab
        tasks_tab = self.create_tasks_table()
        tabs.addTab(tasks_tab, "Tasks")

        # Resources tab
        resources_tab = self.create_resources_table()
        tabs.addTab(resources_tab, "Resources")

        layout.addWidget(tabs)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    def create_tasks_table(self):
        """Create tasks table widget"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Add button
        add_btn = QPushButton("➕ Add Task")
        add_btn.clicked.connect(self.add_task)
        layout.addWidget(add_btn)

        # Table
        table = QTableWidget()
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            "ID", "Name", "Duration", "Release", "Due", "Priority", "Type", "Predecessors", "Actions"
        ])

        self.tasks_table = table
        self.refresh_tasks_table()

        layout.addWidget(table)
        widget.setLayout(layout)

        return widget

    def refresh_tasks_table(self):
        """Refresh tasks table"""
        self.tasks_table.setRowCount(len(current_tasks))

        for i, task in enumerate(current_tasks):
            self.tasks_table.setItem(i, 0, QTableWidgetItem(task.id))
            self.tasks_table.setItem(i, 1, QTableWidgetItem(task.name))
            self.tasks_table.setItem(i, 2, QTableWidgetItem(str(task.duration_min)))
            self.tasks_table.setItem(i, 3, QTableWidgetItem(task.release_time.strftime("%Y-%m-%d %H:%M")))
            self.tasks_table.setItem(i, 4, QTableWidgetItem(task.due_date.strftime("%Y-%m-%d %H:%M")))
            self.tasks_table.setItem(i, 5, QTableWidgetItem(str(task.priority)))
            self.tasks_table.setItem(i, 6, QTableWidgetItem(task.required_type))
            self.tasks_table.setItem(i, 7, QTableWidgetItem('|'.join(task.predecessors)))

            # Action buttons
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)

            edit_btn = QPushButton("✏️")
            delete_btn = QPushButton("🗑️")

            edit_btn.clicked.connect(lambda checked, t=task: self.edit_task(t))
            delete_btn.clicked.connect(lambda checked, tid=task.id: self.delete_task(tid))

            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_widget.setLayout(btn_layout)

            self.tasks_table.setCellWidget(i, 8, btn_widget)

        self.tasks_table.resizeColumnsToContents()

    def create_resources_table(self):
        """Create resources table widget"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Add button
        add_btn = QPushButton("➕ Add Resource")
        add_btn.clicked.connect(self.add_resource)
        layout.addWidget(add_btn)

        # Table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["ID", "Name", "Type", "Capacity", "Actions"])

        self.resources_table = table
        self.refresh_resources_table()

        layout.addWidget(table)
        widget.setLayout(layout)

        return widget

    def refresh_resources_table(self):
        """Refresh resources table"""
        self.resources_table.setRowCount(len(current_resources))

        for i, resource in enumerate(current_resources):
            self.resources_table.setItem(i, 0, QTableWidgetItem(resource.id))
            self.resources_table.setItem(i, 1, QTableWidgetItem(resource.name))
            self.resources_table.setItem(i, 2, QTableWidgetItem(resource.rtype))
            self.resources_table.setItem(i, 3, QTableWidgetItem(str(resource.capacity)))

            # Action buttons
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(0, 0, 0, 0)

            edit_btn = QPushButton("✏️")
            delete_btn = QPushButton("🗑️")

            edit_btn.clicked.connect(lambda checked, r=resource: self.edit_resource(r))
            delete_btn.clicked.connect(lambda checked, rid=resource.id: self.delete_resource(rid))

            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(delete_btn)
            btn_widget.setLayout(btn_layout)

            self.resources_table.setCellWidget(i, 4, btn_widget)

        self.resources_table.resizeColumnsToContents()

    def add_task(self):
        """Add new task"""
        dialog = TaskEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_task = dialog.get_task_data()

            # Check for duplicate ID
            if any(t.id == new_task.id for t in current_tasks):
                QMessageBox.warning(self, "Duplicate ID", f"Task ID '{new_task.id}' already exists!")
                return

            current_tasks.append(new_task)
            self.refresh_tasks_table()
            self.update_data_summary()

    def edit_task(self, task):
        """Edit existing task"""
        dialog = TaskEditDialog(self, task)
        if dialog.exec_() == QDialog.Accepted:
            updated_task = dialog.get_task_data()
            # Find and replace
            for i, t in enumerate(current_tasks):
                if t.id == task.id:
                    current_tasks[i] = updated_task
                    break
            
            # Update existing results to reflect changes immediately
            for result in [last_result_sa, last_result_gwo]:
                if result and result.schedule:
                    for assignment in result.schedule.all_assignments():
                        if assignment.task_id == task.id:
                            assignment.task_id = updated_task.id
                            assignment.end = assignment.start + timedelta(minutes=updated_task.duration_min)

            self.refresh_tasks_table()
            self.update_gantt_chart()

    def delete_task(self, task_id):
        """Delete task"""
        reply = QMessageBox.question(self, "Delete Task",
                                    f"Are you sure you want to delete task {task_id}?",
                                    QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            global current_tasks
            current_tasks = [t for t in current_tasks if t.id != task_id]
            self.refresh_tasks_table()
            self.update_data_summary()

    def add_resource(self):
        """Add new resource"""
        dialog = ResourceEditDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_resource = dialog.get_resource_data()

            # Check for duplicate ID
            if any(r.id == new_resource.id for r in current_resources):
                QMessageBox.warning(self, "Duplicate ID", f"Resource ID '{new_resource.id}' already exists!")
                return

            current_resources.append(new_resource)
            self.refresh_resources_table()
            self.update_data_summary()

    def edit_resource(self, resource):
        """Edit existing resource"""
        dialog = ResourceEditDialog(self, resource)
        if dialog.exec_() == QDialog.Accepted:
            updated_resource = dialog.get_resource_data()
            for i, r in enumerate(current_resources):
                if r.id == resource.id:
                    current_resources[i] = updated_resource
                    break
            self.refresh_resources_table()

    def delete_resource(self, resource_id):
        """Delete resource"""
        reply = QMessageBox.question(self, "Delete Resource",
                                    f"Are you sure you want to delete resource {resource_id}?",
                                    QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            global current_resources
            current_resources = [r for r in current_resources if r.id != resource_id]
            self.refresh_resources_table()
            self.update_data_summary()

    def on_gantt_task_clicked(self, task_id):
        """Handle click on Gantt chart task"""
        task = next((t for t in current_tasks if t.id == task_id), None)
        if task:
            self.edit_task(task)

    def get_algorithm_params(self):
        """Get algorithm parameters from UI"""
        return {
            'random_seed': self.seed_spin.value(),
            't0': self.sa_t0_spin.value(),
            't_min': self.sa_tmin_spin.value(),
            'alpha': self.sa_alpha_spin.value(),
            'iters_per_temp': self.sa_iters_spin.value(),
            'wolves': self.gwo_wolves_spin.value(),
            'iters': self.gwo_iters_spin.value()
        }

    def get_weights(self):
        """Get objective weights"""
        return ObjectiveWeights(
            w_tardiness=self.w_tardiness_spin.value(),
            w_makespan=self.w_makespan_spin.value(),
            w_earliness=self.w_earliness_spin.value()
        )

    def run_algorithm(self, algorithm):
        """Run algorithm in background thread"""
        global current_tasks, current_resources

        if not current_tasks:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        # Disable buttons
        self.run_sa_btn.setEnabled(False)
        self.run_gwo_btn.setEnabled(False)
        self.compare_btn.setEnabled(False)

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Create worker
        params = self.get_algorithm_params()
        weights = self.get_weights()

        self.worker = AlgorithmWorker(algorithm, current_tasks, current_resources,
                                     params, weights)
        self.worker.finished.connect(self.on_algorithm_finished)
        self.worker.error.connect(self.on_algorithm_error)
        self.worker.start()

    def compare_algorithms(self):
        """Run both algorithms"""
        global current_tasks, current_resources

        if not current_tasks:
            QMessageBox.warning(self, "Warning", "Please load data first!")
            return

        # Disable buttons
        self.run_sa_btn.setEnabled(False)
        self.run_gwo_btn.setEnabled(False)
        self.compare_btn.setEnabled(False)

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        # Run SA first
        params = self.get_algorithm_params()
        weights = self.get_weights()

        self.worker_sa = AlgorithmWorker('sa', current_tasks, current_resources,
                                        params, weights)
        self.worker_sa.finished.connect(self.on_sa_finished_for_comparison)
        self.worker_sa.error.connect(self.on_algorithm_error)
        self.worker_sa.start()

    def on_sa_finished_for_comparison(self, result, algo_name):
        """SA finished, now run GWO"""
        global last_result_sa
        last_result_sa = result

        # Run GWO
        params = self.get_algorithm_params()
        weights = self.get_weights()

        self.worker_gwo = AlgorithmWorker('gwo', current_tasks, current_resources,
                                         params, weights)
        self.worker_gwo.finished.connect(self.on_comparison_finished)
        self.worker_gwo.error.connect(self.on_algorithm_error)
        self.worker_gwo.start()

    def on_comparison_finished(self, result, algo_name):
        """Both algorithms finished"""
        global last_result_gwo
        last_result_gwo = result

        # Enable buttons
        self.run_sa_btn.setEnabled(True)
        self.run_gwo_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Display results
        self.display_comparison_results()

        # Show convergence
        self.convergence_canvas.plot_convergence(
            last_result_sa.history,
            last_result_gwo.history
        )
        self.convergence_group.setVisible(True)

        QMessageBox.information(self, "Success", "Comparison completed!")

    def on_algorithm_finished(self, result, algo_name):
        """Algorithm finished callback"""
        global last_result_sa, last_result_gwo
        
        if algo_name == 'SA':
            last_result_sa = result
        else:
            last_result_gwo = result

        # Enable buttons
        self.run_sa_btn.setEnabled(True)
        self.run_gwo_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        # Display results
        self.display_single_result(result, algo_name)

        # Update Gantt
        if self.gantt_algo_combo.currentText() != algo_name:
            self.gantt_algo_combo.setCurrentText(algo_name)
        else:
            self.update_gantt_chart()
            
        # Update Convergence Plot
        # Use history from both algorithms if available to maintain comparison view
        sa_hist = last_result_sa.history if last_result_sa else None
        gwo_hist = last_result_gwo.history if last_result_gwo else None
        
        self.convergence_canvas.plot_convergence(sa_hist, gwo_hist)
        self.convergence_group.setVisible(True)

        self.update_schedule_table(result)

        QMessageBox.information(self, "Success", f"{algo_name} completed successfully!")

    def on_algorithm_error(self, error_msg):
        """Algorithm error callback"""
        self.run_sa_btn.setEnabled(True)
        self.run_gwo_btn.setEnabled(True)
        self.compare_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

        QMessageBox.critical(self, "Error", f"Algorithm failed: {error_msg}")

    def update_schedule_table(self, result):
        """Populate the schedule table and print to console"""
        if not result or not result.schedule:
            self.schedule_table.setRowCount(0)
            return

        tasks_dict = {t.id: t for t in current_tasks}
        resources_dict = {r.id: r for r in current_resources}
        
        # Sort assignments by resource, then start time
        all_assignments = sorted(result.schedule.all_assignments(), key=lambda a: (a.resource_id, a.start))

        # --- Print to Console ---
        headers = ["Resource", "Task", "Task Name", "Start Time", "End Time", "Due Date", "Priority"]
        col_widths = {h: len(h) for h in headers}
        
        table_data = []
        for assignment in all_assignments:
            task = tasks_dict.get(assignment.task_id)
            resource = resources_dict.get(assignment.resource_id)
            if not task or not resource:
                continue

            row_data = {
                "Resource": resource.name,
                "Task": task.id,
                "Task Name": task.name,
                "Start Time": assignment.start.strftime('%Y-%m-%d %H:%M'),
                "End Time": assignment.end.strftime('%Y-%m-%d %H:%M'),
                "Due Date": task.due_date.strftime('%Y-%m-%d %H:%M'),
                "Priority": str(task.priority)
            }
            table_data.append(row_data)

            # Update column widths
            for h in headers:
                col_widths[h] = max(col_widths[h], len(row_data[h]))

        # Create separator line
        separator = "+"+"+".join("-" * (col_widths[h] + 2) for h in headers) + "+"
        
        # Create header line
        header_line = "| " + " | ".join(h.ljust(col_widths[h]) for h in headers) + " |"

        print("\n--- THỜI KHÓA BIỂU ---")
        print(separator)
        print(header_line)
        print(separator)

        # Print data rows
        if not table_data:
            print("|" + " " * (len(separator) - 2) + "|")
            print("|" + "No schedule data to display".center(len(separator) - 2) + "|")
            print("|" + " " * (len(separator) - 2) + "|")
        else:
            for row in table_data:
                line = "| " + " | ".join(row[h].ljust(col_widths[h]) for h in headers) + " |"
                print(line)
        print(separator)
        print("---\n")


        # --- Populate GUI Table ---
        self.schedule_table.setRowCount(len(all_assignments))
        self.schedule_table.setColumnCount(len(headers))
        self.schedule_table.setHorizontalHeaderLabels(headers)
        
        for i, assignment in enumerate(all_assignments):
            task = tasks_dict.get(assignment.task_id)
            resource = resources_dict.get(assignment.resource_id)
            if not task or not resource:
                continue

            self.schedule_table.setItem(i, 0, QTableWidgetItem(resource.name))
            self.schedule_table.setItem(i, 1, QTableWidgetItem(task.id))
            self.schedule_table.setItem(i, 2, QTableWidgetItem(task.name))
            self.schedule_table.setItem(i, 3, QTableWidgetItem(assignment.start.strftime('%Y-%m-%d %H:%M')))
            self.schedule_table.setItem(i, 4, QTableWidgetItem(assignment.end.strftime('%Y-%m-%d %H:%M')))
            self.schedule_table.setItem(i, 5, QTableWidgetItem(task.due_date.strftime('%Y-%m-%d %H:%M')))
            self.schedule_table.setItem(i, 6, QTableWidgetItem(str(task.priority)))
            
        self.schedule_table.resizeColumnsToContents()
        self.schedule_table.setSortingEnabled(True)

    def display_single_result(self, result, algo_name):
        """Display single algorithm result"""
        feasible_icon = "✅" if result.feasible else "❌"
        feasible_text = "Feasible" if result.feasible else "Not Feasible"

        text = f"""
<style>
table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
th, td {{ border: 1px solid #E8E8E8; padding: 6px 8px; text-align: left; }}
th {{ background-color: #E0BBE4; font-weight: bold; }}
</style>
<h3 style="margin: 0 0 8px 0;">{algo_name} Results</h3>
<table>
<tr><th>Metric</th><th>Value</th></tr>
<tr><td><b>Cost</b></td><td>{result.cost:.2f}</td></tr>
<tr><td><b>Status</b></td><td>{feasible_icon} {feasible_text}</td></tr>
<tr><td><b>Runtime</b></td><td>{result.runtime_sec:.2f}s</td></tr>
<tr><td><b>Tasks</b></td><td>{len(result.schedule.all_assignments())}</td></tr>
</table>
"""

        if result.violations:
            text += f"<p style='margin: 5px 0; color: #D32F2F; font-size: 11px;'><b>Violations:</b> {len(result.violations)} issues found</p>"

        self.results_text.setHtml(text)

    def display_comparison_results(self):
        """Display comparison results"""
        sa_feasible = "✅" if last_result_sa.feasible else "❌"
        gwo_feasible = "✅" if last_result_gwo.feasible else "❌"

        winner = "SA" if last_result_sa.cost < last_result_gwo.cost else "GWO"
        improvement = abs((last_result_sa.cost - last_result_gwo.cost) /
                         max(last_result_sa.cost, last_result_gwo.cost) * 100)
        if last_result_sa.cost == last_result_gwo.cost:
            winner = "Tie (Equal)"
        else:
            winner = "SA" if last_result_sa.cost < last_result_gwo.cost else "GWO"
        
        max_cost = max(last_result_sa.cost, last_result_gwo.cost)
        improvement = 0.0 if max_cost == 0 else abs((last_result_sa.cost - last_result_gwo.cost) /
                         max_cost * 100)

        text = f"""
<style>
table {{ border-collapse: collapse; width: 100%; font-size: 12px; }}
th, td {{ border: 1px solid #E8E8E8; padding: 6px 8px; text-align: center; }}
th {{ background-color: #E0BBE4; font-weight: bold; }}
.winner {{ background-color: #B4E7CE; }}
</style>
<h3 style="margin: 0 0 8px 0;">Comparison Results</h3>
<table>
<tr><th>Metric</th><th>SA</th><th>GWO</th></tr>
<tr><td><b>Cost</b></td><td class="{'winner' if winner=='SA' else ''}">{last_result_sa.cost:,.2f}</td><td class="{'winner' if winner=='GWO' else ''}">{last_result_gwo.cost:,.2f}</td></tr>
<tr><td><b>Status</b></td><td>{sa_feasible}</td><td>{gwo_feasible}</td></tr>
<tr><td><b>Runtime</b></td><td>{last_result_sa.runtime_sec:.2f}s</td><td>{last_result_gwo.runtime_sec:.2f}s</td></tr>
</table>
<p style='margin: 5px 0; font-size: 12px;'><b>🏆 Winner:</b> {winner} ({improvement:.2f}% better)</p>
"""

        self.results_text.setHtml(text)

    def update_gantt_chart(self):
        """Update Gantt chart based on selection"""
        algo = self.gantt_algo_combo.currentText()

        if algo == "SA" and last_result_sa:
            tasks_dict = {t.id: t for t in current_tasks}
            self.gantt_canvas.plot_gantt(last_result_sa, tasks_dict,
                                        "Gantt Chart - Simulated Annealing")
        elif algo == "GWO" and last_result_gwo:
            tasks_dict = {t.id: t for t in current_tasks}
            self.gantt_canvas.plot_gantt(last_result_gwo, tasks_dict,
                                        "Gantt Chart - Grey Wolf Optimizer")

    def save_gantt_image(self):
        """Save Gantt chart as image"""
        if self.gantt_algo_combo.currentText() == "Select Algorithm":
             QMessageBox.warning(self, "Warning", "Please select an algorithm to display first!")
             return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Gantt Chart", "gantt_chart.png",
            "Images (*.png *.jpg *.jpeg *.pdf)"
        )

        if file_path:
            try:
                self.gantt_canvas.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", "Gantt chart saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save image: {str(e)}")

    def export_results(self):
        """Export results to CSV"""
        algo = self.gantt_algo_combo.currentText()

        if algo == "Select Algorithm":
            QMessageBox.warning(self, "Warning", "Please select an algorithm first!")
            return

        result = last_result_sa if algo == "SA" else last_result_gwo

        if not result:
            QMessageBox.warning(self, "Warning", "No results to export!")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Results", f"schedule_{algo.lower()}.csv",
            "CSV Files (*.csv)"
        )

        if file_path:
            try:
                from Output.exporter import export_schedule_csv
                tasks_dict = {t.id: t for t in current_tasks}
                resources_dict = {r.id: r for r in current_resources}

                export_schedule_csv(result, tasks_dict, resources_dict, file_path)
                QMessageBox.information(self, "Success", "Results exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")


def main():
    app = QApplication(sys.argv)

    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    window = MainWindow()
    window.showMaximized()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()